from django.db import migrations


class Migration(migrations.Migration):
    """为仍保留旧表单数据的数据库补齐 OnlyOffice 文件字段。

    旧磁盘丢失时数据库保留了历史 0001-0004 迁移记录；这里使用幂等 SQL，
    只增加新列，不改写或删除任何原有任务和提交数据。
    """

    dependencies = [
        ('forms', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE forms_formtemplate ADD COLUMN IF NOT EXISTS source_file varchar(100);
                ALTER TABLE forms_formtemplate ADD COLUMN IF NOT EXISTS source_file_name varchar(255) NOT NULL DEFAULT '';
                ALTER TABLE forms_onlyofficedocument ADD COLUMN IF NOT EXISTS task_id uuid;
                ALTER TABLE forms_onlyofficedocument ADD COLUMN IF NOT EXISTS file varchar(100);
                ALTER TABLE forms_onlyofficedocument ADD COLUMN IF NOT EXISTS file_name varchar(255) NOT NULL DEFAULT '';
                ALTER TABLE forms_onlyofficedocument ADD COLUMN IF NOT EXISTS document_key varchar(128);
                CREATE UNIQUE INDEX IF NOT EXISTS forms_onlyoffice_document_key_uniq
                    ON forms_onlyofficedocument (document_key) WHERE document_key IS NOT NULL;
                CREATE UNIQUE INDEX IF NOT EXISTS forms_onlyoffice_task_uniq
                    ON forms_onlyofficedocument (task_id) WHERE task_id IS NOT NULL;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
