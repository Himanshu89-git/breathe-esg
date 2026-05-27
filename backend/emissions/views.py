from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import EmissionRecord, IngestionBatch, EmissionFactor
from .serializers import (
    EmissionRecordSerializer, IngestionBatchSerializer,
    ReviewActionSerializer, EmissionFactorSerializer
)


class EmissionRecordViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EmissionRecordSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['scope', 'status', 'source_type', 'category', 'is_suspicious']
    search_fields = ['facility', 'category', 'cost_center', 'country']
    ordering_fields = ['activity_date', 'kg_co2e', 'created_at', 'quantity']
    ordering = ['-activity_date']

    def get_queryset(self):
        qs = EmissionRecord.objects.filter(tenant=self.request.user.tenant)
        batch_id = self.request.query_params.get('batch')
        if batch_id:
            qs = qs.filter(batch_id=batch_id)
        return qs

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        record = self.get_object()
        serializer = ReviewActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action_map = {
            'approve': EmissionRecord.STATUS_APPROVED,
            'reject': EmissionRecord.STATUS_REJECTED,
            'flag': EmissionRecord.STATUS_FLAGGED,
        }
        record.status = action_map[serializer.validated_data['action']]
        record.review_notes = serializer.validated_data.get('notes', '')
        record.reviewed_by = request.user
        record.reviewed_at = timezone.now()
        record.save()
        return Response(EmissionRecordSerializer(record).data)

    @action(detail=False, methods=['post'])
    def bulk_approve(self, request):
        ids = request.data.get('ids', [])
        qs = EmissionRecord.objects.filter(
            tenant=request.user.tenant,
            id__in=ids,
            status=EmissionRecord.STATUS_PENDING
        )
        count = qs.update(
            status=EmissionRecord.STATUS_APPROVED,
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        return Response({'approved': count})

    @action(detail=False, methods=['get'])
    def stats(self, request):
        qs = EmissionRecord.objects.filter(tenant=request.user.tenant)
        total_co2 = qs.aggregate(t=Sum('kg_co2e'))['t'] or 0

        by_scope = {}
        for scope in ['1', '2', '3']:
            scope_qs = qs.filter(scope=scope)
            by_scope[f'scope_{scope}'] = {
                'count': scope_qs.count(),
                'kg_co2e': float(scope_qs.aggregate(t=Sum('kg_co2e'))['t'] or 0),
            }

        by_source = {}
        for src in ['sap', 'utility', 'travel']:
            src_qs = qs.filter(source_type=src)
            by_source[src] = {
                'count': src_qs.count(),
                'kg_co2e': float(src_qs.aggregate(t=Sum('kg_co2e'))['t'] or 0),
            }

        recent_batches = IngestionBatch.objects.filter(
            tenant=request.user.tenant
        ).order_by('-created_at')[:5]

        return Response({
            'total_records': qs.count(),
            'pending': qs.filter(status='pending').count(),
            'approved': qs.filter(status='approved').count(),
            'rejected': qs.filter(status='rejected').count(),
            'flagged': qs.filter(status='flagged').count(),
            'suspicious': qs.filter(is_suspicious=True).count(),
            'total_kg_co2e': float(total_co2),
            'by_scope': by_scope,
            'by_source': by_source,
            'recent_batches': IngestionBatchSerializer(recent_batches, many=True).data,
        })


class IngestionBatchViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = IngestionBatchSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['source_type', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        return IngestionBatch.objects.filter(tenant=self.request.user.tenant)
