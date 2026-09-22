import uuid

from django.conf import settings
from django.db import models, transaction


class RewardRecipientType(models.TextChoices):
    INDIVIDUAL = 'INDIVIDUAL', '个人奖励'
    COLLECTIVE = 'COLLECTIVE', '集体奖励'


class RewardImportFile(models.Model):
    """奖励汇总原始文件及其导入结果。"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file_name = models.CharField(max_length=255, db_index=True)
    source_file = models.FileField(upload_to='rewards/source/', null=True, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='uploaded_reward_files',
    )
    upload_time = models.DateTimeField(auto_now_add=True)
    total_records = models.PositiveIntegerField(default=0)
    record_counts = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-upload_time']

    def __str__(self):
        return self.file_name

    def delete(self, *args, **kwargs):
        storage = self.source_file.storage if self.source_file else None
        source_name = self.source_file.name if self.source_file else ''
        result = super().delete(*args, **kwargs)
        if storage and source_name:
            transaction.on_commit(lambda: storage.delete(source_name))
        return result


class RewardRecord(models.Model):
    """一条个人或集体奖励记录。"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    import_file = models.ForeignKey(
        RewardImportFile,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='records',
    )
    recipient_type = models.CharField(
        max_length=16,
        choices=RewardRecipientType.choices,
        default=RewardRecipientType.INDIVIDUAL,
        db_index=True,
    )
    recipient_name = models.CharField(max_length=200, db_index=True)
    award_level = models.CharField(max_length=100, blank=True, db_index=True)
    approval_year = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)
    award_content = models.TextField(blank=True)
    approval_date = models.DateField(null=True, blank=True, db_index=True)
    document_number = models.CharField(max_length=200, blank=True, db_index=True)
    remark = models.TextField(blank=True)
    source_sheet = models.CharField(max_length=100, blank=True)
    source_row = models.PositiveIntegerField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_reward_records',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-approval_year', 'recipient_type', 'recipient_name', '-approval_date']
        indexes = [
            models.Index(fields=['recipient_type', 'approval_year']),
            models.Index(fields=['recipient_name', 'approval_year']),
            models.Index(fields=['import_file', 'recipient_type']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['import_file', 'source_sheet', 'source_row'],
                name='reward_import_source_row_unique',
            ),
        ]

    def __str__(self):
        return f'{self.get_recipient_type_display()}：{self.recipient_name} - {self.award_content}'
