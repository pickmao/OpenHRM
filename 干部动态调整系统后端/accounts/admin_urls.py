from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .admin_views import AdminUserListView, PermissionCatalogView, RoleViewSet, UserRoleAssignView, UserRoleDetailView


router = DefaultRouter()
router.register('roles', RoleViewSet, basename='admin-role')

urlpatterns = [
    path('', include(router.urls)),
    path('permissions/catalog/', PermissionCatalogView.as_view(), name='permission-catalog'),
    path('users/', AdminUserListView.as_view(), name='user-list'),
    path('users/<uuid:user_id>/roles/', UserRoleDetailView.as_view(), name='user-roles'),
    path('users/<uuid:user_id>/roles/assign/', UserRoleAssignView.as_view(), name='user-role-assign'),
]
