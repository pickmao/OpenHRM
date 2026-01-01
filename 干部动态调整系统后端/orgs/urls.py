from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrgUnitViewSet, MembershipViewSet

router = DefaultRouter()
router.register(r'units', OrgUnitViewSet, basename='org-unit')
router.register(r'memberships', MembershipViewSet, basename='membership')

urlpatterns = [
    path('', include(router.urls)),
]
