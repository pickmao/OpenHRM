import re

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import DataScope, Role, ScopeType, UserRole
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


class AdminUserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False, min_length=8)
    confirm_password = serializers.CharField(write_only=True, trim_whitespace=False)

    class Meta:
        model = User
        fields = ['username', 'real_name', 'password', 'confirm_password']
        extra_kwargs = {
            'username': {'min_length': 3, 'max_length': 150},
            'real_name': {'allow_blank': False, 'required': True},
        }

    def validate(self, attrs):
        unknown = set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError({'detail': '只能创建普通用户，请勿传入角色或管理员权限字段'})
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': '两次输入的密码不一致'})
        try:
            validate_password(attrs['password'], User(username=attrs['username'], real_name=attrs['real_name']))
        except DjangoValidationError as error:
            raise serializers.ValidationError({'password': error.messages})
        if not Role.objects.filter(code=Role.CADRE_SELF, is_active=True).exists():
            raise serializers.ValidationError({'detail': '默认的本人账号角色不可用，请先启用该角色'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = User.objects.create_user(
            **validated_data, is_staff=False, is_superuser=False,
            is_active=True, account_status=User.AccountStatus.ACTIVE,
        )
        UserRole.objects.create(
            user=user, role=Role.objects.get(code=Role.CADRE_SELF, is_active=True),
            assigned_by=self.context['request'].user,
        )
        DataScope.objects.create(user=user, scope_type=ScopeType.SELF)
        return user


class UserRolesSerializer(serializers.Serializer):
    role_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=True)

    def validate_role_ids(self, role_ids):
        roles = Role.objects.filter(id__in=role_ids, is_active=True)
        if roles.count() != len(set(role_ids)):
            raise serializers.ValidationError('角色不存在或已停用')
        return list(dict.fromkeys(role_ids))
