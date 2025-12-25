from django.core.management.base import BaseCommand
from accounts.data_management import (
    init_roles_and_permissions,
    create_superuser_if_not_exists,
    create_demo_users
)


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
        if options['create_demo-users']:
            print("\n3. 创建演示用户...")
            create_demo_users()

        print("\n系统数据初始化完成！")