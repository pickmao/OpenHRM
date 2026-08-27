import uuid
from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()


class AuditAction(models.TextChoices):
    CREATE_PLAN = 'CREATE_PLAN', '创建调整方案'
    ADD_MOVE = 'ADD_MOVE', '添加调整明细'
    VALIDATE_PLAN = 'VALIDATE_PLAN', '验证调整方案'
    SUBMIT_PLAN = 'SUBMIT_PLAN', '提交调整方案'
    APPROVE_PLAN = 'APPROVE_PLAN', '批准调整方案'
    APPLY_PLAN = 'APPLY_PLAN', '生效调整方案'
    UPDATE_CADRE = 'UPDATE_CADRE', '更新干部信息'
    CREATE_CADRE = 'CREATE_CADRE', '创建干部'
    DELETE_CADRE = 'DELETE_CADRE', '删除干部'
    UPDATE_ORG = 'UPDATE_ORG', '更新组织信息'
    CREATE_ORG = 'CREATE_ORG', '创建组织'
    DELETE_ORG = 'DELETE_ORG', '删除组织'
    IMPORT_DATA = 'IMPORT_DATA', '导入数据'
    EXPORT_DATA = 'EXPORT_DATA', '导出数据'
    LOGIN = 'LOGIN', '登录'
    LOGOUT = 'LOGOUT', '登出'
    UPDATE_RISK_TAG = 'UPDATE_RISK_TAG', '更新风险标签'
    CREATE_CONFLICT = 'CREATE_CONFLICT', '创建矛盾关系'
    UPDATE_CONFLICT = 'UPDATE_CONFLICT', '更新矛盾关系'
    DELETE_CONFLICT = 'DELETE_CONFLICT', '删除矛盾关系'
    OTHER = 'OTHER', '其他操作'


class AuditLog(models.Model):
    """审计日志"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='audit_logs',
        verbose_name='操作人',
        null=True,
        blank=True
    )
    action = models.CharField(
        '操作类型',
        max_length=30,
        choices=AuditAction.choices,
        default=AuditAction.OTHER,
        db_index=True
    )
    target_type = models.CharField(
        '目标类型',
        max_length=50,
        blank=True,
        db_index=True
    )
    target_id = models.UUIDField(
        '目标ID',
        null=True,
        blank=True,
        db_index=True
    )
    context = models.JSONField(
        '上下文信息',
        default=dict,
        blank=True,
        help_text='记录操作前后的数据变化、客户端信息等'
    )
    ip_address = models.GenericIPAddressField(
        'IP地址',
        null=True,
        blank=True
    )
    user_agent = models.TextField(
        '用户代理',
        blank=True,
        help_text='浏览器或客户端信息'
    )
    created_at = models.DateTimeField(
        '操作时间',
        auto_now_add=True,
        db_index=True
    )

    class Meta:
        verbose_name = '审计日志'
        verbose_name_plural = '审计日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['action', '-created_at']),
            models.Index(fields=['target_type', 'target_id']),
            models.Index(fields=['actor', '-created_at']),
        ]

    def __str__(self):
        actor_name = self.actor.username if self.actor else '未知用户'
        return f"{actor_name} - {self.get_action_display()} - {self.created_at}"
