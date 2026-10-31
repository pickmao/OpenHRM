"""根据用户提供的“各支部”照片整理的部门归属清单。

只维护组织归属；照片中的人名、纸质版字样不用于推断账号或权限。
"""
from django.db import connection, transaction
from rest_framework.exceptions import ValidationError

from .models import OrgUnit, UnitType


NUMERALS = ('一', '二', '三', '四', '五', '六', '七', '八', '九', '十',
            '十一', '十二', '十三', '十四', '十五')
OFFICE_DEPARTMENTS = (
    ('政治处', '工会'),
    ('办公室',),
    ('纪检与审计科',),
    ('狱政管理科', '生活卫生科', '狱内侦查科'),
    ('教育改造科', '刑罚执行科', '改造质量评估科'),
    ('劳动改造科', '安全生产监督管理科'),
    ('企业办公室', '企业财务部', '生产经营部'),
    ('规划财务科',),
    ('警务保障中心',),
    ('监狱指挥中心', '信息技术科'),
)
CATALOG = tuple(
    {'name': f'机关第{NUMERALS[i]}党支部', 'departments': names, 'aliases': ()}
    for i, names in enumerate(OFFICE_DEPARTMENTS)
) + tuple(
    {'name': f'{name}党支部', 'departments': (name,), 'aliases': (name,)}
    for name in [*(f'{n}监区' for n in NUMERALS), '警务监区', '监狱医院']
)


def catalog_preview():
    units = list(OrgUnit.objects.select_related('parent').all())
    rows, errors = [], []
    for index, spec in enumerate(CATALOG, 1):
        branches = [u for u in units if u.unit_type == UnitType.BRANCH
                    and u.name in (spec['name'], *spec['aliases'])]
        branch = branches[0] if len(branches) == 1 else None
        issues = []
        if len(branches) > 1:
            issues.append('存在多个同名或别名支部，请先合并核对')
        if branch and not branch.is_active:
            issues.append('已有支部已停用，请先核对状态')
        departments = []
        for name in spec['departments']:
            matches = [u for u in units if u.unit_type != UnitType.BRANCH and u.name == name]
            department = matches[0] if len(matches) == 1 else None
            if len(matches) > 1:
                issues.append(f'{name}：存在同名部门，无法唯一匹配')
            if department:
                if not department.is_active:
                    issues.append(f'{name}：已有部门已停用')
                if department.parent_id and (not branch or department.parent_id != branch.id):
                    issues.append(f'{name}：已归属「{department.parent.name}」，请先核对归属')
                # 不递归现有树，避免历史脏数据中的环导致无限递归。
                current, seen = branch, set()
                while current and current.id not in seen:
                    seen.add(current.id)
                    if current.id == department.id:
                        issues.append(f'{name}：归属会形成组织循环')
                        break
                    current = current.parent
            departments.append({
                'name': name, 'id': str(department.id) if department else None,
                'action': ('已归属' if branch and department and department.parent_id == branch.id
                           else '纳入支部' if department else '新建并纳入'),
            })
        errors.extend(f"{spec['name']}：{issue}" for issue in issues)
        rows.append({
            'order': index, 'name': spec['name'], 'id': str(branch.id) if branch else None,
            'existing_name': branch.name if branch else None,
            'action': '使用已有支部' if branch else '新建支部',
            'departments': departments, 'issues': issues,
        })
    return {'rows': rows, 'errors': errors, 'can_apply': not errors,
            'branch_count': len(rows),
            'department_count': sum(len(row['departments']) for row in rows)}


@transaction.atomic
def apply_catalog():
    # 串行化本入口，首次空库同时初始化也不会生成两套组织。
    if connection.vendor == 'postgresql':
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_xact_lock(%s)', [2026092201])
    list(OrgUnit.objects.select_for_update().values_list('id', flat=True))
    preview = catalog_preview()
    if preview['errors']:
        raise ValidationError({'error': '清单存在冲突，未修改任何组织', 'errors': preview['errors']})
    created_branches = created_departments = assigned = 0
    for row in preview['rows']:
        if row['id']:
            branch = OrgUnit.objects.get(pk=row['id'])
        else:
            branch = OrgUnit.objects.create(name=row['name'], unit_type=UnitType.BRANCH,
                                            sort_order=row['order'])
            created_branches += 1
        for item in row['departments']:
            if not item['id']:
                OrgUnit.objects.create(name=item['name'], unit_type=UnitType.DEPARTMENT,
                                       parent=branch)
                created_departments += 1
                assigned += 1
            else:
                department = OrgUnit.objects.get(pk=item['id'])
                if department.parent_id != branch.id:
                    department.parent = branch
                    department.save(update_fields=['parent', 'updated_at'])
                    assigned += 1
    return {'message': '各支部清单已应用', 'created_branches': created_branches,
            'created_departments': created_departments, 'assigned': assigned}
