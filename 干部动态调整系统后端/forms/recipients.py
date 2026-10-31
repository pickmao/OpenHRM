"""将当前花名册人员对齐到可以接收在线填报任务的账号。"""
from collections import defaultdict

from accounts.models import User
from cadres.models import PersonnelRoster
from django.db.models import Q
from django.utils import timezone
from orgs.models import Membership


def roster_recipient_options():
    people = list(PersonnelRoster.objects.all())
    people_by_name = defaultdict(list)
    for person in people:
        people_by_name[person.name.strip()].append(person)
    accounts_by_name = defaultdict(list)
    for account in User.objects.filter(real_name__in={person.name for person in people}):
        accounts_by_name[account.real_name.strip()].append(account)

    today = timezone.localdate()
    primary_units = {}
    memberships = Membership.objects.filter(
        user__real_name__in=people_by_name, user__is_active=True, unit__is_active=True,
    ).filter(
        Q(effective_from__isnull=True) | Q(effective_from__lte=today),
        Q(effective_to__isnull=True) | Q(effective_to__gte=today),
    ).select_related('unit').order_by('-is_primary', 'unit__sort_order', 'id')
    for membership in memberships:
        primary_units.setdefault(membership.user_id, membership.unit)

    result = []
    for person in people:
        accounts = accounts_by_name[person.name.strip()]
        active = [account for account in accounts if account.is_active]
        matched = []
        for account in active:
            unit = primary_units.get(account.id)
            if len(active) > 1 or len(people_by_name[person.name.strip()]) > 1:
                if not unit or unit.name.strip() != person.department.strip():
                    continue
                same_department = [row for row in people_by_name[person.name.strip()]
                                   if row.department.strip() == unit.name.strip()]
                if len(same_department) != 1:
                    continue
            matched.append(account)
        account = matched[0] if len(matched) == 1 else None
        state = 'READY' if account else 'AMBIGUOUS' if active else 'DISABLED' if accounts else 'MISSING'
        result.append({
            'roster_id': str(person.id), 'name': person.name,
            'department': person.department, 'position': person.position,
            'user_id': str(account.id) if account else None,
            'username': account.username if account else '',
            'account_state': state,
        })
    return result
