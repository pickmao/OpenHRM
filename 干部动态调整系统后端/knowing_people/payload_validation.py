"""Validate the saved task contract before accepting user-controlled form JSON."""
from copy import deepcopy

from rest_framework.exceptions import ValidationError

from .form_defs import default_payload, validate_payload


def validate_task_payload(task, payload, *, strict=False):
    if not isinstance(payload, dict):
        raise ValidationError('填报内容必须是对象。')
    cleaned = deepcopy(payload)
    defaults = default_payload(task.form_type, task.context_json or {})
    for key in ('targets', 'dimensions', 'items', 'overall', 'works'):
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
        return validate_payload(task.form_type, cleaned, strict=strict)
    except (AttributeError, TypeError, KeyError):
        raise ValidationError('填报字段格式错误，请重新打开表单后填写。')
