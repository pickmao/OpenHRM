from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Role, User, UserRole
from cadres.models import PersonnelRoster
from orgs.models import Membership, OrgUnit

from .models import RecommendationNomination, RecommendationTask


def error_text(payload):
    if payload is None:
        return ''
    if isinstance(payload, str):
        return payload
    if isinstance(payload, list):
        return ' '.join(error_text(item) for item in payload)
    if isinstance(payload, dict):
        return ' '.join(error_text(value) for value in payload.values())
    return str(payload)


class CadreRecommendationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(username='rec_admin', password='password', real_name='推荐管理员')
        self.branch = OrgUnit.objects.create(name='一监区党支部', unit_type='BRANCH')
        self.office = OrgUnit.objects.create(name='一监区办公室', unit_type='DEPARTMENT', parent=self.branch)
        self.other_branch = OrgUnit.objects.create(name='二监区党支部', unit_type='BRANCH')
        self.other_office = OrgUnit.objects.create(name='二监区办公室', unit_type='DEPARTMENT', parent=self.other_branch)
        self.orphan = OrgUnit.objects.create(name='独立科室', unit_type='DEPARTMENT')

        self.filler_role = Role.objects.create(
            code='REC_FILLER', name='推荐填报人',
            permissions=['cadre_recommendations:task:view', 'cadre_recommendations:task:submit'],
        )
        self.viewer_role = Role.objects.create(
            code='REC_VIEWER', name='推荐统计员',
            permissions=['cadre_recommendations:result:view'],
        )
        self.filler = User.objects.create_user(username='filler', password='password', real_name='填报人甲')
        self.other_filler = User.objects.create_user(username='filler2', password='password', real_name='填报人乙')
        self.orphan_filler = User.objects.create_user(username='orphan', password='password', real_name='科室填报人')
        self.viewer = User.objects.create_user(username='viewer', password='password', real_name='统计员')
        UserRole.objects.create(user=self.filler, role=self.filler_role)
        UserRole.objects.create(user=self.other_filler, role=self.filler_role)
        UserRole.objects.create(user=self.orphan_filler, role=self.filler_role)
        UserRole.objects.create(user=self.viewer, role=self.viewer_role)
        Membership.objects.create(user=self.filler, unit=self.office, is_primary=True)
        Membership.objects.create(user=self.other_filler, unit=self.office, is_primary=True)
        Membership.objects.create(user=self.orphan_filler, unit=self.orphan, is_primary=True)

        self.chief = PersonnelRoster.objects.create(
            serial_number=1, name='张正科', department='一监区办公室', gender='M',
            position='监区长', position_rank='正科级', position_category='领导职务',
        )
        self.deputy = PersonnelRoster.objects.create(
            serial_number=2, name='李副科', department='一监区办公室', gender='M',
            position='副监区长', position_rank='副科级', position_category='领导职务',
        )
        self.team_lead = PersonnelRoster.objects.create(
            serial_number=3, name='王团队', department='一监区办公室', gender='M',
            position='工作团队负责人', position_category='监区工作团队正职',
        )
        self.officer = PersonnelRoster.objects.create(
            serial_number=4, name='赵警员', department='一监区办公室', gender='M',
            position='警员', police_rank='一级警员', position_category='警员职务',
        )
        self.outsider = PersonnelRoster.objects.create(
            serial_number=5, name='钱外人', department='二监区办公室', gender='M',
            position='监区长', position_rank='正科级', position_category='领导职务',
        )
        self.self_person = PersonnelRoster.objects.create(
            serial_number=6, name='填报人甲', department='一监区办公室', gender='M',
            position='警员', police_rank='二级警员', position_category='警员职务',
        )
        self.orphan_person = PersonnelRoster.objects.create(
            serial_number=7, name='孙科室', department='独立科室', gender='M',
            position='科员', police_rank='一级警员',
        )

    def dispatch(self, **overrides):
        payload = {
            'name': '2026年优秀干部推荐',
            'deadline_at': (timezone.now() + timedelta(days=3)).isoformat(),
            'allow_self_recommend': False,
            'slot_config': {
                'section_chief': 1,
                'deputy_section_chief': 1,
                'team_lead': 1,
                'deputy_team_lead': 1,
                'police_officer': 2,
            },
            'receiver_type': 'USER',
            'receiver_expr_json': {'user_ids': [str(self.filler.id), str(self.other_filler.id)]},
        }
        payload.update(overrides)
        self.client.force_authenticate(self.admin)
        response = self.client.post('/api/recommendations/campaigns/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return response.data

    def task_for(self, user):
        return RecommendationTask.objects.get(assignee=user)

    def submit(self, user, nominations, recommender_category='BRANCH_STAFF'):
        self.client.force_authenticate(user)
        task = self.task_for(user)
        response = self.client.post(
            f'/api/recommendations/tasks/{task.id}/submit/',
            {'recommender_category': recommender_category, 'nominations': nominations},
            format='json',
        )
        return response

    def test_dispatch_creates_tasks_and_filters_candidates_by_branch(self):
        campaign = self.dispatch()
        self.assertEqual(campaign['progress']['total'], 2)
        self.assertEqual(RecommendationTask.objects.count(), 2)

        self.client.force_authenticate(self.filler)
        task = self.task_for(self.filler)
        detail = self.client.get(f'/api/recommendations/tasks/{task.id}/')
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(detail.data['candidates']['scope_label'], '一监区党支部')
        names = {
            person['name']
            for category in detail.data['candidates']['post_categories']
            for person in category['candidates']
        }
        self.assertIn('张正科', names)
        self.assertIn('赵警员', names)
        self.assertNotIn('钱外人', names)
        self.assertNotIn('填报人甲', names)

        chief_category = next(item for item in detail.data['candidates']['post_categories'] if item['key'] == 'section_chief')
        self.assertTrue(chief_category['position_filtered'])
        self.assertEqual([item['name'] for item in chief_category['candidates']], ['张正科'])

    def test_candidates_fallback_to_department_when_branch_missing(self):
        self.dispatch(receiver_expr_json={'user_ids': [str(self.orphan_filler.id)]})
        self.client.force_authenticate(self.orphan_filler)
        task = self.task_for(self.orphan_filler)
        detail = self.client.get(f'/api/recommendations/tasks/{task.id}/')
        names = {
            person['name']
            for category in detail.data['candidates']['post_categories']
            for person in category['candidates']
        }
        self.assertEqual(detail.data['candidates']['fallback'], 'department')
        self.assertIn('孙科室', names)
        self.assertNotIn('张正科', names)

    def test_slot_limit_and_duplicate_person_are_rejected(self):
        self.dispatch()
        too_many = self.submit(self.filler, [
            {'post_category': 'section_chief', 'slot_index': 1, 'roster_id': str(self.chief.id)},
        ])
        self.assertEqual(too_many.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('最多推荐', error_text(too_many.data))

        duplicate = self.submit(self.filler, [
            {'post_category': 'section_chief', 'slot_index': 0, 'roster_id': str(self.chief.id)},
            {'post_category': 'police_officer', 'slot_index': 0, 'roster_id': str(self.chief.id)},
        ])
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('不能在同一张表的多个岗位重复推荐', error_text(duplicate.data))

        outsider = self.submit(self.filler, [
            {'post_category': 'section_chief', 'slot_index': 0, 'roster_id': str(self.outsider.id)},
        ])
        self.assertEqual(outsider.status_code, status.HTTP_400_BAD_REQUEST)

    def test_self_recommend_default_and_override(self):
        self.dispatch()
        denied = self.submit(self.filler, [
            {'post_category': 'police_officer', 'slot_index': 0, 'roster_id': str(self.self_person.id)},
        ])
        self.assertEqual(denied.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('不允许推荐本人', error_text(denied.data))

        RecommendationTask.objects.all().delete()
        RecommendationNomination.objects.all().delete()
        self.dispatch(name='允许本人推荐', allow_self_recommend=True, receiver_expr_json={'user_ids': [str(self.filler.id)]})
        allowed = self.submit(self.filler, [
            {'post_category': 'police_officer', 'slot_index': 0, 'roster_id': str(self.self_person.id)},
        ])
        self.assertEqual(allowed.status_code, status.HTTP_200_OK, allowed.data)
        self.assertEqual(allowed.data['status'], 'SUBMITTED')

    def test_statistics_group_by_branch_and_count_votes(self):
        campaign = self.dispatch()
        first = self.submit(self.filler, [
            {'post_category': 'section_chief', 'slot_index': 0, 'roster_id': str(self.chief.id)},
            {'post_category': 'police_officer', 'slot_index': 0, 'roster_id': str(self.officer.id)},
        ], recommender_category='BRANCH_SECRETARY')
        self.assertEqual(first.status_code, status.HTTP_200_OK, first.data)
        second = self.submit(self.other_filler, [
            {'post_category': 'section_chief', 'slot_index': 0, 'roster_id': str(self.chief.id)},
            {'post_category': 'deputy_section_chief', 'slot_index': 0, 'roster_id': str(self.deputy.id)},
        ], recommender_category='BRANCH_COMMITTEE')
        self.assertEqual(second.status_code, status.HTTP_200_OK, second.data)

        self.client.force_authenticate(self.admin)
        stats = self.client.get(f"/api/recommendations/campaigns/{campaign['id']}/stats/")
        self.assertEqual(stats.status_code, status.HTTP_200_OK)
        self.assertEqual(stats.data['columns'], ['人员类别', '姓名', '职务职级', '统计人次', '推荐票数'])
        self.assertEqual(stats.data['submitted_count'], 2)
        self.assertEqual(len(stats.data['branches']), 1)
        branch = stats.data['branches'][0]
        self.assertEqual(branch['branch_name'], '一监区党支部')
        self.assertTrue(branch['title'].endswith('优秀干部统计表'))
        chief_row = next(row for row in branch['rows'] if row['name'] == '张正科')
        self.assertEqual(chief_row['post_category_label'], '正科级领导干部')
        self.assertEqual(chief_row['vote_count'], 2)
        self.assertEqual(chief_row['person_count'], 2)
        self.assertIn('正科', chief_row['position_label'])
        self.assertEqual(chief_row['department'], '一监区办公室')

        self.chief.department = '二监区办公室'
        self.chief.save(update_fields=['department', 'updated_at'])
        stats_after = self.client.get(f"/api/recommendations/campaigns/{campaign['id']}/stats/")
        chief_row_after = next(row for row in stats_after.data['branches'][0]['rows'] if row['name'] == '张正科')
        self.assertEqual(chief_row_after['department'], '二监区办公室')
        self.assertEqual(chief_row_after['vote_count'], 2)

        export = self.client.get(f"/api/recommendations/campaigns/{campaign['id']}/stats/export/")
        self.assertEqual(export.status_code, status.HTTP_200_OK)
        self.assertIn('spreadsheetml', export['Content-Type'])

    def test_permissions_are_separated(self):
        campaign = self.dispatch()
        self.client.force_authenticate(self.filler)
        forbidden_stats = self.client.get(f"/api/recommendations/campaigns/{campaign['id']}/stats/")
        self.assertEqual(forbidden_stats.status_code, status.HTTP_403_FORBIDDEN)
        forbidden_create = self.client.post('/api/recommendations/campaigns/', {
            'name': '越权下发',
            'deadline_at': (timezone.now() + timedelta(days=1)).isoformat(),
            'receiver_type': 'USER',
            'receiver_expr_json': {'user_ids': [str(self.filler.id)]},
        }, format='json')
        self.assertEqual(forbidden_create.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.viewer)
        allowed_stats = self.client.get(f"/api/recommendations/campaigns/{campaign['id']}/stats/")
        self.assertEqual(allowed_stats.status_code, status.HTTP_200_OK)
        my_tasks = self.client.get('/api/recommendations/tasks/my/')
        self.assertEqual(my_tasks.status_code, status.HTTP_403_FORBIDDEN)

    def test_org_unit_dispatch_expands_members(self):
        self.client.force_authenticate(self.admin)
        preview = self.client.post('/api/recommendations/campaigns/preview/', {
            'name': '按支部下发',
            'deadline_at': (timezone.now() + timedelta(days=2)).isoformat(),
            'receiver_type': 'ORG_UNIT',
            'receiver_expr_json': {'org_unit_ids': [str(self.branch.id)]},
        }, format='json')
        self.assertEqual(preview.status_code, status.HTTP_200_OK, preview.data)
        names = {item['assignee_name'] for item in preview.data['tasks']}
        self.assertIn('填报人甲', names)
        self.assertIn('填报人乙', names)
        self.assertNotIn('科室填报人', names)
