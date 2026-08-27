from pathlib import Path
from urllib.request import urlopen

from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DispatchBatch, FormTask, FormTaskStatus, FormTemplate, OnlyOfficeDocument
from .permissions import HasFormsPermission, user_has_permission
from .serializers import (
    DispatchBatchSerializer, DraftSaveSerializer, FormSubmissionSerializer, FormTaskSerializer,
    FormTemplateSerializer, ReturnTaskSerializer, TaskSubmitSerializer,
)
from .services import create_onlyoffice_document, preview_dispatch, publish_dispatch, return_task, save_submission, visible_tasks
from .dashboard_service import FormDashboardService


def can_manage_dispatch(user):
    return user.is_superuser or any(
        user_has_permission(user, code)
        for code in ('forms:dispatch:manage', 'forms:template:manage', 'forms:task:manage')
    )


class FormTemplateListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasFormsPermission]
    permission_code = 'forms:template:manage'
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        queryset = FormTemplate.objects.all().order_by('-created_at')
        if request.query_params.get('active') in {'true', '1'}:
            queryset = queryset.filter(is_active=True)
        keyword = request.query_params.get('keyword')
        if keyword:
            queryset = queryset.filter(Q(code__icontains=keyword) | Q(name__icontains=keyword))
        return Response(FormTemplateSerializer(queryset, many=True, context={'request': request}).data)

    def post(self, request):
        serializer = FormTemplateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        template = serializer.save(created_by=request.user)
        if template.source_file and not template.source_file_name:
            template.source_file_name = template.source_file.name.rsplit('/', 1)[-1]
            template.save(update_fields=['source_file_name', 'updated_at'])
        return Response(FormTemplateSerializer(template, context={'request': request}).data, status=status.HTTP_201_CREATED)


class FormTemplateDetailView(APIView):
    permission_classes = [IsAuthenticated, HasFormsPermission]
    permission_code = 'forms:template:manage'
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_object(self, template_id):
        return get_object_or_404(FormTemplate, id=template_id)

    def get(self, request, template_id):
        return Response(FormTemplateSerializer(self.get_object(template_id), context={'request': request}).data)

    def patch(self, request, template_id):
        template = self.get_object(template_id)
        serializer = FormTemplateSerializer(template, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        template = serializer.save()
        if template.source_file and not template.source_file_name:
            template.source_file_name = template.source_file.name.rsplit('/', 1)[-1]
            template.save(update_fields=['source_file_name', 'updated_at'])
        return Response(FormTemplateSerializer(template, context={'request': request}).data)


class DispatchPreviewView(APIView):
    permission_classes = [IsAuthenticated, HasFormsPermission]
    permission_code = 'forms:dispatch:manage'

    def post(self, request):
        return Response(preview_dispatch(request.data))


class DispatchPublishView(APIView):
    permission_classes = [IsAuthenticated, HasFormsPermission]
    permission_code = 'forms:dispatch:manage'

    def post(self, request):
        batch, task_count = publish_dispatch(request.data, request.user)
        return Response({
            'batch': DispatchBatchSerializer(batch, context={'request': request}).data,
            'summary': {'created_tasks': task_count, 'total_tasks': batch.stats_total},
        }, status=status.HTTP_201_CREATED)


class DispatchBatchListView(APIView):
    permission_classes = [IsAuthenticated, HasFormsPermission]
    permission_code = 'forms:dispatch:manage'

    def get(self, request):
        queryset = DispatchBatch.objects.select_related('created_by').prefetch_related('rules__template')
        return Response(DispatchBatchSerializer(queryset, many=True, context={'request': request}).data)


class DispatchProgressView(APIView):
    permission_classes = [IsAuthenticated, HasFormsPermission]
    permission_code = 'forms:dispatch:manage'

    def get(self, request, batch_id):
        batch = get_object_or_404(DispatchBatch, id=batch_id)
        batch.refresh_stats()
        task_statuses = dict(batch.tasks.values_list('status').annotate(total=Count('id')))
        return Response({
            'batch': DispatchBatchSerializer(batch, context={'request': request}).data,
            'summary': {
                'total': batch.stats_total,
                'submitted': batch.stats_submitted,
                'pending': task_statuses.get(FormTaskStatus.PENDING, 0),
                'draft': task_statuses.get(FormTaskStatus.DRAFT, 0),
                'returned': task_statuses.get(FormTaskStatus.RETURNED, 0),
                'overdue': batch.stats_overdue,
            },
        })


class DispatchTaskResultsView(APIView):
    permission_classes = [IsAuthenticated, HasFormsPermission]
    permission_code = 'forms:dispatch:manage'

    def get(self, request, batch_id):
        batch = get_object_or_404(DispatchBatch, id=batch_id)
        queryset = batch.tasks.select_related('template').prefetch_related('submissions').order_by('assignee_name_snapshot')
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return Response({
            'batch': DispatchBatchSerializer(batch, context={'request': request}).data,
            'tasks': FormTaskSerializer(queryset, many=True, context={'request': request}).data,
        })


class DispatchDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, batch_id):
        if not can_manage_dispatch(request.user):
            return Response({'detail': '无权查看填报看板'}, status=status.HTTP_403_FORBIDDEN)
        return Response(FormDashboardService().get_dashboard(batch_id))


class DispatchPendingUsersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, batch_id):
        if not can_manage_dispatch(request.user):
            return Response({'detail': '无权查看未提交人员'}, status=status.HTTP_403_FORBIDDEN)
        statuses = [value.strip() for value in request.query_params.get('task_status', '').split(',') if value.strip()]
        return Response(FormDashboardService().get_pending_users(
            batch_id,
            org_unit_id=request.query_params.get('org_unit_id'),
            task_statuses=statuses or None,
            assignee_role=request.query_params.get('assignee_role'),
            page=request.query_params.get('page', 1),
            page_size=request.query_params.get('page_size', 20),
        ))


class MyTaskListView(APIView):
    permission_classes = [IsAuthenticated, HasFormsPermission]
    permission_code = 'forms:task:view'

    def get(self, request):
        queryset = visible_tasks(request.user).select_related('batch', 'template').prefetch_related('submissions')
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return Response(FormTaskSerializer(queryset, many=True, context={'request': request}).data)


class SaveDraftView(APIView):
    permission_classes = [IsAuthenticated, HasFormsPermission]
    permission_code = 'forms:task:submit'

    def patch(self, request, task_id):
        serializer = DraftSaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = get_object_or_404(FormTask, id=task_id)
        submission = save_submission(task, request.user, request=request, **serializer.validated_data)
        return Response(FormSubmissionSerializer(submission).data)


class SubmitTaskView(APIView):
    permission_classes = [IsAuthenticated, HasFormsPermission]
    permission_code = 'forms:task:submit'

    def post(self, request, task_id):
        serializer = TaskSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = get_object_or_404(FormTask, id=task_id)
        submission = save_submission(task, request.user, final=True, request=request, **serializer.validated_data)
        return Response(FormSubmissionSerializer(submission).data)


class ReturnTaskView(APIView):
    permission_classes = [IsAuthenticated, HasFormsPermission]
    permission_code = 'forms:task:manage'

    def post(self, request, task_id):
        serializer = ReturnTaskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = get_object_or_404(FormTask, id=task_id)
        return_task(task, request.user, serializer.validated_data['reason'], request=request)
        return Response(FormTaskSerializer(task, context={'request': request}).data)


class TaskResultView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        task = get_object_or_404(FormTask.objects.select_related('batch', 'template'), id=task_id)
        if not can_manage_dispatch(request.user) and not task.can_submit(request.user):
            return Response({'detail': '无权查看该任务'}, status=status.HTTP_403_FORBIDDEN)
        submission = task.submissions.filter(is_final=True).order_by('-version').first()
        return Response({
            'task': FormTaskSerializer(task, context={'request': request}).data,
            'submission': FormSubmissionSerializer(submission).data if submission else None,
        })


class FormTaskDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, task_id):
        return get_object_or_404(FormTask, id=task_id)

    def get(self, request, task_id):
        task = self.get_object(task_id)
        if not can_manage_dispatch(request.user) and not task.can_submit(request.user):
            return Response({'detail': '无权查看该任务'}, status=status.HTTP_403_FORBIDDEN)
        return Response(FormTaskSerializer(task, context={'request': request}).data)

    def delete(self, request, task_id):
        if not can_manage_dispatch(request.user):
            return Response({'detail': '无权删除任务'}, status=status.HTTP_403_FORBIDDEN)
        task = self.get_object(task_id)
        task.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OnlyOfficeTaskConfigView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        task = get_object_or_404(FormTask.objects.select_related('template'), id=task_id)
        if not task.can_submit(request.user):
            return Response({'detail': '无权编辑该任务'}, status=status.HTTP_403_FORBIDDEN)
        document = create_onlyoffice_document(task)
        return Response(build_onlyoffice_config(request, task, document, mode='edit'))


class OnlyOfficeTaskViewConfigView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        task = get_object_or_404(FormTask.objects.select_related('template'), id=task_id)
        if not can_manage_dispatch(request.user) and not task.can_submit(request.user):
            return Response({'detail': '无权查看该任务'}, status=status.HTTP_403_FORBIDDEN)
        document = create_onlyoffice_document(task)
        return Response(build_onlyoffice_config(request, task, document, mode='view'))


def build_onlyoffice_config(request, task, document, mode):
    title = document.file_name or f'{task.template.name}.xlsx'
    backend_url = settings.ONLYOFFICE_BACKEND_PUBLIC_URL.rstrip('/')
    return {
        'document_server_url': settings.ONLYOFFICE_DOCUMENT_SERVER.rstrip('/'),
        'document': {
            'fileType': Path(document.file.name).suffix.lstrip('.').lower() or 'xlsx',
            'key': document.document_key,
            'title': title,
            # 该 URL 由 OnlyOffice 容器而非浏览器下载，必须使用容器可访问的后端地址。
            'url': f'{backend_url}{document.file.url}',
        },
        'documentType': 'spreadsheet',
        'editorConfig': {
            'mode': mode,
            'lang': 'zh-CN',
            'callbackUrl': f'{backend_url}/api/forms/tasks/{task.id}/onlyoffice-callback/',
            'user': {'id': str(request.user.id), 'name': request.user.real_name or request.user.username},
            'customization': {'autosave': True, 'forcesave': True},
        },
    }


class OnlyOfficeCallbackView(APIView):
    """OnlyOffice Document Server 保存文件时调用的回调。"""

    permission_classes = [AllowAny]

    def post(self, request, task_id):
        task = get_object_or_404(FormTask, id=task_id)
        document = get_object_or_404(OnlyOfficeDocument, task=task)
        callback_key = request.data.get('key')
        if callback_key != document.document_key:
            return Response({'error': 1, 'message': '文档键不匹配'}, status=status.HTTP_403_FORBIDDEN)
        # 2=文档关闭后可保存，6=强制保存；其他状态无需下载新版本。
        if request.data.get('status') not in {2, 6}:
            document.last_callback_status = request.data.get('status')
            document.save(update_fields=['last_callback_status', 'updated_at'])
            return Response({'error': 0})
        file_url = request.data.get('url')
        if not file_url:
            return Response({'error': 1, 'message': '未提供保存文件地址'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            with urlopen(file_url, timeout=30) as remote_file:
                content = remote_file.read()
        except Exception:
            return Response({'error': 1, 'message': '下载 OnlyOffice 保存文件失败'}, status=status.HTTP_502_BAD_GATEWAY)
        suffix = Path(document.file.name).suffix or '.xlsx'
        document.version += 1
        document.document_key = f'form-{task.id}-v{document.version}'
        document.file.save(f'{task.id}-v{document.version}{suffix}', ContentFile(content), save=False)
        document.file_size = document.file.size
        document.storage_path = document.file.path
        document.last_callback_status = request.data.get('status')
        document.last_saved_at = timezone.now()
        document.save()
        return Response({'error': 0})
