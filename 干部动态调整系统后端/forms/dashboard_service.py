from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from accounts.models import User

from .models import DispatchBatch, FormTask, FormTaskStatus, ReceiverType


class FormDashboardService:
    """批次填报进度和未提交对象的查询服务。"""

    def get_dashboard(self, batch_id):
        batch = DispatchBatch.objects.get(id=batch_id)
        tasks = FormTask.objects.filter(batch=batch)
        total = tasks.count()
        submitted = tasks.filter(status=FormTaskStatus.SUBMITTED).count()
        overdue = sum(task.is_overdue() for task in tasks.only('id', 'deadline_at', 'status'))
        summary = {
            'total': total,
            'submitted': submitted,
            'pending': tasks.filter(status=FormTaskStatus.PENDING).count(),
            'draft': tasks.filter(status=FormTaskStatus.DRAFT).count(),
            'returned': tasks.filter(status=FormTaskStatus.RETURNED).count(),
            'overdue': overdue,
            'completion_rate': round(submitted * 100 / total, 2) if total else 0,
        }
        return {
            'batch_id': str(batch.id), 'batch_name': batch.name, 'cycle_id': batch.cycle_id,
            'stage_code': batch.stage_code, 'status': batch.status,
            'deadline_at': batch.deadline_at.isoformat(), 'summary': summary,
            'org_unit_stats': self._org_unit_stats(tasks),
            'status_stats': self._status_stats(tasks),
            'template_stats': self._template_stats(tasks),
            'timeline': self._timeline(tasks),
        }

    def get_pending_users(self, batch_id, *, org_unit_id=None, task_statuses=None, assignee_role=None, page=1, page_size=20):
        batch = DispatchBatch.objects.get(id=batch_id)
        statuses = task_statuses or [FormTaskStatus.PENDING, FormTaskStatus.OVERDUE]
        tasks = FormTask.objects.filter(batch=batch, status__in=statuses).select_related(
            'template', 'org_unit_snapshot', 'reassign_to'
        ).order_by('deadline_at')
        if org_unit_id:
            tasks = tasks.filter(org_unit_snapshot_id=org_unit_id)
        if assignee_role:
            tasks = tasks.filter(assignee_role_snapshot=assignee_role)
        total = tasks.count()
        page = max(int(page), 1)
        page_size = min(max(int(page_size), 1), 100)
        start = (page - 1) * page_size
        result = []
        now = timezone.now()
        for task in tasks[start:start + page_size]:
            user = task.reassign_to
            if user is None and task.assignee_type == ReceiverType.USER:
                user = User.objects.filter(id=task.assignee_id).first()
            overdue_days = max((now - task.deadline_at).days, 0) if task.is_overdue() else 0
            result.append({
                'task_id': str(task.id), 'assignee_type': task.assignee_type,
                'assignee_id': str(task.assignee_id), 'assignee_name': task.assignee_name_snapshot,
                'assignee_role': task.assignee_role_snapshot,
                'org_unit_id': str(task.org_unit_snapshot_id) if task.org_unit_snapshot_id else None,
                'org_unit': task.org_unit_snapshot.name if task.org_unit_snapshot else '',
                'username': user.username if user else '', 'phone': getattr(user, 'phone', '') if user else '',
                'email': user.email if user else '', 'template_code': task.template.code,
                'template_name': task.template.name, 'task_status': task.status,
                'deadline_at': task.deadline_at.isoformat(), 'is_overdue': task.is_overdue(),
                'days_overdue': overdue_days, 'reassign_to': str(task.reassign_to_id) if task.reassign_to_id else None,
            })
        return {
            'batch_id': str(batch.id), 'batch_name': batch.name, 'total': total,
            'page': page, 'page_size': page_size, 'total_pages': (total + page_size - 1) // page_size,
            'pending_users': result,
        }

    @staticmethod
    def _org_unit_stats(tasks):
        grouped = tasks.filter(org_unit_snapshot_id__isnull=False).values(
            'org_unit_snapshot_id', 'org_unit_snapshot__name'
        ).annotate(
            total=Count('id'), submitted=Count('id', filter=Q(status=FormTaskStatus.SUBMITTED))
        ).order_by('-submitted', 'org_unit_snapshot__name')
        return [{
            'org_unit_id': str(item['org_unit_snapshot_id']), 'org_unit_name': item['org_unit_snapshot__name'],
            'total': item['total'], 'submitted': item['submitted'], 'pending': item['total'] - item['submitted'],
            'completion_rate': round(item['submitted'] * 100 / item['total'], 2) if item['total'] else 0,
        } for item in grouped]

    @staticmethod
    def _status_stats(tasks):
        return [{
            'status': item['status'], 'status_display': FormTaskStatus(item['status']).label, 'count': item['count'],
        } for item in tasks.values('status').annotate(count=Count('id')).order_by('-count')]

    @staticmethod
    def _template_stats(tasks):
        grouped = tasks.values('template__code', 'template__name').annotate(
            total=Count('id'), submitted=Count('id', filter=Q(status=FormTaskStatus.SUBMITTED))
        ).order_by('-total', 'template__name')
        return [{
            'template_code': item['template__code'], 'template_name': item['template__name'],
            'total': item['total'], 'submitted': item['submitted'], 'pending': item['total'] - item['submitted'],
            'completion_rate': round(item['submitted'] * 100 / item['total'], 2) if item['total'] else 0,
        } for item in grouped]

    @staticmethod
    def _timeline(tasks):
        grouped = tasks.filter(submitted_at__isnull=False).annotate(submit_date=TruncDate('submitted_at')).values(
            'submit_date'
        ).annotate(count=Count('id')).order_by('submit_date')
        total = 0
        result = []
        for item in grouped:
            total += item['count']
            result.append({'date': item['submit_date'].isoformat(), 'daily_count': item['count'], 'cumulative_count': total})
        return result
