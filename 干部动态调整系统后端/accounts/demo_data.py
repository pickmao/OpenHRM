"""可重复运行的全栏目演示数据；仅创建固定命名空间中的虚构记录。"""
from datetime import date, timedelta
from uuid import UUID, uuid5

from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils import timezone

from accounts.models import DataScope, Role, User, UserRole
from accounts.permission_catalog import ALL_PERMISSION_CODES
from cadres.models import Cadre, CadreResume, PersonnelRoster
from orgs.models import Membership, OrgUnit
from staffing.models import OrgMembership


NAMESPACE = UUID('fd012337-b4a4-43a6-91b8-563488e2f621')


class DemoContext:
    prefix = '【演示】'

    def __init__(self, password):
        self.now = timezone.now()
        self.password_hash = make_password(password)
        self.created = 0

    def key(self, key):
        return uuid5(NAMESPACE, key)

    def put(self, model, key, **defaults):
        obj, created = model.objects.get_or_create(pk=self.key(key), defaults=defaults)
        self.created += int(created)
        return obj

    def account(self, key, username, name, **extra):
        existing = User.objects.filter(username=username).first()
        if existing and existing.pk != self.key(key):
            raise ValueError(f'账号 {username} 已被其他数据占用，未覆盖')
        return self.put(User, key, username=username, real_name=name,
                        password=self.password_hash, is_active=True,
                        account_status=User.AccountStatus.ACTIVE, **extra)


def seed_base(ctx):
    ctx.admin = ctx.account('admin', 'demo_admin', '演示管理员', is_staff=True, is_superuser=True)
    admin_role = ctx.put(Role, 'admin-role', code='DEMO_ADMIN', name='【演示】系统管理员',
                         permissions=sorted(ALL_PERMISSION_CODES))
    staff_role = ctx.put(Role, 'staff-role', code='DEMO_STAFF', name='【演示】填报人员', permissions=[
        'forms:task:view', 'forms:task:submit', 'knowing_people:task:view', 'knowing_people:task:submit',
        'anonymous_evaluations:task:view', 'anonymous_evaluations:task:submit',
        'cadre_recommendations:task:view', 'cadre_recommendations:task:submit', 'orgs:view',
    ])
    ctx.put(UserRole, 'admin-role-link', user=ctx.admin, role=admin_role, assigned_by=ctx.admin)
    ctx.put(DataScope, 'admin-scope', user=ctx.admin, scope_type='ALL', note='演示管理员')
    ctx.branches = [ctx.put(OrgUnit, f'branch-{i}', name=f'【演示】第{i+1}党支部',
                           code=f'DEMO-B{i+1}', unit_type='BRANCH', sort_order=900+i) for i in range(3)]
    ctx.departments = [ctx.put(OrgUnit, f'department-{i}', name=f'【演示】第{i+1}业务科',
                              code=f'DEMO-D{i+1}', unit_type='DEPARTMENT', parent=ctx.branches[i//2],
                              sort_order=900+i) for i in range(6)]
    ctx.put(Membership, 'admin-membership', user=ctx.admin, unit=ctx.departments[0],
            is_primary=True, position='演示管理员', created_by=ctx.admin)
    ctx.users, ctx.rosters, ctx.cadres = [], [], []
    positions = ['科长', '副科长', '监区工作团队正职', '民警']
    party_positions = ['支部书记', '支部副书记', '组织委员', '党员']
    for i in range(12):
        name = f'演示人员{i+1:02d}'
        department = ctx.departments[i//2]
        birthday = date(1980+i*2, i % 12+1, 15)
        cadre = ctx.put(Cadre, f'cadre-{i}', cadre_code=f'DEMO-{i+1:03d}', name=name,
                        gender='F' if i%3 == 0 else 'M', birth_date=birthday,
                        political_status='中共党员', education_level='MASTER' if i%3 == 0 else 'BACHELOR',
                        join_work_date=date(2004+i, 7, 1), current_position=positions[i%4],
                        current_rank='一级警长', tags={'demo': True})
        # 先建花名册再建账号，避免花名册同步信号另建不稳定 ID 的成员关系。
        person = ctx.put(PersonnelRoster, f'roster-{i}', serial_number=9001+i, name=name,
                         department=department.name, gender=cadre.gender, birth_date=birthday,
                         age=ctx.now.year-birthday.year, ethnicity='汉族', political_status='中共党员',
                         position=positions[i%4], position_category=('领导职务' if i%4 < 2 else
                         '监区工作团队正职' if i%4 == 2 else '非领导职务'),
                         position_rank='正科级' if i%4 == 0 else '副科级' if i%4 == 1 else '',
                         police_rank='一级警长', police_title='三级警督', police_number=f'DEMO{i+1:03d}',
                         join_work_date=cadre.join_work_date, join_party_date=date(2003+i, 6, 1),
                         education_level='研究生' if i%3 == 0 else '本科',
                         highest_education='研究生' if i%3 == 0 else '本科',
                         highest_school='演示院校', highest_major='法学',
                         annual_assessments={str(ctx.now.year-1): '优秀' if i%3 == 0 else '称职'},
                         remark='仅供系统测试的虚构记录', created_by=ctx.admin)
        user = ctx.account(f'user-{i}', f'demo{i+1:02d}', name, profile_cadre=cadre)
        ctx.put(UserRole, f'user-role-{i}', user=user, role=staff_role, assigned_by=ctx.admin)
        ctx.put(DataScope, f'user-scope-{i}', user=user, scope_type='SELF', note='演示填报账号')
        ctx.put(Membership, f'membership-{i}', user=user, unit=department, is_primary=True,
                position=positions[i%4], effective_from=(ctx.now-timedelta(days=365)).date(), created_by=ctx.admin)
        ctx.put(Membership, f'party-membership-{i}', user=user, unit=ctx.branches[i//4], is_primary=False,
                position=party_positions[i%4], effective_from=(ctx.now-timedelta(days=365)).date(), created_by=ctx.admin)
        ctx.put(OrgMembership, f'cadre-membership-{i}', cadre=cadre, org_unit=department,
                role_in_unit='LEADER' if i%4 == 0 else 'MEMBER', start_date=date(2023, 1, 1))
        ctx.put(CadreResume, f'resume-{i}', cadre=cadre, org_unit=department,
                position_title=positions[i%4], start_date=date(2023, 1, 1), remark='【演示】任职履历')
        ctx.users.append(user)
        ctx.rosters.append(person)
        ctx.cadres.append(cadre)
    return {'users': 13, 'branches': 3, 'departments': 6, 'rosters': 12, 'cadres': 12}


@transaction.atomic
def seed_all(password):
    from . import demo_campaigns, demo_flows, demo_records
    ctx = DemoContext(password)
    counts = seed_base(ctx)
    for module in (demo_records, demo_flows, demo_campaigns):
        counts.update(module.seed(ctx))
    return {'created': ctx.created, 'coverage': counts}
