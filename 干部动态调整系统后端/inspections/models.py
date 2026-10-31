import uuid
from django.conf import settings
from django.db import models


class WorkRecord(models.Model):
    class Category(models.TextChoices):
        CHALLENGING = 'CHALLENGING', '急难险重任务'
        OUTSTANDING = 'OUTSTANDING', '突出任务'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='work_records')
    title = models.CharField('任务名称', max_length=200)
    category = models.CharField('任务类型', max_length=20, choices=Category.choices)
    completed_on = models.DateField('完成日期')
    role = models.CharField('承担角色', max_length=100, blank=True)
    details = models.TextField('具体任务及作用发挥')
    outcome = models.TextField('完成成效', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-completed_on', '-created_at']
        verbose_name = '知事识人纪实'
        verbose_name_plural = verbose_name
