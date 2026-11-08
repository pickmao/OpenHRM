from copy import deepcopy
from datetime import date

from django.test import TestCase

from assessments.models import AssessmentRecord
from leadership_assessments.models import LeadershipAssessmentRecord

from . import tests as existing_tests
from .models import InspectionTask, FillerRole


class AssessmentCollectionTests(TestCase):
    setUp = existing_tests.KnowingPeopleApiTests.setUp
    dispatch = existing_tests.KnowingPeopleApiTests.dispatch

    def prepare(self):
        self.chief_roster.birth_date = date(1986, 11, 7)
        self.chief_roster.highest_education = '大学'
        self.chief_roster.current_position_date = date(2021, 11, 7)
        self.chief_roster.save()
        campaign = self.dispatch(['ATTACHMENT_5', 'INSPECTION_REVIEW'], recipients=[
            dict(form_type=form, user_id=str(self.middle.id), branch_id=str(self.branch.id))
            for form in ['ATTACHMENT_5', 'INSPECTION_REVIEW']
        ])
        self.url = f'/api/knowing-people/campaigns/{campaign["id"]}/assessment-collection/'
        self.client.force_authenticate(self.admin)
        linked = self.client.post(self.url, {'version_date': '2026-11-07'}, format='json')
        self.assertEqual(linked.status_code, 200)
        return campaign

    def submit_story(self, year='2025', title='联合演练'):
        task = InspectionTask.objects.get(form_type='ATTACHMENT_5')
        self.client.force_authenticate(self.middle)
        payload = self.client.get(f'/api/knowing-people/tasks/{task.id}/').data['payload']
        payload['works'] = [dict(year=year, title=title, description='完成应急预案演练', people=[
            dict(roster_id=str(self.chief_roster.id), name=self.chief_roster.name,
                 roles=['主导者'], task_and_role='组织实施并完成复盘')])]
        response = self.client.post(f'/api/knowing-people/tasks/{task.id}/submit/', {'payload': payload}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        return task, payload

    def test_submission_updates_both_final_tables_and_repeated_sync_is_idempotent(self):
        self.prepare()
        task, _ = self.submit_story()
        branch = LeadershipAssessmentRecord.objects.get(source_object_id=self.branch.id)
        cadre = AssessmentRecord.objects.get(source_object_id=self.chief_roster.id)
        self.assertIn('联合演练', branch.performance_by_year['2025'])
        self.assertIn('组织实施并完成复盘', cadre.performance_by_year['2025'])
        self.assertIn(str(task.id), branch.collection_data['source_task_ids'])
        self.client.force_authenticate(self.admin)
        count = AssessmentRecord.objects.count()
        self.assertEqual(self.client.post(self.url, {'version_date': '2026-11-07'}, format='json').status_code, 200)
        self.assertEqual(AssessmentRecord.objects.count(), count)
        self.assertEqual(LeadershipAssessmentRecord.objects.count(), 1)

    def test_return_clears_generated_text_and_resubmit_preserves_manual_text(self):
        self.prepare()
        task, payload = self.submit_story()
        self.client.force_authenticate(self.admin)
        self.client.post(f'/api/knowing-people/tasks/{task.id}/return/', {'reason': '补充工作'}, format='json')
        branch = LeadershipAssessmentRecord.objects.get(source_object_id=self.branch.id)
        self.assertEqual(branch.performance_by_year, {})
        branch.ability_assessment = '考察组已经手动修改的评语'
        branch.save()
        review = InspectionTask.objects.get(form_type='INSPECTION_REVIEW')
        self.client.force_authenticate(self.middle)
        review_payload = deepcopy(review.payload_json)
        review_payload.update(record_date='2026-11-07', interviewers='考察组', records=[
            dict(roster_id='', ability_assessment='新填报的能力评价', talk_notes='面对面谈话原文', shortcomings='需加强协调')])
        response = self.client.post(f'/api/knowing-people/tasks/{review.id}/submit/', {'payload': review_payload}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        branch.refresh_from_db()
        self.assertEqual(branch.ability_assessment, '考察组已经手动修改的评语')
        self.assertEqual(branch.shortcomings, '需加强协调')
        self.assertIn('面对面谈话原文', branch.collection_data['talk_notes'])
        self.assertIn('ability_assessment', branch.collection_data['protected_fields'])

    def test_legacy_annual_columns_and_cadre_talk_are_populated(self):
        self.prepare()
        self.submit_story(year='2024')
        cadre = AssessmentRecord.objects.get(source_object_id=self.chief_roster.id)
        self.assertIn('联合演练', cadre.performance_2024)
        self.assertEqual(cadre.performance_by_year, {})
        review = InspectionTask.objects.get(form_type='INSPECTION_REVIEW')
        payload = deepcopy(review.payload_json)
        payload.update(record_date='2026-11-07', interviewers='考察组', records=[dict(
            roster_id=str(self.chief_roster.id), talk_notes='干部谈话记录', ability_assessment='业务能力较强', shortcomings='')])
        self.client.force_authenticate(self.middle)
        self.assertEqual(self.client.post(f'/api/knowing-people/tasks/{review.id}/submit/', {'payload': payload}, format='json').status_code, 200)
        cadre.refresh_from_db()
        self.assertIn('干部谈话记录', cadre.talk_assessment)
        self.assertEqual(cadre.ability_assessment, '业务能力较强')
        self.assertIsNone(cadre.comprehensive_score)

    def test_binding_requires_management_of_collection_and_both_assessment_tables(self):
        campaign = self.dispatch(['ATTACHMENT_5'])
        url = f'/api/knowing-people/campaigns/{campaign["id"]}/assessment-collection/'
        self.client.force_authenticate(self.middle)
        self.assertEqual(self.client.post(url, {'version_date': '2026-11-07'}, format='json').status_code, 403)
        self.filler_role.permissions.append('knowing_people:campaign:manage')
        self.filler_role.save()
        self.assertEqual(self.client.post(url, {'version_date': '2026-11-07'}, format='json').status_code, 403)

    def test_counts_use_exact_anniversaries_and_explicit_membership_options(self):
        self.prepare()
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.url, {
            'version_date': '2026-11-07', 'member_ids': {str(self.branch.id): [str(self.chief_roster.id)]},
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        record = LeadershipAssessmentRecord.objects.get(source_object_id=self.branch.id)
        self.assertEqual(record.average_age, 40)
        self.assertEqual(record.undergraduate_count, 1)
        self.assertEqual(record.three_to_5_years_count, 1)
        self.assertEqual(record.over_5_years_count, 0)

    def test_new_campaign_can_enable_automatic_collection_at_dispatch(self):
        campaign = self.dispatch(['ATTACHMENT_5'], assessment_date='2026-11-07')
        self.assertIsNotNone(campaign['assessment_collection'])
        self.assertTrue(LeadershipAssessmentRecord.objects.exists())

    def test_normal_record_edit_preserves_annual_text_and_readonly_source(self):
        self.prepare()
        self.submit_story()
        cadre = AssessmentRecord.objects.get(source_object_id=self.chief_roster.id)
        self.client.force_authenticate(self.admin)
        url = f'/api/assessments/analysis-records/{cadre.id}/'
        response = self.client.patch(url, {'performance_by_year': {'2025': '考察组修改后的年度评价'},
                                         'collection_data': {}, 'source_object_id': None}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['performance_by_year']['2025'], '考察组修改后的年度评价')
        self.assertEqual(response.data['source_object_id'], str(self.chief_roster.id))
        self.assertTrue(response.data['collection_data'])
        self.client.post(self.url, {'version_date': '2026-11-07'}, format='json')
        cadre.refresh_from_db()
        self.assertEqual(cadre.performance_by_year['2025'], '考察组修改后的年度评价')
        self.assertIn('performance_by_year.2025', cadre.collection_data['protected_fields'])
        self.assertEqual(self.client.patch(url, {'performance_by_year': ['错误形状']}, format='json').status_code, 400)

    def test_second_campaign_cannot_overwrite_same_period(self):
        self.prepare()
        campaign = self.dispatch(['ATTACHMENT_5'])
        self.client.force_authenticate(self.admin)
        response = self.client.post(f'/api/knowing-people/campaigns/{campaign["id"]}/assessment-collection/',
                                    {'version_date': '2026-11-07'}, format='json')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(LeadershipAssessmentRecord.objects.count(), 1)

    def test_statistics_feed_correct_columns_and_return_removes_final_score(self):
        recipients = []
        for form, user, role in [
            ('ATTACHMENT_6_1', self.admin, FillerRole.PRISON_LEADER),
            ('ATTACHMENT_6_1', self.secretary, FillerRole.BRANCH_SECRETARY),
            ('ATTACHMENT_6_2', self.staff, FillerRole.BRANCH_STAFF),
            ('ATTACHMENT_7_1', self.admin, FillerRole.PRINCIPAL_LEADER),
            ('ATTACHMENT_7_1', self.middle, FillerRole.PRISON_LEADER),
            ('ATTACHMENT_7_1', self.secretary, FillerRole.BRANCH_SECRETARY),
            ('ATTACHMENT_7_4', self.committee, FillerRole.BRANCH_COMMITTEE),
            ('ATTACHMENT_7_4', self.staff, FillerRole.BRANCH_STAFF),
        ]:
            recipients.append(dict(form_type=form, user_id=str(user.id), filler_role=role, branch_id=str(self.branch.id)))
        campaign = self.dispatch(sorted({r['form_type'] for r in recipients}), recipients=recipients,
                                 assessment_date='2026-11-07')
        for task in InspectionTask.objects.all():
            self.client.force_authenticate(task.assignee)
            payload = self.client.get(f'/api/knowing-people/tasks/{task.id}/').data['payload']
            for target in payload.get('targets') or []:
                target['scores'] = dict.fromkeys(target['scores'], '优')
                if task.form_type == 'ATTACHMENT_7_4':
                    target['recognition'] = '认可'
            if task.form_type == 'ATTACHMENT_6_2':
                payload.update(scores=dict.fromkeys(payload['scores'], '优'), recognition='认可')
            response = self.client.post(f'/api/knowing-people/tasks/{task.id}/submit/', {'payload': payload}, format='json')
            self.assertEqual(response.status_code, 200, response.data)
        branch = LeadershipAssessmentRecord.objects.get(source_object_id=self.branch.id)
        cadre = AssessmentRecord.objects.get(source_object_id=self.chief_roster.id)
        self.assertEqual(branch.secretary_score, 19)
        self.assertEqual(branch.democratic_score, 95)
        self.assertEqual(branch.total_score, 95)
        self.assertIsNone(branch.ranking)  # 另一被评支部尚缺民警职工来源，批次排名待收齐。
        self.assertEqual(cadre.seven_looks_score, 95)
        self.assertEqual(cadre.work_recognition_score, 95)
        self.assertIsNone(cadre.comprehensive_score)
        self.assertIsNone(branch.approval_rate)
        self.client.force_authenticate(self.admin)
        self.client.post(f'/api/knowing-people/campaigns/{campaign["id"]}/assessment-collection/',
                         {'version_date': '2026-11-07', 'approval_rule': 'RECOGNIZED_AND_BASIC'}, format='json')
        branch.refresh_from_db()
        self.assertEqual(branch.approval_rate, 1)
        task = InspectionTask.objects.get(form_type='ATTACHMENT_6_2')
        self.client.post(f'/api/knowing-people/tasks/{task.id}/return/', {'reason': '核对评分'}, format='json')
        branch.refresh_from_db()
        self.assertIsNone(branch.total_score)
        self.assertIsNone(branch.ranking)
        self.assertIsNone(branch.approval_rate)
