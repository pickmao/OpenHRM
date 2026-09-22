from rest_framework import serializers

from cadres.org_alignment import roster_department_by_names

from .models import RewardImportFile, RewardRecord, RewardRecipientType


class RewardImportFileSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.real_name', read_only=True, default=None)

    class Meta:
        model = RewardImportFile
        fields = '__all__'
        read_only_fields = ('id', 'file_name', 'source_file', 'uploaded_by', 'upload_time', 'total_records',
                            'record_counts', 'created_at', 'updated_at')


class RewardRecordSerializer(serializers.ModelSerializer):
    recipient_type_display = serializers.CharField(source='get_recipient_type_display', read_only=True)
    import_file_name = serializers.CharField(source='import_file.file_name', read_only=True, default=None)
    source_file = serializers.FileField(source='import_file.source_file', read_only=True, default=None)
    created_by_name = serializers.CharField(source='created_by.real_name', read_only=True, default=None)
    current_department = serializers.SerializerMethodField()

    class Meta:
        model = RewardRecord
        fields = '__all__'
        read_only_fields = ('id', 'import_file', 'source_sheet', 'source_row', 'created_by', 'created_at', 'updated_at')

    def get_current_department(self, obj):
        if obj.recipient_type != RewardRecipientType.INDIVIDUAL:
            return ''
        mapping = self.context.get('roster_departments')
        if mapping is None:
            mapping = roster_department_by_names([obj.recipient_name])
            self.context['roster_departments'] = mapping
        return mapping.get(obj.recipient_name) or ''
