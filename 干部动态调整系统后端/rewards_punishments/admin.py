from django.contrib import admin

from .models import RewardImportFile, RewardRecord


@admin.register(RewardImportFile)
class RewardImportFileAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'total_records', 'upload_time', 'uploaded_by')
    search_fields = ('file_name',)
    readonly_fields = ('upload_time', 'created_at', 'updated_at')


@admin.register(RewardRecord)
class RewardRecordAdmin(admin.ModelAdmin):
    list_display = ('recipient_name', 'recipient_type', 'award_level', 'approval_year', 'approval_date')
    list_filter = ('recipient_type', 'approval_year', 'award_level')
    search_fields = ('recipient_name', 'award_content', 'document_number')
