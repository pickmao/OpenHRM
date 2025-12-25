"""
数据管理模块
用于初始化角色、权限和默认数据
"""

from django.core.management.base import BaseCommand
from accounts.models import User, Role, UserRole, DataScope


def init_roles_and_permissions():
    """初始化角色和权限"""

    # 定义角色权限映射
    ROLE_PERMISSIONS = {
        'SUPER_ADMIN': [
            'cadres:view', 'cadres:create', 'cadres:edit', 'cadres:delete',
            'orgs:view', 'orgs:create', 'orgs:edit', 'orgs:delete',
            'staffing:plan:create', 'staffing:plan:submit', 'staffing:plan:apply',
            'risk:view', 'risk:manage',
            'audit:view'
        ],
        'POLITICAL_OFFICE_ADMIN': [
            'cadres:view', 'cadres:edit',
            'orgs:view',
            'staffing:plan:create', 'staffing:plan:submit', 'staffing:plan:apply',
            'risk:view', 'risk:manage',
            'audit:view'
        ],
        'DEPT_MANAGER': [
            'cadres:view',
            'orgs:view',
            'staffing:plan:create',
            'risk:view',
            'audit:view'
        ],
        'ANALYST': [
            'cadres:view',
            'orgs:view',
            'analytics:view',
            'risk:view',
            'audit:view'
        ],
        'CADRE_SELF': [
            'cadres:view_self',
            'audit:view_self'
        ]
    }

    # 创建角色
    for role_code, permissions in ROLE_PERMISSIONS.items():
        role, created = Role.objects.get_or_create(
            code=role_code,
            defaults={
                'name': Role.ROLE_CHOICES_DICT[role_code],
                'permissions': permissions,
                'is_active': True
            }
        )

        if created:
            print(f"创建角色: {role.name}")
        else:
            # 更新权限
            if role.permissions != permissions:
                role.permissions = permissions
                role.save()
                print(f"更新角色权限: {role.name}")


def create_superuser_if_not_exists():
    """创建超级管理员（如果不存在）"""

    # 默认超级管理员信息
    DEFAULT_SUPERUSER = {
        'username': 'admin',
        'email': 'admin@example.com',
        'password': 'admin123456',
        'real_name': '系统管理员'
    }

    if not User.objects.filter(username=DEFAULT_SUPERUSER['username']).exists():
        user = User.objects.create_superuser(
            username=DEFAULT_SUPERUSER['username'],
            email=DEFAULT_SUPERUSER['email'],
            password=DEFAULT_SUPERUSER['password'],
            real_name=DEFAULT_SUPERUSER['real_name']
        )
        print(f"创建超级管理员: {user.username}")

        # 分配超级管理员角色
        try:
            super_admin_role = Role.objects.get(code='SUPER_ADMIN')
            UserRole.objects.create(
                user=user,
                role=super_admin_role,
                assigned_by=user
            )

            # 创建数据范围
            DataScope.objects.create(
                user=user,
                scope_type='ALL'
            )
            print("为超级管理员分配角色和数据范围")
        except Role.DoesNotExist:
            print("警告: 超级管理员角色不存在，请先运行 init_roles_and_permissions()")
    else:
        print("超级管理员已存在")


def create_demo_users():
    """创建演示用户"""

    demo_users = [
        {
            'username': 'political_admin',
            'password': '123456',
            'real_name': '张政治',
            'email': 'political@example.com',
            'role': 'POLITICAL_OFFICE_ADMIN'
        },
        {
            'username': 'dept_manager',
            'password': '123456',
            'real_name': '李经理',
            'email': 'manager@example.com',
            'role': 'DEPT_MANAGER'
        },
        {
            'username': 'analyst',
            'password': '123456',
            'real_name': '王分析',
            'email': 'analyst@example.com',
            'role': 'ANALYST'
        }
    ]

    for user_data in demo_users:
        if not User.objects.filter(username=user_data['username']).exists():
            user = User.objects.create_user(
                username=user_data['username'],
                password=user_data['password'],
                email=user_data['email'],
                real_name=user_data['real_name'],
                is_active=True
            )

            # 分配角色
            try:
                role = Role.objects.get(code=user_data['role'])
                UserRole.objects.create(
                    user=user,
                    role=role
                )

                # 创建数据范围（根据角色设置不同的范围）
                scope_type = 'SELF' if user_data['role'] == 'ANALYST' else 'ORG_UNIT'
                DataScope.objects.create(
                    user=user,
                    scope_type=scope_type
                )

                print(f"创建演示用户: {user.real_name} ({user.username})")
            except Role.DoesNotExist:
                print(f"警告: 角色 {user_data['role']} 不存在")
        else:
            print(f"用户 {user_data['username']} 已存在")


class Command(BaseCommand):
    help = '初始化系统数据：角色、权限和演示用户'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-superuser',
            action='store_true',
            help='创建超级管理员用户'
        )
        parser.add_argument(
            '--create-demo-users',
            action='store_true',
            help='创建演示用户'
        )

    def handle(self, *args, **options):
        print("开始初始化系统数据...")

        # 1. 初始化角色和权限
        print("\n1. 初始化角色和权限...")
        init_roles_and_permissions()

        # 2. 创建超级管理员
        if options['create_superuser']:
            print("\n2. 创建超级管理员...")
            create_superuser_if_not_exists()

        # 3. 创建演示用户
        if options['create_demo_users']:
            print("\n3. 创建演示用户...")
            create_demo_users()

        print("\n系统数据初始化完成！")