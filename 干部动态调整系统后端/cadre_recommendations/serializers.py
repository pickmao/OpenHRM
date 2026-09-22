from django.utils import timezone
from rest_framework import serializers

from .models import (
    POST_CATEGORY_KEYS, RECOMMENDER_CATEGORIES, RecommenderCategory,
    default_slot_config, normalize_slot_config,
)


class CampaignCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    deadline_at = serializers.DateTimeField()
    allow_self_recommend = serializers.BooleanField(required=False, default=False)
    slot_config = serializers.JSONField(required=False)
    receiver_type = serializers.ChoiceField(choices=['USER', 'ORG_UNIT', 'ORG_ROLE'])
    receiver_expr_json = serializers.JSONField()

    def validate_slot_config(self, value):
        try:
            return normalize_slot_config(value or default_slot_config())
        except Exception as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate(self, attrs):
        if attrs['deadline_at'] <= timezone.now():
            raise serializers.ValidationError({'deadline_at': '截止时间必须晚于当前时间。'})
        attrs['slot_config'] = normalize_slot_config(attrs.get('slot_config') or default_slot_config())
        expr = attrs.get('receiver_expr_json') or {}
        receiver_type = attrs['receiver_type']
        if receiver_type == 'USER' and not expr.get('all_users') and not (expr.get('user_ids') or expr.get('ids')):
            raise serializers.ValidationError({'receiver_expr_json': '请选择填报人员，或选择下发给全部启用用户。'})
        if receiver_type == 'ORG_UNIT' and not (expr.get('org_unit_ids') or expr.get('ids')):
            raise serializers.ValidationError({'receiver_expr_json': '请选择支部、部门或监区。'})
        if receiver_type == 'ORG_ROLE' and not (expr.get('role_codes') or expr.get('role_code')):
            raise serializers.ValidationError({'receiver_expr_json': '请选择接收角色。'})
        return attrs


class NominationItemSerializer(serializers.Serializer):
    post_category = serializers.ChoiceField(choices=POST_CATEGORY_KEYS)
    slot_index = serializers.IntegerField(min_value=0, max_value=19)
    roster_id = serializers.UUIDField()


class TaskSaveSerializer(serializers.Serializer):
    recommender_category = serializers.ChoiceField(
        choices=[item['key'] for item in RECOMMENDER_CATEGORIES],
        required=False, allow_blank=True, allow_null=True,
    )
    nominations = NominationItemSerializer(many=True, required=False)

    def validate_recommender_category(self, value):
        return value or ''


class TaskSubmitSerializer(TaskSaveSerializer):
    recommender_category = serializers.ChoiceField(
        choices=RecommenderCategory.choices,
        required=True,
    )
