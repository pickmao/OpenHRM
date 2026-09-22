from collections import defaultdict

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts.models import User
from orgs.models import OrgUnit, UnitType

from .form_defs import (
    CADRE_TALK_DIMENSIONS, FORM_META_MAP, RULES_TEXT, SELF_DIMENSIONS, TALK_OVERALL,
    TEAM_DIMENSIONS, TEAM_EVAL_ITEMS, default_payload, form_catalog, merge_payload, schema_for, validate_payload,
)
from .matching import build_context_for_recipient, match_form_type, recipient_payload
from .models import CampaignStatus, FillerRole, FormType, InspectionCampaign, InspectionTask, TaskStatus
from .permissions import has_knowing_people_permission
from .payload_validation import validate_task_payload


MANAGE_PERMISSION = 'knowing_people:campaign:manage'
TASK_VIEW_PERMISSION = 'knowing_people:task:view'
TASK_SUBMIT_PERMISSION = 'knowing_people:task:submit'
RESULT_PERMISSION = 'knowing_people:result:view'

DIMENSION_LABELS = {
    item['key']: item['label']
    for group in (SELF_DIMENSIONS, TEAM_DIMENSIONS, CADRE_TALK_DIMENSIONS, TEAM_EVAL_ITEMS, TALK_OVERALL)
    for item in group
}


def _normalize_form_types(values):
    if not values:
        raise ValidationError({'form_types': '请至少选择一种填报表。'})
    cleaned = []
    for item in values:
        if item not in FormType.values:
            raise ValidationError({'form_types': f'不支持的表单类型：{item}'})
        if item not in cleaned:
            cleaned.append(item)
    return cleaned


def preview_dispatch(data):
    form_types = _normalize_form_types(data.get('form_types'))
    branch_ids = data.get('branch_ids') or []
    if branch_ids and OrgUnit.objects.filter(id__in=branch_ids, is_active=True, unit_type=UnitType.BRANCH).count() != len(set(branch_ids)):
        raise ValidationError({'branch_ids': '所选支部不存在或已停用，请重新选择。'})
    extra_by_type = data.get('extra_user_ids_by_type') or {}
    groups = []
    total = 0
    for form_type in form_types:
        matched = match_form_type(
            form_type,
            branch_ids=branch_ids or None,
            extra_user_ids=extra_by_type.get(form_type) or [],
        )
        for recipient in matched['recipients']:
            context = build_context_for_recipient(recipient)
            recipient['target_count'] = len(context.get('targets') or [])
            recipient['target_names'] = [target['name'] for target in context.get('targets') or []]
        groups.append({
            'form_type': form_type,
            'form_label': FormType(form_type).label,
            'auto_dispatch': FORM_META_MAP[form_type]['auto_dispatch'],
            'recipients': matched['recipients'],
            'unmatched': matched['unmatched'],
            'warnings': matched['warnings'],
            'count': len(matched['recipients']),
        })
        total += len(matched['recipients'])
    return {'summary': {'total': total, 'form_types': len(form_types)}, 'groups': groups, 'rules_text': RULES_TEXT}


def _recipient_from_override(item):
    user = User.objects.filter(id=item.get('user_id'), is_active=True).first()
    if not user:
        raise ValidationError({'recipients': '存在无效或停用的填报人。'})
    form_type = item.get('form_type')
    if form_type not in FormType.values:
        raise ValidationError({'recipients': f'不支持的表单类型：{form_type}'})
    branch = None
    if item.get('branch_id'):
        branch = OrgUnit.objects.filter(id=item['branch_id'], is_active=True, unit_type=UnitType.BRANCH).first()
        if not branch:
            raise ValidationError({'recipients': '所选支部不存在或已停用。'})
    role = item.get('filler_role') if item.get('filler_role') in FillerRole.values else FillerRole.MANUAL
    role = {
        FormType.ATTACHMENT_2: FillerRole.MIDDLE_LEADER,
        FormType.ATTACHMENT_3: FillerRole.MIDDLE_LEADER,
        FormType.ATTACHMENT_4: FillerRole.BRANCH_LEADERSHIP,
        FormType.ATTACHMENT_6_2: FillerRole.BRANCH_STAFF,
        FormType.ATTACHMENT_1: FillerRole.INSPECTION_TALKER,
    }.get(form_type, role)
    return recipient_payload(
        user,
        form_type=form_type,
        filler_role=role,
        branch=branch,
        extra={'source': item.get('source') or '管理员指定', 'auto': False},
    )


@transaction.atomic
def create_campaign(data, creator):
    form_types = _normalize_form_types(data.get('form_types'))
    recipients = data.get('recipients') if 'recipients' in data else None
    if recipients is not None:
        resolved = [_recipient_from_override(item) for item in recipients]
        if data.get('form_types'):
            allowed = set(form_types)
            resolved = [item for item in resolved if item['form_type'] in allowed]
    else:
        preview = preview_dispatch(data)
        resolved = [item for group in preview['groups'] for item in group['recipients']]
    if not resolved:
        raise ValidationError({'recipients': '当前勾选的表单没有匹配到填报人。请调整范围或手动指定。'})

    now = timezone.now()
    campaign = InspectionCampaign.objects.create(
        name=data['name'].strip(),
        year=(data.get('year') or '').strip(),
        period_start=data.get('period_start'),
        period_end=data.get('period_end'),
        description=(data.get('description') or '').strip(),
        status=CampaignStatus.PUBLISHED,
        form_types=form_types,
        deadline_at=data['deadline_at'],
        published_at=now,
        created_by=creator,
    )
    tasks = []
    seen = set()
    branch_forms = {FormType.ATTACHMENT_4, FormType.ATTACHMENT_5}
    branch_representatives = set()
    for item in resolved:
        global_forms = {FormType.ATTACHMENT_2, FormType.ATTACHMENT_3, FormType.ATTACHMENT_6_1,
                        FormType.ATTACHMENT_7_1, FormType.ATTACHMENT_7_2, FormType.ATTACHMENT_7_3}
        branch_key = item.get('branch_id') if item['form_type'] not in global_forms else None
        key = (item['form_type'], item['user_id'], branch_key)
        if key in seen:
            continue
        seen.add(key)
        user = User.objects.get(id=item['user_id'])
        context = build_context_for_recipient(item)
        context['campaign_year'] = campaign.year
        context['period_start'] = campaign.period_start.isoformat() if campaign.period_start else ''
        context['period_end'] = campaign.period_end.isoformat() if campaign.period_end else ''
        branch = context.get('branch') or {}
        if item['form_type'] in {FormType.ATTACHMENT_4, FormType.ATTACHMENT_5, FormType.ATTACHMENT_6_2, FormType.ATTACHMENT_7_4, FormType.ATTACHMENT_1} and not branch.get('id'):
            raise ValidationError({'recipients': f'{item["user_name"]}的{item["form_label"]}未关联支部，请在预览中指定支部。'})
        if item['form_type'] in branch_forms:
            representative_key = (item['form_type'], branch['id'])
            if representative_key in branch_representatives:
                raise ValidationError({'recipients': f'{branch["name"]}的{item["form_label"]}只能指定一名填报代表。'})
            branch_representatives.add(representative_key)
        if item['form_type'] in {FormType.ATTACHMENT_6_1, FormType.ATTACHMENT_6_2, FormType.ATTACHMENT_7_1, FormType.ATTACHMENT_7_2, FormType.ATTACHMENT_7_3, FormType.ATTACHMENT_7_4, FormType.ATTACHMENT_1} and not context.get('targets'):
            raise ValidationError({'recipients': f'{item["form_label"]}没有被评对象，请先完善花名册和支部归属。'})
        tasks.append(InspectionTask(
            campaign=campaign,
            form_type=item['form_type'],
            filler_role=item['filler_role'],
            assignee=user,
            branch_id=branch.get('id'),
            roster_id=item.get('roster_id'),
            assignee_name_snapshot=item['user_name'],
            org_unit_name_snapshot=item.get('org_unit_name') or '',
            branch_name_snapshot=item.get('branch_name') or '',
            payload_json=default_payload(item['form_type'], context),
            context_json=context,
        ))
    InspectionTask.objects.bulk_create(tasks)
    return campaign


@transaction.atomic
def close_campaign(campaign):
    campaign = InspectionCampaign.objects.select_for_update().get(id=campaign.id)
    if campaign.status != CampaignStatus.PUBLISHED:
        raise ValidationError('只有填写中的批次可以关闭。')
    campaign.status = CampaignStatus.CLOSED
    campaign.closed_at = timezone.now()
    campaign.save(update_fields=['status', 'closed_at', 'updated_at'])
    return campaign


def progress_stats(tasks):
    total = len(tasks)
    submitted = sum(1 for task in tasks if task.status == TaskStatus.SUBMITTED)
    draft = sum(1 for task in tasks if task.status == TaskStatus.DRAFT)
    returned = sum(1 for task in tasks if task.status == TaskStatus.RETURNED)
    pending = sum(1 for task in tasks if task.status == TaskStatus.PENDING)
    return {
        'total': total,
        'submitted': submitted,
        'draft': draft,
        'returned': returned,
        'pending': pending,
        'completion_rate': round(submitted * 100 / total, 1) if total else 0,
    }


def campaign_summary(campaign, *, include_progress=False):
    payload = {
        'id': str(campaign.id),
        'name': campaign.name,
        'year': campaign.year,
        'period_start': campaign.period_start,
        'period_end': campaign.period_end,
        'description': campaign.description,
        'status': campaign.status,
        'status_display': campaign.get_status_display(),
        'form_types': campaign.form_types or [],
        'form_type_labels': [FormType(item).label for item in (campaign.form_types or []) if item in FormType.values],
        'deadline_at': campaign.deadline_at,
        'published_at': campaign.published_at,
        'closed_at': campaign.closed_at,
        'is_open': campaign.is_open(),
        'created_at': campaign.created_at,
        'rules_text': RULES_TEXT,
    }
    if include_progress:
        tasks = list(campaign.tasks.all())
        payload['progress'] = progress_stats(tasks)
        by_type = defaultdict(list)
        by_branch = defaultdict(list)
        for task in tasks:
            by_type[task.form_type].append(task)
            by_branch[task.branch_name_snapshot or '未关联支部'].append(task)
        payload['by_form_type'] = [
            {'form_type': key, 'form_label': FormType(key).label if key in FormType.values else key, **progress_stats(items)}
            for key, items in by_type.items()
        ]
        payload['by_branch'] = [
            {'branch_name': key, **progress_stats(items)}
            for key, items in sorted(by_branch.items())
        ]
    return payload


def serialize_task(task, *, include_form=False, user=None):
    campaign = task.campaign
    can_manage = bool(user and has_knowing_people_permission(user, MANAGE_PERMISSION))
    payload = {
        'id': str(task.id),
        'campaign_id': str(campaign.id),
        'campaign_name': campaign.name,
        'form_type': task.form_type,
        'form_label': task.get_form_type_display(),
        'short_label': FORM_META_MAP.get(task.form_type, {}).get('short_label', task.get_form_type_display()),
        'filler_role': task.filler_role,
        'filler_role_label': task.get_filler_role_display(),
        'status': task.status,
        'status_display': task.get_status_display(),
        'assignee_id': str(task.assignee_id),
        'assignee_name': task.assignee_name_snapshot,
        'org_unit_name': task.org_unit_name_snapshot,
        'branch_id': str(task.branch_id) if task.branch_id else None,
        'branch_name': task.branch_name_snapshot,
        'deadline_at': campaign.deadline_at,
        'is_open': campaign.is_open() and task.status != TaskStatus.SUBMITTED,
        'readonly': task.status == TaskStatus.SUBMITTED or not campaign.is_open() or bool(user and task.assignee_id != user.id),
        'submitted_at': task.submitted_at,
        'return_reason': task.return_reason,
        'remind_count': task.remind_count,
        'reminded_at': task.reminded_at,
        'can_manage': can_manage,
    }
    if include_form:
        context = task.context_json or {}
        payload['schema'] = schema_for(task.form_type)
        if task.form_type == FormType.ATTACHMENT_5:
            payload['schema']['roster_people'] = context.get('roster_people') or []
        payload['context'] = context
        payload['payload'] = merge_payload(task.form_type, task.payload_json or {}, context)
        payload['prefill_hint'] = '带「花名册」标记的字段来自人员库，可核对后修改。'
    return payload


def _ensure_editable(task, user, *, allow_manage_return=False):
    if task.assignee_id != user.id and not has_knowing_people_permission(user, MANAGE_PERMISSION):
        raise PermissionDenied('只能填写本人的任务。')
    if task.assignee_id != user.id:
        raise PermissionDenied('管理员请使用退回后由本人重填。')
    if task.status == TaskStatus.SUBMITTED:
        raise ValidationError('已提交的表单不能再修改。')
    if not task.campaign.is_open():
        raise ValidationError('该批次已截止或已关闭。')


@transaction.atomic
def save_draft(task, user, payload):
    task = InspectionTask.objects.select_for_update().select_related('campaign').get(id=task.id)
    _ensure_editable(task, user)
    task.payload_json = validate_task_payload(task, payload, strict=False)
    if task.status != TaskStatus.RETURNED:
        task.status = TaskStatus.DRAFT
    task.save(update_fields=['payload_json', 'status', 'updated_at'])
    return task


@transaction.atomic
def submit_task(task, user, payload):
    task = InspectionTask.objects.select_for_update().select_related('campaign').get(id=task.id)
    _ensure_editable(task, user)
    cleaned = validate_task_payload(task, payload, strict=True)
    task.payload_json = cleaned
    task.status = TaskStatus.SUBMITTED
    task.submitted_at = timezone.now()
    task.return_reason = ''
    task.save(update_fields=['payload_json', 'status', 'submitted_at', 'return_reason', 'updated_at'])
    return task


@transaction.atomic
def return_task(task, operator, reason):
    task = InspectionTask.objects.select_for_update().get(id=task.id)
    if not (reason or '').strip():
        raise ValidationError({'reason': '请填写退回原因。'})
    if task.status != TaskStatus.SUBMITTED:
        raise ValidationError('只能退回已提交的任务。')
    task.status = TaskStatus.RETURNED
    task.submitted_at = None
    task.return_reason = reason.strip()
    task.returned_by = operator
    task.returned_at = timezone.now()
    task.save(update_fields=['status', 'submitted_at', 'return_reason', 'returned_by', 'returned_at', 'updated_at'])
    return task


@transaction.atomic
def remind_task(task):
    if task.status == TaskStatus.SUBMITTED:
        raise ValidationError('该任务已提交，无需催办。')
    task.remind_count = (task.remind_count or 0) + 1
    task.reminded_at = timezone.now()
    task.save(update_fields=['remind_count', 'reminded_at', 'updated_at'])
    return task


def _grade_bucket(grade):
    mapping = {'优': 'excellent', '良': 'good', '中': 'average', '差': 'poor', '好': 'excellent', '较好': 'good', '一般': 'average'}
    return mapping.get(grade)


def accumulate_votes(task):
    payload = task.payload_json or {}
    form_type = task.form_type
    rows = []
    if form_type in {FormType.ATTACHMENT_6_1, FormType.ATTACHMENT_7_1, FormType.ATTACHMENT_7_2, FormType.ATTACHMENT_7_3, FormType.ATTACHMENT_7_4}:
        for target in payload.get('targets') or []:
            for key, grade in (target.get('scores') or {}).items():
                rows.append((form_type, target.get('name') or '', key, grade))
    elif form_type == FormType.ATTACHMENT_6_2:
        name = payload.get('branch_name') or task.branch_name_snapshot
        for key, grade in (payload.get('scores') or {}).items():
            rows.append((form_type, name, key, grade))
    elif form_type == FormType.ATTACHMENT_1:
        for item in payload.get('overall') or []:
            rows.append((form_type, '班子总体', item.get('key'), item.get('grade')))
        for target in payload.get('targets') or []:
            for key, grade in (target.get('scores') or {}).items():
                rows.append((form_type, target.get('name') or '', key, grade))
    elif form_type == FormType.ATTACHMENT_2:
        for item in payload.get('dimensions') or []:
            rows.append((form_type, task.assignee_name_snapshot, item.get('key'), item.get('grade')))
    elif form_type == FormType.ATTACHMENT_4:
        for item in payload.get('items') or []:
            rows.append((form_type, payload.get('branch_name') or task.branch_name_snapshot, item.get('key'), item.get('grade')))
    return rows


def build_statistics(campaign):
    from .statistics import build_statistics as build_report
    return build_report(campaign)


def dispatch_options():
    from accounts.models import Role
    from orgs.models import OrgUnit

    units = OrgUnit.objects.filter(is_active=True).select_related('parent').order_by('unit_type', 'sort_order', 'name')
    return {
        'form_types': form_catalog(),
        'rules_text': RULES_TEXT,
        'filler_roles': [{'key': item.value, 'label': item.label} for item in FillerRole],
        'users': [
            {'id': str(user.id), 'real_name': user.real_name, 'username': user.username}
            for user in User.objects.filter(is_active=True).order_by('real_name', 'username')
        ],
        'roles': list(Role.objects.filter(is_active=True).values('code', 'name')),
        'branches': [
            {'id': str(unit.id), 'name': unit.name, 'label': f'{unit.name}（{unit.get_unit_type_display()}）'}
            for unit in units if unit.unit_type == 'BRANCH'
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
    }
