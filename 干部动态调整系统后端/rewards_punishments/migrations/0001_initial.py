import django.db.models.deletion
import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='RewardImportFile',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('file_name', models.CharField(db_index=True, max_length=255)),
                ('source_file', models.FileField(blank=True, null=True, upload_to='rewards/source/')),
                ('upload_time', models.DateTimeField(auto_now_add=True)),
                ('total_records', models.PositiveIntegerField(default=0)),
                ('record_counts', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('uploaded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='uploaded_reward_files', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-upload_time']},
        ),
        migrations.CreateModel(
            name='RewardRecord',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('recipient_type', models.CharField(choices=[('INDIVIDUAL', '个人奖励'), ('COLLECTIVE', '集体奖励')], db_index=True, default='INDIVIDUAL', max_length=16)),
                ('recipient_name', models.CharField(db_index=True, max_length=200)),
                ('award_level', models.CharField(blank=True, db_index=True, max_length=100)),
                ('approval_year', models.PositiveSmallIntegerField(blank=True, db_index=True, null=True)),
                ('award_content', models.TextField(blank=True)),
                ('approval_date', models.DateField(blank=True, db_index=True, null=True)),
                ('document_number', models.CharField(blank=True, db_index=True, max_length=200)),
                ('remark', models.TextField(blank=True)),
                ('source_sheet', models.CharField(blank=True, max_length=100)),
                ('source_row', models.PositiveIntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_reward_records', to=settings.AUTH_USER_MODEL)),
                ('import_file', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='records', to='rewards_punishments.rewardimportfile')),
            ],
            options={'ordering': ['-approval_year', 'recipient_type', 'recipient_name', '-approval_date']},
        ),
        migrations.AddIndex(
            model_name='rewardrecord',
            index=models.Index(fields=['recipient_type', 'approval_year'], name='rewards_pun_recipie_65e4b6_idx'),
        ),
        migrations.AddIndex(
            model_name='rewardrecord',
            index=models.Index(fields=['recipient_name', 'approval_year'], name='rewards_pun_recipie_7ea9a4_idx'),
        ),
        migrations.AddIndex(
            model_name='rewardrecord',
            index=models.Index(fields=['import_file', 'recipient_type'], name='rewards_pun_import__0215b0_idx'),
        ),
        migrations.AddConstraint(
            model_name='rewardrecord',
            constraint=models.UniqueConstraint(fields=('import_file', 'source_sheet', 'source_row'), name='reward_import_source_row_unique'),
        ),
    ]
