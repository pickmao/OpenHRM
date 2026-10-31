from rest_framework.permissions import BasePermission


def has_recommendation_permission(user, code):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return any(
        code in (assignment.role.permissions or [])
        for assignment in user.user_roles.select_related('role').filter(role__is_active=True)
    )


class HasRecommendationPermission(BasePermission):
    def has_permission(self, request, view):
        return has_recommendation_permission(request.user, getattr(view, 'permission_code', None))
