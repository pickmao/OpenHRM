from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from .models import AssessmentChangeLog


def _json_value(value):
    if isinstance(value, (date, datetime, UUID, Decimal)):
        return str(value)
    return value


def record_change(*, instance, validated_data, user, resource_type):
    """保存记录前后仅发生变化字段的快照，供审计和追溯使用。"""
    field_names = list(validated_data.keys())
    before_values = {field: _json_value(getattr(instance, field)) for field in field_names}
    for field, value in validated_data.items():
        setattr(instance, field, value)
    instance.save()
    after_values = {field: _json_value(getattr(instance, field)) for field in field_names}
    changed_fields = [field for field in field_names if before_values[field] != after_values[field]]
    if changed_fields:
        AssessmentChangeLog.objects.create(
            resource_type=resource_type,
            resource_id=instance.id,
            version_date=instance.file.version_date,
            record_name=instance.name,
            changed_fields=changed_fields,
            before_values={field: before_values[field] for field in changed_fields},
            after_values={field: after_values[field] for field in changed_fields},
            editor=user if getattr(user, 'is_authenticated', False) else None,
        )
    return instance
