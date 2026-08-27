import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class FormTaskStatus(models.TextChoices):
    PENDING = 'PENDING', '待填报'
    DRAFT = 'DRAFT', '草稿'
    SUBMITTED = 'SUBMITTED', '已提交'
    RETURNED = 'RETURNED', '退回修改'
    OVERDUE = 'OVERDUE', '逾期未交'
    CLOSED = 'CLOSED', '已关闭'


class DispatchBatchStatus(models.TextChoices):
    DRAFT = 'DRAFT', '草稿'
    PUBLISHED = 'PUBLISHED', '已发布'
    CLOSED = 'CLOSED', '已关闭'


class ReceiverType(models.TextChoices):
    USER = 'USER', '指定用户'
    ORG_UNIT = 'ORG_UNIT', '指定单位'
    ORG_ROLE = 'ORG_ROLE', '单位角色'


class TargetType(models.TextChoices):
    USER = 'USER', '个人'
    ORG_UNIT = 'ORG_UNIT', '单位'


class TaskAuditAction(models.TextChoices):
    DISPATCH = 'DISPATCH', '下发任务'
    REASSIGN = 'REASSIGN', '改派任务'
    SAVE_DRAFT = 'SAVE_DRAFT', '保存草稿'
    SUBMIT = 'SUBMIT', '提交任务'
    RETURN = 'RETURN', '退回修改'
    CLOSE = 'CLOSE', '关闭任务'
    REOPEN = 'REOPEN', '重新打开'
    DELETE = 'DELETE', '删除任务'


class FormTemplate(models.Model):
    """一个可复用的 Excel/OnlyOffice 表单定义。"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField('模板编码', max_length=50, unique=True, db_index=True)
    name = models.CharField('模板名称', max_length=200)
    version = models.CharField('版本号', max_length=20, default='1.0')
    description = models.TextField('说明', blank=True)
    schema_json = models.JSONField('表单结构定义', default=dict, blank=True)
    scoring_rule_json = models.JSONField('评分规则', null=True, blank=True)
    source_file = models.FileField('原始 Excel 文件', upload_to='forms/templates/', blank=True, null=True)
    source_file_name = models.CharField('原始文件名', max_length=255, blank=True)
    is_active = models.BooleanField('是否启用', default=True, db_index=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_form_templates',
        verbose_name='创建人',
    )

    class Meta:
        verbose_name = '表单模板'
        verbose_name_plural = '表单模板'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code', 'version']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f'{self.code} v{self.version} - {self.name}'


class DispatchBatch(models.Model):
    """一次表格下发操作。"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cycle_id = models.CharField('考核周期', max_length=50, blank=True, default='', db_index=True)
    stage_code = models.CharField('阶段编码', max_length=50, blank=True, default='')
    name = models.CharField('下发批次名称', max_length=200)
    status = models.CharField(
        '状态', max_length=20, choices=DispatchBatchStatus.choices,
        default=DispatchBatchStatus.DRAFT, db_index=True,
    )
    # 历史生产库将截止时间设为必填；下发流程也要求填写，保持模型与既有数据约束一致。
    deadline_at = models.DateTimeField('截止时间')
    published_at = models.DateTimeField('发布时间', null=True, blank=True)
    closed_at = models.DateTimeField('关闭时间', null=True, blank=True)
    stats_total = models.IntegerField('应填总数', default=0)
    stats_submitted = models.IntegerField('已提交总数', default=0)
    stats_overdue = models.IntegerField('逾期总数', default=0)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_dispatch_batches',
        verbose_name='创建人',
    )

    class Meta:
        verbose_name = '下发批次'
        verbose_name_plural = '下发批次'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['cycle_id', 'stage_code']), models.Index(fields=['status'])]

    def __str__(self):
        return self.name

    def refresh_stats(self):
        tasks = self.tasks.all()
        self.stats_total = tasks.count()
        self.stats_submitted = tasks.filter(status=FormTaskStatus.SUBMITTED).count()
        self.stats_overdue = sum(task.is_overdue() for task in tasks.exclude(status=FormTaskStatus.SUBMITTED))
        self.save(update_fields=['stats_total', 'stats_submitted', 'stats_overdue', 'updated_at'])


class DispatchRule(models.Model):
    """保留批次的接收人选择规则，便于回溯。"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(DispatchBatch, on_delete=models.CASCADE, related_name='rules')
    template = models.ForeignKey(FormTemplate, on_delete=models.PROTECT, related_name='dispatch_rules')
    receiver_type = models.CharField('接收人类型', max_length=20, choices=ReceiverType.choices)
    receiver_expr_json = models.JSONField('接收人条件', default=dict, blank=True)
    target_type = models.CharField('评价对象类型', max_length=20, choices=TargetType.choices, default=TargetType.USER)
    target_expr_json = models.JSONField('评价对象条件', default=dict, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_dispatch_rules', verbose_name='创建人',
    )

    class Meta:
        verbose_name = '下发规则'
        verbose_name_plural = '下发规则'


class FormTask(models.Model):
    """一个用户（或单位负责人）需要处理的填报任务。"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(DispatchBatch, on_delete=models.CASCADE, related_name='tasks')
    template = models.ForeignKey(FormTemplate, on_delete=models.PROTECT, related_name='tasks')
    template_version = models.CharField('模板版本快照', max_length=20, blank=True)
    assignee_type = models.CharField('填报人类型', max_length=20, choices=ReceiverType.choices, default=ReceiverType.USER)
    assignee_id = models.UUIDField('填报人或单位 ID', db_index=True)
    assignee_role_snapshot = models.CharField('填报人角色快照', max_length=100, blank=True)
    assignee_name_snapshot = models.CharField('填报人姓名快照', max_length=100, blank=True)
    org_unit_snapshot = models.ForeignKey(
        'orgs.OrgUnit', on_delete=models.SET_NULL, related_name='+', null=True, blank=True,
        verbose_name='所属单位快照',
    )
    # 保留历史数据结构；当前“Excel 下发”模式中与填报人相同，不在前端展示。
    target_type = models.CharField('评价对象类型', max_length=20, choices=TargetType.choices, default=TargetType.USER)
    target_id = models.UUIDField('评价对象 ID', null=True, blank=True)
    status = models.CharField(
        '状态', max_length=20, choices=FormTaskStatus.choices,
        default=FormTaskStatus.PENDING, db_index=True,
    )
    # 与历史生产表一致：每个下发任务均继承批次的必填截止时间。
    deadline_at = models.DateTimeField('截止时间', db_index=True)
    submitted_at = models.DateTimeField('提交时间', null=True, blank=True)
    closed_at = models.DateTimeField('关闭时间', null=True, blank=True)
    reassign_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reassigned_form_tasks', verbose_name='改派给',
    )
    reassign_reason = models.CharField('改派原因', max_length=200, blank=True)
    reassign_at = models.DateTimeField('改派时间', null=True, blank=True)
    reassign_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='form_tasks_reassigned_by', verbose_name='改派人',
    )
    context_json = models.JSONField('上下文信息', default=dict, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '填报任务'
        verbose_name_plural = '填报任务'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['batch', 'status']),
            models.Index(fields=['assignee_type', 'assignee_id']),
            models.Index(fields=['status', 'deadline_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['batch', 'template', 'assignee_type', 'assignee_id', 'target_type', 'target_id'],
                name='unique_form_task',
            )
        ]

    def __str__(self):
        return f'{self.assignee_name_snapshot or self.assignee_id} - {self.template.name}'

    def is_overdue(self):
        return bool(
            self.deadline_at
            and self.status not in {FormTaskStatus.SUBMITTED, FormTaskStatus.CLOSED}
            and timezone.now() > self.deadline_at
        )

    def can_submit(self, user):
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if self.reassign_to_id:
            return self.reassign_to_id == user.id
        if self.assignee_type == ReceiverType.USER:
            return self.assignee_id == user.id
        if self.assignee_type == ReceiverType.ORG_UNIT:
            from orgs.models import Membership
            return Membership.objects.filter(user=user, unit_id=self.assignee_id, is_manager=True).exists()
        return False


class FormSubmission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(FormTask, on_delete=models.CASCADE, related_name='submissions')
    version = models.IntegerField('版本号', validators=[MinValueValidator(1)], default=1)
    is_final = models.BooleanField('是否最终提交', default=False)
    payload_json = models.JSONField('表单数据', default=dict, blank=True)
    score_json = models.JSONField('评分数据', null=True, blank=True)
    attachments_json = models.JSONField('附件信息', default=list, blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='form_submissions', verbose_name='提交人',
    )
    submitted_at = models.DateTimeField('提交时间', null=True, blank=True)
    ip_address = models.GenericIPAddressField('IP 地址', null=True, blank=True)
    user_agent = models.TextField('用户代理', blank=True)
    return_reason = models.TextField('退回原因', blank=True)
    returned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='returned_form_submissions', verbose_name='退回人',
    )
    returned_at = models.DateTimeField('退回时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '提交版本'
        verbose_name_plural = '提交版本'
        ordering = ['-version']
        constraints = [models.UniqueConstraint(fields=['task', 'version'], name='unique_form_submission_version')]


class FormTaskAudit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(FormTask, on_delete=models.CASCADE, related_name='audits')
    action = models.CharField('操作', max_length=20, choices=TaskAuditAction.choices)
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    before_json = models.JSONField('操作前', default=dict, blank=True)
    after_json = models.JSONField('操作后', default=dict, blank=True)
    reason = models.TextField('原因', blank=True)
    ip_address = models.GenericIPAddressField('IP 地址', null=True, blank=True)
    user_agent = models.TextField('用户代理', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '任务审计日志'
        verbose_name_plural = '任务审计日志'
        ordering = ['-created_at']


class OnlyOfficeDocument(models.Model):
    """任务的独立副本，供 OnlyOffice 在线编辑和回调保存。"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # 以下字段来自故障前已部署的 OnlyOffice 文档表。保留映射以兼容已有记录，
    # 同时让新建文档满足旧表中仍然存在的非空约束。
    original_name = models.CharField('原始文件名', max_length=255)
    file_ext = models.CharField('文件扩展名', max_length=20, db_index=True)
    mime_type = models.CharField('MIME 类型', max_length=120, blank=True)
    file_size = models.BigIntegerField('文件大小', default=0)
    storage_path = models.CharField('存储路径', max_length=500)
    access_token = models.CharField('访问令牌', max_length=64, unique=True, db_index=True)
    last_callback_status = models.IntegerField('最近回调状态', null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='onlyoffice_documents',
        verbose_name='创建人',
    )
    task = models.OneToOneField(
        FormTask, on_delete=models.CASCADE, related_name='onlyoffice_document', null=True, blank=True
    )
    file = models.FileField('任务文档', upload_to='forms/tasks/', null=True, blank=True)
    file_name = models.CharField('文件名', max_length=255)
    document_key = models.CharField('OnlyOffice 文档键', max_length=128, unique=True, db_index=True, null=True, blank=True)
    version = models.PositiveIntegerField('版本', default=1)
    last_saved_at = models.DateTimeField('最后保存时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = 'OnlyOffice 文档'
        verbose_name_plural = 'OnlyOffice 文档'
