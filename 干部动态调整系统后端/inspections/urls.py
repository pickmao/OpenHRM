from rest_framework.routers import DefaultRouter
from .views import WorkRecordViewSet

router = DefaultRouter()
router.register('records', WorkRecordViewSet, basename='work-record')
urlpatterns = router.urls
