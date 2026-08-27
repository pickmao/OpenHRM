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
}


ALL_PERMISSION_CODES = {code for items in PERMISSION_CATALOG.values() for code, _ in items}


def is_valid_permission_code(code):
    return code in ALL_PERMISSION_CODES


def catalog_response():
    return [
        {'module': module, 'permissions': [{'code': code, 'name': name} for code, name in permissions]}
        for module, permissions in PERMISSION_CATALOG.items()
    ]
