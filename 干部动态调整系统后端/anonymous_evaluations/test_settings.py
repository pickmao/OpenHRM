"""匿名测评模块的 SQLite 隔离测试配置。"""

from 干部动态调整系统.settings import *  # noqa: F401,F403


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    },
}

# forms 的历史 OnlyOffice 迁移包含 PostgreSQL 专用 SQL；匿名测评测试不依赖该应用的数据迁移。
MIGRATION_MODULES = {'forms': None}
