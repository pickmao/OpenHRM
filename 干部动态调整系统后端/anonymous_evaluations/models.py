import re
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


DIMENSION_KEY_RE = re.compile(r'^[a-z][a-z0-9_]{0,49}$')


def default_dimensions():
    return [
        {'key': 'political_quality', 'label': '政治素质', 'weight': 1},
        {'key': 'performance', 'label': '履职能力', 'weight': 1},
        {'key': 'responsibility', 'label': '担当作为', 'weight': 1},
        {'key': 'collaboration', 'label': '协作作风', 'weight': 1},
        {'key': 'integrity', 'label': '廉洁自律', 'weight': 1},
    ]


def validate_dimensions(value):
    if not isinstance(value, list) or not 1 <= len(value) <= 10:
        raise ValidationError('评价维度必须为 1 至 10 项。')
    keys = set()
    for item in value:
        if not isinstance(item, dict):
            raise ValidationError('评价维度格式不正确。')
        key = str(item.get('key', ''))
        label = str(item.get('label', '')).strip()
        weight = item.get('weight', 1)
        if not DIMENSION_KEY_RE.fullmatch(key):
            raise ValidationError('评价维度编码只能使用小写字母、数字和下划线。')
        if key in keys or not label or len(label) > 30:
            raise ValidationError('评价维度名称不能为空、不能重复且最多 30 个字。')
        if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not 0 < weight <= 100:
            raise ValidationError('评价维度权重必须大于 0 且不超过 100。')
        keys.add(key)


class CampaignStatus(models.TextChoices):
    DRAFT = 'DRAFT', '草稿'
    PUBLISHED = 'PUBLISHED', '填写中'
    CLOSED = 'CLOSED', '已关闭'


class EvaluationCampaign(models.Model):
    """一次匿名民主测评活动；活动发布后只允许关闭，不修改范围和题目。"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('活动名称', max_length=200)
    description = models.TextField('活动说明', blank=True)
    status = models.CharField('状态', max_length=20, choices=CampaignStatus.choices, default=CampaignStatus.DRAFT, db_index=True)
    dimensions_json = models.JSONField('评价维度', default=default_dimensions, validators=[validate_dimensions])
    min_valid_responses = models.PositiveSmallIntegerField('最小有效样本数', default=8, validators=[MinValueValidator(2)])
    starts_at = models.DateTimeField('开始时间', null=True, blank=True)
    deadline_at = models.DateTimeField('截止时间')
    published_at = models.DateTimeField('发布时间', null=True, blank=True)
    closed_at = models.DateTimeField('关闭时间', null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_anonymous_evaluation_campaigns', verbose_name='创建人',
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '匿名测评活动'
        verbose_name_plural = '匿名测评活动'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['status', 'deadline_at'])]

    def clean(self):
        validate_dimensions(self.dimensions_json)
        if self.starts_at and self.deadline_at and self.starts_at >= self.deadline_at:
            raise ValidationError({'deadline_at': '截止时间必须晚于开始时间。'})

    def is_open(self):
        now = timezone.now()
        return self.status == CampaignStatus.PUBLISHED and (not self.starts_at or self.starts_at <= now) and now <= self.deadline_at

    def __str__(self):
        return self.name


class EvaluationTarget(models.Model):
    """活动内被评价对象的发布快照。"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(EvaluationCampaign, on_delete=models.CASCADE, related_name='targets')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='anonymous_evaluation_targets')
    target_name_snapshot = models.CharField('评价对象姓名快照', max_length=100)
    org_name_snapshot = models.CharField('组织名称快照', max_length=100, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '匿名测评对象'
        verbose_name_plural = '匿名测评对象'
        constraints = [models.UniqueConstraint(fields=['campaign', 'user'], name='unique_evaluation_target_per_campaign')]

    def __str__(self):
        return f'{self.campaign.name} - {self.target_name_snapshot}'


class EvaluationEligibility(models.Model):
    """资格账本只用于一次性提交校验，绝不连接至匿名答案。"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(EvaluationCampaign, on_delete=models.CASCADE, related_name='eligibilities')
    target = models.ForeignKey(EvaluationTarget, on_delete=models.CASCADE, related_name='eligibilities')
    evaluator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='anonymous_evaluation_eligibilities')
    submitted = models.BooleanField('是否已提交', default=False, db_index=True)
    submitted_on = models.DateField('提交日期', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '匿名测评资格'
        verbose_name_plural = '匿名测评资格'
        constraints = [models.UniqueConstraint(fields=['target', 'evaluator'], name='unique_evaluation_eligibility')]
        indexes = [models.Index(fields=['campaign', 'evaluator', 'submitted'])]


class EvaluationResponse(models.Model):
    """匿名答卷没有填写人、资格或 IP 字段，且不提供逐份读取接口。"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    anonymous_token = models.UUIDField('匿名令牌', default=uuid.uuid4, unique=True, editable=False)
    campaign = models.ForeignKey(EvaluationCampaign, on_delete=models.CASCADE, related_name='responses')
    target = models.ForeignKey(EvaluationTarget, on_delete=models.CASCADE, related_name='responses')
    scores_json = models.JSONField('评分数据', default=dict)
    comment = models.TextField('具体建议', blank=True)
    submitted_on = models.DateField('提交日期', default=timezone.localdate)

    class Meta:
        verbose_name = '匿名测评答卷'
        verbose_name_plural = '匿名测评答卷'
        indexes = [models.Index(fields=['campaign', 'target'])]
