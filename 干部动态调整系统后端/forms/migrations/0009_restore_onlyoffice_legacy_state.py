# 这些字段已由故障前版本的 forms.0004_onlyoffice_document 创建于生产库。
# 当前恢复的代码需要重新声明它们；只同步迁移状态，避免对现有列重复执行 ADD COLUMN。

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('forms', '0008_alter_formtask_deadline_at'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE forms_onlyofficedocument
                            ADD COLUMN IF NOT EXISTS original_name varchar(255) NOT NULL DEFAULT '',
                            ADD COLUMN IF NOT EXISTS file_ext varchar(20) NOT NULL DEFAULT '',
                            ADD COLUMN IF NOT EXISTS mime_type varchar(120) NOT NULL DEFAULT '',
                            ADD COLUMN IF NOT EXISTS file_size bigint NOT NULL DEFAULT 0,
                            ADD COLUMN IF NOT EXISTS storage_path varchar(500) NOT NULL DEFAULT '',
                            ADD COLUMN IF NOT EXISTS access_token varchar(64) NOT NULL DEFAULT '',
                            ADD COLUMN IF NOT EXISTS last_callback_status integer NULL,
                            ADD COLUMN IF NOT EXISTS created_by_id uuid NULL;

                        UPDATE forms_onlyofficedocument
                        SET access_token = md5(id::text)
                        WHERE access_token = '';

                        ALTER TABLE forms_onlyofficedocument
                            ALTER COLUMN original_name DROP DEFAULT,
                            ALTER COLUMN file_ext DROP DEFAULT,
                            ALTER COLUMN mime_type DROP DEFAULT,
                            ALTER COLUMN file_size DROP DEFAULT,
                            ALTER COLUMN storage_path DROP DEFAULT,
                            ALTER COLUMN access_token DROP DEFAULT;

                        CREATE INDEX IF NOT EXISTS forms_onlyoffice_file_ext_idx
                            ON forms_onlyofficedocument (file_ext);
                        CREATE UNIQUE INDEX IF NOT EXISTS forms_onlyoffice_access_token_uniq
                            ON forms_onlyofficedocument (access_token);
                        CREATE INDEX IF NOT EXISTS forms_onlyoffice_created_by_idx
                            ON forms_onlyofficedocument (created_by_id);
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='onlyofficedocument',
                    name='original_name',
                    field=models.CharField(max_length=255, verbose_name='原始文件名'),
                ),
                migrations.AddField(
                    model_name='onlyofficedocument',
                    name='file_ext',
                    field=models.CharField(db_index=True, max_length=20, verbose_name='文件扩展名'),
                ),
                migrations.AddField(
                    model_name='onlyofficedocument',
                    name='mime_type',
                    field=models.CharField(blank=True, max_length=120, verbose_name='MIME 类型'),
                ),
                migrations.AddField(
                    model_name='onlyofficedocument',
                    name='file_size',
                    field=models.BigIntegerField(default=0, verbose_name='文件大小'),
                ),
                migrations.AddField(
                    model_name='onlyofficedocument',
                    name='storage_path',
                    field=models.CharField(max_length=500, verbose_name='存储路径'),
                ),
                migrations.AddField(
                    model_name='onlyofficedocument',
                    name='access_token',
                    field=models.CharField(db_index=True, max_length=64, unique=True, verbose_name='访问令牌'),
                ),
                migrations.AddField(
                    model_name='onlyofficedocument',
                    name='last_callback_status',
                    field=models.IntegerField(blank=True, null=True, verbose_name='最近回调状态'),
                ),
                migrations.AddField(
                    model_name='onlyofficedocument',
                    name='created_by',
                    field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='onlyoffice_documents', to=settings.AUTH_USER_MODEL, verbose_name='创建人'),
                ),
            ],
        ),
    ]
