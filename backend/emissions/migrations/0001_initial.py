import uuid
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EmissionFactor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_type', models.CharField(max_length=50)),
                ('activity', models.CharField(max_length=100)),
                ('unit', models.CharField(max_length=30)),
                ('kg_co2e_per_unit', models.DecimalField(decimal_places=6, max_digits=12)),
                ('region', models.CharField(blank=True, default='GLOBAL', max_length=50)),
                ('valid_from', models.DateField(blank=True, null=True)),
                ('valid_to', models.DateField(blank=True, null=True)),
                ('source_reference', models.CharField(blank=True, max_length=255)),
            ],
            options={
                'ordering': ['source_type', 'activity'],
                'unique_together': {('source_type', 'activity', 'unit', 'region')},
            },
        ),
        migrations.CreateModel(
            name='IngestionBatch',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('source_type', models.CharField(
                    choices=[('sap', 'SAP Export'), ('utility', 'Utility Data'), ('travel', 'Corporate Travel')],
                    max_length=20,
                )),
                ('status', models.CharField(
                    choices=[('pending', 'Pending'), ('processing', 'Processing'), ('done', 'Done'), ('failed', 'Failed')],
                    default='pending', max_length=20,
                )),
                ('file_name', models.CharField(blank=True, max_length=255)),
                ('file_path', models.FileField(blank=True, null=True, upload_to='uploads/')),
                ('row_count', models.IntegerField(default=0)),
                ('error_count', models.IntegerField(default=0)),
                ('warning_count', models.IntegerField(default=0)),
                ('error_log', models.JSONField(default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
                ('reporting_period_start', models.DateField(blank=True, null=True)),
                ('reporting_period_end', models.DateField(blank=True, null=True)),
                ('notes', models.TextField(blank=True)),
                ('tenant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='batches', to='accounts.tenant',
                )),
                ('uploaded_by', models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='batches', to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='EmissionRecord',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('scope', models.CharField(
                    choices=[('1', 'Scope 1 — Direct'), ('2', 'Scope 2 — Indirect Electricity'), ('3', 'Scope 3 — Value Chain')],
                    max_length=1,
                )),
                ('source_type', models.CharField(max_length=20)),
                ('category', models.CharField(max_length=100)),
                ('activity_date', models.DateField()),
                ('quantity', models.DecimalField(decimal_places=4, max_digits=16)),
                ('unit', models.CharField(max_length=30)),
                ('quantity_original', models.DecimalField(blank=True, decimal_places=4, max_digits=16, null=True)),
                ('unit_original', models.CharField(blank=True, max_length=30)),
                ('kg_co2e', models.DecimalField(blank=True, decimal_places=4, max_digits=16, null=True)),
                ('facility', models.CharField(blank=True, max_length=255)),
                ('cost_center', models.CharField(blank=True, max_length=100)),
                ('country', models.CharField(blank=True, max_length=100)),
                ('raw_data', models.JSONField(default=dict)),
                ('status', models.CharField(
                    choices=[('pending', 'Pending Review'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('flagged', 'Flagged')],
                    default='pending', max_length=20,
                )),
                ('review_notes', models.TextField(blank=True)),
                ('is_suspicious', models.BooleanField(default=False)),
                ('suspicion_reason', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_edited', models.BooleanField(default=False)),
                ('edit_history', models.JSONField(default=list)),
                ('batch', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='records', to='emissions.ingestionbatch',
                )),
                ('emission_factor', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    to='emissions.emissionfactor',
                )),
                ('reviewed_by', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='reviewed_records', to=settings.AUTH_USER_MODEL,
                )),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('tenant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='records', to='accounts.tenant',
                )),
            ],
            options={'ordering': ['-activity_date', '-created_at']},
        ),
        migrations.AddIndex(
            model_name='emissionrecord',
            index=models.Index(fields=['tenant', 'scope', 'status'], name='emissions_e_tenant_scope_status_idx'),
        ),
        migrations.AddIndex(
            model_name='emissionrecord',
            index=models.Index(fields=['tenant', 'source_type'], name='emissions_e_tenant_source_idx'),
        ),
        migrations.AddIndex(
            model_name='emissionrecord',
            index=models.Index(fields=['batch'], name='emissions_e_batch_idx'),
        ),
        migrations.AddIndex(
            model_name='emissionrecord',
            index=models.Index(fields=['activity_date'], name='emissions_e_activity_date_idx'),
        ),
    ]
