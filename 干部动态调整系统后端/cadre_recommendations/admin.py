from django.contrib import admin

from .models import RecommendationCampaign, RecommendationTask


@admin.register(RecommendationCampaign)
class RecommendationCampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'deadline_at', 'allow_self_recommend', 'created_at']
    list_filter = ['status']
    search_fields = ['name']


@admin.register(RecommendationTask)
class RecommendationTaskAdmin(admin.ModelAdmin):
    list_display = ['assignee_name_snapshot', 'campaign', 'status', 'branch_name_snapshot', 'submitted_at']
    list_filter = ['status']
    search_fields = ['assignee_name_snapshot', 'branch_name_snapshot']
