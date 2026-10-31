from rest_framework.permissions import BasePermission


def has_evaluation_permission(user, code):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    # 角色权限存放在 JSON 数组中。逐个读取不仅兼容 PostgreSQL，也让 SQLite
    # 隔离测试不依赖 JSON contains lookup。
    return any(
        code in (assignment.role.permissions or [])
        for assignment in user.user_roles.select_related('role').filter(role__is_active=True)
    )


class HasEvaluationPermission(BasePermission):
    def has_permission(self, request, view):
        return has_evaluation_permission(request.user, getattr(view, 'permission_code', None))
