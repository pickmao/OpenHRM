import json
import secrets

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from accounts.demo_data import seed_all
from accounts.models import User


class Command(BaseCommand):
    help = '为各业务栏目补建带演示标识的测试数据；重复运行保留已操作的数据和密码。'

    def add_arguments(self, parser):
        parser.add_argument('--password', help='新建演示账号的共同密码；省略则随机生成')

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('此命令仅允许在 DEBUG 开发环境运行')
        password = options['password'] or secrets.token_urlsafe(12)
        existed = User.objects.filter(username='demo_admin').exists()
        try:
            result = seed_all(password)
        except (ValueError, TypeError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
        self.stdout.write(self.style.SUCCESS('全栏目演示数据已就绪：demo_admin / demo01 至 demo12'))
        if not existed:
            self.stdout.write(f'新建演示账号密码：{password}')
        else:
            self.stdout.write('已有演示账号密码和操作数据保持不变。')
