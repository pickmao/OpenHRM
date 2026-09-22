from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from accounts.models import User
from .models import WorkRecord


class WorkRecordTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create(username='owner')
        self.other = User.objects.create(username='other')
        self.client = APIClient()
        self.client.force_authenticate(self.owner)
        self.payload = {'title': '防汛任务', 'category': 'CHALLENGING', 'completed_on': timezone.localdate().isoformat(), 'details': '完成物资转移', 'role': '执行者', 'outcome': '按时完成'}

    def test_create_list_edit_and_search_own_record(self):
        response = self.client.post('/api/inspections/records/', {**self.payload, 'owner': str(self.other.id)}, format='json')
        self.assertEqual(response.status_code, 201)
        record = WorkRecord.objects.get(pk=response.data['id'])
        self.assertEqual(record.owner, self.owner)
        url = f'/api/inspections/records/{record.id}/'
        self.assertEqual(self.client.patch(url, {'outcome': '提前完成'}, format='json').status_code, 200)
        record.refresh_from_db(); self.assertEqual(record.outcome, '提前完成')
        result = self.client.get('/api/inspections/records/', {'search': '防汛'}).data
        self.assertEqual(result['count'], 1)

    def test_other_user_cannot_read_or_edit_record(self):
        record = WorkRecord.objects.create(owner=self.other, **self.payload)
        url = f'/api/inspections/records/{record.id}/'
        self.assertEqual(self.client.get('/api/inspections/records/').data['count'], 0)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.patch(url, {'title': '篡改'}, format='json').status_code, 404)

    def test_validation_and_authentication(self):
        for patch in [{'title': ' '}, {'details': ''}, {'category': 'INVALID'}, {'completed_on': (timezone.localdate() + timedelta(days=1)).isoformat()}]:
            self.assertEqual(self.client.post('/api/inspections/records/', {**self.payload, **patch}, format='json').status_code, 400)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/inspections/records/').status_code, 401)
