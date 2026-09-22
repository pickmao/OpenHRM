from django.contrib import admin

from .models import InspectionCampaign, InspectionTask


@admin.register(InspectionCampaign)
class InspectionCampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'year', 'status', 'deadline_at', 'created_at']
    list_filter = ['status', 'year']
    search_fields = ['name']


@admin.register(InspectionTask)
class InspectionTaskAdmin(admin.ModelAdmin):
    list_display = ['assignee_name_snapshot', 'form_type', 'campaign', 'status', 'branch_name_snapshot', 'submitted_at']
    list_filter = ['status', 'form_type']
    search_fields = ['assignee_name_snapshot', 'branch_name_snapshot']
