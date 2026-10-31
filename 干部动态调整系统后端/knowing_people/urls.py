from django.urls import path

from . import views


app_name = 'knowing_people'

urlpatterns = [
    path('options/', views.DispatchOptionsView.as_view(), name='options'),
    path('campaigns/preview/', views.CampaignPreviewView.as_view(), name='campaign-preview'),
    path('campaigns/', views.CampaignListCreateView.as_view(), name='campaign-list'),
    path('campaigns/<uuid:campaign_id>/close/', views.CampaignCloseView.as_view(), name='campaign-close'),
    path('campaigns/<uuid:campaign_id>/progress/', views.CampaignProgressView.as_view(), name='campaign-progress'),
    path('campaigns/<uuid:campaign_id>/statistics-export/', views.CampaignStatisticsExportView.as_view(), name='campaign-statistics-export'),
    path('tasks/my/', views.MyTaskListView.as_view(), name='my-tasks'),
    path('tasks/<uuid:task_id>/', views.TaskDetailView.as_view(), name='task-detail'),
    path('tasks/<uuid:task_id>/save-draft/', views.TaskSaveDraftView.as_view(), name='task-save-draft'),
    path('tasks/<uuid:task_id>/submit/', views.TaskSubmitView.as_view(), name='task-submit'),
    path('tasks/<uuid:task_id>/return/', views.TaskReturnView.as_view(), name='task-return'),
    path('tasks/<uuid:task_id>/remind/', views.TaskRemindView.as_view(), name='task-remind'),
]
