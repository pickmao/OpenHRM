from datetime import timedelta
from io import BytesIO
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from openpyxl import Workbook
from rest_framework.test import APIClient

from accounts.models import User
from cadre_recommendations.models import (
    RecommendationCampaign, RecommendationNomination, RecommendationTask,
)
from cadres.models import PersonnelRoster


def excel(rows):
    book = Workbook()
    sheet = book.active
    sheet.append(['姓名', '部门', '性别', '警号', '身份证号'])
    for row in rows:
        sheet.append(row)
    result = BytesIO()
    book.save(result)
    result.seek(0)
    result.name = 'history-replace.xlsx'
    return result


class RosterHistoryReplacementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='history-admin', is_superuser=True)
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.old = PersonnelRoster.objects.create(
            serial_number=1, name='原人员', department='原部门', gender='M',
            police_number='900001', id_card='110101199001010015',
        )
        campaign = RecommendationCampaign.objects.create(
            name='历史推荐', deadline_at=timezone.now() + timedelta(days=1),
        )
        task = RecommendationTask.objects.create(
            campaign=campaign, assignee=self.user, assignee_name_snapshot='管理员',
        )
        self.nomination = RecommendationNomination.objects.create(
            task=task, roster=self.old, post_category='police_officer', slot_index=0,
            name_snapshot='原人员', department_snapshot='原部门', position_snapshot='民警',
        )

    def upload(self, rows):
        return self.client.post('/api/roster/upload-excel/', {'file': excel(rows)}, format='multipart')

    def test_replacing_linked_person_preserves_history_and_hides_old_from_current_list(self):
        response = self.upload([['新人', '新部门', '女', '900002', '']])
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(list(PersonnelRoster.objects.values_list('name', flat=True)), ['新人'])
        self.nomination.refresh_from_db()
        self.assertEqual(self.nomination.roster_id, self.old.pk)
        self.assertEqual(self.nomination.roster.name, '原人员')
        self.assertEqual(self.nomination.name_snapshot, '原人员')
        self.assertFalse(PersonnelRoster.all_objects.get(pk=self.old.pk).is_active)
        self.assertEqual(self.client.get('/api/roster/').data['count'], 1)
        self.assertEqual(self.client.get('/api/roster/statistics/').data['total'], 1)
        self.assertEqual(self.client.get(f'/api/roster/{self.old.pk}/').status_code, 404)

    def test_reimport_same_identifiers_updates_existing_id(self):
        response = self.upload([['原人员', '调入部门', '男', '900001', '110101199001010015']])
        self.assertEqual(response.status_code, 201, response.data)
        person = PersonnelRoster.objects.get()
        self.assertEqual(person.pk, self.old.pk)
        self.assertEqual(person.department, '调入部门')
        self.assertEqual(response.data['updated_count'], 1)
        self.nomination.refresh_from_db()
        self.assertEqual(self.nomination.roster_id, person.pk)
        self.assertEqual(self.nomination.department_snapshot, '原部门')

    def test_returning_archived_identifier_restores_same_id(self):
        first = self.upload([['新人', '新部门', '女', '900002', '']])
        self.assertEqual(first.status_code, 201, first.data)
        second = self.upload([['原人员', '返岗部门', '男', '900001', '110101199001010015']])
        self.assertEqual(second.status_code, 201, second.data)
        self.assertEqual(PersonnelRoster.objects.get().pk, self.old.pk)
        self.assertEqual(RecommendationNomination.objects.get().roster_id, self.old.pk)

    def test_conflicting_identifiers_do_not_change_existing_roster(self):
        other = PersonnelRoster.objects.create(
            serial_number=2, name='另一人', department='另一部门', gender='F',
            police_number='900002', id_card='110101199002020020',
        )
        response = self.upload([['冲突人员', '新部门', '男', other.police_number, self.old.id_card]])
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(PersonnelRoster.objects.count(), 2)
        self.old.refresh_from_db()
        self.assertEqual(self.old.name, '原人员')

    def test_one_invalid_row_aborts_whole_replacement(self):
        response = self.upload([['有效新人', '新部门', '男', '900003', ''], ['', '新部门', '男', '', '']])
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(PersonnelRoster.objects.get().pk, self.old.pk)
        self.assertEqual(RecommendationNomination.objects.count(), 1)

    def test_sync_failure_rolls_back_replacement(self):
        with patch('cadres.org_alignment.sync_memberships_from_rosters', side_effect=RuntimeError('forced sync failure')):
            response = self.upload([['新人', '新部门', '女', '900002', '']])
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(PersonnelRoster.objects.get().pk, self.old.pk)
        self.assertEqual(RecommendationNomination.objects.count(), 1)

    def test_same_name_without_identifiers_keeps_id_when_unambiguous(self):
        anonymous = PersonnelRoster.objects.create(serial_number=2, name='无编号人员', department='原部门', gender='M')
        response = self.upload([['无编号人员', '原部门', '男', '', '']])
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(PersonnelRoster.objects.get().pk, anonymous.pk)

    def test_database_error_is_not_exposed_to_user(self):
        with patch('cadres.org_alignment.sync_memberships_from_rosters', side_effect=RuntimeError('internal database detail')):
            response = self.upload([['新人', '新部门', '女', '900002', '']])
        self.assertEqual(response.status_code, 400, response.data)
        self.assertNotIn('internal database detail', response.data['error'])

    def test_manual_create_cannot_reuse_archived_unique_identity(self):
        response = self.upload([['新人', '新部门', '女', '900002', '']])
        self.assertEqual(response.status_code, 201, response.data)
        response = self.client.post('/api/roster/', {
            'serial_number': 3, 'name': '重复身份', 'department': '新部门',
            'gender': 'M', 'police_number': self.old.police_number,
        }, format='json')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(PersonnelRoster.objects.count(), 1)


