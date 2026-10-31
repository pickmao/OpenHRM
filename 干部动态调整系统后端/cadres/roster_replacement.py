"""Replace the current roster without deleting historical personnel references."""
from collections import defaultdict

from django.core.exceptions import ValidationError
from django.db import connection
from django.utils import timezone

from .models import PersonnelRoster


class RosterReplacementError(ValueError):
    pass


def replace_current_roster(incoming, *, actor):
    """Called inside transaction.atomic; retain stable IDs and archive missing rows."""
    if connection.vendor == 'postgresql':
        # Serialize roster writes while allowing readers during the replacement.
        table = connection.ops.quote_name(PersonnelRoster._meta.db_table)
        with connection.cursor() as cursor:
            cursor.execute(f'LOCK TABLE {table} IN SHARE ROW EXCLUSIVE MODE')

    existing = list(PersonnelRoster.all_objects.select_for_update().all())
    by_card = {person.id_card: person for person in existing if person.id_card}
    by_police = {person.police_number: person for person in existing if person.police_number}
    by_name_department = defaultdict(list)
    for person in existing:
        if not person.id_card and not person.police_number:
            by_name_department[(person.name, person.department)].append(person)

    matched_ids = set()
    writes = []
    updated_count = 0
    current_ids = {person.pk for person in existing if person.is_active}
    fields = [field.name for field in PersonnelRoster._meta.concrete_fields
              if field.name not in {'id', 'created_at', 'created_by', 'updated_at', 'is_active'}]
    for row_number, person in enumerate(incoming, 2):
        card_match = by_card.get(person.id_card) if person.id_card else None
        police_match = by_police.get(person.police_number) if person.police_number else None
        if card_match and police_match and card_match.pk != police_match.pk:
            raise RosterReplacementError(f'第 {row_number} 行的身份证号与警号对应不同人员，已保留原有花名册。')
        match = card_match or police_match
        if match and person.id_card and match.id_card and person.id_card != match.id_card:
            raise RosterReplacementError(f'第 {row_number} 行的警号与已有身份证号不一致，请核对人员身份。')
        if not match and not person.id_card and not person.police_number:
            candidates = by_name_department.get((person.name, person.department), [])
            if len(candidates) > 1:
                raise RosterReplacementError(f'第 {row_number} 行存在同名同部门人员，请补充警号或身份证号后导入。')
            match = candidates[0] if candidates else None
        if match:
            if match.pk in matched_ids:
                raise RosterReplacementError(f'第 {row_number} 行与文件内其他行对应同一人员，已取消覆盖。')
            matched_ids.add(match.pk)
            previous_card, previous_police = match.id_card, match.police_number
            for field in fields:
                setattr(match, field, getattr(person, field))
            # Missing identifiers in a new sheet must not erase stable identity.
            match.id_card = person.id_card or previous_card
            match.police_number = person.police_number or previous_police
            match.is_active = True
            writes.append(match)
            updated_count += 1
        else:
            person.created_by = actor
            writes.append(person)

    # No protected FK is removed: historical recommendation/assessment rows retain IDs.
    archived_count = len(current_ids - matched_ids)
    PersonnelRoster.objects.exclude(pk__in=matched_ids).update(is_active=False)
    for person in writes:
        try:
            person.full_clean(exclude=['created_by'])
        except ValidationError as exc:
            raise RosterReplacementError('人员信息校验失败，已取消覆盖：' + '; '.join(exc.messages)) from exc
    updates = [person for person in writes if not person._state.adding]
    creates = [person for person in writes if person._state.adding]
    for person in updates:
        person.updated_at = timezone.now()
    if updates:
        PersonnelRoster.all_objects.bulk_update(updates, fields + ['is_active', 'updated_at'], batch_size=100)
    if creates:
        PersonnelRoster.objects.bulk_create(creates, batch_size=100)

    return {
        'created_count': len(writes) - updated_count,
        'updated_count': updated_count,
        'deleted_count': archived_count,
        'archived_count': archived_count,
    }


