from django.contrib import admin
from .models import EmissionRecord, IngestionBatch, EmissionFactor

@admin.register(EmissionFactor)
class EmissionFactorAdmin(admin.ModelAdmin):
    list_display = ['activity', 'source_type', 'unit', 'kg_co2e_per_unit', 'region']
    list_filter = ['source_type', 'region']
    search_fields = ['activity']

@admin.register(IngestionBatch)
class IngestionBatchAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'source_type', 'status', 'row_count', 'error_count', 'created_at']
    list_filter = ['source_type', 'status', 'tenant']

@admin.register(EmissionRecord)
class EmissionRecordAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'scope', 'category', 'activity_date', 'quantity', 'unit', 'kg_co2e', 'status']
    list_filter = ['scope', 'status', 'source_type', 'tenant', 'is_suspicious']
    search_fields = ['facility', 'category', 'cost_center']
    readonly_fields = ['raw_data', 'edit_history', 'created_at', 'updated_at']
