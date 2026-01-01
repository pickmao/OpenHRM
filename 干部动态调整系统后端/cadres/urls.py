from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PersonnelRosterViewSet, CadreViewSet, CadreResumeViewSet

router = DefaultRouter()
router.register(r'roster', PersonnelRosterViewSet, basename='personnel-roster')
router.register(r'cadres', CadreViewSet, basename='cadre')
router.register(r'resumes', CadreResumeViewSet, basename='cadre-resume')

urlpatterns = [
    path('', include(router.urls)),
]
