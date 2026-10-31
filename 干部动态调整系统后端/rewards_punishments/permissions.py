from rest_framework.permissions import SAFE_METHODS, BasePermission

from forms.permissions import user_has_permission


class HasRewardPermission(BasePermission):
    """奖励汇总的查看和维护权限；维护权限包含查看权限。"""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        required = {'rewards:view', 'rewards:manage'}
        if request.method not in SAFE_METHODS:
            required = {'rewards:manage', 'rewards:record:manage', 'rewards:file:manage'}
        else:
            required.update({'rewards:record:view', 'rewards:record:manage', 'rewards:file:view', 'rewards:file:manage'})
        return any(user_has_permission(user, permission) for permission in required)
