from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from emissions.models import IngestionBatch, EmissionRecord, EmissionFactor
from ingestion.parsers.sap_parser import parse_sap_file
from ingestion.parsers.utility_parser import parse_utility_file
from ingestion.parsers.travel_parser import parse_travel_file
from emissions.serializers import IngestionBatchSerializer


PARSERS = {
    'sap': parse_sap_file,
    'utility': parse_utility_file,
    'travel': parse_travel_file,
}


def _find_emission_factor(source_type, category, unit):
    """Try to find a matching emission factor."""
    try:
        return EmissionFactor.objects.get(
            source_type=source_type,
            activity=category,
            unit=unit,
        )
    except EmissionFactor.DoesNotExist:
        return None
    except EmissionFactor.MultipleObjectsReturned:
        return EmissionFactor.objects.filter(
            source_type=source_type, activity=category, unit=unit
        ).first()


class UploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        source_type = request.data.get('source_type')
        if source_type not in PARSERS:
            return Response(
                {'error': f"Invalid source_type. Must be one of: {list(PARSERS.keys())}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)

        tenant = request.user.tenant
        if not tenant:
            return Response({'error': 'User has no tenant assigned'}, status=status.HTTP_403_FORBIDDEN)

        # Create batch record
        batch = IngestionBatch.objects.create(
            tenant=tenant,
            uploaded_by=request.user,
            source_type=source_type,
            status=IngestionBatch.STATUS_PROCESSING,
            file_name=file.name,
            file_path=file,
            notes=request.data.get('notes', ''),
        )

        try:
            file_content = file.read() if hasattr(file, 'read') else open(batch.file_path.path, 'rb').read()
        except Exception as e:
            batch.status = IngestionBatch.STATUS_FAILED
            batch.error_log = [{'error': f'Could not read file: {str(e)}'}]
            batch.save()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Parse
        parser = PARSERS[source_type]
        try:
            result = parser(file_content, file.name)
        except Exception as e:
            batch.status = IngestionBatch.STATUS_FAILED
            batch.error_log = [{'error': f'Parser crash: {str(e)}'}]
            batch.save()
            return Response({'error': f'Parser failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        parsed_records = result.get('records', [])
        errors = result.get('errors', [])
        warnings = result.get('warnings', [])

        # Infer reporting period from records
        dates = [r['activity_date'] for r in parsed_records if r.get('activity_date')]
        if dates:
            batch.reporting_period_start = min(dates)
            batch.reporting_period_end = max(dates)

        # Create EmissionRecord objects
        created = 0
        for rec in parsed_records:
            ef = _find_emission_factor(source_type, rec.get('category'), rec.get('unit'))

            kg_co2e = rec.get('kg_co2e')  # travel parser pre-computes
            if not kg_co2e and ef and rec.get('quantity'):
                kg_co2e = float(rec['quantity']) * float(ef.kg_co2e_per_unit)

            EmissionRecord.objects.create(
                tenant=tenant,
                batch=batch,
                emission_factor=ef,
                scope=rec.get('scope', '3'),
                source_type=source_type,
                category=rec.get('category', ''),
                activity_date=rec.get('activity_date'),
                quantity=rec.get('quantity', 0),
                unit=rec.get('unit', ''),
                quantity_original=rec.get('quantity_original'),
                unit_original=rec.get('unit_original', ''),
                facility=rec.get('facility', ''),
                cost_center=rec.get('cost_center', ''),
                country=rec.get('country', ''),
                kg_co2e=kg_co2e,
                is_suspicious=rec.get('is_suspicious', False),
                suspicion_reason=rec.get('suspicion_reason', ''),
                raw_data=rec.get('raw_data', {}),
            )
            created += 1

        batch.status = IngestionBatch.STATUS_DONE
        batch.row_count = created
        batch.error_count = len(errors)
        batch.warning_count = len(warnings)
        batch.error_log = errors + [{'type': 'warning', **w} for w in warnings]
        batch.processed_at = timezone.now()
        batch.save()

        return Response({
            'batch': IngestionBatchSerializer(batch).data,
            'created': created,
            'errors': len(errors),
            'warnings': len(warnings),
            'error_detail': errors[:20],  # cap for response size
        }, status=status.HTTP_201_CREATED)
