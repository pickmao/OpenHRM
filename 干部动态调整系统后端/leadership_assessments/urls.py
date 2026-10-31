from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import LeadershipFileViewSet, LeadershipRecordViewSet

router = DefaultRouter()
router.register(r'files', LeadershipFileViewSet, basename='leadership-file')
router.register(r'records', LeadershipRecordViewSet, basename='leadership-record')

urlpatterns = [path('', include(router.urls))]
