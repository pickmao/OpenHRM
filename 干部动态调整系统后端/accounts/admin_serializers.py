import re

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Role, UserRole
from .permission_catalog import is_valid_permission_code


User = get_user_model()


class RoleSerializer(serializers.ModelSerializer):
    user_count = serializers.IntegerField(source='role_users.count', read_only=True)

    class Meta:
        model = Role
        fields = ['id', 'code', 'name', 'description', 'is_active', 'permissions', 'user_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'user_count']

    def validate_code(self, value):
        if not re.fullmatch(r'[A-Z][A-Z0-9_]{1,49}', value):
            raise serializers.ValidationError('角色编码只能包含大写字母、数字和下划线，并以字母开头')
        return value

    def validate_permissions(self, values):
        unknown = sorted(set(values) - {item for item in values if is_valid_permission_code(item)})
        if unknown:
            raise serializers.ValidationError(f'存在未定义的权限码：{", ".join(unknown)}')
        return sorted(set(values))


class RolePermissionsSerializer(serializers.Serializer):
    permissions = serializers.ListField(child=serializers.CharField(), allow_empty=True)

    def validate_permissions(self, values):
        unknown = [code for code in values if not is_valid_permission_code(code)]
        if unknown:
            raise serializers.ValidationError(f'存在未定义的权限码：{", ".join(sorted(set(unknown)))}')
        return sorted(set(values))


class AdminUserListSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'real_name', 'email', 'phone', 'is_active', 'is_superuser', 'last_login', 'date_joined', 'roles']
        read_only_fields = fields

    def get_roles(self, user):
        return [
            {'id': str(item.role_id), 'code': item.role.code, 'name': item.role.name}
            for item in user.user_roles.select_related('role').filter(role__is_active=True)
        ]


class UserRolesSerializer(serializers.Serializer):
    role_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=True)

    def validate_role_ids(self, role_ids):
        roles = Role.objects.filter(id__in=role_ids, is_active=True)
        if roles.count() != len(set(role_ids)):
            raise serializers.ValidationError('角色不存在或已停用')
        return list(dict.fromkeys(role_ids))
