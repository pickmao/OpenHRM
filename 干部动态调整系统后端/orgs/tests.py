from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from openpyxl import Workbook
from rest_framework.test import APIClient

from accounts.models import User
from cadres.models import PersonnelRoster
from .models import Membership, OrgUnit


def _excel_file(rows, headers=None):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers or ['支部名称', '部门名称', '支部编码', '部门编码', '备注'])
    for row in rows:
        sheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return SimpleUploadedFile(
        'branches.xlsx',
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


class BranchAssignmentTests(TestCase):
    def test_assign_department_to_branch_and_reject_cycle(self):
        client = APIClient(); client.force_authenticate(User.objects.create(username='org-admin', is_superuser=True))
        branch = OrgUnit.objects.create(name='支部', unit_type='BRANCH')
        unit = OrgUnit.objects.create(name='部门', unit_type='DEPARTMENT')
        url = f'/api/org/units/{unit.id}/'
        self.assertEqual(client.patch(url, {'parent': str(branch.id)}, format='json').status_code, 200)
        unit.refresh_from_db(); self.assertEqual(unit.parent_id, branch.id)
        self.assertEqual(client.patch(url, {'parent': str(unit.id)}, format='json').status_code, 400)
        self.assertEqual(client.patch(f'/api/org/units/{branch.id}/', {'parent': str(unit.id)}, format='json').status_code, 400)


class BranchManageTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(username='branch-admin', is_superuser=True)
        self.client.force_authenticate(self.user)

    def test_create_branch(self):
        response = self.client.post('/api/org/branches/', {'name': '第一党支部', 'code': 'B01'}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['name'], '第一党支部')
        branch = OrgUnit.objects.get(id=response.data['id'])
        self.assertEqual(branch.unit_type, 'BRANCH')
        self.assertTrue(branch.is_active)

    def test_assign_and_remove_department(self):
        branch = OrgUnit.objects.create(name='第一党支部', unit_type='BRANCH')
        other = OrgUnit.objects.create(name='第二党支部', unit_type='BRANCH')
        department = OrgUnit.objects.create(name='办公室', unit_type='DEPARTMENT', parent=other)
        assign_url = f'/api/org/branches/{branch.id}/assign-departments/'
        response = self.client.post(assign_url, {'department_ids': [str(department.id)]}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        department.refresh_from_db()
        self.assertEqual(department.parent_id, branch.id)

        listed = self.client.get('/api/org/branches/')
        self.assertEqual(listed.status_code, 200)
        target = next(item for item in listed.data if item['id'] == str(branch.id))
        self.assertEqual(target['department_count'], 1)
        self.assertEqual(target['departments'][0]['name'], '办公室')

        remove_url = f'/api/org/branches/{branch.id}/remove-departments/'
        removed = self.client.post(remove_url, {'department_ids': [str(department.id)]}, format='json')
        self.assertEqual(removed.status_code, 200, removed.data)
        department.refresh_from_db()
        self.assertIsNone(department.parent_id)

    def test_deactivate_branch(self):
        branch = OrgUnit.objects.create(name='待停用支部', unit_type='BRANCH')
        response = self.client.patch(f'/api/org/branches/{branch.id}/', {'is_active': False}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        branch.refresh_from_db()
        self.assertFalse(branch.is_active)

    def test_upload_replace_rebuilds_assignments(self):
        first = OrgUnit.objects.create(name='第一党支部', unit_type='BRANCH', code='B01')
        second = OrgUnit.objects.create(name='第二党支部', unit_type='BRANCH', code='B02')
        office = OrgUnit.objects.create(name='办公室', unit_type='DEPARTMENT', parent=first)
        workshop = OrgUnit.objects.create(name='生产科', unit_type='DEPARTMENT', parent=first)
        extra = OrgUnit.objects.create(name='未列入部门', unit_type='DEPARTMENT', parent=second)
        team = OrgUnit.objects.create(name='突击队', unit_type='TEAM', parent=office)

        upload = _excel_file([
            ['第一党支部', '办公室', 'B01', '', ''],
            ['第二党支部', '生产科', 'B02', '', '备注'],
        ])
        response = self.client.post('/api/org/branches/upload-excel/', {'file': upload, 'replace': 'true'}, format='multipart')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['mode'], 'replace')
        office.refresh_from_db()
        workshop.refresh_from_db()
        extra.refresh_from_db()
        team.refresh_from_db()
        self.assertEqual(office.parent_id, first.id)
        self.assertEqual(workshop.parent_id, second.id)
        self.assertIsNone(extra.parent_id)
        self.assertEqual(team.parent_id, office.id)
        self.assertTrue(OrgUnit.objects.filter(id=extra.id).exists())
        self.assertEqual(OrgUnit.objects.filter(unit_type='BRANCH').count(), 2)

    def test_upload_missing_units_does_not_change_tree(self):
        branch = OrgUnit.objects.create(name='第一党支部', unit_type='BRANCH')
        department = OrgUnit.objects.create(name='办公室', unit_type='DEPARTMENT', parent=branch)
        upload = _excel_file([
            ['不存在的支部', '办公室', '', '', ''],
            ['第一党支部', '不存在的部门', '', '', ''],
        ])
        response = self.client.post('/api/org/branches/upload-excel/', {'file': upload, 'replace': 'true'}, format='multipart')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertGreaterEqual(response.data.get('error_count', 0), 2)
        errors = ' '.join(item['error'] for item in response.data.get('errors', []))
        self.assertIn('找不到支部', errors)
        self.assertIn('找不到部门', errors)
        department.refresh_from_db()
        self.assertEqual(department.parent_id, branch.id)

    def test_download_template(self):
        response = self.client.get('/api/org/branches/download-template/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('spreadsheetml', response['Content-Type'])


class MembershipTransferRosterTests(TestCase):
    def test_transfer_updates_matching_roster_department(self):
        client = APIClient()
        admin = User.objects.create_superuser(username='transfer-admin', password='password', real_name='调配员')
        client.force_authenticate(admin)
        source = OrgUnit.objects.create(name='一监区办公室', unit_type='DEPARTMENT')
        target = OrgUnit.objects.create(name='二监区办公室', unit_type='DEPARTMENT')
        person = User.objects.create_user(username='li', password='password', real_name='李四')
        Membership.objects.create(user=person, unit=source, is_primary=True)
        roster = PersonnelRoster.objects.create(serial_number=1, name='李四', department='一监区办公室', gender='M')

        response = client.post('/api/org/memberships/transfer/', {
            'members': [str(person.id)],
            'from_dept': str(source.id),
            'to_dept': str(target.id),
            'reason': '工作需要',
            'effective_date': '2026-09-18',
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['success'], 1)
        roster.refresh_from_db()
        self.assertEqual(roster.department, '二监区办公室')
        self.assertTrue(
            Membership.objects.filter(user=person, unit=target, effective_to__isnull=True).exists()
        )
