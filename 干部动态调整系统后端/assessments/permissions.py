from rest_framework.permissions import BasePermission, SAFE_METHODS

from forms.permissions import user_has_permission


class HasAssessmentPermission(BasePermission):
    """研判数据的查看与维护分离；管理权限包含查看权限。"""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        is_leadership = view.__class__.__module__.startswith('leadership_assessments')
        legacy_prefix = 'leadership' if is_leadership else 'assessments'
        suffixes = ('record', 'file')
        if request.method in SAFE_METHODS:
            required = {'assessments:view', 'assessments:manage'}
            required.update(f'{legacy_prefix}:{suffix}:view' for suffix in suffixes)
            required.update(f'{legacy_prefix}:{suffix}:manage' for suffix in suffixes)
        else:
            required = {'assessments:manage'}
            required.update(f'{legacy_prefix}:{suffix}:manage' for suffix in suffixes)
        return any(user_has_permission(user, permission) for permission in required)
