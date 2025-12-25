import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from orgs.models import OrgUnit
from cadres.models import Cadre


User = get_user_model()


class RoleInUnit(models.TextChoices):
    SECRETARY = 'SECRETARY', '书记'
    COMMITTEE_MEMBER = 'COMMITTEE_MEMBER', '委员'
    MEMBER = 'MEMBER', '成员'
    LEADER = 'LEADER', '负责人'
    DEPUTY = 'DEPUTY', '副职'
    OTHER = 'OTHER', '其他'


class MembershipStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', '在职'
    INACTIVE = 'INACTIVE', '离职'


class PlanStatus(models.TextChoices):
    DRAFT = 'DRAFT', '草案'
    SUBMITTED = 'SUBMITTED', '已提交'
    APPROVED = 'APPROVED', '已批准'
    APPLIED = 'APPLIED', '已生效'
    REJECTED = 'REJECTED', '已拒绝'
    CANCELED = 'CANCELED', '已取消'


class MoveType(models.TextChoices):
    ASSIGN = 'ASSIGN', '分配'
    REMOVE = 'REMOVE', '移除'
    TRANSFER = 'TRANSFER', '调动'


class OrgMembership(models.Model):
    """干部当前归属/任职到支部"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cadre = models.ForeignKey(
        Cadre,
        on_delete=models.CASCADE,
        related_name='memberships',
        verbose_name='干部'
    )
    org_unit = models.ForeignKey(
        OrgUnit,
        on_delete=models.PROTECT,
        related_name='members',
        verbose_name='组织单位'
    )
    role_in_unit = models.CharField(
        '单位内角色',
        max_length=20,
        choices=RoleInUnit.choices,
        default=RoleInUnit.MEMBER
    )
    is_primary = models.BooleanField('是否主归属', default=True, db_index=True)
    start_date = models.DateField('生效日期')
    end_date = models.DateField('结束日期', null=True, blank=True)
    status = models.CharField(
        '状态',
        max_length=20,
        choices=MembershipStatus.choices,
        default=MembershipStatus.ACTIVE,
        db_index=True
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '组织归属'
        verbose_name_plural = '组织归属'
        ordering = ['-status', '-start_date']
        indexes = [
            models.Index(fields=['org_unit', 'status']),
            models.Index(fields=['cadre', 'status']),
            models.Index(fields=['org_unit', 'is_primary', 'status']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['cadre'],
                condition=models.Q(status='ACTIVE', is_primary=True),
                name='unique_primary_active_membership'
            )
        ]

    def __str__(self):
        return f"{self.cadre.name} - {self.org_unit.name}"

    def clean(self):
        """业务校验：同一干部只能有一个 primary active 归属"""
        if self.is_primary and self.status == MembershipStatus.ACTIVE:
            existing = OrgMembership.objects.filter(
                cadre=self.cadre,
                is_primary=True,
                status=MembershipStatus.ACTIVE
            ).exclude(pk=self.pk)

            if existing.exists():
                raise ValidationError('一个干部只能有一个主归属关系')


class StaffingPlan(models.Model):
    """人事调整方案/草案"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField('方案标题', max_length=200)
    description = models.TextField('方案描述', blank=True)
    status = models.CharField(
        '状态',
        max_length=20,
        choices=PlanStatus.choices,
        default=PlanStatus.DRAFT,
        db_index=True
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='created_plans',
        verbose_name='创建人'
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='approved_plans',
        verbose_name='批准人',
        null=True,
        blank=True
    )
    approved_at = models.DateTimeField('批准时间', null=True, blank=True)
    applied_at = models.DateTimeField('生效时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '人事调整方案'
        verbose_name_plural = '人事调整方案'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"


class StaffingPlanMove(models.Model):
    """拖拽动作明细"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(
        StaffingPlan,
        on_delete=models.CASCADE,
        related_name='moves',
        verbose_name='调整方案'
    )
    cadre = models.ForeignKey(
        Cadre,
        on_delete=models.PROTECT,
        related_name='plan_moves',
        verbose_name='干部'
    )
    from_unit = models.ForeignKey(
        OrgUnit,
        on_delete=models.PROTECT,
        related_name='moves_from',
        verbose_name='原单位',
        null=True,
        blank=True
    )
    to_unit = models.ForeignKey(
        OrgUnit,
        on_delete=models.PROTECT,
        related_name='moves_to',
        verbose_name='目标单位',
        null=True,
        blank=True
    )
    move_type = models.CharField(
        '调整类型',
        max_length=20,
        choices=MoveType.choices,
        default=MoveType.TRANSFER
    )
    reason = models.CharField('调整原因', max_length=200, blank=True)
    risk_snapshot = models.JSONField('风险快照', default=dict, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='created_moves',
        verbose_name='创建人'
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '调整明细'
        verbose_name_plural = '调整明细'
        ordering = ['plan', '-created_at']
        indexes = [
            models.Index(fields=['plan', '-created_at']),
            models.Index(fields=['to_unit', '-created_at']),
            models.Index(fields=['cadre', 'plan']),
        ]

    def __str__(self):
        action = f"从 {self.from_unit.name} 调到 {self.to_unit.name}" if self.from_unit and self.to_unit else \
                 f"分配到 {self.to_unit.name}" if self.to_unit else \
                 f"从 {self.from_unit.name} 移除" if self.from_unit else "未知操作"
        return f"{self.cadre.name} - {action}"
