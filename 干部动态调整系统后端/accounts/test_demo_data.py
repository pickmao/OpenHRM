from tempfile import TemporaryDirectory

from django.apps import apps
from django.db import connection
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .demo_data import seed_all
from .models import DataScope, Role, User, UserRole


class DemoDataTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.media = TemporaryDirectory()
        cls.settings_override = override_settings(MEDIA_ROOT=cls.media.name)
        cls.settings_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.settings_override.disable()
        cls.media.cleanup()

    @classmethod
    def setUpTestData(cls):
        cls.original = User.objects.create_user(username='existing-account', real_name='已有测试账号')
        cls.seed_result = seed_all('Demo-test-only-2026')
        cls.admin = User.objects.get(username='demo_admin')

    def test_rerun_is_idempotent_and_keeps_existing_data_and_password(self):
        models = [m for m in apps.get_models() if m._meta.app_label not in {'sessions', 'contenttypes'}]
        before = {m._meta.label: m.objects.count() for m in models}
        user = User.objects.get(username='demo01')
        user.set_password('Changed-by-test-2026')
        user.save(update_fields=['password'])
        seed_all('Should-not-reset-2026')
        self.assertEqual(before, {m._meta.label: m.objects.count() for m in models})
        user.refresh_from_db()
        self.assertTrue(user.check_password('Changed-by-test-2026'))
        self.original.refresh_from_db()
        self.assertEqual(self.original.real_name, '已有测试账号')

    def test_admin_columns_and_personal_tasks_are_readable(self):
        client = APIClient()
        client.force_authenticate(self.admin)
        urls = [
            '/api/org/branches/', '/api/org/units/', '/api/org/memberships/transfer-history/',
            '/api/admin/roles/', '/api/admin/users/', '/api/roster/',
            '/api/forms/templates/', '/api/forms/dispatch/', '/api/forms/tasks/my/',
            '/api/knowing-people/campaigns/', '/api/knowing-people/tasks/my/',
            '/api/evaluations/campaigns/', '/api/evaluations/tasks/my/',
            '/api/recommendations/campaigns/', '/api/recommendations/tasks/my/',
            '/api/assessments/analysis-files/', '/api/assessments/analysis-records/',
            '/api/leadership-assessments/files/', '/api/leadership-assessments/records/',
            '/api/rewards/reward-files/', '/api/rewards/reward-records/', '/api/inspections/records/',
        ]
        for url in urls:
            with self.subTest(url=url):
                response = client.get(url)
                self.assertEqual(response.status_code, 200, getattr(response, 'data', None))
                self.assertTrue(response.data, url)
        client.force_authenticate(User.objects.get(username='demo01'))
        urls = ['/api/knowing-people/tasks/my/', '/api/evaluations/tasks/my/',
                '/api/recommendations/tasks/my/', '/api/inspections/records/']
        # Legacy forms permissions use PostgreSQL JSON contains; verify that
        # endpoint for ordinary users in the PostgreSQL smoke check instead.
        if connection.features.supports_json_field_contains:
            urls.append('/api/forms/tasks/my/')
        for url in urls:
            with self.subTest(user='demo01', url=url):
                response = client.get(url)
                self.assertEqual(response.status_code, 200, response.data)
                self.assertTrue(response.data)

    def test_closed_campaign_results_have_scores(self):
        from knowing_people.models import InspectionCampaign
        from knowing_people.services import build_statistics
        from anonymous_evaluations.models import EvaluationCampaign
        from anonymous_evaluations.services import build_results
        campaign = InspectionCampaign.objects.get(status='CLOSED')
        for section in build_statistics(campaign)['report_sections']:
            if section['key'] == 'unclassified':
                self.assertFalse(section['rows'])
                continue
            self.assertTrue(section['rows'], section['key'])
            self.assertTrue(all(row['final_score'] is not None for row in section['rows']), section['key'])
        results = build_results(EvaluationCampaign.objects.get(status='CLOSED'))
        self.assertEqual(len(results), 3)
        self.assertTrue(all(row['available'] and row['overall_score'] is not None for row in results))

    def test_transfer_history_requires_permission_and_both_departments_in_scope(self):
        from orgs.models import OrgUnit
        user = User.objects.get(username='demo01')
        client = APIClient()
        client.force_authenticate(user)
        url = '/api/org/memberships/transfer-history/'
        self.assertEqual(client.get(url).status_code, 403)
        role = Role.objects.create(code='HISTORY_TEST', name='测试历史查看', permissions=['orgs:membership:transfer'])
        UserRole.objects.create(user=user, role=role)
        scope = DataScope.objects.get(user=user)
        scope.scope_type = 'ORG_UNIT'
        scope.save()
        target = OrgUnit.objects.get(code='DEMO-D1')
        source = OrgUnit.objects.get(code='DEMO-D2')
        scope.org_units.add(target)
        self.assertEqual(client.get(url).data['count'], 0)
        scope.org_units.add(source)
        result = client.get(url)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data['count'], 1)
        self.assertEqual(result.data['results'][0]['person_name'], '演示人员02')
