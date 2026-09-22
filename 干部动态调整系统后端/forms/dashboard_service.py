from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from accounts.models import User
from cadres.org_alignment import current_department_names_for_user_ids, current_org_units_for_user_ids
from orgs.models import OrgUnit

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
        people_summary, branch_stats = self._people_stats(tasks)
        return {
            'batch_id': str(batch.id), 'batch_name': batch.name, 'cycle_id': batch.cycle_id,
            'stage_code': batch.stage_code, 'status': batch.status,
            'deadline_at': batch.deadline_at.isoformat(), 'summary': summary,
            'org_unit_stats': self._org_unit_stats(tasks),
            'people_summary': people_summary,
            'branch_stats': branch_stats,
            'status_stats': self._status_stats(tasks),
            'template_stats': self._template_stats(tasks),
            'timeline': self._timeline(tasks),
        }

    @staticmethod
    def _assignee_user_id(task):
        if task.assignee_type != ReceiverType.USER:
            return None
        return task.reassign_to_id or task.assignee_id

    @classmethod
    def _branch_for_unit(cls, unit, units):
        unit_id = unit.id if unit else None
        seen = set()
        while unit_id and unit_id not in seen:
            seen.add(unit_id)
            current = units.get(unit_id)
            if not current:
                break
            if current.unit_type == 'BRANCH':
                return current
            unit_id = current.parent_id
        return None

    @classmethod
    def _people_stats(cls, tasks):
        # 人数按实际接收用户去重；一人全部表格提交后才计入已完成人数。
        # 支部归集以花名册当前部门对应组织节点为准，下发快照只作兜底。
        units = {unit.id: unit for unit in OrgUnit.objects.all()}
        people, branches = {}, {}
        user_tasks = list(tasks.filter(assignee_type=ReceiverType.USER).exclude(status=FormTaskStatus.CLOSED))
        user_ids = {cls._assignee_user_id(task) for task in user_tasks}
        current_units = current_org_units_for_user_ids(user_ids)
        for task in user_tasks:
            user_id = cls._assignee_user_id(task)
            done = task.status == FormTaskStatus.SUBMITTED
            people[user_id] = people.get(user_id, True) and done
            unit = current_units.get(user_id) or task.org_unit_snapshot
            branch = cls._branch_for_unit(unit, units)
            key = str(branch.id) if branch else None
            group = branches.setdefault(key, {
                'branch_id': key,
                'branch_name': branch.name if branch else '未关联支部',
                'people': {},
            })
            group['people'][user_id] = group['people'].get(user_id, True) and done

        def summarize(values):
            total, submitted = len(values), sum(values.values())
            return {'total': total, 'submitted': submitted, 'completion_rate': round(submitted * 100 / total, 2) if total else 0}

        return summarize(people), [
            {'branch_id': group['branch_id'], 'branch_name': group['branch_name'], **summarize(group['people'])}
            for group in sorted(branches.values(), key=lambda item: item['branch_name'])
        ]

    def get_pending_users(self, batch_id, *, org_unit_id=None, task_statuses=None, assignee_role=None, page=1, page_size=20):
        batch = DispatchBatch.objects.get(id=batch_id)
        statuses = task_statuses or [FormTaskStatus.PENDING, FormTaskStatus.OVERDUE]
        tasks = FormTask.objects.filter(batch=batch, status__in=statuses).select_related(
            'template', 'org_unit_snapshot', 'reassign_to'
        ).order_by('deadline_at')
        if assignee_role:
            tasks = tasks.filter(assignee_role_snapshot=assignee_role)
        task_list = list(tasks)
        user_ids = {self._assignee_user_id(task) for task in task_list}
        current_names = current_department_names_for_user_ids(user_ids)
        current_units = current_org_units_for_user_ids(user_ids)
        if org_unit_id:
            org_unit_id = str(org_unit_id)
            filtered = []
            for task in task_list:
                unit = current_units.get(self._assignee_user_id(task)) or task.org_unit_snapshot
                if unit and str(unit.id) == org_unit_id:
                    filtered.append(task)
            task_list = filtered
        total = len(task_list)
        page = max(int(page), 1)
        page_size = min(max(int(page_size), 1), 100)
        start = (page - 1) * page_size
        result = []
        now = timezone.now()
        for task in task_list[start:start + page_size]:
            user = task.reassign_to
            if user is None and task.assignee_type == ReceiverType.USER:
                user = User.objects.filter(id=task.assignee_id).first()
            overdue_days = max((now - task.deadline_at).days, 0) if task.is_overdue() else 0
            user_id = self._assignee_user_id(task)
            unit = current_units.get(user_id) or task.org_unit_snapshot
            org_name = current_names.get(user_id) or (unit.name if unit else '')
            result.append({
                'task_id': str(task.id), 'assignee_type': task.assignee_type,
                'assignee_id': str(task.assignee_id), 'assignee_name': task.assignee_name_snapshot,
                'assignee_role': task.assignee_role_snapshot,
                'org_unit_id': str(unit.id) if unit else None,
                'org_unit': org_name,
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

    @classmethod
    def _org_unit_stats(cls, tasks):
        task_list = list(tasks.select_related('org_unit_snapshot'))
        user_ids = {cls._assignee_user_id(task) for task in task_list}
        current_names = current_department_names_for_user_ids(user_ids)
        current_units = current_org_units_for_user_ids(user_ids)
        grouped = {}
        for task in task_list:
            user_id = cls._assignee_user_id(task)
            dept_name = current_names.get(user_id) or (
                task.org_unit_snapshot.name if task.org_unit_snapshot else ''
            )
            if not dept_name:
                continue
            unit = current_units.get(user_id) or task.org_unit_snapshot
            key = str(unit.id) if unit else f'name:{dept_name}'
            bucket = grouped.setdefault(key, {
                'org_unit_id': str(unit.id) if unit else None,
                'org_unit_name': dept_name,
                'total': 0,
                'submitted': 0,
            })
            bucket['total'] += 1
            if task.status == FormTaskStatus.SUBMITTED:
                bucket['submitted'] += 1
        result = []
        for item in grouped.values():
            pending = item['total'] - item['submitted']
            result.append({
                **item,
                'pending': pending,
                'completion_rate': round(item['submitted'] * 100 / item['total'], 2) if item['total'] else 0,
            })
        return sorted(result, key=lambda item: (-item['submitted'], item['org_unit_name']))

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
