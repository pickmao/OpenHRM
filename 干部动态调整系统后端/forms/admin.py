from django.contrib import admin

from .models import DispatchBatch, DispatchRule, FormSubmission, FormTask, FormTaskAudit, FormTemplate, OnlyOfficeDocument


@admin.register(FormTemplate)
class FormTemplateAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'version', 'is_active', 'created_at']
    search_fields = ['code', 'name']
    list_filter = ['is_active']


@admin.register(DispatchBatch)
class DispatchBatchAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'deadline_at', 'stats_total', 'stats_submitted', 'created_at']
    search_fields = ['name', 'cycle_id', 'stage_code']
    list_filter = ['status']


admin.site.register(DispatchRule)
admin.site.register(FormTask)
admin.site.register(FormSubmission)
admin.site.register(FormTaskAudit)
admin.site.register(OnlyOfficeDocument)
