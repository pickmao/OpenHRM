from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User

from .models import CampaignStatus, EvaluationCampaign, EvaluationEligibility, EvaluationTarget
from .permissions import has_evaluation_permission
from .serializers import CampaignCreateSerializer, SubmissionSerializer
from .services import build_results, campaign_summary, close_campaign, create_campaign, publish_campaign, submit_response
from cadres.org_alignment import current_department_names_for_user_ids


MANAGE_PERMISSION = 'anonymous_evaluations:campaign:manage'
TASK_VIEW_PERMISSION = 'anonymous_evaluations:task:view'
TASK_SUBMIT_PERMISSION = 'anonymous_evaluations:task:submit'
RESULT_PERMISSION = 'anonymous_evaluations:result:view'


def require_any(request, *codes):
    if not any(has_evaluation_permission(request.user, code) for code in codes):
        return Response({'detail': '没有权限访问匿名评价功能。'}, status=status.HTTP_403_FORBIDDEN)
    return None


class CampaignListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        denied = require_any(request, MANAGE_PERMISSION, RESULT_PERMISSION)
        if denied:
            return denied
        can_manage = has_evaluation_permission(request.user, MANAGE_PERMISSION)
        campaigns = EvaluationCampaign.objects.all().order_by('-created_at')
        return Response([campaign_summary(campaign, include_progress=can_manage) for campaign in campaigns])

    def post(self, request):
        denied = require_any(request, MANAGE_PERMISSION)
        if denied:
            return denied
        serializer = CampaignCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        campaign = create_campaign(dict(serializer.validated_data), request.user)
        return Response(campaign_summary(campaign, include_progress=True), status=status.HTTP_201_CREATED)


class ParticipantListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        denied = require_any(request, MANAGE_PERMISSION)
        if denied:
            return denied
        users = User.objects.filter(is_active=True).order_by('username')
        return Response([
            {'id': str(user.id), 'username': user.username, 'real_name': user.real_name, 'label': user.real_name or user.username}
            for user in users
        ])


class CampaignPublishView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, campaign_id):
        denied = require_any(request, MANAGE_PERMISSION)
        if denied:
            return denied
        campaign = publish_campaign(get_object_or_404(EvaluationCampaign, id=campaign_id))
        return Response(campaign_summary(campaign, include_progress=True))


class CampaignCloseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, campaign_id):
        denied = require_any(request, MANAGE_PERMISSION)
        if denied:
            return denied
        campaign = close_campaign(get_object_or_404(EvaluationCampaign, id=campaign_id))
        return Response(campaign_summary(campaign, include_progress=True))


class MyEvaluationTaskListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        denied = require_any(request, TASK_VIEW_PERMISSION)
        if denied:
            return denied
        eligibilities = list(EvaluationEligibility.objects.filter(
            evaluator=request.user,
            campaign__status=CampaignStatus.PUBLISHED,
        ).select_related('campaign', 'target', 'target__user').order_by('campaign__deadline_at', 'target__target_name_snapshot'))
        current_orgs = current_department_names_for_user_ids([item.target.user_id for item in eligibilities])
        return Response([
            {
                'campaign_id': str(item.campaign_id),
                'campaign_name': item.campaign.name,
                'target_id': str(item.target_id),
                'target_name': item.target.target_name_snapshot,
                'org_name': current_orgs.get(item.target.user_id) or item.target.org_name_snapshot,
                'dimensions': item.campaign.dimensions_json,
                'deadline_at': item.campaign.deadline_at,
                'is_open': item.campaign.is_open(),
                'submitted': item.submitted,
            }
            for item in eligibilities
        ])


class AnonymousSubmissionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, campaign_id, target_id):
        denied = require_any(request, TASK_SUBMIT_PERMISSION)
        if denied:
            return denied
        campaign = get_object_or_404(EvaluationCampaign, id=campaign_id)
        target = get_object_or_404(EvaluationTarget, id=target_id, campaign=campaign)
        serializer = SubmissionSerializer(data=request.data, context={'campaign': campaign})
        serializer.is_valid(raise_exception=True)
        submit_response(campaign, target, request.user, serializer.validated_data['scores'], serializer.validated_data.get('comment', ''))
        return Response({'detail': '匿名评价已提交。'}, status=status.HTTP_201_CREATED)


class CampaignResultsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, campaign_id):
        denied = require_any(request, RESULT_PERMISSION)
        if denied:
            return denied
        campaign = get_object_or_404(EvaluationCampaign, id=campaign_id)
        if campaign.status != CampaignStatus.CLOSED:
            return Response({'detail': '活动关闭后才能查看汇总结果。'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'campaign': campaign_summary(campaign),
            'results': build_results(campaign),
        })
