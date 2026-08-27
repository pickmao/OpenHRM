from django.contrib import admin

from .models import LeadershipAssessmentFile, LeadershipAssessmentRecord


@admin.register(LeadershipAssessmentFile)
class LeadershipAssessmentFileAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'version_date', 'total_records', 'is_active', 'upload_time')
    list_filter = ('is_active',)
    search_fields = ('file_name',)


@admin.register(LeadershipAssessmentRecord)
class LeadershipAssessmentRecordAdmin(admin.ModelAdmin):
    list_display = ('name', 'leadership_count', 'vacancy_count', 'total_score', 'ranking')
    search_fields = ('name',)
