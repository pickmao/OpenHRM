"""花名册是人员当前部门的唯一真相源。

其他模块查询“这个人现在在哪个部门”时走这里，不要各自维护一份部门字段。
发生时快照（下发、推荐提交、研判 Excel）仍保留在原表，不在这里改写。
"""
from django.contrib.auth import get_user_model
from django.utils import timezone

from orgs.models import Membership, OrgUnit, UnitType

from .models import PersonnelRoster


User = get_user_model()


def normalize_text(value):
    return (value or '').strip()


def find_unique_roster_for_user(user):
    """用账号真实姓名对齐花名册；重名且部门不一致时不猜测。"""
    name = normalize_text(getattr(user, 'real_name', ''))
    if not name:
        return None
    people = list(PersonnelRoster.objects.filter(name=name))
    if not people:
        return None
    if len(people) == 1:
        return people[0]
    unit = membership_primary_unit(user)
    if not unit:
        return None
    matched = [person for person in people if normalize_text(person.department) == normalize_text(unit.name)]
    if len(matched) == 1:
        return matched[0]
    return None


def find_unique_users_for_roster(person):
    name = normalize_text(person.name)
    if not name:
        return []
    users = list(User.objects.filter(real_name=name, is_active=True))
    if len(users) <= 1:
        return users
    return []


def find_org_unit_by_name(name):
    name = normalize_text(name)
    if not name:
        return None
    units = list(OrgUnit.objects.filter(name=name, is_active=True).order_by('sort_order', 'id'))
    if not units:
        return None
    departments = [unit for unit in units if unit.unit_type == UnitType.DEPARTMENT]
    pool = departments or units
    if len(pool) == 1:
        return pool[0]
    return None


def membership_primary_unit(user):
    today = timezone.localdate()
    from django.db.models import Q
    membership = Membership.objects.filter(
        user=user, unit__is_active=True,
    ).filter(
        Q(effective_from__isnull=True) | Q(effective_from__lte=today),
        Q(effective_to__isnull=True) | Q(effective_to__gte=today),
    ).order_by('-is_primary', 'unit__sort_order', 'id').select_related('unit').first()
    return membership.unit if membership else None


def current_department_name_for_user(user):
    person = find_unique_roster_for_user(user)
    if person and normalize_text(person.department):
        return person.department
    unit = membership_primary_unit(user)
    return unit.name if unit else ''


def current_org_unit_for_user(user):
    person = find_unique_roster_for_user(user)
    if person:
        unit = find_org_unit_by_name(person.department)
        if unit:
            return unit
    return membership_primary_unit(user)


def _unique_roster_by_name(names):
    result = {}
    ambiguous = set()
    for person in PersonnelRoster.objects.filter(name__in=names):
        key = person.name
        existing = result.get(key)
        if existing and existing.department != person.department:
            ambiguous.add(key)
            continue
        if existing is None:
            result[key] = person
    for key in ambiguous:
        result.pop(key, None)
    return result


def _primary_membership_units(user_ids):
    units = {}
    memberships = Membership.objects.filter(
        user_id__in=user_ids, unit__is_active=True, effective_to__isnull=True,
    ).select_related('unit').order_by('-is_primary', 'unit__sort_order', 'id')
    for membership in memberships:
        units.setdefault(membership.user_id, membership.unit)
    return units


def current_department_names_for_user_ids(user_ids):
    user_ids = [user_id for user_id in user_ids if user_id]
    if not user_ids:
        return {}
    users = User.objects.in_bulk(user_ids)
    names = {normalize_text(user.real_name) for user in users.values() if normalize_text(user.real_name)}
    people = _unique_roster_by_name(names)
    memberships = _primary_membership_units(user_ids)
    result = {}
    for user_id, user in users.items():
        person = people.get(normalize_text(user.real_name))
        if person and normalize_text(person.department):
            result[user_id] = person.department
        elif user_id in memberships:
            result[user_id] = memberships[user_id].name
        else:
            result[user_id] = ''
    return result


def current_org_units_for_user_ids(user_ids):
    names = current_department_names_for_user_ids(user_ids)
    unit_by_name = {}
    for dept_name in {item for item in names.values() if item}:
        unit = find_org_unit_by_name(dept_name)
        if unit:
            unit_by_name[dept_name] = unit
    memberships = _primary_membership_units(user_ids)
    result = {}
    for user_id, dept_name in names.items():
        unit = unit_by_name.get(dept_name)
        if unit:
            result[user_id] = unit
        elif user_id in memberships:
            result[user_id] = memberships[user_id]
    return result


def roster_department_by_names(names):
    """同名且当前部门唯一时，返回 姓名 → 花名册部门。"""
    cleaned = [normalize_text(name) for name in names if normalize_text(name)]
    if not cleaned:
        return {}
    grouped = {}
    for name, department in PersonnelRoster.objects.filter(name__in=cleaned).values_list('name', 'department'):
        grouped.setdefault(name, set()).add(department)
    return {name: next(iter(departments)) for name, departments in grouped.items() if len(departments) == 1}


def sync_memberships_from_roster(person, *, actor=None, effective_date=None):
    """花名册部门变化后，把同名账号的主部门调到同名组织单元。找不到组织节点则只改花名册。"""
    unit = find_org_unit_by_name(person.department)
    if not unit:
        return []
    moved = []
    for user in find_unique_users_for_roster(person):
        if _move_user_to_unit(user, unit, actor=actor, effective_date=effective_date):
            moved.append(user)
    return moved


def sync_memberships_from_rosters(people, *, actor=None):
    for person in people:
        sync_memberships_from_roster(person, actor=actor)


def sync_roster_department_for_user(user, department_name, *, actor=None):
    """部门调配生效时回写花名册，保持花名册仍是当前归属。"""
    person = find_unique_roster_for_user(user)
    department_name = normalize_text(department_name)
    if not person or not department_name or person.department == department_name:
        return person
    person.department = department_name
    person.save(update_fields=['department', 'updated_at'])
    return person


def _move_user_to_unit(user, unit, *, actor=None, effective_date=None):
    effective_date = effective_date or timezone.localdate()
    current = Membership.objects.filter(
        user=user, is_primary=True, effective_to__isnull=True,
    ).select_related('unit')
    if current.filter(unit_id=unit.id).exists():
        return False
    current.update(effective_to=effective_date)
    existing = Membership.objects.filter(user=user, unit=unit, effective_to__isnull=True).first()
    if existing:
        if not existing.is_primary:
            existing.is_primary = True
            existing.save(update_fields=['is_primary', 'updated_at'])
        return True
    Membership.objects.create(
        user=user,
        unit=unit,
        is_primary=True,
        effective_from=effective_date,
        created_by=actor,
    )
    return True
