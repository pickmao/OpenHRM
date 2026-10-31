from datetime import date, timedelta
from io import BytesIO
from unittest.mock import patch
import json

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import DataScope, Role, ScopeType, User, UserRole
from assessments.models import AssessmentFile, AssessmentRecord
from anonymous_evaluations.models import EvaluationCampaign, EvaluationResponse, EvaluationTarget
from cadre_recommendations.models import RecommendationCampaign, RecommendationNomination, RecommendationTask
from knowing_people.models import FormType, InspectionCampaign, InspectionTask, TaskStatus
from orgs.models import Membership, OrgUnit

from .models import PersonnelRoster


class OverallReviewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(username='review_admin', password='secret', real_name='管理员')
        self.viewer = User.objects.create_user(username='review_viewer', password='secret', real_name='阅览员')
        role = Role.objects.create(code='REVIEW_VIEW', name='查阅', permissions=['cadres:overall_review:view'])
        UserRole.objects.create(user=self.viewer, role=role)
        DataScope.objects.create(user=self.viewer, scope_type=ScopeType.ALL)
        self.a = PersonnelRoster.objects.create(serial_number=1, name='同名甲', department='一监区',
                                                 gender='M', position='监区长')
        self.b = PersonnelRoster.objects.create(serial_number=2, name='同名甲', department='二监区',
                                                 gender='F', position='副监区长')
        self.unit = OrgUnit.objects.create(name='一监区', unit_type='DEPARTMENT')
        self.employee = User.objects.create_user(username='employee_a', password='secret', real_name='同名甲')
        Membership.objects.create(user=self.employee, unit=self.unit, is_primary=True)
        self.campaign_old = self._campaign('旧版')
        self.campaign_new = self._campaign('新版')

    def _campaign(self, name):
        return InspectionCampaign.objects.create(name=name, year='2026',
            deadline_at=timezone.now() + timedelta(days=1), created_by=self.admin)

    def _self_task(self, campaign, text):
        return InspectionTask.objects.create(
            campaign=campaign, form_type=FormType.ATTACHMENT_2, assignee=self.employee,
            roster=self.a, status=TaskStatus.SUBMITTED, assignee_name_snapshot='同名甲',
            submitted_at=timezone.now() + (timedelta(hours=1) if text == '新整改' else timedelta()),
            payload_json={'rectification': text, 'id_card': 'secret'},
        )

    def test_name_search_keeps_people_separate_and_scope_is_enforced(self):
        self.client.force_authenticate(self.viewer)
        result = self.client.get('/api/overall-reviews/search/', {'name': '同名甲'})
        self.assertEqual(result.status_code, 200)
        self.assertEqual({row['id'] for row in result.data['results']}, {str(self.a.pk), str(self.b.pk)})
        self.viewer.data_scope.scope_type = ScopeType.ORG_UNIT
        self.viewer.data_scope.save(update_fields=['scope_type'])
        self.viewer.data_scope.org_units.add(self.unit)
        result = self.client.get('/api/overall-reviews/search/', {'name': '同名甲'})
        self.assertEqual([row['id'] for row in result.data['results']], [str(self.a.pk)])
        self.assertEqual(self.client.get(f'/api/overall-reviews/{self.b.pk}/').status_code, 404)

    def test_latest_annual_form_and_exact_department_assessment(self):
        self._self_task(self.campaign_old, '旧整改')
        self._self_task(self.campaign_new, '新整改')
        file = AssessmentFile.objects.create(version_date=date(2026, 3, 1), file_name='测试研判')
        AssessmentRecord.objects.create(file=file, name='同名甲', department='一监区',
                                        position='监区长', position_category='PRISON_WARDEN',
                                        main_performance='甲的工作')
        AssessmentRecord.objects.create(file=file, name='同名甲', department='二监区',
                                        position='副监区长', position_category='DEPUTY_PRISON',
                                        main_performance='乙的工作')
        self.client.force_authenticate(self.admin)
        snapshot = self.client.get(f'/api/overall-reviews/{self.a.pk}/')
        self.assertEqual(snapshot.status_code, 200, snapshot.data)
        self.assertEqual(len(snapshot.data['sections']['self_forms']), 1)
        self.assertEqual(snapshot.data['sections']['self_forms'][0]['内容']['rectification'], '新整改')
        self.assertNotIn('id_card', snapshot.data['sections']['self_forms'][0]['内容'])
        self.assertEqual(len(snapshot.data['sections']['assessments']), 1)
        self.assertEqual(snapshot.data['sections']['assessments'][0]['工作成效'], '甲的工作')
        self.assertFalse(snapshot.data['sections']['rewards'])

    def test_two_positions_in_one_year_are_not_collapsed(self):
        first = self._self_task(self.campaign_old, '第一岗位')
        second = self._self_task(self.campaign_new, '第二岗位')
        first.payload_json = {**first.payload_json, 'position_rank': '监区长'}
        second.payload_json = {**second.payload_json, 'position_rank': '副监区长'}
        first.save(update_fields=['payload_json'])
        second.save(update_fields=['payload_json'])
        self.client.force_authenticate(self.admin)
        rows = self.client.get(f'/api/overall-reviews/{self.a.pk}/').data['sections']['self_forms']
        self.assertEqual({row['当时职务'] for row in rows}, {'监区长', '副监区长'})

    def test_generation_requires_manage_permission_and_fresh_confirmation(self):
        self.client.force_authenticate(self.viewer)
        snapshot = self.client.get(f'/api/overall-reviews/{self.a.pk}/').data
        endpoint = f'/api/overall-reviews/{self.a.pk}/generate/'
        self.assertEqual(self.client.post(endpoint, {'digest': snapshot['digest'],
            'confirm_external_transfer': True}, format='json').status_code, 403)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post(endpoint, {'digest': snapshot['digest']}, format='json').status_code, 400)
        self.assertEqual(self.client.post(endpoint, {'digest': 'old',
            'confirm_external_transfer': True}, format='json').status_code, 409)
        with patch.dict('os.environ', {'DASHSCOPE_API_KEY': ''}):
            response = self.client.post(endpoint, {'digest': snapshot['digest'],
                'confirm_external_transfer': True}, format='json')
        self.assertEqual(response.status_code, 503)

    def test_only_closed_aggregate_results_enter_snapshot(self):
        campaign = EvaluationCampaign.objects.create(
            name='匿名测评', status='CLOSED', deadline_at=timezone.now(),
            closed_at=timezone.now(), min_valid_responses=2,
        )
        target = EvaluationTarget.objects.create(
            campaign=campaign, user=self.employee, target_name_snapshot='同名甲',
            org_name_snapshot='一监区',
        )
        EvaluationResponse.objects.create(campaign=campaign, target=target,
            scores_json={'performance': 4}, comment='只给汇总')
        self.client.force_authenticate(self.admin)
        endpoint = f'/api/overall-reviews/{self.a.pk}/'
        hidden = self.client.get(endpoint).data
        self.assertFalse(hidden['sections']['anonymous_evaluations'])
        EvaluationResponse.objects.create(campaign=campaign, target=target,
            scores_json={'performance': 5}, comment='个人意见')
        visible = self.client.get(endpoint).data
        self.assertEqual(visible['sections']['anonymous_evaluations'][0]['有效样本数'], 2)
        self.assertNotIn('个人意见', json.dumps(visible, ensure_ascii=False))

        recommendation = RecommendationCampaign.objects.create(
            name='优秀推荐', status='CLOSED', deadline_at=timezone.now(), closed_at=timezone.now(),
        )
        task = RecommendationTask.objects.create(
            campaign=recommendation, assignee=self.admin, status='SUBMITTED',
            assignee_name_snapshot='管理员', submitted_at=timezone.now(),
        )
        RecommendationNomination.objects.create(
            task=task, roster=self.a, post_category='section_chief', slot_index=0,
            name_snapshot='同名甲', department_snapshot='一监区', position_snapshot='监区长',
        )
        result = self.client.get(endpoint).data
        self.assertEqual(result['sections']['recommendations'][0]['推荐次数'], 1)

    def test_confirmed_generation_transmits_only_previewed_person(self):
        self._self_task(self.campaign_new, '新整改')
        self.client.force_authenticate(self.admin)
        preview = self.client.get(f'/api/overall-reviews/{self.a.pk}/').data
        endpoint = f'/api/overall-reviews/{self.a.pk}/generate/'
        with patch.dict('os.environ', {'DASHSCOPE_API_KEY': 'test-key'}), patch(
            'cadres.overall_review_views.urllib.request.urlopen', return_value=BytesIO(
                json.dumps({'choices': [{'message': {'content': '待核实的草稿'}}]}).encode('utf-8')
            )
        ) as outgoing:
            result = self.client.post(endpoint, {'digest': preview['digest'],
                'confirm_external_transfer': True}, format='json')
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data['draft'], '待核实的草稿')
        body = outgoing.call_args.args[0].data.decode('utf-8')
        self.assertIn('新整改', body)
        self.assertNotIn('secret', body)
        self.assertNotIn(str(self.b.pk), body)

    def test_qwen_timeout_returns_service_error(self):
        self.client.force_authenticate(self.admin)
        preview = self.client.get(f'/api/overall-reviews/{self.a.pk}/').data
        endpoint = f'/api/overall-reviews/{self.a.pk}/generate/'
        with patch.dict('os.environ', {'DASHSCOPE_API_KEY': 'test-key'}), patch(
            'cadres.overall_review_views.urllib.request.urlopen', side_effect=TimeoutError()
        ):
            response = self.client.post(endpoint, {'digest': preview['digest'],
                'confirm_external_transfer': True}, format='json')
        self.assertEqual(response.status_code, 502)
