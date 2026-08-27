"""
快速创建超级管理员脚本

使用方法：
1. 确保已激活虚拟环境
2. 运行: python create_superuser.py

默认超级管理员信息：
- 用户名: admin
- 密码: admin123456
- 邮箱: admin@example.com
- 真实姓名: 系统管理员
"""

import os
import sys
import django

# 将项目根目录添加到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 设置Django环境变量
os.environ.setdefault('DJANGO_SETTINGS_MODULE', '干部动态调整系统.settings')

# 初始化Django
django.setup()

from accounts.models import User, Role, UserRole, DataScope


def create_superuser():
    """创建超级管理员"""

    # 默认超级管理员信息
    SUPERUSER_INFO = {
        'username': 'admin',
        'password': 'admin123456',
        'email': 'admin@example.com',
        'real_name': '系统管理员'
    }

    print("=" * 50)
    print("创建超级管理员")
    print("=" * 50)

    # 检查用户是否已存在
    if User.objects.filter(username=SUPERUSER_INFO['username']).exists():
        print(f"\n用户 '{SUPERUSER_INFO['username']}' 已存在！")
        choice = input("是否重置密码？(y/n): ").strip().lower()

        if choice == 'y':
            user = User.objects.get(username=SUPERUSER_INFO['username'])
            user.set_password(SUPERUSER_INFO['password'])
            user.save()
            print(f"\n✓ 密码已重置！")
        else:
            print("\n操作取消")
            return
    else:
        # 创建超级管理员
        user = User.objects.create_superuser(
            username=SUPERUSER_INFO['username'],
            email=SUPERUSER_INFO['email'],
            password=SUPERUSER_INFO['password'],
            real_name=SUPERUSER_INFO['real_name']
        )
        print(f"\n✓ 超级管理员创建成功！")

    # 确保角色和数据权限存在
    try:
        # 确保有超级管理员角色
        super_admin_role, created = Role.objects.get_or_create(
            code='SUPER_ADMIN',
            defaults={
                'name': '系统超级管理员',
                'permissions': [
                    'cadres:view', 'cadres:create', 'cadres:edit', 'cadres:delete',
                    'orgs:view', 'orgs:create', 'orgs:edit', 'orgs:delete',
                    'staffing:plan:create', 'staffing:plan:submit', 'staffing:plan:apply',
                    'risk:view', 'risk:manage',
                    'audit:view'
                ],
                'is_active': True
            }
        )

        if created:
            print(f"✓ 创建角色: {super_admin_role.name}")

        # 分配角色
        user_role, created = UserRole.objects.get_or_create(
            user=user,
            role=super_admin_role,
            defaults={'assigned_by': user}
        )

        if created:
            print(f"✓ 分配角色: {super_admin_role.name}")

        # 创建或更新数据范围
        data_scope, created = DataScope.objects.get_or_create(
            user=user,
            defaults={'scope_type': 'ALL'}
        )

        if not created and data_scope.scope_type != 'ALL':
            data_scope.scope_type = 'ALL'
            data_scope.save()
            print(f"✓ 更新数据范围: 全部数据")
        elif created:
            print(f"✓ 创建数据范围: 全部数据")

    except Exception as e:
        print(f"\n警告: 分配角色或权限时出错 - {e}")

    # 显示登录信息
    print("\n" + "=" * 50)
    print("超级管理员信息")
    print("=" * 50)
    print(f"用户名: {SUPERUSER_INFO['username']}")
    print(f"密码: {SUPERUSER_INFO['password']}")
    print(f"邮箱: {SUPERUSER_INFO['email']}")
    print(f"真实姓名: {SUPERUSER_INFO['real_name']}")
    print("=" * 50)
    print("\n请妥善保管账号密码！")
    print("\n登录地址:")
    print("  - 前端: http://localhost:5173/login")
    print("  - API文档: http://localhost:8000/swagger/")


def create_custom_superuser():
    """创建自定义超级管理员"""

    print("\n" + "=" * 50)
    print("创建自定义超级管理员")
    print("=" * 50)

    username = input("用户名: ").strip()
    if not username:
        print("用户名不能为空！")
        return

    password = input("密码 (至少6位): ").strip()
    if len(password) < 6:
        print("密码至少需要6位！")
        return

    email = input("邮箱 (可选): ").strip() or f"{username}@example.com"
    real_name = input("真实姓名 (可选): ").strip() or username

    # 检查用户是否已存在
    if User.objects.filter(username=username).exists():
        print(f"\n用户 '{username}' 已存在！")
        return

    # 创建超级管理员
    user = User.objects.create_superuser(
        username=username,
        email=email,
        password=password,
        real_name=real_name
    )

    print(f"\n✓ 超级管理员 '{username}' 创建成功！")

    # 分配超级管理员角色和数据范围
    try:
        super_admin_role = Role.objects.get(code='SUPER_ADMIN')
        UserRole.objects.create(user=user, role=super_admin_role, assigned_by=user)
        DataScope.objects.create(user=user, scope_type='ALL')
        print(f"✓ 已分配超级管理员权限")
    except Role.DoesNotExist:
        print(f"警告: 超级管理员角色不存在")


if __name__ == '__main__':
    print("\n干部动态调整系统 - 超级管理员创建工具\n")
    print("请选择:")
    print("1. 使用默认配置创建超级管理员")
    print("2. 自定义创建超级管理员")
    print("0. 退出")

    choice = input("\n请输入选项 (0-2): ").strip()

    if choice == '1':
        create_superuser()
    elif choice == '2':
        create_custom_superuser()
    else:
        print("操作取消")
