"""按附件8和花名册/组织树匹配填报人、被评对象。"""

from django.db.models import Q
from django.utils import timezone

from accounts.models import User
from cadres.models import PersonnelRoster
from cadres.org_alignment import current_org_unit_for_user, find_unique_roster_for_user, membership_primary_unit
from orgs.models import Membership, OrgUnit, UnitType

from .form_defs import FORM_META_MAP
from .models import FillerRole, FormType


MIDDLE_POSITION_CATEGORIES = ['领导职务', '内定领导职务', '监区工作团队正职', '监区工作团队副职']
SECRETARY_KEYWORDS = ['书记']
COMMITTEE_KEYWORDS = ['支委', '组织委员', '宣传委员', '纪检委员', '青年委员', '统战委员']


def _active_memberships(user=None):
    today = timezone.localdate()
    queryset = Membership.objects.filter(unit__is_active=True, user__is_active=True).filter(
        Q(effective_from__isnull=True) | Q(effective_from__lte=today),
        Q(effective_to__isnull=True) | Q(effective_to__gte=today),
    )
    if user is not None:
        queryset = queryset.filter(user=user)
    return queryset.select_related('unit', 'unit__parent', 'user')


def primary_unit(user):
    return current_org_unit_for_user(user) if user and user.is_active else None


def find_branch(unit):
    current = unit
    while current:
        if current.unit_type == UnitType.BRANCH:
            return current
        current = current.parent
    return None


def collect_scope(user):
    unit = primary_unit(user)
    if not unit:
        return {
            'unit': None, 'branch': None, 'branch_name': '', 'org_unit_name': '',
            'department_names': [], 'scope_label': '未关联组织',
        }
    branch = find_branch(unit)
    if unit.unit_type == UnitType.BRANCH:
        branch = unit
    names = []
    if branch:
        names.append(branch.name)
        for child in branch.get_descendants():
            names.append(child.name)
        scope_label = branch.name
    else:
        names.append(unit.name)
        for child in unit.get_descendants():
            names.append(child.name)
        scope_label = unit.name
        branch = None
    unique = []
    seen = set()
    for name in names:
        text = (name or '').strip()
        if text and text not in seen:
            seen.add(text)
            unique.append(text)
    return {
        'unit': unit,
        'branch': branch,
        'branch_name': branch.name if branch else '',
        'org_unit_name': unit.name,
        'department_names': unique,
        'scope_label': scope_label,
    }


def position_blob(person):
    return ''.join([
        person.position or '',
        person.position_category or '',
        person.position_rank or '',
        person.position_level or '',
        person.police_rank or '',
        person.police_title or '',
    ])


def is_middle_leader(person):
    if (person.department or '') == '监狱领导':
        return False
    if (person.position_rank or '').startswith('县处级'):
        return False
    position = person.position or ''
    return (
        person.position_category in MIDDLE_POSITION_CATEGORIES
        or '团队' in position
        or '分监区长' in position
    )


def is_team_lead(person):
    blob = position_blob(person)
    position = person.position or ''
    category = person.position_category or ''
    return category in {'监区工作团队正职', '监区工作团队副职'} or '团队' in blob or '分监区长' in position


def is_deputy(person):
    category = person.position_category or ''
    if '副职' in category:
        return True
    if '正职' in category:
        return False
    rank = person.position_rank or person.position_level or ''
    if '正科' in rank:
        return False
    if '副科' in rank:
        return True
    position = person.position or ''
    return '副监区' in position or position.startswith('副')


def is_chief(person):
    if not is_middle_leader(person) or is_team_lead(person) or is_deputy(person):
        return False
    blob = position_blob(person)
    return '正科' in blob or is_middle_leader(person)


def middle_roster():
    return PersonnelRoster.objects.filter(
        Q(position_category__in=MIDDLE_POSITION_CATEGORIES)
        | Q(position__contains='团队')
        | Q(position__contains='分监区长')
    ).exclude(department='监狱领导').exclude(position_rank__startswith='县处级').order_by('department', 'serial_number', 'name')


def format_position(person):
    parts = [person.position, person.position_rank or person.position_level or person.police_rank]
    return ' / '.join(part for part in parts if part)


def gender_label(person):
    mapping = {'M': '男', 'F': '女', 'U': '未知'}
    return mapping.get(person.gender, person.gender or '')


def roster_snapshot(person):
    if not person:
        return {}
    return {
        'id': str(person.id),
        'name': person.name,
        'department': person.department,
        'gender': gender_label(person),
        'birth_date': person.birth_date.isoformat()[:7] if person.birth_date else '',
        'position': person.position or '',
        'position_rank': person.position_rank or person.position_level or '',
        'position_label': format_position(person),
        'department_position': ' / '.join(part for part in [person.department, person.position] if part),
        'political_status': person.political_status or '',
        'current_position_years': person.current_position_years or '',
        'current_position_date': person.current_position_date.isoformat()[:7] if person.current_position_date else '',
        'work_charge': person.work_charge or '',
        'residence': person.household_registration or person.native_place or '',
        'prison_work_years': person.unit_work_years or '',
        'phone': person.phone or '',
        'source': '花名册',
    }


def serialize_target_person(person):
    snapshot = roster_snapshot(person)
    return {
        'id': snapshot['id'],
        'name': snapshot['name'],
        'department': snapshot['department'],
        'position': snapshot['position'],
        'position_label': snapshot['position_label'],
        'position_category': person.position_category or '',
        'position_rank': person.position_rank or '',
        'police_rank': person.police_rank or '',
        'target_group': ('team' if is_team_lead(person) else 'chief' if is_chief(person)
                         else 'deputy' if is_middle_leader(person) and is_deputy(person) else 'police'),
        'source': '花名册',
    }


def serialize_target_branch(unit):
    return {'id': str(unit.id), 'name': unit.name, 'department': unit.name, 'source': '组织树'}


def list_branches(branch_ids=None):
    queryset = OrgUnit.objects.filter(is_active=True, unit_type=UnitType.BRANCH).order_by('sort_order', 'name')
    if branch_ids:
        queryset = queryset.filter(id__in=branch_ids)
    return list(queryset)


def branch_unit_ids(branch):
    ids = {branch.id}
    for child in branch.get_descendants():
        ids.add(child.id)
    return ids


def branch_memberships(branch):
    return list(
        _active_memberships().filter(unit_id__in=branch_unit_ids(branch)).select_related('user', 'unit')
    )


def _position_text(membership):
    return membership.position or ''


def classify_membership_role(membership):
    text = _position_text(membership)
    if '副书记' in text:
        return FillerRole.BRANCH_DEPUTY_SECRETARY
    if any(keyword in text for keyword in SECRETARY_KEYWORDS):
        return FillerRole.BRANCH_SECRETARY
    if any(keyword in text for keyword in COMMITTEE_KEYWORDS):
        return FillerRole.BRANCH_COMMITTEE
    if '委员' in text and '书记' not in text:
        return FillerRole.BRANCH_COMMITTEE
    return FillerRole.BRANCH_STAFF


def pick_secretary(memberships):
    secretaries = [item for item in memberships if classify_membership_role(item) == FillerRole.BRANCH_SECRETARY]
    if len({item.user_id for item in secretaries}) == 1:
        secretaries.sort(key=lambda item: (not item.is_manager, not item.is_primary, item.id.hex))
        return secretaries[0]
    return None


def users_by_real_name():
    mapping = {}
    for user in User.objects.filter(is_active=True):
        name = (user.real_name or '').strip()
        if name:
            mapping.setdefault(name, []).append(user)
    return mapping


def match_user_for_roster(person, name_map, preferred_departments=None):
    candidates = [user for user in name_map.get((person.name or '').strip(), []) if user.is_active]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0] if find_roster_for_user(candidates[0], [person.department]) == person else None
    matched = []
    for user in candidates:
        # Use membership evidence directly: resolving a name through the roster here
        # would make every same-name account appear to belong to this person.
        unit = membership_primary_unit(user)
        if unit and unit.name.strip() == (person.department or '').strip():
            matched.append(user)
    return matched[0] if len(matched) == 1 else None


def find_roster_for_user(user, preferred_departments=None):
    if not user or not user.is_active:
        return None
    name = (user.real_name or '').strip()
    if not name:
        return None
    queryset = PersonnelRoster.objects.filter(name=name)
    people = list(queryset)
    if not people:
        return None
    if len(people) == 1:
        return people[0]
    aligned = find_unique_roster_for_user(user)
    if aligned:
        return aligned
    preferred = set(preferred_departments or [])
    matched = [person for person in people if person.department in preferred]
    return matched[0] if len(matched) == 1 else None


def roster_in_departments(department_names, predicate=None):
    if not department_names:
        people = []
    else:
        query = Q()
        for name in department_names:
            query |= Q(department=name)
        people = list(PersonnelRoster.objects.filter(query).order_by('department', 'serial_number', 'name'))
    if predicate:
        people = [person for person in people if predicate(person)]
    return people


def recipient_payload(user, *, form_type, filler_role, branch=None, roster=None, extra=None):
    scope = collect_scope(user)
    branch = branch or scope['branch']
    roster = roster or find_roster_for_user(user, scope['department_names'])
    item = {
        'user_id': str(user.id),
        'user_name': user.real_name or user.username,
        'username': user.username,
        'form_type': form_type,
        'form_label': FormType(form_type).label,
        'filler_role': filler_role,
        'filler_role_label': FillerRole(filler_role).label,
        'branch_id': str(branch.id) if branch else None,
        'branch_name': branch.name if branch else scope['branch_name'],
        'org_unit_name': scope['org_unit_name'],
        'roster_id': str(roster.id) if roster else None,
        'roster_name': roster.name if roster else '',
        'source': '附件8自动匹配',
        'auto': True,
    }
    if extra:
        item.update(extra)
    return item


def match_form_type(form_type, *, branch_ids=None, extra_user_ids=None):
    extra_user_ids = extra_user_ids or []
    name_map = users_by_real_name()
    branches = list_branches(branch_ids)
    recipients = []
    unmatched = []
    warnings = []

    if form_type in {FormType.ATTACHMENT_2, FormType.ATTACHMENT_3}:
        allowed_departments = None
        if branch_ids:
            allowed_departments = set()
            for branch in branches:
                allowed_departments.add(branch.name)
                for child in branch.get_descendants():
                    allowed_departments.add(child.name)
        for person in middle_roster():
            if allowed_departments is not None and person.department not in allowed_departments:
                continue
            user = match_user_for_roster(person, name_map, [person.department])
            if not user:
                unmatched.append({'name': person.name, 'department': person.department, 'reason': '缺少可用账号或同名身份不唯一，请核对真实姓名、当前部门和账号启用状态'})
                continue
            recipients.append(recipient_payload(
                user, form_type=form_type, filler_role=FillerRole.MIDDLE_LEADER, roster=person,
            ))

    elif form_type in {FormType.ATTACHMENT_4, FormType.ATTACHMENT_5, FormType.ATTACHMENT_6_1, FormType.ATTACHMENT_7_1, FormType.ATTACHMENT_7_2}:
        role = FillerRole.BRANCH_SECRETARY
        if form_type == FormType.ATTACHMENT_4:
            role = FillerRole.BRANCH_LEADERSHIP
        for branch in branches:
            memberships = branch_memberships(branch)
            secretary = pick_secretary(memberships)
            if not secretary:
                unmatched.append({'name': branch.name, 'department': branch.name, 'reason': '未找到唯一的在职党支部书记账号，请核对职务或由管理员指定'})
                continue
            recipients.append(recipient_payload(
                secretary.user, form_type=form_type, filler_role=role, branch=branch,
            ))
        if not branches:
            warnings.append('系统中没有启用的党支部，无法按附件8自动匹配书记。')

    elif form_type in {FormType.ATTACHMENT_6_2, FormType.ATTACHMENT_7_4}:
        role_priority = {
            FillerRole.BRANCH_STAFF: 0,
            FillerRole.BRANCH_COMMITTEE: 1,
            FillerRole.BRANCH_DEPUTY_SECRETARY: 2,
            FillerRole.BRANCH_SECRETARY: 3,
        }
        for branch in branches:
            members = {}
            for membership in branch_memberships(branch):
                role = classify_membership_role(membership)
                if role == FillerRole.BRANCH_STAFF:
                    current_branch = collect_scope(membership.user)['branch']
                    if current_branch and current_branch.id != branch.id:
                        continue
                current = members.get(membership.user_id)
                if not current or role_priority[role] > role_priority[current[1]]:
                    members[membership.user_id] = (membership.user, role)
            departments = [branch.name, *[child.name for child in branch.get_descendants()]]
            for person in roster_in_departments(departments):
                user = match_user_for_roster(person, name_map, departments)
                if not user:
                    unmatched.append({'name': person.name, 'department': person.department,
                                      'reason': '缺少可用账号或同名身份不唯一，请核对真实姓名、当前部门和账号启用状态'})
                elif user.id not in members:
                    members[user.id] = (user, FillerRole.BRANCH_STAFF)
            for user, role in members.values():
                recipients.append(recipient_payload(
                    user, form_type=form_type,
                    filler_role=role if form_type == FormType.ATTACHMENT_7_4 else FillerRole.BRANCH_STAFF,
                    branch=branch,
                ))
            if not members:
                unmatched.append({'name': branch.name, 'department': branch.name, 'reason': '该支部没有可唯一匹配的在职成员账号'})

    elif form_type in {FormType.ATTACHMENT_7_3, FormType.ATTACHMENT_1}:
        users = list(User.objects.filter(id__in=extra_user_ids, is_active=True).order_by('real_name', 'username'))
        role = FillerRole.POLITICAL_LEADER if form_type == FormType.ATTACHMENT_7_3 else FillerRole.INSPECTION_TALKER
        for user in users:
            recipients.append(recipient_payload(
                user, form_type=form_type, filler_role=role, extra={'source': '管理员指定', 'auto': False},
            ))
        if not users:
            warnings.append(FORM_META_MAP[form_type]['rule'])

    # 个人材料及全监狱测评每人一份；支部材料保留兼任支部的任务。
    once_per_user = {
        FormType.ATTACHMENT_2, FormType.ATTACHMENT_3, FormType.ATTACHMENT_6_1,
        FormType.ATTACHMENT_7_1, FormType.ATTACHMENT_7_2, FormType.ATTACHMENT_7_3,
    }
    unique = []
    seen_keys = set()
    for item in recipients:
        key = (item['form_type'], item['user_id'],
               None if form_type in once_per_user else item['branch_id'])
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique.append(item)
    return {'recipients': unique, 'unmatched': unmatched, 'warnings': warnings}


def build_context_for_recipient(item):
    user = User.objects.filter(id=item['user_id']).first()
    scope = collect_scope(user) if user else {
        'unit': None, 'branch': None, 'branch_name': '', 'org_unit_name': '', 'department_names': [],
    }
    branch = None
    if item.get('branch_id'):
        branch = OrgUnit.objects.filter(id=item['branch_id'], is_active=True, unit_type=UnitType.BRANCH).first()
    else:
        branch = scope.get('branch')
    roster = None
    if item.get('roster_id'):
        roster = PersonnelRoster.objects.filter(id=item['roster_id']).first()
    roster = roster or (find_roster_for_user(user, scope.get('department_names')) if user else None)
    # A selected branch replaces the user's own scope. Missing branch never means all staff.
    department_names = ([branch.name, *[child.name for child in branch.get_descendants()]]
                        if branch else [])

    form_type = item['form_type']
    targets = []
    if form_type == FormType.ATTACHMENT_6_1:
        targets = [serialize_target_branch(unit) for unit in list_branches()]
    elif form_type == FormType.ATTACHMENT_6_2:
        if branch:
            targets = [serialize_target_branch(branch)]
    elif form_type == FormType.ATTACHMENT_7_1:
        targets = [serialize_target_person(person) for person in middle_roster() if is_chief(person)]
    elif form_type == FormType.ATTACHMENT_7_2:
        targets = [serialize_target_person(person) for person in middle_roster()
                   if is_deputy(person) and not is_team_lead(person)]
    elif form_type == FormType.ATTACHMENT_7_3:
        targets = [serialize_target_person(person) for person in middle_roster() if is_team_lead(person)]
    elif form_type in {FormType.ATTACHMENT_7_4, FormType.ATTACHMENT_1}:
        targets = [serialize_target_person(person) for person in roster_in_departments(department_names)]

    return {
        'roster': roster_snapshot(roster),
        'branch': {'id': str(branch.id), 'name': branch.name} if branch else {'id': None, 'name': scope.get('branch_name') or ''},
        'targets': targets,
        'roster_people': [serialize_target_person(person) for person in roster_in_departments(department_names)],
        'department_names': department_names,
        'filler_role': item.get('filler_role'),
    }
