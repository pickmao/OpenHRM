from urllib.parse import quote

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Role, User
from orgs.models import OrgUnit

from .models import POST_CATEGORIES, RECOMMENDER_CATEGORIES, RecommendationCampaign, RecommendationTask, default_slot_config
from .permissions import has_recommendation_permission
from .serializers import CampaignCreateSerializer, TaskSaveSerializer, TaskSubmitSerializer
from .services import (
    RULES_TEXT, campaign_summary, close_campaign, create_campaign, export_statistics_xlsx,
    preview_dispatch, save_draft, serialize_task, submit_task, build_statistics,
)


MANAGE_PERMISSION = 'cadre_recommendations:campaign:manage'
TASK_VIEW_PERMISSION = 'cadre_recommendations:task:view'
TASK_SUBMIT_PERMISSION = 'cadre_recommendations:task:submit'
RESULT_PERMISSION = 'cadre_recommendations:result:view'


def require_any(request, *codes):
    if not any(has_recommendation_permission(request.user, code) for code in codes):
        return Response({'detail': '没有权限访问优秀干部推荐功能。'}, status=status.HTTP_403_FORBIDDEN)
    return None


class DispatchOptionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        denied = require_any(request, MANAGE_PERMISSION)
        if denied:
            return denied
        units = OrgUnit.objects.filter(is_active=True).select_related('parent').order_by('unit_type', 'sort_order', 'name')
        return Response({
            'post_categories': POST_CATEGORIES,
            'recommender_categories': RECOMMENDER_CATEGORIES,
            'defaults': {
                'allow_self_recommend': False,
                'slot_config': default_slot_config(),
            },
            'rules_text': RULES_TEXT,
            'roles': list(Role.objects.filter(is_active=True).values('code', 'name')),
            'users': [
                {'id': str(user.id), 'real_name': user.real_name, 'username': user.username}
                for user in User.objects.filter(is_active=True).order_by('real_name', 'username')
            ],
            'org_units': [
                {
                    'id': str(unit.id),
                    'name': unit.name,
                    'unit_type': unit.unit_type,
                    'unit_type_display': unit.get_unit_type_display(),
                    'parent_name': unit.parent.name if unit.parent else '',
                    'label': f'{unit.name}（{unit.get_unit_type_display()}）',
                }
                for unit in units
            ],
        })


class CampaignPreviewView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        denied = require_any(request, MANAGE_PERMISSION)
        if denied:
            return denied
        serializer = CampaignCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(preview_dispatch(serializer.validated_data))


class CampaignListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        denied = require_any(request, MANAGE_PERMISSION, RESULT_PERMISSION)
        if denied:
            return denied
        can_manage = has_recommendation_permission(request.user, MANAGE_PERMISSION)
        campaigns = RecommendationCampaign.objects.all().order_by('-created_at')
        return Response([campaign_summary(item, include_progress=can_manage) for item in campaigns])

    def post(self, request):
        denied = require_any(request, MANAGE_PERMISSION)
        if denied:
            return denied
        serializer = CampaignCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        campaign = create_campaign(dict(serializer.validated_data), request.user)
        return Response(campaign_summary(campaign, include_progress=True), status=status.HTTP_201_CREATED)


class CampaignCloseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, campaign_id):
        denied = require_any(request, MANAGE_PERMISSION)
        if denied:
            return denied
        campaign = close_campaign(get_object_or_404(RecommendationCampaign, id=campaign_id))
        return Response(campaign_summary(campaign, include_progress=True))


class MyTaskListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        denied = require_any(request, TASK_VIEW_PERMISSION, TASK_SUBMIT_PERMISSION)
        if denied:
            return denied
        tasks = RecommendationTask.objects.filter(assignee=request.user).select_related('campaign').order_by(
            'campaign__deadline_at', '-created_at',
        )
        return Response([serialize_task(task) for task in tasks])


class TaskDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        denied = require_any(request, TASK_VIEW_PERMISSION, TASK_SUBMIT_PERMISSION)
        if denied:
            return denied
        task = get_object_or_404(
            RecommendationTask.objects.select_related('campaign', 'assignee'),
            id=task_id, assignee=request.user,
        )
        return Response(serialize_task(task, include_candidates=True))


class TaskSaveDraftView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        denied = require_any(request, TASK_SUBMIT_PERMISSION)
        if denied:
            return denied
        task = get_object_or_404(RecommendationTask, id=task_id, assignee=request.user)
        serializer = TaskSaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = save_draft(task, request.user, serializer.validated_data)
        return Response(serialize_task(task, include_candidates=True))


class TaskSubmitView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        denied = require_any(request, TASK_SUBMIT_PERMISSION)
        if denied:
            return denied
        task = get_object_or_404(RecommendationTask, id=task_id, assignee=request.user)
        serializer = TaskSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = submit_task(task, request.user, serializer.validated_data)
        return Response(serialize_task(task, include_candidates=True), status=status.HTTP_200_OK)


class CampaignStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, campaign_id):
        denied = require_any(request, RESULT_PERMISSION, MANAGE_PERMISSION)
        if denied:
            return denied
        campaign = get_object_or_404(RecommendationCampaign, id=campaign_id)
        return Response(build_statistics(campaign))


class CampaignStatsExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, campaign_id):
        denied = require_any(request, RESULT_PERMISSION, MANAGE_PERMISSION)
        if denied:
            return denied
        campaign = get_object_or_404(RecommendationCampaign, id=campaign_id)
        content = export_statistics_xlsx(campaign)
        filename = f'{campaign.name}-党支部优秀干部统计表.xlsx'
        response = HttpResponse(
            content,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f"attachment; filename*=UTF-8''{quote(filename)}"
        return response
