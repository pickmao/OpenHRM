from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, Role, DataScope, ScopeType
from audit.models import AuditLog, AuditAction


class LoginSerializer(serializers.Serializer):
    """登录序列化器"""
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, write_only=True)
    captcha = serializers.CharField(max_length=10, required=False)
    device_id = serializers.CharField(max_length=100, required=False)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        # 验证用户名密码
        user = authenticate(username=username, password=password)

        if user is None:
            # 记录登录失败日志
            AuditLog.objects.create(
                actor=None,
                action=AuditAction.OTHER,
                target_type='User',
                context={
                    'username': username,
                    'reason': '用户名或密码错误',
                    'ip': self.context.get('request').META.get('REMOTE_ADDR'),
                    'user_agent': self.context.get('request').META.get('HTTP_USER_AGENT')
                }
            )
            raise serializers.ValidationError('用户名或密码错误')

        if not user.is_active:
            AuditLog.objects.create(
                actor=user,
                action=AuditAction.OTHER,
                target_type='User',
                target_id=user.id,
                context={
                    'reason': '用户已被禁用',
                    'ip': self.context.get('request').META.get('REMOTE_ADDR'),
                    'user_agent': self.context.get('request').META.get('HTTP_USER_AGENT')
                }
            )
            raise serializers.ValidationError('用户已被禁用')

        attrs['user'] = user
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    """用户信息序列化器"""
    roles = serializers.SerializerMethodField()
    data_scope = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'real_name', 'phone', 'email', 'roles', 'data_scope', 'permissions']
        read_only_fields = ['id', 'username', 'email']

    def get_roles(self, obj):
        """获取用户角色列表"""
        return [user_role.role.code for user_role in obj.user_roles.all() if user_role.role.is_active]

    def get_data_scope(self, obj):
        """获取用户数据范围"""
        try:
            data_scope = obj.data_scope
            return {
                'scope_type': data_scope.scope_type,
                'org_unit_ids': [str(org.id) for org in data_scope.org_units.all()]
            }
        except DataScope.DoesNotExist:
            return {
                'scope_type': ScopeType.SELF,
                'org_unit_ids': []
            }

    def get_permissions(self, obj):
        """获取用户权限点"""
        permissions = set()
        for user_role in obj.user_roles.all():
            if user_role.role.is_active:
                permissions.update(user_role.role.permissions)
        return list(permissions)


class RefreshTokenSerializer(serializers.Serializer):
    """刷新Token序列化器"""
    refresh = serializers.CharField()


class LogoutSerializer(serializers.Serializer):
    """登出序列化器"""
    refresh = serializers.CharField()


class ChangePasswordSerializer(serializers.Serializer):
    """修改密码序列化器"""
    old_password = serializers.CharField(max_length=128, write_only=True)
    new_password = serializers.CharField(max_length=128, write_only=True)
    confirm_password = serializers.CharField(max_length=128, write_only=True)

    def validate_old_password(self, value):
        """验证旧密码"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('旧密码不正确')
        return value

    def validate(self, attrs):
        """验证新密码"""
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError('两次输入的密码不一致')

        validate_password(attrs['new_password'], self.context['request'].user)
        return attrs