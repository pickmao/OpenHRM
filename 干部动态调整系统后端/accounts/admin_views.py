from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.models import AuditAction, AuditLog

from .admin_serializers import AdminUserListSerializer, RolePermissionsSerializer, RoleSerializer, UserRolesSerializer
from .models import Role, UserRole
from .permission_catalog import catalog_response
from .permissions import HasPermissionCode


User = get_user_model()
SYSTEM_ROLE_CODES = {Role.SUPER_ADMIN, Role.POLITICAL_OFFICE_ADMIN, Role.DEPT_MANAGER, Role.ANALYST, Role.CADRE_SELF}


def audit(actor, target_type, target_id, context):
    AuditLog.objects.create(actor=actor, action=AuditAction.OTHER, target_type=target_type, target_id=target_id, context=context)


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.prefetch_related('role_users').all().order_by('code')
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated, HasPermissionCode]

    def get_permission_code(self):
        return {
            'list': 'accounts:role:view',
            'retrieve': 'accounts:role:view',
            'create': 'accounts:role:create',
            'partial_update': 'accounts:role:edit',
            'update': 'accounts:role:edit',
            'destroy': 'accounts:role:delete',
            'permissions': 'accounts:role:grant_permissions',
        }.get(self.action)

    def perform_create(self, serializer):
        role = serializer.save()
        audit(self.request.user, 'Role', role.id, {'action': 'create_role', 'role_code': role.code})

    def perform_update(self, serializer):
        role = serializer.save()
        audit(self.request.user, 'Role', role.id, {'action': 'update_role', 'role_code': role.code})

    def destroy(self, request, *args, **kwargs):
        role = self.get_object()
        if role.code in SYSTEM_ROLE_CODES:
            return Response({'detail': '系统内置角色不能删除'}, status=status.HTTP_400_BAD_REQUEST)
        if role.role_users.exists():
            return Response({'detail': '已有用户分配该角色，不能删除'}, status=status.HTTP_400_BAD_REQUEST)
        role_id = role.id
        role_code = role.code
        role.delete()
        audit(request.user, 'Role', role_id, {'action': 'delete_role', 'role_code': role_code})
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['put'], url_path='permissions')
    def permissions(self, request, pk=None):
        role = self.get_object()
        serializer = RolePermissionsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        before = role.permissions
        role.permissions = serializer.validated_data['permissions']
        role.save(update_fields=['permissions', 'updated_at'])
        audit(request.user, 'Role', role.id, {'action': 'update_permissions', 'before': before, 'after': role.permissions})
        return Response(RoleSerializer(role).data)


class PermissionCatalogView(APIView):
    permission_classes = [IsAuthenticated, HasPermissionCode]
    permission_code = 'accounts:permission:view_catalog'

    def get(self, request):
        return Response({'catalog': catalog_response()})


class AdminUserListView(APIView):
    permission_classes = [IsAuthenticated, HasPermissionCode]
    permission_code = 'accounts:user:view'

    def get(self, request):
        keyword = request.query_params.get('keyword', '').strip()
        queryset = User.objects.all().prefetch_related('user_roles__role').order_by('username')
        if keyword:
            queryset = queryset.filter(Q(username__icontains=keyword) | Q(real_name__icontains=keyword))
        return Response(AdminUserListSerializer(queryset, many=True).data)


class UserRoleDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermissionCode]
    permission_code = 'accounts:user:view_roles'

    def get(self, request, user_id):
        user = User.objects.get(id=user_id)
        roles = user.user_roles.select_related('role').filter(role__is_active=True)
        permissions = sorted({code for item in roles for code in item.role.permissions})
        return Response({
            'user': AdminUserListSerializer(user).data,
            'roles': [{'id': str(item.role_id), 'code': item.role.code, 'name': item.role.name} for item in roles],
            'all_permissions': permissions,
        })


class UserRoleAssignView(APIView):
    permission_classes = [IsAuthenticated, HasPermissionCode]
    permission_code = 'accounts:user:assign_role'

    @transaction.atomic
    def put(self, request, user_id):
        user = User.objects.get(id=user_id)
        serializer = UserRolesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role_ids = serializer.validated_data['role_ids']
        previous = list(user.user_roles.values_list('role_id', flat=True))
        user.user_roles.exclude(role_id__in=role_ids).delete()
        existing = set(user.user_roles.values_list('role_id', flat=True))
        UserRole.objects.bulk_create([
            UserRole(user=user, role_id=role_id, assigned_by=request.user)
            for role_id in role_ids if role_id not in existing
        ])
        audit(request.user, 'User', user.id, {
            'action': 'assign_roles', 'before_role_ids': [str(item) for item in previous],
            'after_role_ids': [str(item) for item in role_ids],
        })
        return UserRoleDetailView().get(request, user_id)
