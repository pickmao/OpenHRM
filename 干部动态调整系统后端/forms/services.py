import mimetypes
import secrets
from collections import defaultdict
from shutil import copyfileobj

from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts.models import User
from orgs.models import Membership, OrgUnit

from .models import (
    DispatchBatch, DispatchBatchStatus, DispatchRule, FormSubmission, FormTask, FormTaskAudit,
    FormTaskStatus, FormTemplate, OnlyOfficeDocument, ReceiverType, TargetType, TaskAuditAction,
)


def client_metadata(request):
    return {
        'ip_address': request.META.get('REMOTE_ADDR'),
        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
    }


def add_audit(task, action, operator, before=None, after=None, reason='', request=None):
    metadata = client_metadata(request) if request else {}
    return FormTaskAudit.objects.create(
        task=task,
        action=action,
        operator=operator,
        before_json=before or {},
        after_json=after or {},
        reason=reason,
        **metadata,
    )


def resolve_recipients(rule):
    """把前端保存的规则解析为可下发的用户或单位。"""
    expr = rule.get('receiver_expr_json') or {}
    receiver_type = rule.get('receiver_type', ReceiverType.USER)
    if receiver_type == ReceiverType.USER:
        ids = expr.get('user_ids') or expr.get('ids') or []
        if expr.get('all_users'):
            users = User.objects.filter(is_active=True)
        else:
            users = User.objects.filter(id__in=ids, is_active=True)
        return [(ReceiverType.USER, user, None, '') for user in users]

    if receiver_type == ReceiverType.ORG_UNIT:
        ids = expr.get('org_unit_ids') or expr.get('ids') or []
        units = OrgUnit.objects.filter(id__in=ids, is_active=True)
        return [(ReceiverType.ORG_UNIT, unit, unit, 'DEPT_MANAGER') for unit in units]

    if receiver_type == ReceiverType.ORG_ROLE:
        role_codes = expr.get('role_codes') or ([expr['role_code']] if expr.get('role_code') else [])
        unit_ids = expr.get('org_unit_ids') or []
        users = User.objects.filter(is_active=True, user_roles__role__is_active=True, user_roles__role__code__in=role_codes)
        if unit_ids:
            users = users.filter(memberships__unit_id__in=unit_ids, memberships__effective_to__isnull=True)
        return [(ReceiverType.USER, user, _primary_unit(user), ','.join(role_codes)) for user in users.distinct()]

    raise ValidationError({'receiver_type': '不支持的接收人类型'})


def _primary_unit(user):
    membership = Membership.objects.filter(user=user, effective_to__isnull=True).order_by('-is_primary').select_related('unit').first()
    return membership.unit if membership else None


@transaction.atomic
def publish_dispatch(payload, creator):
    rules = payload.get('rules') or []
    if not rules:
        raise ValidationError({'rules': '至少选择一类接收人'})
    batch_id = payload.get('batch_id')
    if batch_id:
        batch = DispatchBatch.objects.select_for_update().filter(id=batch_id).first()
        if not batch:
            raise ValidationError({'batch_id': '所选填报批次不存在'})
        if batch.status == DispatchBatchStatus.CLOSED:
            raise ValidationError({'batch_id': '所选填报批次已关闭，不能继续追加表格'})
    else:
        if not payload.get('deadline_at'):
            raise ValidationError({'deadline_at': '新建填报批次必须填写截止时间'})
        batch = DispatchBatch.objects.create(
            cycle_id=payload.get('cycle_id', ''),
            stage_code=payload.get('stage_code', ''),
            name=payload.get('batch_name') or payload.get('name') or '未命名表单下发',
            deadline_at=payload.get('deadline_at'),
            status=DispatchBatchStatus.PUBLISHED,
            published_at=timezone.now(),
            created_by=creator,
        )
    task_count = 0
    for raw_rule in rules:
        template_id = raw_rule.get('template_id') or raw_rule.get('template')
        template_code = raw_rule.get('template_code')
        template_query = FormTemplate.objects.filter(is_active=True)
        template = template_query.get(id=template_id) if template_id else template_query.get(code=template_code)
        target_type = raw_rule.get('target_type', TargetType.USER)
        rule = DispatchRule.objects.create(
            batch=batch,
            template=template,
            receiver_type=raw_rule.get('receiver_type', ReceiverType.USER),
            receiver_expr_json=raw_rule.get('receiver_expr_json') or {},
            target_type=target_type,
            target_expr_json=raw_rule.get('target_expr_json') or {},
            created_by=creator,
        )
        for assignee_type, assignee, unit, role_name in resolve_recipients(raw_rule):
            if assignee_type == ReceiverType.USER:
                assignee_id = assignee.id
                assignee_name = assignee.real_name or assignee.username
                target_id = assignee.id
            else:
                assignee_id = assignee.id
                assignee_name = assignee.name
                target_id = assignee.id
            task, created = FormTask.objects.get_or_create(
                batch=batch,
                template=template,
                assignee_type=assignee_type,
                assignee_id=assignee_id,
                target_type=TargetType.ORG_UNIT if assignee_type == ReceiverType.ORG_UNIT else TargetType.USER,
                target_id=target_id,
                defaults={
                    'template_version': template.version,
                    'assignee_name_snapshot': assignee_name,
                    'assignee_role_snapshot': role_name,
                    'org_unit_snapshot': unit,
                    'deadline_at': batch.deadline_at,
                    'context_json': {'dispatch_rule_id': str(rule.id), 'source_file_name': template.source_file_name},
                },
            )
            if created:
                task_count += 1
                add_audit(task, TaskAuditAction.DISPATCH, creator, after={'batch_id': str(batch.id)})
    batch.refresh_stats()
    return batch, task_count


def preview_dispatch(payload):
    result = []
    duplicate_keys = set()
    batch_id = payload.get('batch_id')
    existing_keys = set()
    if batch_id:
        batch = DispatchBatch.objects.filter(id=batch_id).first()
        if not batch:
            raise ValidationError({'batch_id': '所选填报批次不存在'})
        if batch.status == DispatchBatchStatus.CLOSED:
            raise ValidationError({'batch_id': '所选填报批次已关闭，不能继续追加表格'})
        existing_keys = {
            (str(template_id), assignee_type, str(assignee_id), target_type, str(target_id))
            for template_id, assignee_type, assignee_id, target_type, target_id in batch.tasks.values_list(
                'template_id', 'assignee_type', 'assignee_id', 'target_type', 'target_id'
            )
        }
    for index, rule in enumerate(payload.get('rules') or []):
        template_id = rule.get('template_id') or rule.get('template')
        template_code = rule.get('template_code')
        template_query = FormTemplate.objects.filter(is_active=True)
        template = template_query.get(id=template_id) if template_id else template_query.get(code=template_code)
        for assignee_type, assignee, unit, role_name in resolve_recipients(rule):
            assignee_id = assignee.id
            target_type = TargetType.ORG_UNIT if assignee_type == ReceiverType.ORG_UNIT else TargetType.USER
            key = (str(template.id), assignee_type, str(assignee_id), target_type, str(assignee_id))
            if key in duplicate_keys or key in existing_keys:
                continue
            duplicate_keys.add(key)
            result.append({
                'rule_index': index,
                'template_id': str(template.id),
                'template_name': template.name,
                'assignee_type': assignee_type,
                'assignee_id': str(assignee_id),
                'assignee_name': getattr(assignee, 'real_name', '') or getattr(assignee, 'name', ''),
                'assignee_role': role_name,
                'org_unit': unit.name if unit else '',
            })
    return {'summary': {'total': len(result)}, 'tasks': result}


def visible_tasks(user):
    unit_ids = Membership.objects.filter(user=user, is_manager=True, effective_to__isnull=True).values_list('unit_id', flat=True)
    return FormTask.objects.filter(
        Q(assignee_type=ReceiverType.USER, assignee_id=user.id)
        | Q(reassign_to=user)
        | Q(assignee_type=ReceiverType.ORG_UNIT, assignee_id__in=unit_ids)
    )


@transaction.atomic
def save_submission(task, user, *, payload_json, attachments_json=None, score_json=None, final=False, request=None):
    if not task.can_submit(user):
        raise PermissionDenied('无权处理该填报任务')
    if task.status == FormTaskStatus.CLOSED:
        raise ValidationError('任务已关闭')
    before = {'status': task.status}
    next_version = (task.submissions.order_by('-version').values_list('version', flat=True).first() or 0) + 1
    metadata = client_metadata(request) if request else {}
    submission = FormSubmission.objects.create(
        task=task,
        version=next_version,
        is_final=final,
        payload_json=payload_json or {},
        score_json=score_json,
        attachments_json=attachments_json or [],
        submitted_by=user,
        submitted_at=timezone.now() if final else None,
        **metadata,
    )
    if final:
        task.submissions.exclude(id=submission.id).filter(is_final=True).update(is_final=False)
        task.status = FormTaskStatus.SUBMITTED
        task.submitted_at = timezone.now()
        action = TaskAuditAction.SUBMIT
    else:
        task.status = FormTaskStatus.DRAFT
        action = TaskAuditAction.SAVE_DRAFT
    task.save(update_fields=['status', 'submitted_at', 'updated_at'])
    add_audit(task, action, user, before=before, after={'status': task.status, 'submission_id': str(submission.id)}, request=request)
    task.batch.refresh_stats()
    return submission


@transaction.atomic
def return_task(task, operator, reason, request=None):
    before = {'status': task.status}
    task.status = FormTaskStatus.RETURNED
    task.submitted_at = None
    task.save(update_fields=['status', 'submitted_at', 'updated_at'])
    task.submissions.filter(is_final=True).update(is_final=False, return_reason=reason, returned_by=operator, returned_at=timezone.now())
    add_audit(task, TaskAuditAction.RETURN, operator, before=before, after={'status': task.status}, reason=reason, request=request)
    task.batch.refresh_stats()


def create_onlyoffice_document(task):
    if hasattr(task, 'onlyoffice_document'):
        return task.onlyoffice_document
    template_file = task.template.source_file
    if not template_file:
        raise ValidationError('该模板没有上传 Excel 文件')
    suffix = template_file.name.rsplit('.', 1)[-1] if '.' in template_file.name else 'xlsx'
    file_name = f'{task.id}.{suffix}'
    original_name = task.template.source_file_name or file_name
    document = OnlyOfficeDocument(
        task=task,
        original_name=original_name,
        file_ext=suffix.lower(),
        mime_type=mimetypes.guess_type(original_name)[0] or 'application/octet-stream',
        file_size=0,
        storage_path='',
        access_token=secrets.token_hex(32),
        file_name=original_name,
        document_key=f'form-{task.id}-v1',
        created_by_id=task.assignee_id if task.assignee_type == ReceiverType.USER else None,
    )
    template_file.open('rb')
    try:
        document.file.save(file_name, ContentFile(template_file.read()), save=False)
    finally:
        template_file.close()
    document.file_size = document.file.size
    document.storage_path = document.file.path
    document.save()
    return document
