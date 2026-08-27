from rest_framework import serializers

from .models import LeadershipAssessmentFile, LeadershipAssessmentRecord


class LeadershipFileSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.real_name', read_only=True, default=None)

    class Meta:
        model = LeadershipAssessmentFile
        fields = '__all__'
        read_only_fields = ('id', 'version_date', 'file_name', 'source_file', 'upload_time', 'uploaded_by',
                            'total_records', 'created_at', 'updated_at')


class LeadershipFileListSerializer(LeadershipFileSerializer):
    pass


class LeadershipRecordSerializer(serializers.ModelSerializer):
    file_name = serializers.CharField(source='file.file_name', read_only=True)
    version_date = serializers.DateField(source='file.version_date', read_only=True)

    class Meta:
        model = LeadershipAssessmentRecord
        fields = '__all__'
        read_only_fields = ('id', 'file', 'created_at', 'updated_at')


class LeadershipRecordListSerializer(LeadershipRecordSerializer):
    class Meta(LeadershipRecordSerializer.Meta):
        fields = ('id', 'file', 'file_name', 'version_date', 'name', 'leadership_count', 'vacancy_count',
                  'average_age', 'total_score', 'approval_rate', 'ranking', 'adjustment_suggestion')


class LeadershipRecordDetailSerializer(LeadershipRecordSerializer):
    pass
