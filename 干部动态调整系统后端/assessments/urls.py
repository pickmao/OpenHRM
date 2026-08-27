from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AssessmentFileViewSet, AssessmentRecordViewSet

router = DefaultRouter()
router.register(r'analysis-files', AssessmentFileViewSet, basename='analysis-files')
router.register(r'analysis-records', AssessmentRecordViewSet, basename='analysis-records')

urlpatterns = [path('', include(router.urls))]
