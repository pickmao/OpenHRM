from copy import deepcopy
from datetime import timedelta
from uuid import uuid4

from django.test import TestCase
from django.utils import timezone

from .form_defs import TEAM_DIMENSIONS
from .models import FormType, InspectionCampaign, InspectionTask
from . import tests as existing_tests


class TaskContractTests(TestCase):
    setUp = existing_tests.KnowingPeopleApiTests.setUp
    dispatch = existing_tests.KnowingPeopleApiTests.dispatch
    task_for = existing_tests.KnowingPeopleApiTests.task_for

    def matrix(self):
        self.dispatch([FormType.ATTACHMENT_7_1])
        task = self.task_for(self.secretary, FormType.ATTACHMENT_7_1)
        self.client.force_authenticate(self.secretary)
        payload = self.client.get(f'/api/knowing-people/tasks/{task.id}/').data['payload']
        for row in payload['targets']:
            row['scores'] = {dim['key']: '优' for dim in TEAM_DIMENSIONS}
        return task, payload

    def test_target_cannot_be_added_duplicated_or_removed(self):
        task, payload = self.matrix()
        url = f'/api/knowing-people/tasks/{task.id}/submit/'
        for rows in ([], payload['targets'] * 2, [{**payload['targets'][0], 'id': str(uuid4())}]):
            response = self.client.post(url, {'payload': {**payload, 'targets': rows}}, format='json')
            self.assertEqual(response.status_code, 400, response.data)
        renamed = deepcopy(payload)
        renamed['targets'][0]['name'] = '冒名'
        response = self.client.post(url, {'payload': renamed}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertNotEqual(response.data['payload']['targets'][0]['name'], '冒名')

    def test_invalid_json_shape_returns_400_without_saving(self):
        task, payload = self.matrix()
        for invalid in ([1], 'text', {'targets': ['bad']}, {'targets': [{**payload['targets'][0], 'scores': []}]}):
            response = self.client.post(f'/api/knowing-people/tasks/{task.id}/save-draft/', {'payload': invalid}, format='json')
            self.assertEqual(response.status_code, 400, response.data)
        task.refresh_from_db()
        self.assertEqual(task.status, 'PENDING')

    def test_admin_inspection_is_readonly_and_other_filler_cannot_read(self):
        task, _ = self.matrix()
        self.client.force_authenticate(self.admin)
        self.assertTrue(self.client.get(f'/api/knowing-people/tasks/{task.id}/').data['readonly'])
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.get(f'/api/knowing-people/tasks/{task.id}/').status_code, 404)

    def test_two_branch_representatives_rejected_atomically(self):
        self.client.force_authenticate(self.admin)
        before = InspectionCampaign.objects.count()
        response = self.client.post('/api/knowing-people/campaigns/', {
            'name': '重复支部表', 'deadline_at': (timezone.now() + timedelta(days=1)).isoformat(),
            'form_types': ['ATTACHMENT_5'],
            'recipients': [dict(form_type='ATTACHMENT_5', user_id=str(user.id), branch_id=str(self.branch.id))
                           for user in (self.secretary, self.staff)],
        }, format='json')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(InspectionCampaign.objects.count(), before)

    def test_same_representative_can_fill_one_story_per_branch(self):
        self.dispatch(['ATTACHMENT_5'], recipients=[
            dict(form_type='ATTACHMENT_5', user_id=str(self.secretary.id), branch_id=str(branch.id))
            for branch in (self.branch, self.other_branch)
        ])
        self.assertEqual(InspectionTask.objects.filter(assignee=self.secretary).count(), 2)

    def test_manual_branch_form_requires_branch(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post('/api/knowing-people/campaigns/', {
            'name': '无支部', 'deadline_at': (timezone.now() + timedelta(days=1)).isoformat(),
            'form_types': ['ATTACHMENT_7_4'],
            'recipients': [dict(form_type='ATTACHMENT_7_4', user_id=str(self.admin.id))],
        }, format='json')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(InspectionCampaign.objects.exists())

    def test_export_is_not_available_to_ordinary_filler(self):
        campaign = self.dispatch(['ATTACHMENT_2'])
        self.client.force_authenticate(self.middle)
        response = self.client.get(f'/api/knowing-people/campaigns/{campaign["id"]}/statistics-export/')
        self.assertEqual(response.status_code, 403)

    def test_invalid_recipient_id_returns_400(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post('/api/knowing-people/campaigns/', {
            'name': '无效人员', 'deadline_at': (timezone.now() + timedelta(days=1)).isoformat(),
            'form_types': ['ATTACHMENT_2'], 'recipients': [{'form_type': 'ATTACHMENT_2', 'user_id': 'not-a-uuid'}],
        }, format='json')
        self.assertEqual(response.status_code, 400)
