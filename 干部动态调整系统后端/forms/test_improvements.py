from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Role, User, UserRole
from cadres.models import PersonnelRoster
from orgs.models import Membership, OrgUnit
from .dashboard_service import FormDashboardService
from .models import DispatchBatch, FormTask, FormTemplate
from .services import preview_dispatch, publish_dispatch


class DispatchImprovementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create(username='admin', is_superuser=True)
        self.user = User.objects.create(username='one', real_name='测试人员')
        self.other = User.objects.create(username='two')
        self.branch = OrgUnit.objects.create(name='测试支部', unit_type='BRANCH')
        self.unit = OrgUnit.objects.create(name='测试部门', unit_type='DEPARTMENT', parent=self.branch)
        Membership.objects.create(user=self.user, unit=self.unit, is_primary=True)
        self.template = FormTemplate.objects.create(code='TEST', name='测试表')
        self.batch = DispatchBatch.objects.create(name='测试批次', status='PUBLISHED', deadline_at=timezone.now() - timedelta(days=1))
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def task(self, user=None, **kwargs):
        return FormTask.objects.create(batch=self.batch, template=self.template,
            assignee_id=(user or self.user).id, deadline_at=self.batch.deadline_at,
            org_unit_snapshot=self.unit, **kwargs)

    def test_extend_deadline_updates_open_tasks_and_audits(self):
        task = self.task(status='OVERDUE')
        closed = self.task(self.other, status='CLOSED')
        deadline = timezone.now() + timedelta(days=2)
        response = self.client.post(f'/api/forms/dispatch/{self.batch.id}/extend-deadline/', {'deadline_at': deadline.isoformat()}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        task.refresh_from_db(); closed.refresh_from_db(); self.batch.refresh_from_db()
        self.assertEqual(task.deadline_at, deadline)
        self.assertEqual(task.status, 'PENDING')
        self.assertEqual(self.batch.deadline_at, deadline)
        self.assertEqual(self.batch.stats_overdue, 0)
        self.assertNotEqual(closed.deadline_at, deadline)
        self.assertTrue(task.audits.filter(action='EXTEND_DEADLINE').exists())

    def test_reject_shorter_deadline_and_closed_batch(self):
        url = f'/api/forms/dispatch/{self.batch.id}/extend-deadline/'
        self.assertEqual(self.client.post(url, {'deadline_at': self.batch.deadline_at.isoformat()}, format='json').status_code, 400)
        self.batch.status = 'CLOSED'; self.batch.save()
        self.assertEqual(self.client.post(url, {'deadline_at': (timezone.now() + timedelta(days=1)).isoformat()}, format='json').status_code, 400)

    def test_only_authenticated_dispatch_manager_can_extend(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.post(f'/api/forms/dispatch/{self.batch.id}/extend-deadline/', {}, format='json').status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post(f'/api/forms/dispatch/{self.batch.id}/extend-deadline/', {}, format='json').status_code, 401)

    def test_dispatch_options_use_dispatch_permission_without_role_admin_permission(self):
        role = Role.objects.create(code='DISPATCHER', name='填报管理员', permissions=['forms:dispatch:manage'])
        UserRole.objects.create(user=self.user, role=role)
        Role.objects.create(code='DISABLED', name='停用角色', is_active=False)
        self.other.is_active = False; self.other.save()
        self.client.force_authenticate(self.user)
        response = self.client.get('/api/forms/dispatch/options/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([r['code'] for r in response.data['roles']], ['DISPATCHER'])
        self.assertNotIn(self.other.id, [r['id'] for r in response.data['users']])
        response = self.client.post(f'/api/forms/dispatch/{self.batch.id}/extend-deadline/', {'deadline_at': (timezone.now() + timedelta(days=3)).isoformat()}, format='json')
        self.assertEqual(response.status_code, 200)

    def test_role_dispatch_deduplicates_and_excludes_disabled_users(self):
        role = Role.objects.create(code='TEST_ROLE', name='测试角色')
        UserRole.objects.create(user=self.user, role=role)
        self.other.is_active = False; self.other.save()
        UserRole.objects.create(user=self.other, role=role)
        payload = {'batch_id': str(self.batch.id), 'rules': [
            {'template_id': str(self.template.id), 'receiver_type': 'ORG_ROLE', 'receiver_expr_json': {'role_codes': [role.code]}},
            {'template_id': str(self.template.id), 'receiver_type': 'USER', 'receiver_expr_json': {'user_ids': [str(self.user.id)]}},
        ]}
        self.assertEqual(preview_dispatch(payload)['summary']['total'], 1)
        _, count = publish_dispatch(payload, self.admin)
        self.assertEqual(count, 1)

    def test_selected_users_keep_department(self):
        result = preview_dispatch({'rules': [{'template_id': str(self.template.id), 'receiver_type': 'USER', 'receiver_expr_json': {'user_ids': [str(self.user.id)]}}]})
        self.assertEqual(result['tasks'][0]['org_unit'], '测试部门')

    def test_people_rate_requires_all_tasks_and_rolls_up_branch(self):
        self.task(status='SUBMITTED')
        self.task(status='DRAFT')
        self.task(self.other, status='SUBMITTED')
        dashboard = FormDashboardService().get_dashboard(self.batch.id)
        self.assertEqual(dashboard['people_summary'], {'total': 2, 'submitted': 1, 'completion_rate': 50.0})
        branch = dashboard['branch_stats'][0]
        self.assertEqual(branch['branch_name'], '测试支部')
        self.assertEqual(branch['total'], 2)
        self.assertEqual(branch['submitted'], 1)
        self.assertEqual(branch['completion_rate'], 50.0)

    def test_dashboard_follows_roster_department_after_transfer(self):
        new_branch = OrgUnit.objects.create(name='新支部', unit_type='BRANCH')
        new_unit = OrgUnit.objects.create(name='新部门', unit_type='DEPARTMENT', parent=new_branch)
        PersonnelRoster.objects.create(serial_number=1, name='测试人员', department='新部门', gender='M')
        self.task(status='PENDING')
        dashboard = FormDashboardService().get_dashboard(self.batch.id)
        self.assertEqual(dashboard['branch_stats'][0]['branch_name'], '新支部')
        self.assertEqual(dashboard['org_unit_stats'][0]['org_unit_name'], '新部门')
        pending = FormDashboardService().get_pending_users(self.batch.id)
        self.assertEqual(pending['pending_users'][0]['org_unit'], '新部门')
