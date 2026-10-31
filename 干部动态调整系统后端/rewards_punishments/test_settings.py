"""奖励汇总应用的隔离测试配置，避免依赖本机保留的 PostgreSQL 测试库。"""

from 干部动态调整系统.settings import *  # noqa: F401,F403


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    },
}

# forms 的历史 OnlyOffice 迁移包含 PostgreSQL 专用 SQL；奖励模块测试不依赖该迁移。
MIGRATION_MODULES = {'forms': None}
