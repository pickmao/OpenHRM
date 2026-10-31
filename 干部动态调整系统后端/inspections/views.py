from django.db.models import Q
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from .models import WorkRecord
from .serializers import WorkRecordSerializer


class WorkRecordViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                        mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = WorkRecordSerializer

    def get_queryset(self):
        records = WorkRecord.objects.filter(owner=self.request.user)
        keyword = self.request.query_params.get('search', '').strip()
        if keyword:
            records = records.filter(Q(title__icontains=keyword) | Q(details__icontains=keyword) | Q(outcome__icontains=keyword))
        category = self.request.query_params.get('category')
        if category:
            records = records.filter(category=category)
        return records

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
