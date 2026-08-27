from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrgUnitViewSet, MembershipViewSet
from .transfer_views import MembershipTransferView

router = DefaultRouter()
router.register(r'units', OrgUnitViewSet, basename='org-unit')
router.register(r'memberships', MembershipViewSet, basename='membership')

urlpatterns = [
    path('memberships/transfer/', MembershipTransferView.as_view(), name='membership-transfer'),
    path('', include(router.urls)),
]
