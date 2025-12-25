from rest_framework import permissions
from .models import ScopeType


class HasPermissionCode(permissions.BasePermission):
    """
    基于权限码的权限控制
    使用方式：permission_classes = [IsAuthenticated, HasPermissionCode]
              permission_code = 'cadres:view'
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # 获取视图所需的权限码
        permission_code = getattr(view, 'permission_code', None)
        if not permission_code:
            return True  # 如果没有设置权限码，默认允许

        # 超级管理员拥有所有权限
        if request.user.is_superuser:
            return True

        # 检查用户是否有所需权限
        user_permissions = set()
        for user_role in request.user.user_roles.all():
            if user_role.role.is_active:
                user_permissions.update(user_role.role.permissions)

        return permission_code in user_permissions


class DataScopePermission:
    """数据范围权限过滤器"""

    @staticmethod
    def apply_data_scope(user, queryset):
        """
        根据用户的数据范围过滤查询集

        Args:
            user: 用户对象
            queryset: 查询集

        Returns:
            过滤后的查询集
        """
        # 超级管理员返回全部数据
        if user.is_superuser:
            return queryset

        try:
            data_scope = user.data_scope

            if data_scope.scope_type == ScopeType.ALL:
                # 全部数据权限
                return queryset
            elif data_scope.scope_type == ScopeType.ORG_UNIT:
                # 指定组织单元权限
                allowed_org_units = data_scope.org_units.all()

                # 如果查询集是Cadre
                if queryset.model.__name__ == 'Cadre':
                    from staffing.models import OrgMembership
                    cadre_ids = OrgMembership.objects.filter(
                        org_unit__in=allowed_org_units,
                        status='ACTIVE'
                    ).values_list('cadre_id', flat=True)
                    return queryset.filter(id__in=cadre_ids)

                # 如果查询集是OrgMembership
                elif queryset.model.__name__ == 'OrgMembership':
                    return queryset.filter(
                        org_unit__in=allowed_org_units,
                        status='ACTIVE'
                    )

                # 如果查询集是OrgUnit
                elif queryset.model.__name__ == 'OrgUnit':
                    return queryset.filter(id__in=allowed_org_units)

                # 其他情况，返回空
                return queryset.none()

            elif data_scope.scope_type == ScopeType.SELF:
                # 本人权限
                if queryset.model.__name__ == 'Cadre':
                    if hasattr(user, 'profile_cadre') and user.profile_cadre:
                        return queryset.filter(id=user.profile_cadre.id)
                    else:
                        return queryset.none()
                elif queryset.model.__name__ == 'User':
                    return queryset.filter(id=user.id)
                else:
                    return queryset.none()

        except Exception:
            # 如果出现异常，返回空数据
            return queryset.none()

        return queryset.none()


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    只有对象的所有者才能编辑
    """

    def has_object_permission(self, request, view, obj):
        # 读取权限对所有认证用户开放
        if request.method in permissions.SAFE_METHODS:
            return True

        # 写入权限只对所有者开放
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        elif hasattr(obj, 'actor'):
            return obj.actor == request.user
        else:
            return False


class CanManageStaffingPlan(permissions.BasePermission):
    """
    人事调整方案管理权限
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        # 检查是否有人事调整管理权限
        required_permissions = [
            'staffing:plan:create',
            'staffing:plan:submit',
            'staffing:plan:apply'
        ]

        user_permissions = set()
        for user_role in request.user.user_roles.all():
            if user_role.role.is_active:
                user_permissions.update(user_role.role.permissions)

        # 创建草案只需要create权限
        if request.method == 'POST' and view.action == 'create':
            return 'staffing:plan:create' in user_permissions

        # 提交方案需要submit权限
        if request.method in ['PUT', 'PATCH'] and view.action == 'submit':
            return 'staffing:plan:submit' in user_permissions

        # 生效方案需要apply权限
        if request.method in ['PUT', 'PATCH'] and view.action == 'apply':
            return 'staffing:plan:apply' in user_permissions

        return False


class CanManageRiskData(permissions.BasePermission):
    """
    风险数据管理权限
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        # 检查是否有风险管理权限
        user_permissions = set()
        for user_role in request.user.user_roles.all():
            if user_role.role.is_active:
                user_permissions.update(user_role.role.permissions)

        # 读取权限
        if request.method in permissions.SAFE_METHODS:
            return 'risk:view' in user_permissions

        # 管理权限
        return 'risk:manage' in user_permissions