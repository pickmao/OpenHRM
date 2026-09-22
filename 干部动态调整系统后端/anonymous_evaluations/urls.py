from django.urls import path

from . import views


app_name = 'anonymous_evaluations'

urlpatterns = [
    path('campaigns/', views.CampaignListCreateView.as_view(), name='campaign-list'),
    path('campaigns/participants/', views.ParticipantListView.as_view(), name='participants'),
    path('campaigns/<uuid:campaign_id>/publish/', views.CampaignPublishView.as_view(), name='campaign-publish'),
    path('campaigns/<uuid:campaign_id>/close/', views.CampaignCloseView.as_view(), name='campaign-close'),
    path('campaigns/<uuid:campaign_id>/results/', views.CampaignResultsView.as_view(), name='campaign-results'),
    path('tasks/my/', views.MyEvaluationTaskListView.as_view(), name='my-tasks'),
    path('tasks/<uuid:campaign_id>/<uuid:target_id>/submit/', views.AnonymousSubmissionView.as_view(), name='submit'),
]
