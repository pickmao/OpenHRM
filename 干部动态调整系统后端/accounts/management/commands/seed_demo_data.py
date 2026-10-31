import json
import secrets
import sys

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from accounts.demo_data import seed_all
from accounts.models import User


class Command(BaseCommand):
    help = '为各业务栏目补建带演示标识的测试数据；重复运行保留已操作的数据和密码。'

    def add_arguments(self, parser):
        parser.add_argument('--password', help='新建演示账号的共同密码；省略则随机生成')
        parser.add_argument('--password-stdin', action='store_true', help='从标准输入读取密码，不在命令行或输出中显示')
        parser.add_argument('--allow-production', action='store_true', help='明确允许在生产配置下追加虚构演示数据')

    def handle(self, *args, **options):
        if not settings.DEBUG and not options['allow_production']:
            raise CommandError('生产环境必须显式指定 --allow-production；请先备份数据库')
        if options['password'] and options['password_stdin']:
            raise CommandError('--password 与 --password-stdin 不能同时使用')
        supplied_password = sys.stdin.readline().rstrip('\r\n') if options['password_stdin'] else options['password']
        if options['password_stdin'] and not supplied_password:
            raise CommandError('标准输入密码不能为空')
        if not settings.DEBUG and (not supplied_password or len(supplied_password) < 12):
            raise CommandError('生产演示账号需明确提供至少 12 位密码，建议使用 --password-stdin')
        password = supplied_password or secrets.token_urlsafe(12)
        existed = User.objects.filter(username='demo_admin').exists()
        try:
            result = seed_all(password)
        except (ValueError, TypeError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
        self.stdout.write(self.style.SUCCESS('全栏目演示数据已就绪：demo_admin / demo01 至 demo12'))
        if not existed and not supplied_password:
            self.stdout.write(f'新建演示账号密码：{password}')
        elif existed:
            self.stdout.write('已有演示账号密码和操作数据保持不变。')
