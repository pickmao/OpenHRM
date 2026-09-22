from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import RewardImportFileViewSet, RewardRecordViewSet


router = DefaultRouter()
router.register(r'reward-files', RewardImportFileViewSet, basename='reward-files')
router.register(r'reward-records', RewardRecordViewSet, basename='reward-records')

urlpatterns = [path('', include(router.urls))]
