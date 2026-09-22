from django.utils import timezone
from rest_framework import serializers
from .models import WorkRecord


class WorkRecordSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = WorkRecord
        fields = ['id', 'owner', 'title', 'category', 'category_display', 'completed_on', 'role', 'details', 'outcome', 'created_at', 'updated_at']
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']

    def validate_completed_on(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError('完成日期不能晚于今天')
        return value
