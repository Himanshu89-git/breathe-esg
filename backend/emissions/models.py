from django.db import models
from accounts.models import Tenant, User
import uuid


class EmissionFactor(models.Model):
    """Lookup table for emission factors by activity type and unit."""
    source_type = models.CharField(max_length=50)   # fuel, electricity, travel
    activity = models.CharField(max_length=100)      # diesel, petrol, flight-short-haul, etc.
    unit = models.CharField(max_length=30)           # litre, kWh, km, passenger-km
    kg_co2e_per_unit = models.DecimalField(max_digits=12, decimal_places=6)
    region = models.CharField(max_length=50, blank=True, default='GLOBAL')
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    source_reference = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ['source_type', 'activity', 'unit', 'region']
        ordering = ['source_type', 'activity']

    def __str__(self):
        return f"{self.activity} ({self.unit}) = {self.kg_co2e_per_unit} kgCO2e"


class IngestionBatch(models.Model):
    """One upload/pull session = one batch. Tracks provenance."""
    SOURCE_SAP = 'sap'
    SOURCE_UTILITY = 'utility'
    SOURCE_TRAVEL = 'travel'
    SOURCE_CHOICES = [
        (SOURCE_SAP, 'SAP Export'),
        (SOURCE_UTILITY, 'Utility Data'),
        (SOURCE_TRAVEL, 'Corporate Travel'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_DONE = 'done'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_DONE, 'Done'),
        (STATUS_FAILED, 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='batches')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='batches')
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    file_name = models.CharField(max_length=255, blank=True)
    file_path = models.FileField(upload_to='uploads/', null=True, blank=True)
    row_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    warning_count = models.IntegerField(default=0)
    error_log = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    reporting_period_start = models.DateField(null=True, blank=True)
    reporting_period_end = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.tenant} | {self.source_type} | {self.created_at.date()}"


class EmissionRecord(models.Model):
    """
    Normalised emission record — one row per activity event.
    This is the source-of-truth table that feeds auditors.
    """
    SCOPE_1 = '1'
    SCOPE_2 = '2'
    SCOPE_3 = '3'
    SCOPE_CHOICES = [
        (SCOPE_1, 'Scope 1 — Direct'),
        (SCOPE_2, 'Scope 2 — Indirect Electricity'),
        (SCOPE_3, 'Scope 3 — Value Chain'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_FLAGGED = 'flagged'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending Review'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_FLAGGED, 'Flagged'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='records')
    batch = models.ForeignKey(IngestionBatch, on_delete=models.CASCADE, related_name='records')
    emission_factor = models.ForeignKey(
        EmissionFactor, on_delete=models.SET_NULL, null=True, blank=True
    )

    # Classification
    scope = models.CharField(max_length=1, choices=SCOPE_CHOICES)
    source_type = models.CharField(max_length=20)   # sap / utility / travel
    category = models.CharField(max_length=100)     # diesel, electricity, flight, hotel, etc.

    # Activity data (normalised)
    activity_date = models.DateField()
    quantity = models.DecimalField(max_digits=16, decimal_places=4)
    unit = models.CharField(max_length=30)           # normalised unit (always SI or standard)
    quantity_original = models.DecimalField(max_digits=16, decimal_places=4, null=True, blank=True)
    unit_original = models.CharField(max_length=30, blank=True)

    # Computed emissions
    kg_co2e = models.DecimalField(max_digits=16, decimal_places=4, null=True, blank=True)

    # Location / entity
    facility = models.CharField(max_length=255, blank=True)
    cost_center = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)

    # Raw source snapshot (never mutated after ingest)
    raw_data = models.JSONField(default=dict)

    # Review workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    review_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_records'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # Flags for analyst attention
    is_suspicious = models.BooleanField(default=False)
    suspicion_reason = models.TextField(blank=True)

    # Audit trail
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_edited = models.BooleanField(default=False)
    edit_history = models.JSONField(default=list)  # list of {field, old, new, by, at}

    class Meta:
        ordering = ['-activity_date', '-created_at']
        indexes = [
            models.Index(fields=['tenant', 'scope', 'status']),
            models.Index(fields=['tenant', 'source_type']),
            models.Index(fields=['batch']),
            models.Index(fields=['activity_date']),
        ]

    def __str__(self):
        return f"{self.tenant} | {self.scope} | {self.category} | {self.activity_date}"

    def compute_emissions(self):
        if self.emission_factor and self.quantity:
            self.kg_co2e = float(self.quantity) * float(self.emission_factor.kg_co2e_per_unit)
        return self.kg_co2e
