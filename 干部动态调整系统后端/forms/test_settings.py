"""改进需求的隔离测试库；历史 PostgreSQL 兼容迁移不在 SQLite 执行。"""
from anonymous_evaluations.test_settings import *  # noqa: F401,F403

MIGRATION_MODULES = {'forms': None, 'accounts': None}
