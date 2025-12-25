import uuid
from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()


class UnitType(models.TextChoices):
    BRANCH = 'BRANCH', '支部'
    DEPARTMENT = 'DEPARTMENT', '部门'
    TEAM = 'TEAM', '团队'
    DIVISION = 'DIVISION', '处室'
    OFFICE = 'OFFICE', '办公室'


class OrgUnit(models.Model):
    """组织单元：支部/部门/岗位容器"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('名称', max_length=100)
    code = models.CharField('组织编码', max_length=50, unique=True, blank=True, null=True)
    unit_type = models.CharField(
        '单位类型',
        max_length=20,
        choices=UnitType.choices,
        default=UnitType.BRANCH,
        db_index=True
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='上级单位'
    )
    sort_order = models.IntegerField('排序', default=0)
    is_active = models.BooleanField('启用', default=True, db_index=True)
    metrics_snapshot = models.JSONField('指标快照', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '组织单元'
        verbose_name_plural = '组织单元'
        ordering = ['unit_type', 'sort_order', 'name']
        indexes = [
            models.Index(fields=['unit_type', 'is_active']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['code'], condition=models.Q(code__isnull=False), name='unique_org_unit_code')
        ]

    def __str__(self):
        return f"{self.get_unit_type_display()}: {self.name}"
