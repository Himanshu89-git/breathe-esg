from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmissionRecordViewSet, IngestionBatchViewSet

router = DefaultRouter()
router.register('records', EmissionRecordViewSet, basename='records')
router.register('batches', IngestionBatchViewSet, basename='batches')

# DRF router auto-generates these URL names:
#   records-list         GET  /api/emissions/records/
#   records-detail       GET  /api/emissions/records/{pk}/
#   records-review       POST /api/emissions/records/{pk}/review/
#   records-stats        GET  /api/emissions/records/stats/
#   records-bulk-approve POST /api/emissions/records/bulk_approve/
#   batches-list         GET  /api/emissions/batches/
#   batches-detail       GET  /api/emissions/batches/{pk}/

urlpatterns = [
    path('', include(router.urls)),
]
