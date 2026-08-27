from datetime import date
from io import BytesIO

import pandas as pd
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.db.models import Avg, Sum
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import LeadershipAssessmentFile, LeadershipAssessmentRecord
from assessments.audit import record_change
from assessments.models import AssessmentChangeLog
from assessments.permissions import HasAssessmentPermission
from .serializers import (LeadershipFileListSerializer, LeadershipFileSerializer,
                          LeadershipRecordDetailSerializer, LeadershipRecordListSerializer,
                          LeadershipRecordSerializer)


def _text(row, index, default=''):
    if index >= len(row) or pd.isna(row.iloc[index]):
        return default
    value = str(row.iloc[index]).strip()
    return default if value.lower() == 'nan' else value


def _integer(row, index):
    try:
        value = _text(row, index, None)
        return int(float(value)) if value not in (None, '') else None
    except (TypeError, ValueError):
        return None


def _number(row, index):
    try:
        value = _text(row, index, None)
        return float(value) if value not in (None, '') else None
    except (TypeError, ValueError):
        return None


class LeadershipFileViewSet(viewsets.ModelViewSet):
    permission_classes = [HasAssessmentPermission]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        queryset = LeadershipAssessmentFile.objects.select_related('uploaded_by')
        active = self.request.query_params.get('is_active')
        if active is not None:
            queryset = queryset.filter(is_active=active.lower() == 'true')
        if self.request.query_params.get('start_date'):
            queryset = queryset.filter(version_date__gte=self.request.query_params['start_date'])
        if self.request.query_params.get('end_date'):
            queryset = queryset.filter(version_date__lte=self.request.query_params['end_date'])
        return queryset

    def get_serializer_class(self):
        return LeadershipFileListSerializer if self.action == 'list' else LeadershipFileSerializer

    @action(detail=False, methods=['post'], url_path='upload-excel')
    def upload_excel(self, request):
        upload = request.FILES.get('file')
        if not upload:
            return Response({'error': '请上传文件'}, status=status.HTTP_400_BAD_REQUEST)
        if not upload.name.lower().endswith('.xlsx'):
            return Response({'error': '请使用 Excel/WPS 另存为标准 .xlsx 文件后再上传'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            version_date = self._resolve_version_date(request, upload)
        except Exception as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if LeadershipAssessmentFile.objects.filter(version_date=version_date).exists():
            return Response({'error': f'{version_date} 已有领导班子研判数据，同一期间不允许重复上传，请进入该期间逐条修改'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            content = upload.read()
            if not content.startswith(b'PK\x03\x04'):
                return Response({'error': '文件扩展名与实际格式不一致或为旧格式。请用 Excel/WPS“另存为”标准 .xlsx 后再上传'}, status=status.HTTP_400_BAD_REQUEST)
            workbook = pd.ExcelFile(BytesIO(content), engine='openpyxl')
            if '班子' not in workbook.sheet_names:
                return Response({'error': 'Excel文件中必须包含“班子”工作表'}, status=status.HTTP_400_BAD_REQUEST)
            frame = pd.read_excel(workbook, sheet_name='班子', header=None)
            records = [self._parse_row(row) for _, row in frame.iloc[3:].iterrows()]
            records = [record for record in records if record]
        except Exception as exc:
            return Response({'error': f'文件解析失败: {exc}'}, status=status.HTTP_400_BAD_REQUEST)
        if not records:
            return Response({'error': '未识别到可导入的数据行，请确认第4行起的数据格式'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            with transaction.atomic():
                assessment_file = LeadershipAssessmentFile.objects.create(
                    file_name=upload.name, version_date=version_date, uploaded_by=request.user,
                    source_file=ContentFile(content, name=upload.name), total_records=len(records)
                )
                LeadershipAssessmentRecord.objects.bulk_create(
                    [LeadershipAssessmentRecord(file=assessment_file, **record) for record in records], batch_size=200
                )
        except IntegrityError:
            return Response({'error': f'{version_date} 已有领导班子研判数据，同一期间不允许重复上传'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'message': f'导入成功，共导入 {len(records)} 条记录', 'file_id': str(assessment_file.id),
                         'file_name': assessment_file.file_name, 'version_date': str(assessment_file.version_date),
                         'total_records': assessment_file.total_records}, status=status.HTTP_201_CREATED)

    @staticmethod
    def _resolve_version_date(request, upload):
        supplied = request.data.get('version_date')
        if supplied:
            try:
                return date.fromisoformat(str(supplied))
            except ValueError as exc:
                raise ValueError('研判期间必须是 YYYY-MM-DD 格式') from exc
        return LeadershipAssessmentFile.validate_file_name(upload.name)

    def _parse_row(self, row):
        name = _text(row, 0)
        if not name:
            return None
        integer_fields = ('leadership_count', 'vacancy_count', 'team_leader_count', 'team_leader_vacancy_count',
                          'max_age', 'min_age', 'postgraduate_count', 'undergraduate_count', 'college_below_count',
                          'over_5_years_count', 'three_to_5_years_count', 'under_3_years_count',
                          'long_term_office_count', 'balanced_count', 'long_term_prison_count')
        result = {'name': name}
        for index, field in enumerate(integer_fields[:4], 1):
            result[field] = _integer(row, index)
        result['average_age'] = _number(row, 5)
        for index, field in enumerate(integer_fields[4:], 6):
            result[field] = _integer(row, index)
        result.update({
            'ability_assessment': _text(row, 17), 'performance_2023': _text(row, 18),
            'performance_2024': _text(row, 19), 'shortcomings': _text(row, 20),
            'secretary_score': _number(row, 21), 'democratic_score': _number(row, 22),
            'total_score': _number(row, 23), 'approval_rate': _number(row, 24),
            'ranking': _integer(row, 25), 'adjustment_suggestion': _text(row, 26),
        })
        return result

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        files = LeadershipAssessmentFile.objects.all()
        if request.query_params.get('version_date'):
            files = files.filter(version_date=request.query_params['version_date'])
        records = LeadershipAssessmentRecord.objects.filter(file__in=files.filter(is_active=True))
        return Response({'total_files': files.count(), 'active_files': files.filter(is_active=True).count(),
                         'total_records': files.aggregate(total=Sum('total_records'))['total'] or 0,
                         'average_age': round(records.aggregate(value=Avg('average_age'))['value'] or 0, 2),
                         'average_score': round(records.aggregate(value=Avg('total_score'))['value'] or 0, 2)})


class LeadershipRecordViewSet(viewsets.ModelViewSet):
    permission_classes = [HasAssessmentPermission]

    def get_queryset(self):
        queryset = LeadershipAssessmentRecord.objects.select_related('file', 'file__uploaded_by')
        params = self.request.query_params
        if params.get('file'):
            queryset = queryset.filter(file_id=params['file'])
        if params.get('version_date'):
            queryset = queryset.filter(file__version_date=params['version_date'])
        if params.get('is_active') is not None:
            queryset = queryset.filter(file__is_active=params['is_active'].lower() == 'true')
        if params.get('name'):
            queryset = queryset.filter(name__icontains=params['name'])
        if params.get('ranking_min'):
            queryset = queryset.filter(ranking__gte=params['ranking_min'])
        if params.get('ranking_max'):
            queryset = queryset.filter(ranking__lte=params['ranking_max'])
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return LeadershipRecordListSerializer
        if self.action == 'retrieve':
            return LeadershipRecordDetailSerializer
        return LeadershipRecordSerializer

    def perform_update(self, serializer):
        record_change(
            instance=serializer.instance,
            validated_data=serializer.validated_data,
            user=self.request.user,
            resource_type=AssessmentChangeLog.ResourceType.LEADERSHIP_RECORD,
        )

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        record = self.get_object()
        logs = AssessmentChangeLog.objects.filter(
            resource_type=AssessmentChangeLog.ResourceType.LEADERSHIP_RECORD,
            resource_id=record.id,
        ).select_related('editor')
        return Response([
            {
                'id': str(log.id), 'changed_fields': log.changed_fields,
                'before_values': log.before_values, 'after_values': log.after_values,
                'editor_name': getattr(log.editor, 'real_name', '') or getattr(log.editor, 'username', '') if log.editor else '',
                'created_at': log.created_at,
            }
            for log in logs
        ])
