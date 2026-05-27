from rest_framework import serializers
from .models import EmissionRecord, IngestionBatch, EmissionFactor
from accounts.serializers import UserSerializer


class EmissionFactorSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmissionFactor
        fields = '__all__'


class IngestionBatchSerializer(serializers.ModelSerializer):
    uploaded_by = UserSerializer(read_only=True)

    class Meta:
        model = IngestionBatch
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'uploaded_by', 'created_at', 'processed_at']


class EmissionRecordSerializer(serializers.ModelSerializer):
    reviewed_by = UserSerializer(read_only=True)
    batch_info = serializers.SerializerMethodField()

    class Meta:
        model = EmissionRecord
        fields = '__all__'
        read_only_fields = [
            'id', 'tenant', 'batch', 'raw_data', 'created_at',
            'scope', 'source_type', 'category', 'activity_date',
            'quantity', 'unit', 'quantity_original', 'unit_original',
        ]

    def get_batch_info(self, obj):
        return {
            'id': str(obj.batch.id),
            'source_type': obj.batch.source_type,
            'file_name': obj.batch.file_name,
            'created_at': obj.batch.created_at,
        }


class ReviewActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve', 'reject', 'flag'])
    notes = serializers.CharField(required=False, allow_blank=True)


class DashboardStatsSerializer(serializers.Serializer):
    total_records = serializers.IntegerField()
    pending = serializers.IntegerField()
    approved = serializers.IntegerField()
    rejected = serializers.IntegerField()
    flagged = serializers.IntegerField()
    suspicious = serializers.IntegerField()
    total_kg_co2e = serializers.FloatField()
    by_scope = serializers.DictField()
    by_source = serializers.DictField()
    recent_batches = IngestionBatchSerializer(many=True)
