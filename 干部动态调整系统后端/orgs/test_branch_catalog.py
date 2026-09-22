from django.test import TestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from accounts.models import User
from cadres.models import PersonnelRoster
from knowing_people.matching import collect_scope
from .branch_catalog import apply_catalog, catalog_preview
from .models import OrgUnit, UnitType


class BranchCatalogTests(TestCase):
    def test_preview_read_only_and_apply_idempotent(self):
        preview = catalog_preview()
        self.assertEqual(preview['branch_count'], 27)
        self.assertEqual(preview['department_count'], 36)
        self.assertFalse(OrgUnit.objects.exists())
        first = apply_catalog()
        self.assertEqual(first['created_branches'], 27)
        self.assertEqual(first['created_departments'], 36)
        second = apply_catalog()
        self.assertEqual(second['created_branches'], 0)
        self.assertEqual(second['assigned'], 0)
        self.assertEqual(OrgUnit.objects.count(), 63)

    def test_existing_branch_alias_and_unrelated_units_preserved(self):
        prison = OrgUnit.objects.create(name='一监区', unit_type=UnitType.BRANCH)
        unit = OrgUnit.objects.create(name='一监区', unit_type=UnitType.DEPARTMENT)
        other = OrgUnit.objects.create(name='其他支部', unit_type=UnitType.BRANCH)
        extra = OrgUnit.objects.create(name='其他部门', unit_type=UnitType.DEPARTMENT, parent=other)
        apply_catalog()
        unit.refresh_from_db()
        extra.refresh_from_db()
        self.assertEqual(unit.parent_id, prison.id)
        self.assertEqual(extra.parent_id, other.id)
        self.assertFalse(OrgUnit.objects.filter(name='一监区党支部').exists())

    def test_conflict_rejects_entire_catalog(self):
        other = OrgUnit.objects.create(name='其他支部', unit_type=UnitType.BRANCH)
        office = OrgUnit.objects.create(name='办公室', unit_type=UnitType.DEPARTMENT, parent=other)
        self.assertFalse(catalog_preview()['can_apply'])
        with self.assertRaises(ValidationError):
            apply_catalog()
        self.assertEqual(OrgUnit.objects.count(), 2)
        office.refresh_from_db()
        self.assertEqual(office.parent_id, other.id)

    def test_duplicate_and_inactive_units_rejected(self):
        OrgUnit.objects.create(name='政治处', unit_type=UnitType.DEPARTMENT)
        OrgUnit.objects.create(name='政治处', unit_type=UnitType.DEPARTMENT)
        OrgUnit.objects.create(name='机关第二党支部', is_active=False)
        with self.assertRaises(ValidationError):
            apply_catalog()
        self.assertEqual(OrgUnit.objects.count(), 3)

    def test_cycle_rejected(self):
        unit = OrgUnit.objects.create(name='政治处', unit_type=UnitType.DEPARTMENT)
        OrgUnit.objects.create(name='机关第一党支部', parent=unit)
        with self.assertRaises(ValidationError):
            apply_catalog()
        self.assertEqual(OrgUnit.objects.count(), 2)

    def test_roster_department_resolves_photo_branch(self):
        apply_catalog()
        user = User.objects.create(username='photo-staff', real_name='测试民警')
        PersonnelRoster.objects.create(serial_number=1, name='测试民警', department='生活卫生科', gender='M')
        scope = collect_scope(user)
        self.assertEqual(scope['branch'].name, '机关第四党支部')

    def test_api_denies_unprivileged_write(self):
        client = APIClient()
        client.force_authenticate(User.objects.create(username='ordinary'))
        self.assertEqual(client.post('/api/org/branches/reference-catalog/').status_code, 403)
        self.assertFalse(OrgUnit.objects.exists())
        client.force_authenticate(User.objects.create(username='admin', is_superuser=True))
        self.assertEqual(client.get('/api/org/branches/reference-catalog/').status_code, 200)
        self.assertFalse(OrgUnit.objects.exists())
        self.assertEqual(client.post('/api/org/branches/reference-catalog/').status_code, 200)
