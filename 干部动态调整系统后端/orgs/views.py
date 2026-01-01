from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404

from .models import OrgUnit, Membership
from .serializers import (
    OrgUnitListSerializer,
    OrgUnitDetailSerializer,
    OrgUnitTreeSerializer,
    MembershipSerializer,
    MembershipCreateSerializer,
    OrgUnitMoveSerializer,
    OrgUnitReorderSerializer,
    OrgUnitManagerSerializer
)


class OrgUnitViewSet(viewsets.ModelViewSet):
    """组织单元视图集"""
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """获取查询集"""
        queryset = OrgUnit.objects.select_related('parent').all()

        # 搜索过滤
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search)
            )

        # 类型过滤
        unit_type = self.request.query_params.get('unit_type', None)
        if unit_type:
            queryset = queryset.filter(unit_type=unit_type)

        # 启用状态过滤
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        # 只获取根节点（无父节点）
        root_only = self.request.query_params.get('root_only', None)
        if root_only and root_only.lower() == 'true':
            queryset = queryset.filter(parent__isnull=True)

        return queryset

    def get_serializer_class(self):
        """根据操作返回不同的序列化器"""
        if self.action == 'list':
            return OrgUnitListSerializer
        elif self.action == 'retrieve':
            return OrgUnitDetailSerializer
        return OrgUnitDetailSerializer

    def perform_create(self, serializer):
        """创建时自动设置创建人"""
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        """删除部门（检查是否有子部门或成员）"""
        instance = self.get_object()

        # 检查是否有子部门
        if instance.children.exists():
            return Response(
                {'error': '该部门下有子部门，请先删除或移动子部门'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 检查是否有成员
        if instance.memberships.filter(effective_to__isnull=True).exists():
            return Response(
                {'error': '该部门下有成员，请先移除成员'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def tree(self, request):
        """获取组织树"""
        # 只返回根节点，子节点通过序列化器的 children 字段递归获取
        root_units = self.get_queryset().filter(parent__isnull=True, is_active=True)
        serializer = OrgUnitTreeSerializer(root_units, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        """移动部门到新的父节点"""
        unit = self.get_object()
        serializer = OrgUnitMoveSerializer(data=request.data)

        if serializer.is_valid():
            new_parent_id = serializer.validated_data.get('new_parent_id')
            position = serializer.validated_data.get('position', 0)

            # 验证新父节点
            if new_parent_id:
                try:
                    new_parent = OrgUnit.objects.get(id=new_parent_id)
                    # 检查是否会形成循环
                    if new_parent in unit.get_descendants():
                        return Response(
                            {'error': '不能将部门移动到其子部门下'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    unit.parent = new_parent
                except OrgUnit.DoesNotExist:
                    return Response(
                        {'error': '新的父部门不存在'},
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                unit.parent = None

            unit.sort_order = position
            unit.save()

            return Response({'message': '部门移动成功'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def reorder(self, request):
        """批量排序部门"""
        serializer = OrgUnitReorderSerializer(data=request.data)

        if serializer.is_valid():
            parent_id = serializer.validated_data.get('parent_id')
            ordered_ids = serializer.validated_data.get('ordered_ids', [])

            # 获取同级部门
            siblings = OrgUnit.objects.filter(parent_id=parent_id)
            sibling_ids = set(siblings.values_list('id', flat=True))

            # 验证所有ID都是同级部门
            if not set(ordered_ids).issubset(sibling_ids):
                return Response(
                    {'error': '存在不属于同一父节点的部门'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 更新排序
            for index, unit_id in enumerate(ordered_ids):
                OrgUnit.objects.filter(id=unit_id).update(sort_order=index)

            return Response({'message': '排序更新成功'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """获取部门成员列表"""
        unit = self.get_object()
        memberships = unit.memberships.select_related('user__real_name', 'unit').filter(
            effective_to__isnull=True
        )

        # 是否包含子部门成员
        include_children = request.query_params.get('include_children', 'false').lower() == 'true'
        if include_children:
            descendant_ids = [u.id for u in unit.get_descendants()]
            memberships = Membership.objects.filter(
                unit_id__in=descendant_ids + [unit.id],
                effective_to__isnull=True
            ).select_related('user', 'unit')

        # 搜索
        search = request.query_params.get('search', None)
        if search:
            memberships = memberships.filter(
                Q(user__username__icontains=search) |
                Q(user__real_name__icontains=search) |
                Q(position__icontains=search)
            )

        # 只获取主部门成员
        primary_only = request.query_params.get('primary_only', 'false').lower() == 'true'
        if primary_only:
            memberships = memberships.filter(is_primary=True)

        serializer = MembershipSerializer(memberships, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def manager(self, request, pk=None):
        """设置部门负责人"""
        unit = self.get_object()
        serializer = OrgUnitManagerSerializer(data=request.data)

        if serializer.is_valid():
            user_id = serializer.validated_data.get('user_id')

            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = User.objects.get(id=user_id)

                # 查找或创建成员关系
                membership, created = Membership.objects.get_or_create(
                    user=user,
                    unit=unit,
                    defaults={'is_manager': True}
                )

                if not created:
                    membership.is_manager = True
                    membership.save()

                # 取消其他负责人（如果只允许一个负责人）
                Membership.objects.filter(
                    unit=unit,
                    is_manager=True
                ).exclude(id=membership.id).update(is_manager=False)

                return Response({'message': f'已设置 {user.real_name or user.username} 为部门负责人'})
            except User.DoesNotExist:
                return Response(
                    {'error': '用户不存在'},
                    status=status.HTTP_404_NOT_FOUND
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MembershipViewSet(viewsets.ModelViewSet):
    """部门成员视图集"""
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """获取查询集"""
        queryset = Membership.objects.select_related('user', 'unit').all()

        # 用户过滤
        user_id = self.request.query_params.get('user_id', None)
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        # 部门过滤
        unit_id = self.request.query_params.get('unit_id', None)
        if unit_id:
            queryset = queryset.filter(unit_id=unit_id)

        # 是否主部门
        is_primary = self.request.query_params.get('is_primary', None)
        if is_primary is not None:
            queryset = queryset.filter(is_primary=is_primary.lower() == 'true')

        # 是否负责人
        is_manager = self.request.query_params.get('is_manager', None)
        if is_manager is not None:
            queryset = queryset.filter(is_manager=is_manager.lower() == 'true')

        return queryset

    def get_serializer_class(self):
        """根据操作返回不同的序列化器"""
        if self.action == 'create':
            return MembershipCreateSerializer
        return MembershipSerializer

    def perform_create(self, serializer):
        """创建时自动设置创建人"""
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def by_user(self, request):
        """查询某个用户的组织归属"""
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response(
                {'error': '请提供 user_id 参数'},
                status=status.HTTP_400_BAD_REQUEST
            )

        memberships = self.get_queryset().filter(user_id=user_id)
        serializer = MembershipSerializer(memberships, many=True)
        return Response(serializer.data)
