"""支部管理：CRUD、纳入部门、模板下载与覆盖导入。"""
from io import BytesIO

import pandas as pd
from django.db.models import Prefetch
from django.http import FileResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import HasPermissionCode

from .branch_import import (
    apply_branch_assignments,
    build_template_bytes,
    parse_branch_rows,
    resolve_assignments,
)
from .models import OrgUnit, UnitType
from .branch_catalog import apply_catalog, catalog_preview
from .serializers import (
    AssignableDepartmentSerializer,
    AssignDepartmentsSerializer,
    BranchSerializer,
)


class BranchViewSet(viewsets.ModelViewSet):
    """支部视图集。复用 orgs:view/create/edit/delete。"""
    permission_classes = [IsAuthenticated, HasPermissionCode]
    serializer_class = BranchSerializer
    pagination_class = None

    def get_permission_code(self):
        if self.action == 'reference_catalog':
            return 'orgs:view' if self.request.method == 'GET' else 'orgs:create'
        if self.action in {'list', 'retrieve', 'download_template', 'assignable_departments'}:
            return 'orgs:view'
        if self.action == 'create':
            return 'orgs:create'
        if self.action == 'destroy':
            return 'orgs:delete'
        return 'orgs:edit'

    @action(detail=False, methods=['get', 'post'], url_path='reference-catalog')
    def reference_catalog(self, request):
        if request.method == 'GET':
            return Response(catalog_preview())
        # 初始化既创建组织又更改归属，必须同时有创建和编辑权限。
        permissions = {code for link in request.user.user_roles.all()
                       if link.role.is_active for code in link.role.permissions}
        if not request.user.is_superuser and 'orgs:edit' not in permissions:
            return Response({'error': '需要组织编辑权限'}, status=status.HTTP_403_FORBIDDEN)
        return Response(apply_catalog())

    def get_queryset(self):
        queryset = OrgUnit.objects.filter(unit_type=UnitType.BRANCH).prefetch_related(
            Prefetch(
                'children',
                queryset=OrgUnit.objects.exclude(unit_type=UnitType.BRANCH).order_by('sort_order', 'name'),
            )
        )
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        is_active = self.request.query_params.get('is_active')
        if is_active is not None and is_active != '':
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        return queryset.order_by('sort_order', 'name')

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.children.exists():
            return Response(
                {'error': '该支部下仍有部门，请先移出部门或改为停用'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='assignable-departments')
    def assignable_departments(self, request):
        queryset = OrgUnit.objects.exclude(unit_type=UnitType.BRANCH).select_related('parent').order_by(
            'sort_order', 'name'
        )
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        return Response(AssignableDepartmentSerializer(queryset, many=True).data)

    @action(detail=True, methods=['post'], url_path='assign-departments')
    def assign_departments(self, request, pk=None):
        branch = self.get_object()
        serializer = AssignDepartmentsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        departments = list(OrgUnit.objects.filter(id__in=serializer.validated_data['department_ids']))
        found_ids = {item.id for item in departments}
        missing = [str(item) for item in serializer.validated_data['department_ids'] if item not in found_ids]
        if missing:
            return Response({'error': f'部门不存在: {", ".join(missing)}'}, status=status.HTTP_400_BAD_REQUEST)

        assigned = []
        for department in departments:
            if department.unit_type == UnitType.BRANCH:
                return Response(
                    {'error': f'「{department.name}」是支部，不能作为部门纳入'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if branch in department.get_descendants():
                return Response(
                    {'error': f'不能将部门「{department.name}」纳入其下级支部'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            department.parent = branch
            department.save(update_fields=['parent', 'updated_at'])
            assigned.append(department.name)
        return Response({'message': f'已将 {len(assigned)} 个部门纳入「{branch.name}」', 'assigned': assigned})

    @action(detail=True, methods=['post'], url_path='remove-departments')
    def remove_departments(self, request, pk=None):
        branch = self.get_object()
        serializer = AssignDepartmentsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = OrgUnit.objects.filter(
            id__in=serializer.validated_data['department_ids'],
            parent=branch,
        ).exclude(unit_type=UnitType.BRANCH).update(parent=None)
        return Response({'message': f'已从「{branch.name}」移出 {updated} 个部门', 'removed_count': updated})

    @action(detail=False, methods=['get'], url_path='download-template')
    def download_template(self, request):
        buffer = BytesIO(build_template_bytes())
        return FileResponse(
            buffer,
            as_attachment=True,
            filename='支部部门关系导入模板.xlsx',
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

    @action(
        detail=False,
        methods=['post'],
        url_path='upload-excel',
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_excel(self, request):
        if 'file' not in request.FILES:
            return Response({'error': '请上传文件'}, status=status.HTTP_400_BAD_REQUEST)

        uploaded = request.FILES['file']
        replace_raw = request.data.get('replace', 'true')
        replace = str(replace_raw).strip().lower() in {'1', 'true', 'yes', 'on'}
        if not uploaded.name.lower().endswith(('.xlsx', '.xls')):
            return Response({'error': '只支持Excel文件格式 (.xlsx, .xls)'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            try:
                dataframe = pd.read_excel(
                    uploaded,
                    engine='xlrd' if uploaded.name.lower().endswith('.xls') else None,
                )
            except Exception:
                uploaded.seek(0)
                dataframe = pd.read_excel(uploaded)

            parsed_rows, parse_errors = parse_branch_rows(dataframe)
            resolved, resolve_errors = resolve_assignments(parsed_rows) if parsed_rows else ([], [])
            errors = parse_errors + resolve_errors
            if not parsed_rows and not errors:
                return Response({'error': '没有有效的数据行'}, status=status.HTTP_400_BAD_REQUEST)
            if errors:
                return Response(
                    {
                        'error': '覆盖导入失败，存在无法匹配的支部或部门',
                        'errors': errors[:50],
                        'error_count': len(errors),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            result = apply_branch_assignments(resolved, replace=replace)
            mode_label = '覆盖导入' if replace else '追加导入'
            return Response(
                {
                    'message': (
                        f'{mode_label}完成！按模板归属 {result["mapped_count"]} 个部门，'
                        f'新纳入 {result["assigned_count"]} 个'
                        + (f'，移出原支部 {result["unassigned_count"]} 个' if replace else '')
                    ),
                    'mode': 'replace' if replace else 'append',
                    'total': len(dataframe),
                    'success_count': result['mapped_count'],
                    'assigned_count': result['assigned_count'],
                    'unassigned_count': result['unassigned_count'],
                    'error_count': 0,
                    'errors': [],
                },
                status=status.HTTP_201_CREATED,
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({'error': f'文件处理失败: {exc}'}, status=status.HTTP_400_BAD_REQUEST)
