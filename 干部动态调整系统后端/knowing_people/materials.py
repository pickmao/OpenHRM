"""按考察批次归集已提交的研判材料，保留原表及对象身份。"""

from copy import deepcopy
import re
from uuid import UUID

from rest_framework.exceptions import ValidationError

from orgs.models import OrgUnit

from .form_defs import TALK_ISSUES, merge_payload
from .matching import roster_in_departments
from .models import FormType, TaskStatus
from .payload_validation import resolve_story_person


def _year(value):
    value = str(value or '')
    return value if re.fullmatch(r'[1-9]\d{3}', value) else ''


def _fields(task, payload):
    labels = {
        'leadership_current': '领导现有人数', 'leadership_vacancy': '领导空缺人数',
        'team_leader_current': '团队负责人现有人数', 'team_leader_vacancy': '团队负责人空缺人数',
        'performance': '现实表现（整表意见）', 'shortcomings': '存在不足（整表意见）',
        'other_issues': '其他情况（整表意见）', 'other': '需要反映的其他情况',
        'rectification': '整改措施', 'team_requests': '班子诉求',
        'adjustment_needed': '是否需要调整', 'adjustment_suggestion': '调整建议',
        'name': '姓名', 'unit': '单位', 'position_rank': '职务职级',
        'main_business_lines': '主要业务', 'rewards_last_3y': '近三年奖励',
        'punishments_last_3y': '近三年惩处', 'personal_requests': '个人诉求',
    }
    fields = [{'label': label, 'text': str(payload[key])} for key, label in labels.items()
              if payload.get(key) is not None and payload.get(key) != '']
    if task.form_type == FormType.ATTACHMENT_4:
        for key in ('leadership_current', 'leadership_vacancy', 'team_leader_current', 'team_leader_vacancy'):
            if payload.get(key) is None or payload.get(key) == '':
                fields.append({'label': labels[key], 'text': '未填'})
    for key, label in [('office', '长期在机关人数'), ('balanced', '相对均衡人数'), ('prison', '长期在监区人数')]:
        value = (payload.get('experience_counts') or {}).get(key)
        if value is not None or task.form_type == FormType.ATTACHMENT_4:
            fields.append({'label': label, 'text': str(value) if value is not None else '未填'})
    for row in (payload.get('dimensions') or []) + (payload.get('items') or []):
        if task.form_type == FormType.ATTACHMENT_3:
            label = row.get('key_work') or row.get('experience') or '个人述事'
            text = '\n'.join(filter(None, [row.get('experience'), '、'.join(row.get('roles') or []), row.get('details')]))
        else:
            label = row.get('label') or row.get('key') or '评价'
            text = '\n'.join(f'{label}：{row[key]}' for key, label in
                             [('grade', '评价'), ('performance', '现实表现'), ('shortcomings', '存在不足')]
                             if row.get(key))
        fields.append({'label': label, 'text': text})
    if task.form_type == FormType.ATTACHMENT_1:
        fields.extend({'label': row.get('label') or row['key'], 'text': row.get('grade') or '未填'}
                      for row in payload.get('overall') or [])
        issue_labels = {row['key']: row['label'] for row in TALK_ISSUES}
        fields.extend({'label': '反映问题', 'text': issue_labels.get(key, key)} for key in payload.get('issues') or [])
    return fields


def build_materials(campaign):
    tasks = list(campaign.tasks.select_related('branch').order_by('created_at', 'id'))
    branches, stories, reviews, sources = {}, [], [], []
    submitted_count = 0
    for task in tasks:
        context = task.context_json or {}
        branch = context.get('branch') or {}
        branch_id = str(task.branch_id or branch.get('id') or '')
        branch_name = branch.get('name') or task.branch_name_snapshot
        if branch_id:
            branches[branch_id] = {'id': branch_id, 'name': branch_name,
                                   'department_names': context.get('department_names') or []}
        if task.form_type == FormType.ATTACHMENT_6_1:
            for target in context.get('targets') or []:
                try:
                    identity = str(UUID(str(target.get('id'))))
                except (ValueError, TypeError):
                    continue
                branches.setdefault(identity, {'id': identity, 'name': target.get('name') or '', 'department_names': []})
        if task.status != TaskStatus.SUBMITTED:
            continue
        submitted_count += 1
        source = {
            'source_task_id': str(task.id), 'form_type': task.form_type,
            'form_label': task.get_form_type_display(), 'branch_id': branch_id,
            'branch_name': branch_name, 'submitted_at': task.submitted_at,
            'assignee_name': task.assignee_name_snapshot,
        }
        payload = merge_payload(task.form_type, task.payload_json or {}, context)
        if task.form_type == FormType.ATTACHMENT_5:
            # Read the stored year so a fallback to the batch year remains visible.
            for index, work in enumerate((task.payload_json or {}).get('works') or []):
                if not isinstance(work, dict):
                    continue
                people = []
                for person in work.get('people') or []:
                    if not isinstance(person, dict):
                        continue
                    try:
                        person = resolve_story_person(person, context.get('roster_people') or [])
                    except ValidationError:
                        person = {**deepcopy(person), 'roster_id': ''}
                    people.append(person)
                explicit_year = _year(work.get('year'))
                year = explicit_year or _year(context.get('campaign_year') or campaign.year)
                stories.append({**source, 'id': f'{task.id}:{index}', 'year': year,
                                'year_source': '填报年度' if explicit_year else '批次年度' if year else '待补充',
                                'title': work.get('title') or '', 'description': work.get('description') or '',
                                'people': people})
        elif task.form_type == FormType.INSPECTION_REVIEW:
            for index, record in enumerate(payload.get('records') or []):
                reviews.append({**record, **source, 'id': f'{task.id}:{index}',
                                'year': payload.get('material_year') or '',
                                'record_date': payload.get('record_date') or '',
                                'interviewers': payload.get('interviewers') or ''})
        else:
            fields = _fields(task, payload)
            if fields:
                sources.append({**source, 'fields': fields,
                                'scope_names': [row.get('name') or '' for row in context.get('targets') or []]})
    roster_people = []
    units = {str(unit.id): unit for unit in OrgUnit.objects.filter(id__in=list(branches))}
    for branch_id, branch in branches.items():
        unit = units.get(branch_id)
        departments = ([unit.name, *[child.name for child in unit.get_descendants()]] if unit
                       else branch['department_names'])
        for person in roster_in_departments(departments):
            roster_people.append({
                'id': str(person.id), 'branch_id': branch_id, 'branch_name': branch['name'],
                'name': person.name, 'department': person.department, 'position': person.position,
                'position_category': person.position_category, 'age': person.age,
                'birth_date': person.birth_date, 'highest_education': person.highest_education,
                'current_position_years': person.current_position_years,
                'current_position_date': person.current_position_date,
            })
    return {
        'campaign_id': str(campaign.id), 'campaign_name': campaign.name, 'year': campaign.year,
        'submitted_count': submitted_count, 'pending_count': len(tasks) - submitted_count,
        'branches': [{'id': row['id'], 'name': row['name']} for row in branches.values()],
        'stories': stories, 'reviews': reviews, 'sources': sources, 'roster_people': roster_people,
        'roster_source': '当前花名册（查询时）',
    }
