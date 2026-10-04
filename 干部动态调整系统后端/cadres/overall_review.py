"""Identity-safe evidence snapshot for a human-reviewed employee evaluation."""

import hashlib
import json
import re
from collections import defaultdict

from django.contrib.auth import get_user_model
from django.db.models import Q

from accounts.models import ScopeType
from anonymous_evaluations.models import CampaignStatus as AnonymousStatus, EvaluationTarget
from anonymous_evaluations.services import build_results
from assessments.models import AssessmentRecord
from cadre_recommendations.models import CampaignStatus as RecommendationStatus, RecommendationNomination
from forms.models import FormSubmission, FormTask, FormTaskStatus, ReceiverType
from inspections.models import WorkRecord
from knowing_people.models import FormType, InspectionTask, TaskStatus
from rewards_punishments.models import RewardRecord, RewardRecipientType

from .models import Cadre, PersonnelRoster
from .org_alignment import find_unique_roster_for_user, membership_primary_unit


User = get_user_model()
PERSON_FORMS = {FormType.ATTACHMENT_1, FormType.ATTACHMENT_7_1,
                FormType.ATTACHMENT_7_2, FormType.ATTACHMENT_7_3, FormType.ATTACHMENT_7_4}
SELF_FORMS = {FormType.ATTACHMENT_2, FormType.ATTACHMENT_3}


def allowed_rosters(user):
    queryset = PersonnelRoster.objects.all()
    if user.is_superuser:
        return queryset
    try:
        scope = user.data_scope
    except Exception:
        return queryset.none()
    if scope.scope_type == ScopeType.ALL:
        return queryset
    if scope.scope_type == ScopeType.ORG_UNIT:
        names = list(scope.org_units.values_list('name', flat=True))
        return queryset.filter(department__in=names)
    return queryset.none()


def search_people(user, name):
    name = name.strip()
    if not name or len(name) > 50:
        return []
    results = []
    for person in allowed_rosters(user).filter(name__icontains=name).order_by('name', 'department', 'id')[:30]:
        cadre = _cadre_for(person, _users_for(person))
        results.append({'id': str(person.id), 'name': person.name,
                        'department': person.department, 'position': person.position,
                        'cadre_code': cadre.cadre_code if cadre else ''})
    return results


def _users_for(person):
    users = list(User.objects.filter(real_name=person.name, is_active=True).select_related('profile_cadre'))
    matched = [user for user in users if (unit := membership_primary_unit(user))
               and unit.name == person.department and find_unique_roster_for_user(user) == person]
    return matched if len(matched) == 1 else []


def _cadre_for(person, users):
    linked = [user.profile_cadre for user in users if user.profile_cadre_id]
    if len(linked) == 1 and linked[0].name == person.name:
        return linked[0]
    # Name alone is never enough to attach a cadre file.
    return None


def _clean(value, limit=None):
    if value is None or value == '':
        return None
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, default=str)
    cleaned = str(value).strip()
    return cleaned[:limit] if limit else cleaned


def _compact(source, fields):
    return {label: cleaned for label, attr in fields.items()
            if (cleaned := _clean(getattr(source, attr, None))) is not None}


PRIVATE_KEYS = {'id_card', 'phone', 'birth_date', 'residence', 'address',
                'marital_status', 'health', 'political_status', 'gender',
                'ethnicity', 'native_place', 'household_registration',
                '身份证号', '电话', '出生日期', '住址', '婚姻状况', '健康状况', '政治面貌', '性别', '民族', '籍贯'}
PRIVATE_KEY_FRAGMENTS = ('身份证', '手机号', '联系电话', '出生年月', '家庭住址', '户籍地址')


def _safe_payload(value):
    if isinstance(value, dict):
        return {key: _safe_payload(item) for key, item in value.items()
                if str(key).lower() not in PRIVATE_KEYS and
                not any(fragment in str(key) for fragment in PRIVATE_KEY_FRAGMENTS)}
    if isinstance(value, list):
        return [_safe_payload(item) for item in value]
    return _clean(value)


def _year(task):
    raw = str(task.campaign.year or '')
    match = re.search(r'\d{4}', raw)
    if match:
        return match.group()
    date = task.campaign.period_end or task.campaign.period_start
    return str(date.year) if date else str((task.submitted_at or task.created_at).year)


def build_snapshot(user, roster_id):
    person = allowed_rosters(user).filter(pk=roster_id).first()
    if person is None:
        return None
    users = _users_for(person)
    cadre = _cadre_for(person, users)
    warnings = []
    if not users:
        warnings.append('账号未能通过姓名和部门唯一关联，账号填报与纪实未纳入。')
    if not cadre:
        warnings.append('干部主档未通过账号外键关联，履历未纳入。')

    sections = {}
    sections['basic'] = [{
        'source': f'roster:{person.pk}',
        **_compact(person, {'姓名': 'name', '部门': 'department', '职务': 'position',
                            '职务类别': 'position_category', '职级': 'position_rank',
                            '分管工作': 'work_charge', '年度考核': 'annual_assessments'}),
    }]
    sections['resumes'] = []
    if cadre:
        for row in cadre.resumes.select_related('org_unit').order_by('-start_date', 'id'):
            sections['resumes'].append({
                'source': f'cadre_resume:{row.pk}', '单位': row.org_unit.name if row.org_unit else '',
                '职务': row.position_title, '开始': str(row.start_date),
                '结束': str(row.end_date) if row.end_date else '至今',
            })

    # Imported assessments have no employee FK. Match exact historical department;
    # a name collision in the same department remains unresolved and is excluded.
    same_name = PersonnelRoster.objects.filter(name=person.name)
    dept_unique = same_name.filter(department=person.department).count() == 1
    assessment_rows = []
    if dept_unique:
        assessments = AssessmentRecord.objects.filter(
            name=person.name, department=person.department
        ).select_related('file').order_by('-file__version_date', '-updated_at', 'id')
        seen = set()
        for row in assessments:
            key = (row.file.version_date.year, row.position_category, row.position)
            if key in seen:
                continue
            seen.add(key)
            assessment_rows.append({
                'source': f'assessment:{row.pk}', '年度': key[0],
                '版本日期': str(row.file.version_date), '职务': row.position,
                **_compact(row, {'主要工作': 'main_business', '近三年考核': 'annual_assessment_3years',
                                 '工作成效': 'main_performance', '能力研判': 'ability_assessment',
                                 '短板': 'shortcomings', '综合研判': 'comprehensive_assessment',
                                 '综合得分': 'comprehensive_score'}),
            })
    else:
        warnings.append('同部门存在同名人员，未纳入仅按姓名和部门标识的研判记录。')
    sections['assessments'] = assessment_rows

    user_ids = [user.pk for user in users]
    own_tasks = InspectionTask.objects.filter(
        status=TaskStatus.SUBMITTED, form_type__in=SELF_FORMS,
    ).filter(Q(roster=person) | Q(roster__isnull=True, assignee_id__in=user_ids)).select_related('campaign').order_by('-submitted_at', '-created_at', 'id')
    seen = set()
    self_forms = []
    for task in own_tasks:
        payload = task.payload_json or {}
        position = (payload.get('position_rank') or payload.get('department_position') or
                    (task.context_json or {}).get('roster', {}).get('position_label') or person.position)
        key = (_year(task), task.form_type, position)
        if key in seen:
            continue
        seen.add(key)
        if task.form_type == FormType.ATTACHMENT_2:
            evidence = {key: payload.get(key) for key in ('dimensions', 'rectification', 'main_business_lines', 'rewards_last_3y', 'punishments_last_3y') if payload.get(key)}
        else:
            evidence = {'items': payload.get('items') or []}
        self_forms.append({'source': f'knowing_task:{task.pk}', '年度': _year(task), '当时职务': position,
                           '表单': task.get_form_type_display(), '提交时间': str(task.submitted_at),
                           '内容': _safe_payload(evidence)})
    sections['self_forms'] = self_forms

    # Each rater is a legitimate observation. Aggregate by year/form/position,
    # while replacing a rater's duplicate submission with its newest version.
    rating_groups = defaultdict(lambda: {'count': 0, 'scores': defaultdict(lambda: defaultdict(int)), 'sources': []})
    rating_tasks = InspectionTask.objects.filter(status=TaskStatus.SUBMITTED, form_type__in=PERSON_FORMS).select_related('campaign').order_by('-submitted_at', '-created_at', 'id')
    latest_rater = set()
    for task in rating_tasks:
        for target in (task.payload_json or {}).get('targets') or []:
            if str(target.get('id')) != str(person.pk):
                continue
            position = target.get('position') or person.position
            key = (_year(task), task.form_type, position)
            rater_key = (*key, task.assignee_id)
            if rater_key in latest_rater:
                continue
            latest_rater.add(rater_key)
            group = rating_groups[key]
            group['count'] += 1
            group['sources'].append(f'knowing_task:{task.pk}')
            for dimension, value in (target.get('scores') or {}).items():
                grade = value.get('grade') if isinstance(value, dict) else value
                if grade:
                    group['scores'][dimension][str(grade)] += 1
    sections['ratings'] = [
        {'年度': year, '表单': form_type, '职务': position, '评价人数': group['count'],
         '维度分布': {k: dict(v) for k, v in group['scores'].items()}, 'sources': group['sources']}
        for (year, form_type, position), group in sorted(rating_groups.items(), reverse=True)
    ]

    anonymous_rows = []
    targets = EvaluationTarget.objects.filter(
        user_id__in=user_ids, campaign__status=AnonymousStatus.CLOSED,
    ).select_related('campaign').order_by('-campaign__closed_at', '-created_at', 'id')
    for target in targets:
        result = next((row for row in build_results(target.campaign)
                       if row['target_id'] == str(target.pk)), None)
        if result and result['available']:
            anonymous_rows.append({
                'source': f'anonymous_target:{target.pk}', '活动': target.campaign.name,
                '关闭时间': str(target.campaign.closed_at or ''),
                '有效样本数': result['valid_response_count'], '综合均分': result['overall_score'],
                '维度': result['dimensions'],
            })
        elif result:
            warnings.append(f'匿名测评活动“{target.campaign.name}”样本不足，结果未纳入。')
    sections['anonymous_evaluations'] = anonymous_rows

    nomination_groups = defaultdict(lambda: {'count': 0, 'sources': []})
    nominations = RecommendationNomination.objects.filter(
        roster=person, task__status='SUBMITTED', task__campaign__status=RecommendationStatus.CLOSED,
    ).select_related('task__campaign').order_by('-task__campaign__closed_at', 'id')
    for nomination in nominations:
        key = (str(nomination.task.campaign.pk), nomination.task.campaign.name,
               nomination.post_category, nomination.position_snapshot)
        nomination_groups[key]['count'] += 1
        nomination_groups[key]['sources'].append(f'recommendation_nomination:{nomination.pk}')
    sections['recommendations'] = [
        {'活动': name, '岗位类别': category, '当时职位': position,
         '推荐次数': value['count'], 'sources': value['sources']}
        for (_, name, category, position), value in nomination_groups.items()
    ]

    sections['work'] = [
        {'source': f'work_record:{row.pk}', '日期': str(row.completed_on),
         **_compact(row, {'任务': 'title', '职责': 'role', '过程': 'details', '成效': 'outcome'})}
        for row in WorkRecord.objects.filter(owner_id__in=user_ids).order_by('-completed_on', '-created_at', 'id')
    ]
    # General form payloads are included only when the target is the employee or
    # the employee filled a self-targeted form; document-only submissions have no
    # machine-readable contents and are disclosed as metadata.
    form_rows = []
    tasks = FormTask.objects.filter(status=FormTaskStatus.SUBMITTED).filter(
        Q(target_type='USER', target_id__in=user_ids) |
        Q(assignee_type=ReceiverType.USER, assignee_id__in=user_ids, target_id__isnull=True)
    ).select_related('template', 'batch').order_by('-submitted_at', '-created_at', 'id')
    form_seen = set()
    for task in tasks:
        year_match = re.search(r'\d{4}', task.batch.cycle_id or '')
        year = year_match.group() if year_match else str((task.submitted_at or task.created_at).year)
        key = (year, task.template.code, task.assignee_role_snapshot, str(task.target_id or task.assignee_id))
        if key in form_seen:
            continue
        form_seen.add(key)
        submission = FormSubmission.objects.filter(task=task, is_final=True).order_by('-version').first()
        form_rows.append({'source': f'form_task:{task.pk}', '年度': year, '模板': task.template.name,
                          '填报身份': task.assignee_role_snapshot,
                          '内容': _safe_payload(submission.payload_json) if submission else {},
                          '说明': '' if submission and submission.payload_json else '仅有文档或任务元数据，未提取正文'})
    sections['other_forms'] = form_rows

    # Reward imports also lack a person FK, so use them only when this name is
    # unique in the complete roster, never merely within the viewer's scope.
    if same_name.count() == 1:
        sections['rewards'] = [
            {'source': f'reward:{row.pk}', '年度': row.approval_year,
             '日期': str(row.approval_date) if row.approval_date else '',
             '级别': row.award_level, '内容': _clean(row.award_content)}
            for row in RewardRecord.objects.filter(
                recipient_type=RewardRecipientType.INDIVIDUAL, recipient_name=person.name
            ).order_by('-approval_year', '-approval_date', 'id')
        ]
    else:
        sections['rewards'] = []
        warnings.append('存在同名人员，未纳入无人员外键的个人奖励记录。')

    snapshot = {'person': {'id': str(person.pk), 'name': person.name,
                           'department': person.department, 'position': person.position},
                'sections': sections, 'warnings': warnings}
    canonical = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, default=str)
    snapshot['digest'] = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    return snapshot
