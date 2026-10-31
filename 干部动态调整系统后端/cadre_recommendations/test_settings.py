"""优秀干部推荐模块的 SQLite 隔离测试配置。"""

from 干部动态调整系统.settings import *  # noqa: F401,F403


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    },
}

MIGRATION_MODULES = {'forms': None, 'accounts': None}
