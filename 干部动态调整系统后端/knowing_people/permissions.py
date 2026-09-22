from rest_framework.permissions import BasePermission


def has_knowing_people_permission(user, code):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return any(
        code in (assignment.role.permissions or [])
        for assignment in user.user_roles.select_related('role').filter(role__is_active=True)
    )


class HasKnowingPeoplePermission(BasePermission):
    def has_permission(self, request, view):
        return has_knowing_people_permission(request.user, getattr(view, 'permission_code', None))
