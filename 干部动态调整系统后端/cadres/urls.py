from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PersonnelRosterViewSet, CadreViewSet, CadreResumeViewSet
from .overall_review_views import ReviewSearchView, ReviewSnapshotView, ReviewGenerateView

router = DefaultRouter()
router.register(r'roster', PersonnelRosterViewSet, basename='personnel-roster')
router.register(r'cadres', CadreViewSet, basename='cadre')
router.register(r'resumes', CadreResumeViewSet, basename='cadre-resume')

urlpatterns = [
    path('overall-reviews/search/', ReviewSearchView.as_view(), name='overall-review-search'),
    path('overall-reviews/<uuid:roster_id>/', ReviewSnapshotView.as_view(), name='overall-review-snapshot'),
    path('overall-reviews/<uuid:roster_id>/generate/', ReviewGenerateView.as_view(), name='overall-review-generate'),
    path('', include(router.urls)),
]
