import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class CampaignStatus(models.TextChoices):
    DRAFT = 'DRAFT', '草稿'
    PUBLISHED = 'PUBLISHED', '填写中'
    CLOSED = 'CLOSED', '已关闭'


class TaskStatus(models.TextChoices):
    PENDING = 'PENDING', '待填报'
    DRAFT = 'DRAFT', '草稿'
    SUBMITTED = 'SUBMITTED', '已提交'
    RETURNED = 'RETURNED', '退回修改'


class FormType(models.TextChoices):
    ATTACHMENT_2 = 'ATTACHMENT_2', '附件2 近距离考察干部自评表'
    ATTACHMENT_3 = 'ATTACHMENT_3', '附件3 个人述事表'
    ATTACHMENT_4 = 'ATTACHMENT_4', '附件4 中层领导班子评价表'
    ATTACHMENT_5 = 'ATTACHMENT_5', '附件5 支部述事表'
    ATTACHMENT_6_1 = 'ATTACHMENT_6_1', '附件6-1 中层领导班子测评（书记评各支部）'
    ATTACHMENT_6_2 = 'ATTACHMENT_6_2', '附件6-2 中层领导班子测评（本支部民警职工）'
    ATTACHMENT_7_1 = 'ATTACHMENT_7_1', '附件7-1 中层领导干部测评（评正职）'
    ATTACHMENT_7_2 = 'ATTACHMENT_7_2', '附件7-2 中层领导干部测评（评副职）'
    ATTACHMENT_7_3 = 'ATTACHMENT_7_3', '附件7-3 中层领导干部测评（评团队负责人）'
    ATTACHMENT_7_4 = 'ATTACHMENT_7_4', '附件7-4 中层领导干部测评（本支部干部）'
    ATTACHMENT_1 = 'ATTACHMENT_1', '附件1 谈话研判测评表'


class FillerRole(models.TextChoices):
    MIDDLE_LEADER = 'MIDDLE_LEADER', '中层领导（含团队负责人）'
    BRANCH_LEADERSHIP = 'BRANCH_LEADERSHIP', '党支部班子'
    BRANCH_SECRETARY = 'BRANCH_SECRETARY', '党支部书记'
    BRANCH_DEPUTY_SECRETARY = 'BRANCH_DEPUTY_SECRETARY', '党支部副书记'
    BRANCH_COMMITTEE = 'BRANCH_COMMITTEE', '党支部支委'
    BRANCH_STAFF = 'BRANCH_STAFF', '本支部民警职工'
    POLITICAL_LEADER = 'POLITICAL_LEADER', '政工领导'
    POLITICAL_DIRECTOR = 'POLITICAL_DIRECTOR', '政治处主任'
    POLITICAL_EXECUTIVE_DEPUTY = 'POLITICAL_EXECUTIVE_DEPUTY', '政治处常务副主任'
    POLITICAL_DEPUTY = 'POLITICAL_DEPUTY', '政治处副主任'
    PRISON_LEADER = 'PRISON_LEADER', '其他监狱领导'
    PRINCIPAL_LEADER = 'PRINCIPAL_LEADER', '主要评价监狱领导'
    INSPECTION_TALKER = 'INSPECTION_TALKER', '谈话研判人员'
    MANUAL = 'MANUAL', '管理员指定'


class InspectionCampaign(models.Model):
    """一次知事识人考察填报批次。"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('批次名称', max_length=200)
    year = models.CharField('年度', max_length=20, blank=True)
    period_start = models.DateField('考察开始日期', null=True, blank=True)
    period_end = models.DateField('考察结束日期', null=True, blank=True)
    description = models.TextField('批次说明', blank=True)
    status = models.CharField(
        '状态', max_length=20, choices=CampaignStatus.choices,
        default=CampaignStatus.PUBLISHED, db_index=True,
    )
    form_types = models.JSONField('下发的表单类型', default=list)
    deadline_at = models.DateTimeField('截止时间')
    published_at = models.DateTimeField('发布时间', null=True, blank=True)
    closed_at = models.DateTimeField('关闭时间', null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_knowing_people_campaigns', verbose_name='创建人',
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '知事识人考察批次'
        verbose_name_plural = '知事识人考察批次'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['status', 'deadline_at'])]

    def is_open(self):
        now = timezone.now()
        return self.status == CampaignStatus.PUBLISHED and now <= self.deadline_at

    def __str__(self):
        return self.name


class InspectionTask(models.Model):
    """一名填报人在一次批次中的一张表。"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(InspectionCampaign, on_delete=models.CASCADE, related_name='tasks')
    form_type = models.CharField('表单类型', max_length=30, choices=FormType.choices, db_index=True)
    filler_role = models.CharField(
        '填报身份', max_length=30, choices=FillerRole.choices, default=FillerRole.MANUAL,
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='knowing_people_tasks', verbose_name='填报人',
    )
    branch = models.ForeignKey(
        'orgs.OrgUnit', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='knowing_people_tasks', verbose_name='所属支部',
    )
    roster = models.ForeignKey(
        'cadres.PersonnelRoster', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='knowing_people_tasks', verbose_name='花名册人员',
    )
    status = models.CharField(
        '状态', max_length=20, choices=TaskStatus.choices,
        default=TaskStatus.PENDING, db_index=True,
    )
    assignee_name_snapshot = models.CharField('填报人姓名快照', max_length=100)
    org_unit_name_snapshot = models.CharField('所属部门快照', max_length=100, blank=True)
    branch_name_snapshot = models.CharField('所属支部快照', max_length=100, blank=True)
    payload_json = models.JSONField('填报内容', default=dict, blank=True)
    context_json = models.JSONField('预填上下文', default=dict, blank=True)
    return_reason = models.TextField('退回原因', blank=True)
    returned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='returned_knowing_people_tasks', verbose_name='退回人',
    )
    returned_at = models.DateTimeField('退回时间', null=True, blank=True)
    remind_count = models.PositiveIntegerField('催办次数', default=0)
    reminded_at = models.DateTimeField('最近催办时间', null=True, blank=True)
    submitted_at = models.DateTimeField('提交时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '知事识人填报任务'
        verbose_name_plural = '知事识人填报任务'
        ordering = ['campaign', 'form_type', 'assignee_name_snapshot']
        constraints = [
            models.UniqueConstraint(
                fields=['campaign', 'form_type', 'assignee', 'branch'],
                condition=models.Q(branch__isnull=False),
                name='unique_kp_task_per_branch',
            ),
            models.UniqueConstraint(
                fields=['campaign', 'form_type', 'assignee'],
                condition=models.Q(branch__isnull=True),
                name='unique_kp_task_without_branch',
            ),
        ]
        indexes = [
            models.Index(fields=['campaign', 'status']),
            models.Index(fields=['assignee', 'status']),
            models.Index(fields=['form_type', 'status']),
        ]

    def __str__(self):
        return f'{self.campaign.name} - {self.get_form_type_display()} - {self.assignee_name_snapshot}'
