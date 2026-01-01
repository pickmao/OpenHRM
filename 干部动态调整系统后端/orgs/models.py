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

    def get_ancestors(self):
        """获取所有上级单位"""
        ancestors = []
        parent = self.parent
        while parent:
            ancestors.append(parent)
            parent = parent.parent
        return ancestors

    def get_descendants(self):
        """获取所有下级单位"""
        descendants = []
        children = self.children.all()
        for child in children:
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants


class Membership(models.Model):
    """部门成员关系：支持一人多部门、主部门、职务等"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='memberships',
        verbose_name='用户'
    )
    unit = models.ForeignKey(
        OrgUnit,
        on_delete=models.CASCADE,
        related_name='memberships',
        verbose_name='所属部门'
    )
    is_primary = models.BooleanField('是否主部门', default=True)
    position = models.CharField('职务', max_length=100, blank=True, null=True)
    is_manager = models.BooleanField('是否部门负责人', default=False)
    effective_from = models.DateField('生效日期', null=True, blank=True)
    effective_to = models.DateField('失效日期', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_memberships',
        verbose_name='创建人'
    )

    class Meta:
        verbose_name = '部门成员'
        verbose_name_plural = '部门成员'
        ordering = ['-is_primary', '-is_manager', 'user__username']
        indexes = [
            models.Index(fields=['user', 'unit']),
            models.Index(fields=['unit', 'is_primary']),
            models.Index(fields=['is_manager']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'unit'],
                condition=models.Q(effective_to__isnull=True),
                name='unique_active_membership'
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.unit.name}"

    def is_active(self):
        """判断成员关系是否有效"""
        from django.utils import timezone
        today = timezone.now().date()
        if self.effective_from and self.effective_from > today:
            return False
        if self.effective_to and self.effective_to < today:
            return False
        return True
