import pandas as pd
from datetime import datetime
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from .models import PersonnelRoster, Cadre, CadreResume
from .serializers import (
    PersonnelRosterSerializer,
    PersonnelRosterListSerializer,
    CadreSerializer,
    CadreResumeSerializer
)


class PersonnelRosterViewSet(viewsets.ModelViewSet):
    """花名册视图集"""
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        """获取查询集"""
        queryset = PersonnelRoster.objects.select_related('created_by').all()

        # 搜索过滤
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(department__icontains=search) |
                Q(police_number__icontains=search) |
                Q(id_card__icontains=search)
            )

        # 部门过滤
        department = self.request.query_params.get('department', None)
        if department:
            queryset = queryset.filter(department__icontains=department)

        # 性别过滤
        gender = self.request.query_params.get('gender', None)
        if gender:
            queryset = queryset.filter(gender=gender)

        # 政治面貌过滤
        political_status = self.request.query_params.get('political_status', None)
        if political_status:
            queryset = queryset.filter(political_status=political_status)

        if self.request.query_params.get('leadership_scope') == 'middle':
            # 附件8：中层领导含工作团队负责人；排除监狱领导班子。
            queryset = queryset.filter(
                Q(position_category__in=['领导职务', '内定领导职务', '监区工作团队正职', '监区工作团队副职'])
                | Q(position__contains='团队') | Q(position__contains='分监区长')
            ).exclude(department='监狱领导').exclude(position_rank__startswith='县处级')

        return queryset

    def get_serializer_class(self):
        """根据操作返回不同的序列化器"""
        if self.action == 'list':
            return PersonnelRosterListSerializer
        return PersonnelRosterSerializer

    def perform_create(self, serializer):
        """创建时自动设置创建人"""
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['post'], url_path='upload-excel')
    def upload_excel(self, request):
        """
        上传 Excel 并导入花名册。
        默认 replace=true：清空原有花名册后整表覆盖写入。
        传 replace=false 时追加导入（唯一冲突跳过）。
        """
        from django.db import transaction

        from .roster_import import (
            build_column_map,
            required_columns_present,
            row_to_roster_data,
        )

        if 'file' not in request.FILES:
            return Response(
                {'error': '请上传文件'},
                status=status.HTTP_400_BAD_REQUEST
            )

        file = request.FILES['file']
        replace_raw = request.data.get('replace', 'true')
        replace = str(replace_raw).strip().lower() in {'1', 'true', 'yes', 'on'}

        # 检查文件扩展名
        if not file.name.lower().endswith(('.xlsx', '.xls')):
            return Response(
                {'error': '只支持Excel文件格式 (.xlsx, .xls)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 读取Excel文件（.xls 优先 xlrd）
            try:
                df = pd.read_excel(file, engine='xlrd' if file.name.lower().endswith('.xls') else None)
            except Exception:
                file.seek(0)
                df = pd.read_excel(file)

            column_map = build_column_map(df.columns)
            missing_columns = required_columns_present(column_map)
            if missing_columns:
                return Response(
                    {
                        'error': f'Excel文件缺少必需的列: {", ".join(missing_columns)}',
                        'required_columns': ['姓名', '部门'],
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            total_rows = len(df)
            success_count = 0
            error_count = 0
            errors = []
            roster_list = []
            # 文件内去重，避免覆盖写入时唯一键冲突
            seen_id_cards = set()
            seen_police_numbers = set()

            for index, row in df.iterrows():
                try:
                    roster_data = row_to_roster_data(row, column_map, fallback_serial=index + 1)
                    if not roster_data.get('name'):
                        raise ValueError('姓名为空')
                    if not roster_data.get('department'):
                        raise ValueError('部门为空')
                    if roster_data.get('gender') not in {'M', 'F', 'U'}:
                        roster_data['gender'] = 'U'

                    id_card = roster_data.get('id_card') or None
                    police_number = roster_data.get('police_number') or None
                    if id_card:
                        if id_card in seen_id_cards:
                            raise ValueError(f'文件内身份证号重复：{id_card}')
                        seen_id_cards.add(id_card)
                    if police_number:
                        if police_number in seen_police_numbers:
                            raise ValueError(f'文件内警号重复：{police_number}')
                        seen_police_numbers.add(police_number)

                    roster_data['id_card'] = id_card
                    roster_data['police_number'] = police_number
                    roster = PersonnelRoster(**roster_data)
                    roster.full_clean(exclude=['created_by'])
                    roster_list.append(roster)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    errors.append({
                        'row': index + 2,
                        'name': str(row.get(column_map.get('姓名', '姓名'), '') or ''),
                        'error': str(e)
                    })

            deleted_count = 0
            created_count = 0
            if replace and not roster_list:
                return Response({
                    'error': '覆盖导入失败：文件中没有可写入的有效记录，已保留原有花名册。',
                    'total': total_rows,
                    'success_count': 0,
                    'created_count': 0,
                    'deleted_count': 0,
                    'error_count': error_count,
                    'errors': errors[:10],
                }, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                if replace:
                    deleted_count = PersonnelRoster.objects.count()
                    PersonnelRoster.objects.all().delete()
                    PersonnelRoster.objects.bulk_create(roster_list, batch_size=100)
                    created_count = len(roster_list)
                elif roster_list:
                    before = PersonnelRoster.objects.count()
                    PersonnelRoster.objects.bulk_create(roster_list, batch_size=100, ignore_conflicts=True)
                    created_count = PersonnelRoster.objects.count() - before

            from .org_alignment import sync_memberships_from_rosters
            # bulk_create 不发 post_save，导入后按花名册当前部门对齐账号主部门。
            sync_memberships_from_rosters(
                PersonnelRoster.objects.all() if replace else roster_list,
                actor=request.user,
            )

            mode_label = '覆盖导入' if replace else '追加导入'
            return Response({
                'message': (
                    f'{mode_label}完成！删除原有 {deleted_count} 条，写入 {created_count} 条，'
                    f'解析成功 {success_count} 条，失败 {error_count} 条'
                    if replace else
                    f'{mode_label}完成！新增 {created_count} 条，解析成功 {success_count} 条，失败 {error_count} 条'
                ),
                'mode': 'replace' if replace else 'append',
                'total': total_rows,
                'success_count': success_count,
                'created_count': created_count,
                'deleted_count': deleted_count,
                'error_count': error_count,
                'errors': errors[:10]
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': f'文件处理失败: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """统计信息"""
        from django.db.models import Count

        total = PersonnelRoster.objects.count()
        departments = PersonnelRoster.objects.values('department').distinct().count()
        gender_stats = PersonnelRoster.objects.values('gender').annotate(count=Count('id'))

        return Response({
            'total': total,
            'departments': departments,
            'gender_stats': list(gender_stats),
        })

    @action(detail=False, methods=['get'], url_path='download-template')
    def download_template(self, request):
        """下载花名册导入模板（新版：改进要求/新版花名册）"""
        from pathlib import Path
        from django.http import FileResponse

        doc_dir = Path(__file__).resolve().parent.parent / '文档'
        candidates = [
            doc_dir / '花名册数据模版.xls',
            doc_dir / '花名册数据模版.xlsx',
        ]
        template_path = next((path for path in candidates if path.exists()), None)
        if not template_path:
            return Response({'error': '模板文件不存在'}, status=status.HTTP_404_NOT_FOUND)

        content_types = {
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        }
        suffix = template_path.suffix.lower()
        return FileResponse(
            template_path.open('rb'),
            as_attachment=True,
            filename=f'花名册数据模版{suffix}',
            content_type=content_types.get(suffix, 'application/octet-stream'),
        )

    def _map_gender(self, value):
        """映射性别"""
        if pd.isna(value):
            return 'U'
        value = str(value).strip()
        if value == '男':
            return 'M'
        elif value == '女':
            return 'F'
        return 'U'

    def _parse_date(self, value):
        """解析日期"""
        if pd.isna(value) or value == '':
            return None

        try:
            # 如果是字符串
            if isinstance(value, str):
                # 尝试多种日期格式
                for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d', '%Y%m%d']:
                    try:
                        return datetime.strptime(value, fmt).date()
                    except ValueError:
                        continue
                # 尝试 pandas 的日期解析
                return pd.to_datetime(value).date()

            # 如果已经是 Timestamp 或 datetime
            return pd.to_datetime(value).date()

        except Exception:
            return None


class CadreViewSet(viewsets.ModelViewSet):
    """干部主档视图集"""
    permission_classes = [IsAuthenticated]

    queryset = Cadre.objects.all()
    serializer_class = CadreSerializer

    def get_queryset(self):
        """获取查询集"""
        queryset = Cadre.objects.all()

        # 搜索过滤
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(cadre_code__icontains=search)
            )

        return queryset


class CadreResumeViewSet(viewsets.ModelViewSet):
    """干部履历视图集"""
    permission_classes = [IsAuthenticated]

    queryset = CadreResume.objects.select_related('cadre', 'org_unit').all()
    serializer_class = CadreResumeSerializer

    def get_queryset(self):
        """获取查询集"""
        queryset = CadreResume.objects.all()

        # 按干部过滤
        cadre_id = self.request.query_params.get('cadre', None)
        if cadre_id:
            queryset = queryset.filter(cadre_id=cadre_id)

        return queryset
