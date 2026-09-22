from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .form_defs import RULES_TEXT, form_catalog
from .models import InspectionCampaign, InspectionTask
from .permissions import has_knowing_people_permission
from .serializers import CampaignCreateSerializer, CampaignPreviewSerializer, ReturnSerializer, TaskSaveSerializer
from .services import (
    MANAGE_PERMISSION, RESULT_PERMISSION, TASK_SUBMIT_PERMISSION, TASK_VIEW_PERMISSION,
    build_statistics, campaign_summary, close_campaign, create_campaign, dispatch_options,
    preview_dispatch, remind_task, return_task, save_draft, serialize_task, submit_task,
)


def require_any(request, *codes):
    if not any(has_knowing_people_permission(request.user, code) for code in codes):
        return Response({'detail': '没有权限访问知事识人填报功能。'}, status=status.HTTP_403_FORBIDDEN)
    return None


class DispatchOptionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        denied = require_any(request, MANAGE_PERMISSION)
        if denied:
            return denied
        payload = dispatch_options()
        payload['catalog'] = form_catalog()
        payload['rules_text'] = RULES_TEXT
        return Response(payload)


class CampaignPreviewView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        denied = require_any(request, MANAGE_PERMISSION)
        if denied:
            return denied
        serializer = CampaignPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(preview_dispatch(serializer.validated_data))


class CampaignListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        denied = require_any(request, MANAGE_PERMISSION, RESULT_PERMISSION)
        if denied:
            return denied
        can_manage = has_knowing_people_permission(request.user, MANAGE_PERMISSION)
        campaigns = InspectionCampaign.objects.all().order_by('-created_at')
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
        campaign = close_campaign(get_object_or_404(InspectionCampaign, id=campaign_id))
        return Response(campaign_summary(campaign, include_progress=True))


class CampaignProgressView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, campaign_id):
        denied = require_any(request, MANAGE_PERMISSION, RESULT_PERMISSION)
        if denied:
            return denied
        campaign = get_object_or_404(InspectionCampaign, id=campaign_id)
        data = build_statistics(campaign)
        form_type = request.query_params.get('form_type')
        branch_name = request.query_params.get('branch_name')
        status_filter = request.query_params.get('status')
        tasks = campaign.tasks.select_related('assignee', 'campaign').all()
        if form_type:
            tasks = tasks.filter(form_type=form_type)
        if branch_name:
            tasks = tasks.filter(branch_name_snapshot=branch_name)
        if status_filter:
            tasks = tasks.filter(status=status_filter)
        data['tasks'] = [serialize_task(task, user=request.user) for task in tasks]
        return Response(data)


class MyTaskListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        denied = require_any(request, TASK_VIEW_PERMISSION, TASK_SUBMIT_PERMISSION)
        if denied:
            return denied
        tasks = InspectionTask.objects.filter(assignee=request.user).select_related('campaign').order_by(
            'campaign__deadline_at', 'form_type', '-created_at',
        )
        return Response([serialize_task(task, user=request.user) for task in tasks])


class CampaignStatisticsExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, campaign_id):
        denied = require_any(request, MANAGE_PERMISSION, RESULT_PERMISSION)
        if denied:
            return denied
        from .statistics import statistics_workbook
        campaign = get_object_or_404(InspectionCampaign, id=campaign_id)
        response = HttpResponse(statistics_workbook(campaign), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="knowing-people-statistics.xlsx"'
        return response


class TaskDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        denied = require_any(request, TASK_VIEW_PERMISSION, TASK_SUBMIT_PERMISSION, MANAGE_PERMISSION)
        if denied:
            return denied
        queryset = InspectionTask.objects.select_related('campaign', 'assignee')
        if has_knowing_people_permission(request.user, MANAGE_PERMISSION):
            task = get_object_or_404(queryset, id=task_id)
        else:
            task = get_object_or_404(queryset, id=task_id, assignee=request.user)
        return Response(serialize_task(task, include_form=True, user=request.user))


class TaskSaveDraftView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        denied = require_any(request, TASK_SUBMIT_PERMISSION)
        if denied:
            return denied
        task = get_object_or_404(InspectionTask, id=task_id, assignee=request.user)
        serializer = TaskSaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = save_draft(task, request.user, serializer.validated_data.get('payload'))
        return Response(serialize_task(task, include_form=True, user=request.user))


class TaskSubmitView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        denied = require_any(request, TASK_SUBMIT_PERMISSION)
        if denied:
            return denied
        task = get_object_or_404(InspectionTask, id=task_id, assignee=request.user)
        serializer = TaskSaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = submit_task(task, request.user, serializer.validated_data.get('payload'))
        return Response(serialize_task(task, include_form=True, user=request.user))


class TaskReturnView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        denied = require_any(request, MANAGE_PERMISSION)
        if denied:
            return denied
        task = get_object_or_404(InspectionTask, id=task_id)
        serializer = ReturnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = return_task(task, request.user, serializer.validated_data['reason'])
        return Response(serialize_task(task, include_form=True, user=request.user))


class TaskRemindView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        denied = require_any(request, MANAGE_PERMISSION)
        if denied:
            return denied
        task = remind_task(get_object_or_404(InspectionTask, id=task_id))
        return Response(serialize_task(task, user=request.user))
