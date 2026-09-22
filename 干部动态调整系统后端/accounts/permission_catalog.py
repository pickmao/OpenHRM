"""后台与业务模块共用的权限目录。"""

PERMISSION_CATALOG = {
    '账号与权限': [
        ('accounts:role:view', '查看角色'),
        ('accounts:role:create', '创建角色'),
        ('accounts:role:edit', '编辑角色'),
        ('accounts:role:delete', '删除角色'),
        ('accounts:role:grant_permissions', '配置角色权限'),
        ('accounts:permission:view_catalog', '查看权限目录'),
        ('accounts:user:view', '查看用户'),
        ('accounts:user:manage', '管理用户'),
        ('accounts:user:assign_role', '分配用户角色'),
        ('accounts:user:view_roles', '查看用户角色'),
    ],
    '表单下发与填报': [
        ('forms:template:manage', '管理表单模板'),
        ('forms:dispatch:manage', '下发表单并查看进度'),
        ('forms:task:view', '查看本人填报任务'),
        ('forms:task:submit', '填写和提交本人任务'),
        ('forms:task:manage', '管理和退回任务'),
    ],
    '分析研判': [
        ('assessments:view', '查看干部与领导班子研判'),
        ('assessments:manage', '上传和维护研判数据'),
    ],
    '奖励汇总': [
        ('rewards:view', '查看个人及集体奖励汇总'),
        ('rewards:manage', '导入和维护奖励汇总'),
    ],
    '匿名民主测评': [
        ('anonymous_evaluations:campaign:manage', '管理匿名测评活动'),
        ('anonymous_evaluations:task:view', '查看本人匿名评价任务'),
        ('anonymous_evaluations:task:submit', '填写并提交匿名评价'),
        ('anonymous_evaluations:result:view', '查看匿名测评汇总结果'),
    ],
    '优秀干部推荐': [
        ('cadre_recommendations:campaign:manage', '下发优秀干部推荐活动'),
        ('cadre_recommendations:task:view', '查看本人推荐任务'),
        ('cadre_recommendations:task:submit', '填写并提交推荐表'),
        ('cadre_recommendations:result:view', '查看优秀干部推荐统计'),
    ],
    '知事识人': [
        ('knowing_people:campaign:manage', '下发知事识人填报任务并退回、催办'),
        ('knowing_people:task:view', '查看本人知事识人填报任务'),
        ('knowing_people:task:submit', '填写并提交知事识人表单'),
        ('knowing_people:result:view', '查看知事识人填报进度和计票汇总'),
    ],
    '组织机构': [
        ('orgs:view', '查看组织机构'),
        ('orgs:create', '创建组织单位'),
        ('orgs:edit', '编辑组织单位'),
        ('orgs:delete', '删除组织单位'),
        ('orgs:membership:transfer', '人员部门调配'),
    ],
}


ALL_PERMISSION_CODES = {code for items in PERMISSION_CATALOG.values() for code, _ in items}


def is_valid_permission_code(code):
    return code in ALL_PERMISSION_CODES


def catalog_response():
    return [
        {'module': module, 'permissions': [{'code': code, 'name': name} for code, name in permissions]}
        for module, permissions in PERMISSION_CATALOG.items()
    ]
