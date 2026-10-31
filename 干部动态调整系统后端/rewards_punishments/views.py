from collections import Counter
from datetime import date, datetime
from io import BytesIO
import re

import pandas as pd
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from .models import RewardImportFile, RewardRecipientType, RewardRecord
from .permissions import HasRewardPermission
from .serializers import RewardImportFileSerializer, RewardRecordSerializer
from cadres.org_alignment import roster_department_by_names


HEADER_ALIASES = {
    'recipient_name': {'姓名', '集体名称', '单位名称', '获奖对象', '受奖对象', '名称', '获奖单位', '单位(姓名)'},
    'award_level': {'级别', '奖励级别', '获奖级别', '授奖等级'},
    'approval_year': {'批准年度', '年度', '获奖年度'},
    'award_content': {'奖励情况', '奖励内容', '奖励名称', '奖励项目', '荣誉称号'},
    'approval_date': {'批准时间', '批准日期', '获奖时间', '授奖时间'},
    'document_number': {'文号', '文件号', '批准文号', '授奖文件名号'},
    'remark': {'备注'},
}


def _text(value):
    if value is None or pd.isna(value):
        return ''
    text = str(value).strip()
    return '' if text.lower() in {'nan', 'nat', 'none'} else text


def _normalise_header(value):
    return _text(value).replace(' ', '').replace('\n', '').replace('（', '(').replace('）', ')')


def _parse_year(value):
    text = _text(value)
    if not text:
        return None
    match = re.search(r'(?<!\d)(?:19|20|21)\d{2}(?!\d)', text)
    if match:
        year = int(match.group())
    else:
        try:
            year = int(float(text))
        except (TypeError, ValueError):
            return None
    return year if 1900 <= year <= 2200 else None


def _parse_date(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    parsed = pd.to_datetime(_text(value), errors='coerce')
    return None if pd.isna(parsed) else parsed.date()


def _find_header(frame):
    """在前十行内匹配源表表头，兼容个人表和各集体表。"""
    for row_index in range(min(10, len(frame.index))):
        mapping = {}
        for column_index, value in enumerate(frame.iloc[row_index]):
            header = _normalise_header(value)
            for field, aliases in HEADER_ALIASES.items():
                if header in aliases and field not in mapping:
                    mapping[field] = column_index
        has_identity_and_content = {'recipient_name', 'award_content'} <= set(mapping)
        if has_identity_and_content and ({'approval_year', 'approval_date'} & set(mapping)):
            return row_index, mapping
    return None, None


def _parse_thirty_year_list(frame, sheet_name):
    """导入源文件中按年度横向排布的“从事监狱工作三十年”奖章名单。"""
    for header_row in range(min(10, len(frame.index))):
        year_columns = [(column, _parse_year(value)) for column, value in enumerate(frame.iloc[header_row])]
        year_columns = [(column, year) for column, year in year_columns if year]
        if not year_columns:
            continue
        records = []
        for row_index in range(header_row + 1, len(frame.index)):
            for column, year in year_columns:
                recipient_name = _text(frame.iloc[row_index, column])
                if not recipient_name:
                    continue
                remark = _text(frame.iloc[row_index, column + 1]) if column + 1 < len(frame.columns) else ''
                records.append({
                    'recipient_type': RewardRecipientType.INDIVIDUAL,
                    'recipient_name': recipient_name,
                    'award_level': '',
                    'approval_year': year,
                    'award_content': '从事监狱工作三十年奖章',
                    'approval_date': None,
                    'document_number': '',
                    'remark': remark,
                    'source_sheet': sheet_name,
                    'source_row': row_index + 1,
                })
        return records, None
    return [], '未识别到年度名单表头'


def _parse_sheet(frame, sheet_name):
    if '从事监狱工作三十年' in sheet_name:
        return _parse_thirty_year_list(frame, sheet_name)

    header_row, columns = _find_header(frame)
    if header_row is None:
        return [], '未识别到奖励表头'

    recipient_type = (
        RewardRecipientType.INDIVIDUAL
        if sheet_name.strip() == '个人'
        else RewardRecipientType.COLLECTIVE
    )
    records = []
    previous_recipient_name = ''
    for row_index in range(header_row + 1, len(frame.index)):
        row = frame.iloc[row_index]
        value = lambda field: _text(row.iloc[columns[field]]) if field in columns else ''
        recipient_name = value('recipient_name')
        if recipient_name:
            previous_recipient_name = recipient_name
        elif recipient_type == RewardRecipientType.COLLECTIVE:
            recipient_name = previous_recipient_name
        if not recipient_name or recipient_name == '这一行绝对不能删':
            continue
        approval_date = _parse_date(row.iloc[columns['approval_date']]) if 'approval_date' in columns else None
        payload = {
            'recipient_type': recipient_type,
            'recipient_name': recipient_name,
            'award_level': value('award_level'),
            'approval_year': _parse_year(value('approval_year')) or (approval_date.year if approval_date else None),
            'award_content': value('award_content'),
            'approval_date': approval_date,
            'document_number': value('document_number'),
            'remark': value('remark'),
            'source_sheet': sheet_name,
            'source_row': row_index + 1,
        }
        if any(payload[key] for key in ('award_level', 'approval_year', 'award_content', 'approval_date', 'document_number', 'remark')):
            records.append(payload)
    return records, None


class RewardImportFileViewSet(viewsets.ModelViewSet):
    serializer_class = RewardImportFileSerializer
    permission_classes = [HasRewardPermission]
    parser_classes = [MultiPartParser, FormParser]
    queryset = RewardImportFile.objects.select_related('uploaded_by').all()

    @action(detail=False, methods=['post'], url_path='upload-excel')
    def upload_excel(self, request):
        upload = request.FILES.get('file')
        if not upload:
            return Response({'error': '请上传奖励汇总 Excel 文件'}, status=status.HTTP_400_BAD_REQUEST)
        suffix = upload.name.rsplit('.', 1)[-1].lower() if '.' in upload.name else ''
        if suffix not in {'xls', 'xlsx'}:
            return Response({'error': '仅支持 .xls 或 .xlsx 格式的奖励汇总表'}, status=status.HTTP_400_BAD_REQUEST)

        content = upload.read()
        try:
            engine = 'xlrd' if suffix == 'xls' else 'openpyxl'
            workbook = pd.ExcelFile(BytesIO(content), engine=engine)
        except ImportError:
            return Response({'error': '服务器缺少旧版 .xls 解析依赖，请安装 xlrd 后重试'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({'error': f'文件解析失败：{exc}'}, status=status.HTTP_400_BAD_REQUEST)

        parsed_records, skipped_sheets = [], {}
        try:
            for sheet_name in workbook.sheet_names:
                frame = pd.read_excel(workbook, sheet_name=sheet_name, header=None)
                records, reason = _parse_sheet(frame, sheet_name)
                if reason:
                    skipped_sheets[sheet_name] = reason
                else:
                    parsed_records.extend(records)
        except Exception as exc:
            return Response({'error': f'奖励记录解析失败：{exc}'}, status=status.HTTP_400_BAD_REQUEST)

        if not parsed_records:
            return Response({
                'error': '未识别到可导入奖励记录，请确认表头包含名称、奖励情况及批准年度或时间',
                'skipped_sheets': skipped_sheets,
            }, status=status.HTTP_400_BAD_REQUEST)

        counts = Counter(record['recipient_type'] for record in parsed_records)
        with transaction.atomic():
            import_file = RewardImportFile.objects.create(
                file_name=upload.name,
                source_file=ContentFile(content, name=upload.name),
                uploaded_by=request.user,
                total_records=len(parsed_records),
                record_counts={
                    'individual': counts[RewardRecipientType.INDIVIDUAL],
                    'collective': counts[RewardRecipientType.COLLECTIVE],
                },
            )
            RewardRecord.objects.bulk_create([
                RewardRecord(import_file=import_file, created_by=request.user, **record)
                for record in parsed_records
            ], batch_size=500)

        return Response({
            'message': f'导入成功，共保存 {len(parsed_records)} 条奖励记录',
            'file_id': str(import_file.id),
            'file_name': import_file.file_name,
            'total_records': import_file.total_records,
            'record_counts': import_file.record_counts,
            'skipped_sheets': skipped_sheets,
        }, status=status.HTTP_201_CREATED)


class RewardRecordViewSet(viewsets.ModelViewSet):
    serializer_class = RewardRecordSerializer
    permission_classes = [HasRewardPermission]

    def get_serializer(self, *args, **kwargs):
        serializer = super().get_serializer(*args, **kwargs)
        instance = args[0] if args else kwargs.get('instance')
        names = []
        if instance is None:
            pass
        elif getattr(instance, '__iter__', None) and not isinstance(instance, (str, bytes, RewardRecord)):
            names = [item.recipient_name for item in instance if item.recipient_type == RewardRecipientType.INDIVIDUAL]
        elif getattr(instance, 'recipient_name', None):
            names = [instance.recipient_name]
        serializer.context['roster_departments'] = roster_department_by_names(names)
        return serializer

    def get_queryset(self):
        queryset = RewardRecord.objects.select_related('import_file', 'created_by').all()
        params = self.request.query_params
        if params.get('recipient_type'):
            queryset = queryset.filter(recipient_type=params['recipient_type'])
        if params.get('search'):
            queryset = queryset.filter(recipient_name__icontains=params['search'])
        if params.get('award_level'):
            queryset = queryset.filter(award_level__icontains=params['award_level'])
        if params.get('approval_year'):
            queryset = queryset.filter(approval_year=params['approval_year'])
        if params.get('year_start'):
            queryset = queryset.filter(approval_year__gte=params['year_start'])
        if params.get('year_end'):
            queryset = queryset.filter(approval_year__lte=params['year_end'])
        if params.get('source_sheet'):
            queryset = queryset.filter(source_sheet=params['source_sheet'])
        if params.get('import_file'):
            queryset = queryset.filter(import_file_id=params['import_file'])
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        queryset = self.get_queryset()
        total = queryset.count()
        by_type = {
            item['recipient_type']: item['count']
            for item in queryset.values('recipient_type').annotate(count=Count('id'))
        }
        by_year = list(
            queryset.exclude(approval_year__isnull=True)
            .values('approval_year')
            .annotate(count=Count('id'))
            .order_by('-approval_year')
        )
        by_level = list(
            queryset.exclude(award_level='')
            .values('award_level')
            .annotate(count=Count('id'))
            .order_by('-count', 'award_level')[:10]
        )
        return Response({
            'total': total,
            'individual_count': by_type.get(RewardRecipientType.INDIVIDUAL, 0),
            'collective_count': by_type.get(RewardRecipientType.COLLECTIVE, 0),
            'yearly_counts': by_year,
            'level_counts': by_level,
        })
