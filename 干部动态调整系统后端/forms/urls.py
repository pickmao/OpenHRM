from django.urls import path

from . import views


app_name = 'forms'

urlpatterns = [
    path('templates/', views.FormTemplateListCreateView.as_view(), name='template-list'),
    path('templates/<uuid:template_id>/', views.FormTemplateDetailView.as_view(), name='template-detail'),
    path('dispatch/preview/', views.DispatchPreviewView.as_view(), name='dispatch-preview'),
    path('dispatch/publish/', views.DispatchPublishView.as_view(), name='dispatch-publish'),
    path('dispatch/', views.DispatchBatchListView.as_view(), name='dispatch-list'),
    path('dispatch/<uuid:batch_id>/progress/', views.DispatchProgressView.as_view(), name='dispatch-progress'),
    path('dispatch/<uuid:batch_id>/task-results/', views.DispatchTaskResultsView.as_view(), name='dispatch-task-results'),
    path('dispatch/<uuid:batch_id>/dashboard/', views.DispatchDashboardView.as_view(), name='dispatch-dashboard'),
    path('dispatch/<uuid:batch_id>/pending-users/', views.DispatchPendingUsersView.as_view(), name='dispatch-pending-users'),
    path('tasks/my/', views.MyTaskListView.as_view(), name='my-tasks'),
    path('tasks/<uuid:task_id>/save-draft/', views.SaveDraftView.as_view(), name='save-draft'),
    path('tasks/<uuid:task_id>/submit/', views.SubmitTaskView.as_view(), name='submit-task'),
    path('tasks/<uuid:task_id>/return/', views.ReturnTaskView.as_view(), name='return-task'),
    path('tasks/<uuid:task_id>/result/', views.TaskResultView.as_view(), name='task-result'),
    path('tasks/<uuid:task_id>/onlyoffice-config/', views.OnlyOfficeTaskConfigView.as_view(), name='task-onlyoffice-config'),
    path('tasks/<uuid:task_id>/onlyoffice-view-config/', views.OnlyOfficeTaskViewConfigView.as_view(), name='task-onlyoffice-view-config'),
    path('tasks/<uuid:task_id>/onlyoffice-callback/', views.OnlyOfficeCallbackView.as_view(), name='task-onlyoffice-callback'),
    path('tasks/<uuid:task_id>/', views.FormTaskDetailView.as_view(), name='task-detail'),
]
