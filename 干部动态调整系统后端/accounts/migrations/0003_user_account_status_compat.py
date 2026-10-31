from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_alter_role_code'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE accounts_user "
                "ADD COLUMN IF NOT EXISTS account_status varchar(32) NOT NULL DEFAULT 'ACTIVE'; "
                "ALTER TABLE accounts_user "
                "ALTER COLUMN account_status SET DEFAULT 'ACTIVE';"
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='user',
                    name='account_status',
                    field=models.CharField(
                        choices=[
                            ('PENDING_ACTIVATION', '待激活'),
                            ('ACTIVE', '正常'),
                            ('DISABLED', '已禁用'),
                        ],
                        default='ACTIVE',
                        max_length=32,
                        verbose_name='账号状态',
                    ),
                ),
            ],
        ),
    ]
