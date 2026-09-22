from django.utils import timezone
from rest_framework import serializers

from .models import default_dimensions, validate_dimensions


class CampaignCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    dimensions = serializers.JSONField(required=False, default=default_dimensions)
    min_valid_responses = serializers.IntegerField(required=False, min_value=2, max_value=100, default=8)
    starts_at = serializers.DateTimeField(required=False, allow_null=True)
    deadline_at = serializers.DateTimeField()
    target_user_ids = serializers.ListField(child=serializers.UUIDField(), min_length=1, allow_empty=False)
    evaluator_user_ids = serializers.ListField(child=serializers.UUIDField(), min_length=1, allow_empty=False)

    def validate_dimensions(self, value):
        validate_dimensions(value)
        return value

    def validate(self, attrs):
        starts_at = attrs.get('starts_at')
        if starts_at and starts_at >= attrs['deadline_at']:
            raise serializers.ValidationError({'deadline_at': '截止时间必须晚于开始时间。'})
        if attrs['deadline_at'] <= timezone.now():
            raise serializers.ValidationError({'deadline_at': '截止时间必须晚于当前时间。'})
        return attrs


class SubmissionSerializer(serializers.Serializer):
    scores = serializers.JSONField()
    comment = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def validate_scores(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError('评分数据格式不正确。')
        dimensions = self.context['campaign'].dimensions_json
        allowed_keys = {item['key'] for item in dimensions}
        unknown_keys = set(value) - allowed_keys
        if unknown_keys:
            raise serializers.ValidationError(f'包含未知评价维度：{", ".join(sorted(unknown_keys))}')
        valid_scores = 0
        for key, score in value.items():
            if score is None:
                continue
            if isinstance(score, bool) or not isinstance(score, int) or score not in range(1, 6):
                raise serializers.ValidationError(f'{key} 的评分必须是 1 至 5，或选择不了解。')
            valid_scores += 1
        if not valid_scores:
            raise serializers.ValidationError('请至少为一个维度评分。')
        return value
