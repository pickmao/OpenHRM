import pandas as pd
from datetime import datetime
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
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
    parser_classes = [MultiPartParser, FormParser]

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
        上传Excel文件并批量导入花名册数据
        """
        if 'file' not in request.FILES:
            return Response(
                {'error': '请上传文件'},
                status=status.HTTP_400_BAD_REQUEST
            )

        file = request.FILES['file']

        # 检查文件扩展名
        if not file.name.endswith(('.xlsx', '.xls')):
            return Response(
                {'error': '只支持Excel文件格式 (.xlsx, .xls)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 读取Excel文件
            df = pd.read_excel(file)

            # 检查必需的列
            required_columns = ['姓名*', '部门*', '性别*']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return Response(
                    {
                        'error': f'Excel文件缺少必需的列: {", ".join(missing_columns)}',
                        'required_columns': required_columns
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 数据统计
            total_rows = len(df)
            success_count = 0
            error_count = 0
            errors = []

            # 批量创建数据
            roster_list = []
            for index, row in df.iterrows():
                try:
                    # 映射Excel列名到模型字段
                    roster_data = {
                        'serial_number': row.get('序号*', index + 1),
                        'name': row.get('姓名*', ''),
                        'department': row.get('部门*', ''),
                        'gender': self._map_gender(row.get('性别*', '')),
                        'age': row.get('年龄*', None) if pd.notna(row.get('年龄*', None)) else None,
                        'birth_date': self._parse_date(row.get('出生年月*')),
                        'ethnicity': row.get('民族*', ''),
                        'native_place': row.get('籍贯*', ''),
                        'household_registration': row.get('户籍所在地\n（未核对原件）', ''),
                        'working_years': row.get('工龄', None) if pd.notna(row.get('工龄', None)) else None,
                        'join_work_date': self._parse_date(row.get('参加工作时间*')),
                        'join_prison_date': self._parse_date(row.get('参加监狱工作时间*')),
                        'continuous_service_date': self._parse_date(row.get('连续工龄计算时间*')),
                        'has_2years_grassroots': str(row.get('是否有2年基层工作经历', '')),
                        'political_status': row.get('政治面貌*', ''),
                        'join_party_date': self._parse_date(row.get('入党时间*')),
                        'position': str(row.get('职务*', '')) if pd.notna(row.get('职务*', None)) else '',
                        'promotion_category': str(row.get('晋升四高及以上序列分类', '')) if pd.notna(row.get('晋升四高及以上序列分类', None)) else '',
                        'position_category': str(row.get('职务类别', '')) if pd.notna(row.get('职务类别', None)) else '',
                        'current_position_years': str(row.get('任现职年限', '')) if pd.notna(row.get('任现职年限', None)) else '',
                        'current_position_date': self._parse_date(row.get('任现职务时间')),
                        'position_level': str(row.get('职务级别', '')) if pd.notna(row.get('职务级别', None)) else '',
                        'position_rank': str(row.get('职务层次', '')) if pd.notna(row.get('职务层次', None)) else '',
                        'same_level_leadership_years': str(row.get('任同级领导职务年限', '')) if pd.notna(row.get('任同级领导职务年限', None)) else '',
                        'same_level_leadership_date': self._parse_date(row.get('任同级\n领导职务时间')),
                        'same_level_rank_years': str(row.get('任同级领导职务层次时间年限', '')) if pd.notna(row.get('任同级领导职务层次时间年限', None)) else '',
                        'same_level_rank_date': self._parse_date(row.get('任同级领导职务层次时间')),
                        'current_rank_years': str(row.get('任现职级年限（即任现警员职级年限）*', '')) if pd.notna(row.get('任现职级年限（即任现警员职级年限）*', None)) else '',
                        'current_rank_date': self._parse_date(row.get('任现职级时间（即任现警员职级时间）*')),
                        'calculation_start_date': self._parse_date(row.get('量化计分起算时间')),
                        'police_rank': str(row.get('现警员职级*', '')) if pd.notna(row.get('现警员职级*', None)) else '',
                        'police_rank_start_date': self._parse_date(row.get('任现警员职级起算时间')),
                        'first_set_rank': str(row.get('首套警员职级', '')) if pd.notna(row.get('首套警员职级', None)) else '',
                        'first_set_rank_date': self._parse_date(row.get('首套警员职级起算时间')),
                        'first_promote_rank': str(row.get('首晋警员职级', '')) if pd.notna(row.get('首晋警员职级', None)) else '',
                        'first_promote_rank_date': self._parse_date(row.get('首晋警员职级起算时间')),
                        'work_charge': str(row.get('分管工作', '')) if pd.notna(row.get('分管工作', None)) else '',
                        'fulltime_education': str(row.get('全日制教育学历*', '')) if pd.notna(row.get('全日制教育学历*', None)) else '',
                        'fulltime_school': str(row.get('毕业院校*', '')) if pd.notna(row.get('毕业院校*', None)) else '',
                        'fulltime_major': str(row.get('专业*', '')) if pd.notna(row.get('专业*', None)) else '',
                        'fulltime_degree': str(row.get('学位*', '')) if pd.notna(row.get('学位*', None)) else '',
                        'fulltime_start_date': self._parse_date(row.get('入学时间')),
                        'fulltime_graduate_date': self._parse_date(row.get('毕业时间')),
                        'inservice_education': str(row.get('在职学历*', '')) if pd.notna(row.get('在职学历*', None)) else '',
                        'inservice_school': str(row.get('毕业院校*.1', '')) if pd.notna(row.get('毕业院校*.1', None)) else '',
                        'inservice_form': str(row.get('学习形式', '')) if pd.notna(row.get('学习形式', None)) else '',
                        'inservice_major': str(row.get('专业*.1', '')) if pd.notna(row.get('专业*.1', None)) else '',
                        'inservice_degree': str(row.get('学位*.1', '')) if pd.notna(row.get('学位*.1', None)) else '',
                        'inservice_start_date': self._parse_date(row.get('入学时间.1')),
                        'inservice_graduate_date': self._parse_date(row.get('毕业时间.1')),
                        'police_title': str(row.get('警衔*（已更新至20250526）', '')) if pd.notna(row.get('警衔*（已更新至20250526）', None)) else '',
                        'police_number': str(row.get('警号*', '')) if pd.notna(row.get('警号*', None)) else '',
                        'profession_name': str(row.get('专业资格\n名称', '')) if pd.notna(row.get('专业资格\n名称', None)) else '',
                        'profession_level': str(row.get('专业资格级别', '')) if pd.notna(row.get('专业资格级别', None)) else '',
                        'technical_title': str(row.get('专业技术职务', '')) if pd.notna(row.get('专业技术职务', None)) else '',
                        'counseling_cert_level': str(row.get('心理咨询证书级别', '')) if pd.notna(row.get('心理咨询证书级别', None)) else '',
                        'english_level': str(row.get('英语专业', '')) if pd.notna(row.get('英语专业', None)) else '',
                        'remark': str(row.get('备注', '')) if pd.notna(row.get('备注', None)) else '',
                        'quarterly_remark': str(row.get('季度报表备注', '')) if pd.notna(row.get('季度报表备注', None)) else '',
                        'dept_work_years': str(row.get('在本部门工作年限', '')) if pd.notna(row.get('在本部门工作年限', None)) else '',
                        'dept_work_date': self._parse_date(row.get('本部门工作时间*')),
                        'unit_work_years': str(row.get('在本单位年限', '')) if pd.notna(row.get('在本单位年限', None)) else '',
                        'enter_unit_date': self._parse_date(row.get('进入本单位时间*')),
                        'enter_unit_form': str(row.get('进入本单位形式', '')) if pd.notna(row.get('进入本单位形式', None)) else '',
                        'identity_source': str(row.get('身份来源', '')) if pd.notna(row.get('身份来源', None)) else '',
                        'military_experience': str(row.get('军转干/部队经历*', '')) if pd.notna(row.get('军转干/部队经历*', None)) else '',
                        'highest_education': str(row.get('最高学历*', '')) if pd.notna(row.get('最高学历*', None)) else '',
                        'highest_school': str(row.get('最高学历毕业院校*', '')) if pd.notna(row.get('最高学历毕业院校*', None)) else '',
                        'education_level': str(row.get('学历*', '')) if pd.notna(row.get('学历*', None)) else '',
                        'highest_major': str(row.get('最高学历专业*', '')) if pd.notna(row.get('最高学历专业*', None)) else '',
                        'highest_degree': str(row.get('最高学位*', '')) if pd.notna(row.get('最高学位*', None)) else '',
                        'major_category': str(row.get('最高学历专业类别', '')) if pd.notna(row.get('最高学历专业类别', None)) else '',
                        'id_card': str(row.get('身份证号*', '')) if pd.notna(row.get('身份证号*', None)) else '',
                        'id_card_inconsistent': bool(row.get('出生年月与身份证信息不一致', False)),
                        'phone': str(row.get('电话*', '')) if pd.notna(row.get('电话*', None)) else '',
                        'cert_level': str(row.get('证书级别', '')) if pd.notna(row.get('证书级别', None)) else '',
                    }

                    # 创建对象
                    roster = PersonnelRoster(**roster_data)
                    roster.full_clean()  # 验证数据
                    roster_list.append(roster)
                    success_count += 1

                except Exception as e:
                    error_count += 1
                    errors.append({
                        'row': index + 2,  # Excel行号（包含表头）
                        'name': row.get('姓名*', ''),
                        'error': str(e)
                    })

            # 批量插入数据
            if roster_list:
                PersonnelRoster.objects.bulk_create(roster_list, batch_size=100, ignore_conflicts=True)

            return Response({
                'message': f'导入完成！成功: {success_count}条，失败: {error_count}条',
                'total': total_rows,
                'success_count': success_count,
                'error_count': error_count,
                'errors': errors[:10]  # 只返回前10个错误
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
