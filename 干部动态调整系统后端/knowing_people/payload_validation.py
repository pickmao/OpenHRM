"""Validate the saved task contract before accepting user-controlled form JSON."""
from copy import deepcopy

from rest_framework.exceptions import ValidationError

from .form_defs import default_payload, validate_payload
from .models import FormType


def resolve_story_person(person, candidates):
    """保留手填人员，仅在花名册身份唯一时关联具体干部。"""
    cleaned = deepcopy(person)
    roster_id = str(person.get('roster_id') or '')
    matches = [row for row in candidates if
               (str(row['id']) == roster_id if roster_id else row['name'] == person.get('name'))]
    if roster_id and not matches:
        raise ValidationError('述事人员不在本次下发的支部花名册中，请重新选择。')
    if len(matches) == 1:
        cleaned.update(roster_id=str(matches[0]['id']), name=matches[0]['name'],
                       department=matches[0].get('department') or '')
    else:
        cleaned['roster_id'] = ''
    return cleaned


def validate_task_payload(task, payload, *, strict=False):
    if not isinstance(payload, dict):
        raise ValidationError('填报内容必须是对象。')
    cleaned = deepcopy(payload)
    defaults = default_payload(task.form_type, task.context_json or {})
    for key in ('targets', 'dimensions', 'items', 'overall', 'works', 'records'):
        if key not in cleaned:
            continue
        rows = cleaned[key]
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValidationError(f'{key} 必须为明细列表。')
        if key in ('dimensions', 'overall') or (key == 'items' and task.form_type == 'ATTACHMENT_4'):
            expected = {row['key'] for row in defaults[key]}
            keys = [row.get('key') for row in rows]
            if any(not isinstance(value, str) or value not in expected for value in keys) or len(set(keys)) != len(keys):
                raise ValidationError('评价维度重复或不属于当前表单。')
    for row in cleaned.get('targets', []):
        if not isinstance(row.get('scores', {}), dict):
            raise ValidationError('评价档位必须是按维度填写的对象。')
    if 'scores' in cleaned and not isinstance(cleaned['scores'], dict):
        raise ValidationError('评价档位格式错误。')
    if 'targets' in defaults:
        expected = {str(row['id']): row for row in defaults['targets']}
        rows = cleaned.get('targets', [])
        ids = [str(row.get('id', '')) for row in rows]
        if len(set(ids)) != len(ids) or any(value not in expected for value in ids):
            raise ValidationError('评价对象重复或不在本次下发名单中，请重新打开表单。')
        if strict and set(ids) != set(expected):
            raise ValidationError('请完成本次下发的全部评价对象，不可删除被评人员。')
        for row in rows:
            canonical = expected[str(row['id'])]
            for key in ('name', 'department', 'position'):
                if key in canonical:
                    row[key] = canonical[key]
    branch = (task.context_json or {}).get('branch') or {}
    if branch.get('id') and 'branch_name' in defaults:
        cleaned['branch_name'] = branch['name']
    try:
        candidates = (task.context_json or {}).get('roster_people') or []
        if task.form_type == FormType.ATTACHMENT_5:
            for work in cleaned.get('works') or []:
                work.setdefault('year', (task.context_json or {}).get('campaign_year') or '')
                people = work.get('people') or []
                if not isinstance(people, list) or any(not isinstance(row, dict) for row in people):
                    raise ValidationError('具体人员必须为人员明细列表。')
                work['people'] = [resolve_story_person(person, candidates) for person in people]
        if task.form_type == FormType.INSPECTION_REVIEW:
            people_by_id = {str(person['id']): person for person in candidates}
            for record in cleaned.get('records') or []:
                identity = str(record.get('roster_id') or '')
                if identity:
                    if identity not in people_by_id:
                        raise ValidationError('谈话或研判对象不在本次下发的支部花名册中。')
                    person = people_by_id[identity]
                    record.update(roster_id=identity, name=person['name'], department=person.get('department') or '')
                else:
                    record.update(roster_id='', name=branch.get('name') or task.branch_name_snapshot,
                                  department=branch.get('name') or task.branch_name_snapshot)
        return validate_payload(task.form_type, cleaned, strict=strict)
    except (AttributeError, TypeError, KeyError):
        raise ValidationError('填报字段格式错误，请重新打开表单后填写。')
