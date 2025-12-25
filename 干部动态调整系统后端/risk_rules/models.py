import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from cadres.models import Cadre


User = get_user_model()


class RiskTagType(models.TextChoices):
    B_KEY_PERSON = 'B_KEY_PERSON', 'B库重点人员'
    RELATIONSHIP_BAD = 'RELATIONSHIP_BAD', '关系复杂'
    SENSITIVE = 'SENSITIVE', '敏感人员'
    OTHER = 'OTHER', '其他'


class RiskLevel(models.TextChoices):
    LOW = 'LOW', '低'
    MEDIUM = 'MEDIUM', '中'
    HIGH = 'HIGH', '高'


class ConflictType(models.TextChoices):
    WORK_CONFLICT = 'WORK_CONFLICT', '工作矛盾'
    PERSONAL_CONFLICT = 'PERSONAL_CONFLICT', '个人矛盾'
    OTHER = 'OTHER', '其他'


class RiskPersonTag(models.Model):
    """B库：重点敏感人员库"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cadre = models.OneToOneField(
        Cadre,
        on_delete=models.CASCADE,
        related_name='risk_tag',
        verbose_name='干部'
    )
    tag_type = models.CharField(
        '标签类型',
        max_length=20,
        choices=RiskTagType.choices,
        default=RiskTagType.OTHER,
        db_index=True
    )
    risk_level = models.CharField(
        '风险等级',
        max_length=10,
        choices=RiskLevel.choices,
        default=RiskLevel.LOW,
        db_index=True
    )
    reason = models.TextField('原因', blank=True)
    is_active = models.BooleanField('启用', default=True, db_index=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='created_risk_tags',
        verbose_name='创建人',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '风险人员标签'
        verbose_name_plural = '风险人员标签'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tag_type', 'is_active']),
            models.Index(fields=['risk_level', 'is_active']),
        ]

    def __str__(self):
        return f"{self.cadre.name} - {self.get_tag_type_display()} ({self.get_risk_level_display()})"


class ConflictPair(models.Model):
    """A库：矛盾关系对照表"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cadre_a = models.ForeignKey(
        Cadre,
        on_delete=models.CASCADE,
        related_name='conflicts_as_a',
        verbose_name='干部A'
    )
    cadre_b = models.ForeignKey(
        Cadre,
        on_delete=models.CASCADE,
        related_name='conflicts_as_b',
        verbose_name='干部B'
    )
    conflict_type = models.CharField(
        '矛盾类型',
        max_length=20,
        choices=ConflictType.choices,
        default=ConflictType.OTHER
    )
    severity = models.CharField(
        '严重程度',
        max_length=10,
        choices=RiskLevel.choices,
        default=RiskLevel.LOW,
        db_index=True
    )
    note = models.TextField('备注', blank=True)
    is_active = models.BooleanField('启用', default=True, db_index=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='created_conflicts',
        verbose_name='创建人',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '矛盾关系对'
        verbose_name_plural = '矛盾关系对'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['cadre_a', 'is_active']),
            models.Index(fields=['cadre_b', 'is_active']),
            models.Index(fields=['severity', 'is_active']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['cadre_a', 'cadre_b'], name='unique_cadre_pair')
        ]

    def __str__(self):
        return f"{self.cadre_a.name} - {self.cadre_b.name} ({self.get_conflict_type_display()})"

    def clean(self):
        """验证规则"""
        if self.cadre_a == self.cadre_b:
            raise ValidationError('不能将干部与自身建立矛盾关系')

    def save(self, *args, **kwargs):
        """保存前强制排序，保证对称唯一"""
        self.full_clean()

        # 确保 cadre_a 的 ID 始终小于 cadre_b 的 ID
        if self.cadre_a.id > self.cadre_b.id:
            self.cadre_a, self.cadre_b = self.cadre_b, self.cadre_a

        super().save(*args, **kwargs)
