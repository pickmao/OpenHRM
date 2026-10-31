from django.utils import timezone
from rest_framework import serializers

from .models import FillerRole, FormType


class RecipientOverrideSerializer(serializers.Serializer):
    form_type = serializers.ChoiceField(choices=FormType.choices)
    user_id = serializers.UUIDField()
    branch_id = serializers.UUIDField(required=False, allow_null=True)
    filler_role = serializers.ChoiceField(choices=FillerRole.choices, required=False)
    source = serializers.CharField(required=False, allow_blank=True, max_length=50)


class CampaignPreviewSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True, max_length=200)
    year = serializers.CharField(required=False, allow_blank=True, max_length=20)
    period_start = serializers.DateField(required=False, allow_null=True)
    period_end = serializers.DateField(required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    deadline_at = serializers.DateTimeField(required=False)
    form_types = serializers.ListField(child=serializers.ChoiceField(choices=FormType.choices), allow_empty=False)
    branch_ids = serializers.ListField(child=serializers.UUIDField(), required=False)
    extra_user_ids_by_type = serializers.DictField(child=serializers.ListField(child=serializers.UUIDField()), required=False)
    recipients = RecipientOverrideSerializer(many=True, required=False)


class CampaignCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    year = serializers.CharField(required=False, allow_blank=True, max_length=20)
    period_start = serializers.DateField(required=False, allow_null=True)
    period_end = serializers.DateField(required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    deadline_at = serializers.DateTimeField()
    form_types = serializers.ListField(child=serializers.ChoiceField(choices=FormType.choices), allow_empty=False)
    branch_ids = serializers.ListField(child=serializers.UUIDField(), required=False)
    extra_user_ids_by_type = serializers.DictField(child=serializers.ListField(child=serializers.UUIDField()), required=False)
    recipients = RecipientOverrideSerializer(many=True, required=False)

    def validate(self, attrs):
        if attrs['deadline_at'] <= timezone.now():
            raise serializers.ValidationError({'deadline_at': '截止时间必须晚于当前时间。'})
        start, end = attrs.get('period_start'), attrs.get('period_end')
        if start and end and start > end:
            raise serializers.ValidationError({'period_end': '考察结束日期不能早于开始日期。'})
        extra = attrs.get('extra_user_ids_by_type') or {}
        if extra and not isinstance(extra, dict):
            raise serializers.ValidationError({'extra_user_ids_by_type': '必须是按表单类型分组的对象。'})
        return attrs


class TaskSaveSerializer(serializers.Serializer):
    payload = serializers.JSONField()


class ReturnSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)
