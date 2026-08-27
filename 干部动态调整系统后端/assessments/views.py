from collections import Counter
from datetime import date
from io import BytesIO

import pandas as pd
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.db.models import Sum
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .audit import record_change
from .models import AssessmentChangeLog, AssessmentFile, AssessmentRecord, PositionCategory
from .permissions import HasAssessmentPermission
from .serializers import (AssessmentFileListSerializer, AssessmentFileSerializer,
                          AssessmentRecordDetailSerializer, AssessmentRecordListSerializer,
                          AssessmentRecordSerializer)


SHEET_CATEGORY_MAP = {
    '科室正职': PositionCategory.SECTION_CHIEF, '科室副职': PositionCategory.SECTION_DEPUTY,
    '事、群、团队': PositionCategory.INSTITUTION_2, '监区长': PositionCategory.PRISON_WARDEN,
    '教导员': PositionCategory.INSTRUCTOR, '副区（狱政）': PositionCategory.DEPUTY_PRISON,
    '副区（生产）': PositionCategory.DEPUTY_PRODUCTION, '副区（教育）': PositionCategory.DEPUTY_EDUCATION,
    '监区工作团队': PositionCategory.PRISON_TEAM,
}


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


def _date(row, index):
    if index >= len(row) or pd.isna(row.iloc[index]):
        return None
    try:
        return pd.to_datetime(row.iloc[index]).date()
    except (TypeError, ValueError):
        return None


class AssessmentFileViewSet(viewsets.ModelViewSet):
    permission_classes = [HasAssessmentPermission]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        queryset = AssessmentFile.objects.select_related('uploaded_by')
        active = self.request.query_params.get('is_active')
        if active is not None:
            queryset = queryset.filter(is_active=active.lower() == 'true')
        if self.request.query_params.get('start_date'):
            queryset = queryset.filter(version_date__gte=self.request.query_params['start_date'])
        if self.request.query_params.get('end_date'):
            queryset = queryset.filter(version_date__lte=self.request.query_params['end_date'])
        return queryset

    def get_serializer_class(self):
        return AssessmentFileListSerializer if self.action == 'list' else AssessmentFileSerializer

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
        if AssessmentFile.objects.filter(version_date=version_date).exists():
            return Response({'error': f'{version_date} 已有干部研判数据，同一期间不允许重复上传，请进入该期间逐条修改'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            content = upload.read()
            if not content.startswith(b'PK\x03\x04'):
                return Response({'error': '文件扩展名与实际格式不一致或为旧格式。请用 Excel/WPS“另存为”标准 .xlsx 后再上传'}, status=status.HTTP_400_BAD_REQUEST)
            workbook = pd.ExcelFile(BytesIO(content), engine='openpyxl')
            records = []
            for sheet, category in SHEET_CATEGORY_MAP.items():
                if sheet not in workbook.sheet_names:
                    continue
                frame = pd.read_excel(workbook, sheet_name=sheet, header=None)
                for _, row in frame.iloc[3:].iterrows():
                    record = self._parse_row(row, category)
                    if record:
                        records.append(record)
        except Exception as exc:
            return Response({'error': f'文件解析失败: {exc}'}, status=status.HTTP_400_BAD_REQUEST)
        if not records:
            return Response({'error': '未识别到可导入的数据行，请确认工作表名称和第4行起的数据格式'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            with transaction.atomic():
                assessment_file = AssessmentFile.objects.create(
                    file_name=upload.name, version_date=version_date, uploaded_by=request.user,
                    source_file=ContentFile(content, name=upload.name), total_records=len(records),
                    category_counts=dict(Counter(item['position_category'] for item in records)),
                )
                AssessmentRecord.objects.bulk_create(
                    [AssessmentRecord(file=assessment_file, **record) for record in records], batch_size=200
                )
        except IntegrityError:
            return Response({'error': f'{version_date} 已有干部研判数据，同一期间不允许重复上传'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'message': f'导入成功，共导入 {len(records)} 条记录', 'file_id': str(assessment_file.id),
                         'file_name': assessment_file.file_name, 'version_date': str(assessment_file.version_date),
                         'total_records': assessment_file.total_records, 'category_counts': assessment_file.category_counts},
                        status=status.HTTP_201_CREATED)

    @staticmethod
    def _resolve_version_date(request, upload):
        supplied = request.data.get('version_date')
        if supplied:
            try:
                return date.fromisoformat(str(supplied))
            except ValueError as exc:
                raise ValueError('研判期间必须是 YYYY-MM-DD 格式') from exc
        return AssessmentFile.validate_file_name(upload.name)

    def _parse_row(self, row, category):
        name = _text(row, 0)
        if not name:
            return None
        return {
            'position_category': category, 'name': name, 'department': _text(row, 1), 'position': _text(row, 2),
            'age': _integer(row, 3), 'health_status': _text(row, 4), 'education': _text(row, 5),
            'professional_title': _text(row, 6), 'join_prison_date': _date(row, 7),
            'service_years': _integer(row, 8), 'office_work_years': _integer(row, 9),
            'prison_work_years': _integer(row, 10), 'main_business': _text(row, 11),
            'annual_assessment_3years': _text(row, 12), 'quarterly_assessment': _text(row, 13),
            'rewards_3years': _text(row, 14), 'penalties_3years': _text(row, 15),
            'main_performance': _text(row, 16), 'personality': _text(row, 17),
            'ability_assessment': _text(row, 18), 'performance_2023': _text(row, 19),
            'performance_2024': _text(row, 20), 'shortcomings': _text(row, 21),
            'evaluation_assessment': _text(row, 22), 'talk_assessment': _text(row, 24),
            'comprehensive_assessment': _text(row, 25), 'seven_looks_score': _number(row, 22),
            'work_recognition_score': _number(row, 23), 'talk_score': _number(row, 24),
            'comprehensive_score': _number(row, 25), 'ranking': _integer(row, 26),
            'adjustment_suggestion': _text(row, 27),
        }

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        files = AssessmentFile.objects.all()
        if request.query_params.get('version_date'):
            files = files.filter(version_date=request.query_params['version_date'])
        active_files = files.filter(is_active=True)
        categories = {label: AssessmentRecord.objects.filter(file__in=active_files, position_category=code).count()
                      for code, label in PositionCategory.choices}
        return Response({'total_files': files.count(), 'active_files': active_files.count(),
                         'total_records': files.aggregate(total=Sum('total_records'))['total'] or 0,
                         'category_stats': {key: value for key, value in categories.items() if value}})


class AssessmentRecordViewSet(viewsets.ModelViewSet):
    permission_classes = [HasAssessmentPermission]

    def get_queryset(self):
        queryset = AssessmentRecord.objects.select_related('file', 'file__uploaded_by')
        params = self.request.query_params
        filters = {'file_id': params.get('file'), 'file__version_date': params.get('version_date'),
                   'position_category': params.get('position_category')}
        queryset = queryset.filter(**{key: value for key, value in filters.items() if value})
        if params.get('is_active') is not None:
            queryset = queryset.filter(file__is_active=params['is_active'].lower() == 'true')
        if params.get('name'):
            queryset = queryset.filter(name__icontains=params['name'])
        if params.get('department'):
            queryset = queryset.filter(department__icontains=params['department'])
        if params.get('ranking_min'):
            queryset = queryset.filter(ranking__gte=params['ranking_min'])
        if params.get('ranking_max'):
            queryset = queryset.filter(ranking__lte=params['ranking_max'])
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return AssessmentRecordListSerializer
        if self.action == 'retrieve':
            return AssessmentRecordDetailSerializer
        return AssessmentRecordSerializer

    def perform_update(self, serializer):
        record_change(
            instance=serializer.instance,
            validated_data=serializer.validated_data,
            user=self.request.user,
            resource_type=AssessmentChangeLog.ResourceType.CADRE_RECORD,
        )

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        record = self.get_object()
        logs = AssessmentChangeLog.objects.filter(
            resource_type=AssessmentChangeLog.ResourceType.CADRE_RECORD,
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
