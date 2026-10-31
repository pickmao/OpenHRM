from rest_framework.permissions import BasePermission


def user_has_permission(user, code):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.user_roles.filter(role__is_active=True, role__permissions__contains=[code]).exists()


class HasFormsPermission(BasePermission):
    """以权限码保护表单接口；超级管理员始终允许。"""

    def has_permission(self, request, view):
        code = getattr(view, 'permission_code', None)
        return bool(code and user_has_permission(request.user, code))
