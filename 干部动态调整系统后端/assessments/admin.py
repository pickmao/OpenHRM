from django.contrib import admin
from .models import AssessmentFile, AssessmentRecord


@admin.register(AssessmentFile)
class AssessmentFileAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'version_date', 'total_records', 'is_active', 'upload_time')
    list_filter = ('is_active',)
    search_fields = ('file_name',)


@admin.register(AssessmentRecord)
class AssessmentRecordAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'position', 'position_category', 'ranking')
    list_filter = ('position_category', 'file')
    search_fields = ('name', 'department', 'position')
