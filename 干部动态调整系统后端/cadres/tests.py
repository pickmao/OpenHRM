from io import BytesIO

from django.test import TestCase
from openpyxl import Workbook
from rest_framework.test import APIClient
from accounts.models import User
from orgs.models import Membership, OrgUnit
from .models import PersonnelRoster


def _roster_xlsx(rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(['序号', '姓名', '部门', '性别'])
    for row in rows:
        sheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    buffer.name = 'roster.xlsx'
    return buffer


class MiddleLeadershipFilterTests(TestCase):
    def test_includes_team_leaders_and_excludes_prison_leaders_and_nonleaders(self):
        client = APIClient(); client.force_authenticate(User.objects.create(username='reader'))
        rows = [
            ('中层', '一监区', '领导职务', '监区长'),
            ('团队', '一监区', '内定领导职务', '分监区长'),
            ('普通', '一监区', '非领导职务', ''),
            ('监狱领导', '监狱领导', '领导职务', '监狱长'),
        ]
        for number, (name, department, category, position) in enumerate(rows, 1):
            PersonnelRoster.objects.create(serial_number=number, name=name, department=department, position_category=category, position=position, gender='M')
        response = client.get('/api/roster/', {'leadership_scope': 'middle'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual({row['name'] for row in response.data['results']}, {'中层', '团队'})
        self.assertEqual(client.get('/api/roster/').data['count'], 4)


class RosterReplaceUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(User.objects.create(username='admin', is_superuser=True))
        PersonnelRoster.objects.create(serial_number=1, name='旧人', department='旧部门', gender='M')

    def test_upload_replaces_existing_roster_by_default(self):
        response = self.client.post(
            '/api/roster/upload-excel/',
            {'file': _roster_xlsx([(1, '新人', '新部门', '女')])},
            format='multipart',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['mode'], 'replace')
        self.assertEqual(response.data['deleted_count'], 1)
        self.assertEqual(response.data['created_count'], 1)
        self.assertEqual(PersonnelRoster.objects.count(), 1)
        self.assertEqual(PersonnelRoster.objects.get().name, '新人')

    def test_append_upload_keeps_existing_rows(self):
        response = self.client.post(
            '/api/roster/upload-excel/',
            {'file': _roster_xlsx([(2, '新人', '新部门', '男')]), 'replace': 'false'},
            format='multipart',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['mode'], 'append')
        self.assertEqual(PersonnelRoster.objects.count(), 2)

    def test_replace_aborts_when_file_has_no_valid_rows(self):
        response = self.client.post(
            '/api/roster/upload-excel/',
            {'file': _roster_xlsx([(1, '', '', '男')])},
            format='multipart',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(PersonnelRoster.objects.count(), 1)
        self.assertEqual(PersonnelRoster.objects.get().name, '旧人')


class RosterDepartmentAlignmentTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(username='roster-admin', password='password', real_name='管理员')
        self.client.force_authenticate(self.admin)
        self.old_unit = OrgUnit.objects.create(name='一监区办公室', unit_type='DEPARTMENT')
        self.new_unit = OrgUnit.objects.create(name='二监区办公室', unit_type='DEPARTMENT')
        self.person_user = User.objects.create_user(username='zhang', password='password', real_name='张三')
        Membership.objects.create(user=self.person_user, unit=self.old_unit, is_primary=True)
        self.roster = PersonnelRoster.objects.create(
            serial_number=1, name='张三', department='一监区办公室', gender='M',
        )

    def test_updating_roster_department_moves_matching_membership(self):
        response = self.client.patch(
            f'/api/roster/{self.roster.id}/',
            {'department': '二监区办公室'},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.roster.refresh_from_db()
        self.assertEqual(self.roster.department, '二监区办公室')
        self.assertTrue(
            Membership.objects.filter(
                user=self.person_user, unit=self.new_unit, is_primary=True, effective_to__isnull=True,
            ).exists()
        )
        self.assertFalse(
            Membership.objects.filter(
                user=self.person_user, unit=self.old_unit, effective_to__isnull=True,
            ).exists()
        )

    def test_replace_upload_syncs_membership_to_new_department(self):
        response = self.client.post(
            '/api/roster/upload-excel/',
            {'file': _roster_xlsx([(1, '张三', '二监区办公室', '男')])},
            format='multipart',
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(
            Membership.objects.filter(
                user=self.person_user, unit=self.new_unit, effective_to__isnull=True,
            ).exists()
        )
