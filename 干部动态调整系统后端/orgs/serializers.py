from rest_framework import serializers
from .models import OrgUnit, Membership
from django.contrib.auth import get_user_model

User = get_user_model()


class UserBasicSerializer(serializers.ModelSerializer):
    """用户基本信息序列化器"""
    class Meta:
        model = User
        fields = ['id', 'username', 'real_name', 'email']


class OrgUnitListSerializer(serializers.ModelSerializer):
    """组织单元列表序列化器（精简版）"""
    children_count = serializers.SerializerMethodField()

    class Meta:
        model = OrgUnit
        fields = [
            'id', 'name', 'code', 'unit_type', 'parent',
            'sort_order', 'is_active', 'children_count'
        ]

    def get_children_count(self, obj):
        return obj.children.count()


class OrgUnitDetailSerializer(serializers.ModelSerializer):
    """组织单元详情序列化器"""
    parent_name = serializers.CharField(source='parent.name', read_only=True, allow_null=True)
    parent_type = serializers.CharField(source='parent.unit_type', read_only=True, allow_null=True)
    children = OrgUnitListSerializer(many=True, read_only=True)
    members_count = serializers.SerializerMethodField()
    all_members_count = serializers.SerializerMethodField()

    class Meta:
        model = OrgUnit
        fields = [
            'id', 'name', 'code', 'unit_type', 'parent', 'parent_name', 'parent_type',
            'sort_order', 'is_active', 'metrics_snapshot',
            'children', 'members_count', 'all_members_count',
            'created_at', 'updated_at'
        ]

    def get_members_count(self, obj):
        """直接成员数"""
        return obj.memberships.filter(effective_to__isnull=True).count()

    def get_all_members_count(self, obj):
        """所有成员数（含子部门）"""
        # 获取所有下级部门ID
        descendant_ids = [obj.id]
        descendants = obj.get_descendants()
        descendant_ids.extend([d.id for d in descendants])

        return Membership.objects.filter(
            unit_id__in=descendant_ids,
            effective_to__isnull=True
        ).count()


class OrgUnitTreeSerializer(serializers.ModelSerializer):
    """组织单元树形结构序列化器"""
    label = serializers.CharField(source='name', read_only=True)
    value = serializers.CharField(source='id', read_only=True)
    children = serializers.SerializerMethodField()

    class Meta:
        model = OrgUnit
        fields = ['id', 'name', 'code', 'unit_type', 'label', 'value', 'children', 'is_active', 'sort_order']

    def get_children(self, obj):
        """递归获取子部门"""
        children = obj.children.filter(is_active=True).order_by('sort_order', 'name')
        return OrgUnitTreeSerializer(children, many=True).data


class MembershipSerializer(serializers.ModelSerializer):
    """部门成员序列化器"""
    user_info = UserBasicSerializer(source='user', read_only=True)
    unit_name = serializers.CharField(source='unit.name', read_only=True)
    unit_type = serializers.CharField(source='unit.unit_type', read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Membership
        fields = [
            'id', 'user', 'user_info', 'unit', 'unit_name', 'unit_type',
            'is_primary', 'position', 'is_manager',
            'effective_from', 'effective_to',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_by']


class MembershipCreateSerializer(serializers.ModelSerializer):
    """创建部门成员序列化器"""

    class Meta:
        model = Membership
        fields = [
            'user', 'unit', 'is_primary', 'position',
            'is_manager', 'effective_from', 'effective_to'
        ]

    def validate(self, data):
        """验证数据"""
        user = data.get('user')
        unit = data.get('unit')
        is_primary = data.get('is_primary', True)

        # 如果设置为主部门，检查该用户是否已有主部门
        if is_primary:
            existing_primary = Membership.objects.filter(
                user=user,
                is_primary=True,
                effective_to__isnull=True
            ).exclude(unit=unit).exists()

            if existing_primary:
                raise serializers.ValidationError({
                    'is_primary': '该用户已有主部门，请先取消原主部门或设置为非主部门'
                })

        return data


class OrgUnitMoveSerializer(serializers.Serializer):
    """移动部门序列化器"""
    new_parent_id = serializers.UUIDField(required=False, allow_null=True)
    position = serializers.IntegerField(required=False, min_value=0)


class OrgUnitReorderSerializer(serializers.Serializer):
    """部门排序序列化器"""
    parent_id = serializers.UUIDField(required=False, allow_null=True)
    ordered_ids = serializers.ListField(child=serializers.UUIDField())


class OrgUnitManagerSerializer(serializers.Serializer):
    """设置部门负责人序列化器"""
    user_id = serializers.UUIDField()
