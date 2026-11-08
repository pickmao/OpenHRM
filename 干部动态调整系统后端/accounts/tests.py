from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from audit.models import AuditLog
from .models import DataScope, Role, ScopeType, UserRole


User = get_user_model()


class AdminUserCreationTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username='account-admin', password='Secret!admin123')
        self.default_role = Role.objects.create(
            code=Role.CADRE_SELF, name='本人账号',
            permissions=['forms:task:view', 'forms:task:submit'],
        )
        self.url = reverse('user-list')
        self.payload = {
            'username': 'tutorial_user01', 'real_name': '教程填报人01',
            'password': 'Study!Record2026', 'confirm_password': 'Study!Record2026',
        }

    def test_admin_creates_ordinary_user_with_hashed_password_and_self_scope(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.url, self.payload)
        self.assertEqual(response.status_code, 201, response.data)
        user = User.objects.get(username=self.payload['username'])
        self.assertTrue(user.check_password(self.payload['password']))
        self.assertNotEqual(user.password, self.payload['password'])
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)
        self.assertTrue(user.is_active)
        self.assertEqual(user.account_status, User.AccountStatus.ACTIVE)
        self.assertEqual(user.data_scope.scope_type, ScopeType.SELF)
        self.assertEqual(list(user.user_roles.values_list('role__code', flat=True)), [Role.CADRE_SELF])
        self.assertNotIn('password', response.data)
        self.assertNotIn('confirm_password', response.data)
        self.assertFalse(AuditLog.objects.filter(target_id=str(user.id), context__icontains='Study!Record2026').exists())
        self.assertTrue(AuditLog.objects.filter(target_id=str(user.id)).exists())
        self.client.force_authenticate(None)
        login = self.client.post('/api/auth/login/', {'username': user.username, 'password': self.payload['password']})
        self.assertEqual(login.status_code, 200, login.data)
        self.assertIn('forms:task:submit', login.data['permissions'])

    def test_create_requires_manage_permission_not_just_view(self):
        for permissions in ([], ['accounts:user:view']):
            user = User.objects.create_user(username='viewer'+str(len(permissions)), password='Secret!reader123')
            role = Role.objects.create(code='VIEWER'+str(len(permissions)), name='查看', permissions=permissions)
            UserRole.objects.create(user=user, role=role)
            self.client.force_authenticate(user)
            self.assertEqual(self.client.post(self.url, self.payload).status_code, 403)
        self.assertFalse(User.objects.filter(username=self.payload['username']).exists())

    def test_delegated_user_manager_can_create_ordinary_user(self):
        manager = User.objects.create_user(username='user-manager', password='Secret!manager123')
        role = Role.objects.create(code='USER_MANAGER', name='用户管理员', permissions=['accounts:user:manage'])
        UserRole.objects.create(user=manager, role=role)
        self.client.force_authenticate(manager)
        self.assertEqual(self.client.post(self.url, self.payload).status_code, 201)

    def test_invalid_password_or_confirmation_does_not_create_user(self):
        self.client.force_authenticate(self.admin)
        for changes in ({'confirm_password': 'different'}, {'password': '12345678', 'confirm_password': '12345678'}):
            response = self.client.post(self.url, {**self.payload, **changes})
            self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(User.objects.filter(username=self.payload['username']).exists())

    def test_duplicate_username_does_not_replace_existing_password(self):
        existing = User.objects.create_user(username=self.payload['username'], password='Original!Password2026')
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.url, self.payload)
        self.assertEqual(response.status_code, 400)
        existing.refresh_from_db()
        self.assertTrue(existing.check_password('Original!Password2026'))

    def test_creation_rejects_privilege_fields(self):
        self.client.force_authenticate(self.admin)
        for field, value in [('is_superuser', True), ('is_staff', True), ('role_ids', [str(self.default_role.id)])]:
            response = self.client.post(self.url, {**self.payload, field: value}, format='json')
            self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(User.objects.filter(username=self.payload['username']).exists())

    def test_unavailable_default_role_does_not_leave_partial_account(self):
        self.default_role.is_active = False
        self.default_role.save()
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.url, self.payload)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(User.objects.filter(username=self.payload['username']).exists())
        self.assertEqual(DataScope.objects.count(), 0)
