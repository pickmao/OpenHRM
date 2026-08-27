from rest_framework import serializers

from .models import AssessmentFile, AssessmentRecord


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

    class Meta:
        model = AssessmentRecord
        fields = '__all__'
        read_only_fields = ('id', 'file', 'created_at', 'updated_at')


class AssessmentRecordListSerializer(AssessmentRecordSerializer):
    class Meta(AssessmentRecordSerializer.Meta):
        fields = ('id', 'file', 'file_name', 'version_date', 'name', 'department', 'position',
                  'position_category', 'position_category_display', 'age', 'ranking',
                  'comprehensive_score', 'adjustment_suggestion')


class AssessmentRecordDetailSerializer(AssessmentRecordSerializer):
    pass
