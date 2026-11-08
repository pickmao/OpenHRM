from copy import deepcopy
from uuid import uuid4

from django.test import TestCase

from . import tests as existing_tests
from .form_defs import default_payload
from .models import InspectionTask, TaskStatus


class MaterialCollectionTests(TestCase):
    setUp = existing_tests.KnowingPeopleApiTests.setUp
    dispatch = existing_tests.KnowingPeopleApiTests.dispatch

    def story_task(self):
        campaign = self.dispatch(['ATTACHMENT_5'])
        task = InspectionTask.objects.get(campaign_id=campaign['id'])
        self.client.force_authenticate(self.secretary)
        payload = self.client.get(f'/api/knowing-people/tasks/{task.id}/').data['payload']
        payload['works'] = [{
            'year': '2024', 'title': '应急演练', 'description': '完成跨部门联合演练',
            'people': [{'roster_id': str(self.chief_roster.id), 'name': '任意姓名',
                        'roles': ['主导者', '执行者'], 'task_and_role': '制定预案并组织演练'}],
        }]
        return campaign, task, payload

    def test_story_preserves_year_and_canonical_person_and_rejects_foreign_id(self):
        _, task, payload = self.story_task()
        bad = deepcopy(payload)
        bad['works'][0]['people'][0]['roster_id'] = str(uuid4())
        url = f'/api/knowing-people/tasks/{task.id}/'
        self.assertEqual(self.client.post(url + 'submit/', {'payload': bad}, format='json').status_code, 400)
        response = self.client.post(url + 'submit/', {'payload': payload}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        work = response.data['payload']['works'][0]
        self.assertEqual(work['year'], '2024')
        self.assertEqual(work['people'][0]['name'], '中层乙')
        self.assertEqual(work['people'][0]['department'], '一监区办公室')

    def test_blank_story_description_and_partial_work_cannot_be_silently_submitted(self):
        _, task, payload = self.story_task()
        for changes in ({'description': ''}, {'year': '2024/2025'}, {'title': ''}):
            bad = deepcopy(payload)
            bad['works'][0].update(changes)
            response = self.client.post(f'/api/knowing-people/tasks/{task.id}/submit/', {'payload': bad}, format='json')
            self.assertEqual(response.status_code, 400, response.data)

    def test_materials_are_scoped_submitted_and_traceable(self):
        campaign, task, payload = self.story_task()
        url = f'/api/knowing-people/campaigns/{campaign["id"]}/materials/'
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_authenticate(self.admin)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['stories'], [])
        self.assertEqual(response.data['pending_count'], 1)
        self.client.force_authenticate(self.secretary)
        self.assertEqual(self.client.post(f'/api/knowing-people/tasks/{task.id}/submit/', {'payload': payload}, format='json').status_code, 200)
        self.client.force_authenticate(self.admin)
        material = self.client.get(url).data['stories'][0]
        self.assertEqual(material['source_task_id'], str(task.id))
        self.assertEqual(material['year'], '2024')
        self.assertEqual(material['people'][0]['roster_id'], str(self.chief_roster.id))
        self.assertEqual(material['branch_id'], str(self.branch.id))
        self.client.post(f'/api/knowing-people/tasks/{task.id}/return/', {'reason': '补充事实'}, format='json')
        self.assertEqual(self.client.get(url).data['stories'], [])

    def test_review_form_collects_branch_and_person_without_matrix_grades(self):
        campaign = self.dispatch(['INSPECTION_REVIEW'], recipients=[{
            'form_type': 'INSPECTION_REVIEW', 'user_id': str(self.middle.id), 'branch_id': str(self.branch.id),
        }])
        task = InspectionTask.objects.get(campaign_id=campaign['id'])
        self.client.force_authenticate(self.middle)
        url = f'/api/knowing-people/tasks/{task.id}/'
        payload = self.client.get(url).data['payload']
        payload.update(material_year='2026', record_date='2026-11-07', interviewers='第一考察组', records=[
            {'roster_id': '', 'talk_notes': '班子谈话原文', 'ability_assessment': '统筹能力较好', 'shortcomings': '协同需要加强'},
            {'roster_id': str(self.chief_roster.id), 'talk_notes': '个人谈话原文', 'ability_assessment': '处置能力较强', 'shortcomings': ''},
        ])
        saved = self.client.post(url + 'save-draft/', {'payload': payload}, format='json')
        self.assertEqual(saved.status_code, 200, saved.data)
        submitted = self.client.post(url + 'submit/', {'payload': payload}, format='json')
        self.assertEqual(submitted.status_code, 200, submitted.data)
        loaded = self.client.get(url).data
        self.assertTrue(loaded['readonly'])
        self.assertEqual(loaded['payload']['records'][1]['name'], '中层乙')
        self.client.force_authenticate(self.admin)
        materials = self.client.get(f'/api/knowing-people/campaigns/{campaign["id"]}/materials/').data
        self.assertEqual([r['talk_notes'] for r in materials['reviews']], ['班子谈话原文', '个人谈话原文'])

    def test_roster_facts_and_legacy_story_keep_missing_year_explicit(self):
        campaign, task, _ = self.story_task()
        task.payload_json = {'branch_name': self.branch.name, 'works': [{
            'title': '历史事例', 'description': '历史内容', 'people': [
                {'name': '未关联人员', 'roles': ['协助者'], 'task_and_role': '提供支持'},
            ],
        }]}
        task.status = TaskStatus.SUBMITTED
        task.save()
        self.client.force_authenticate(self.admin)
        response = self.client.get(f'/api/knowing-people/campaigns/{campaign["id"]}/materials/')
        self.assertEqual(response.status_code, 200, response.data)
        story = response.data['stories'][0]
        self.assertEqual(story['year_source'], '批次年度')
        self.assertEqual(story['people'][0]['name'], '未关联人员')
        self.assertFalse(story['people'][0].get('roster_id'))
        facts = response.data['roster_people']
        self.assertIn(str(self.chief_roster.id), [r['id'] for r in facts])
        self.assertTrue(all('id_card' not in r and 'phone' not in r for r in facts))
        task.refresh_from_db()
        self.assertNotIn('year', task.payload_json['works'][0])

    def test_attachment4_requires_all_seven_counts_on_new_submission(self):
        campaign = self.dispatch(['ATTACHMENT_4'])
        task = InspectionTask.objects.get(campaign_id=campaign['id'])
        payload = default_payload(task.form_type, task.context_json)
        for row in payload['items']:
            row.update(grade='良', performance='符合要求')
        self.client.force_authenticate(self.secretary)
        response = self.client.post(f'/api/knowing-people/tasks/{task.id}/submit/', {'payload': payload}, format='json')
        self.assertEqual(response.status_code, 400, response.data)

    def test_review_rejects_foreign_person_and_invalid_date_without_saving(self):
        campaign = self.dispatch(['INSPECTION_REVIEW'], recipients=[{
            'form_type': 'INSPECTION_REVIEW', 'user_id': str(self.middle.id), 'branch_id': str(self.branch.id),
        }])
        task = InspectionTask.objects.get(campaign_id=campaign['id'])
        self.client.force_authenticate(self.middle)
        payload = self.client.get(f'/api/knowing-people/tasks/{task.id}/').data['payload']
        payload.update(material_year='2026', record_date='2026-11-07', interviewers='考察组')
        payload['records'] = [{'roster_id': str(uuid4()), 'talk_notes': '不属于本支部的对象'}]
        url = f'/api/knowing-people/tasks/{task.id}/submit/'
        self.assertEqual(self.client.post(url, {'payload': payload}, format='json').status_code, 400)
        payload['records'][0]['roster_id'] = ''
        payload['record_date'] = '2026-02-30'
        self.assertEqual(self.client.post(url, {'payload': payload}, format='json').status_code, 400)
        task.refresh_from_db()
        self.assertEqual(task.status, TaskStatus.PENDING)

    def test_review_can_be_dispatched_to_each_selected_branch(self):
        campaign = self.dispatch(['INSPECTION_REVIEW'], branch_ids=[str(self.branch.id), str(self.other_branch.id)],
                                 extra_user_ids_by_type={'INSPECTION_REVIEW': [str(self.admin.id)]})
        tasks = InspectionTask.objects.filter(campaign_id=campaign['id'])
        self.assertEqual(set(tasks.values_list('branch_id', flat=True)), {self.branch.id, self.other_branch.id})
        self.assertEqual(set(tasks.values_list('filler_role', flat=True)), {'INSPECTION_TALKER'})
