from rest_framework import serializers
import re

from cadres.org_alignment import roster_department_by_names

from .models import AssessmentFile, AssessmentRecord


def validate_annual_performance(value):
    if not isinstance(value, dict) or any(not re.fullmatch(r'[1-9]\d{3}', str(year)) or not isinstance(text, str)
                                          for year, text in value.items()):
        raise serializers.ValidationError('年度干事评价须按四位年度保存文字内容。')
    return value


class AssessmentFileSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.real_name', read_only=True, default=None)

    class Meta:
        model = AssessmentFile
        fields = '__all__'
        read_only_fields = ('id', 'version_date', 'file_name', 'source_file', 'upload_time', 'uploaded_by',
                            'total_records', 'category_counts', 'created_at', 'updated_at')


class AssessmentFileListSerializer(AssessmentFileSerializer):
    pass


class AssessmentRecordSerializer(serializers.ModelSerializer):
    file_name = serializers.CharField(source='file.file_name', read_only=True)
    version_date = serializers.DateField(source='file.version_date', read_only=True)
    position_category_display = serializers.CharField(source='get_position_category_display', read_only=True)
    current_department = serializers.SerializerMethodField()

    def validate_performance_by_year(self, value):
        return validate_annual_performance(value)

    class Meta:
        model = AssessmentRecord
        fields = '__all__'
        read_only_fields = ('id', 'file', 'created_at', 'updated_at', 'source_object_id', 'collection_data')

    def get_current_department(self, obj):
        mapping = self.context.get('roster_departments')
        if mapping is None:
            mapping = roster_department_by_names([obj.name])
            self.context['roster_departments'] = mapping
        return mapping.get(obj.name) or ''


class AssessmentRecordListSerializer(AssessmentRecordSerializer):
    class Meta(AssessmentRecordSerializer.Meta):
        fields = ('id', 'file', 'file_name', 'version_date', 'name', 'department', 'current_department', 'position',
                  'position_category', 'position_category_display', 'age', 'ranking',
                  'seven_looks_score', 'work_recognition_score', 'comprehensive_score', 'adjustment_suggestion')


class AssessmentRecordDetailSerializer(AssessmentRecordSerializer):
    pass
