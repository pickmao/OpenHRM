import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """扩展用户模型"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    real_name = models.CharField('真实姓名', max_length=50)
    phone = models.CharField('手机号', max_length=20, blank=True, null=True)
    last_login_ip = models.GenericIPAddressField('最后登录IP', null=True, blank=True)
    profile_cadre = models.OneToOneField(
        'cadres.Cadre',
        on_delete=models.PROTECT,
        related_name='user_profile',
        null=True,
        blank=True,
        verbose_name='关联干部档案'
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.real_name} ({self.username})"


class Role(models.Model):
    """角色模型"""
    SUPER_ADMIN = 'SUPER_ADMIN'
    POLITICAL_OFFICE_ADMIN = 'POLITICAL_OFFICE_ADMIN'
    DEPT_MANAGER = 'DEPT_MANAGER'
    ANALYST = 'ANALYST'
    CADRE_SELF = 'CADRE_SELF'

    ROLE_CHOICES = [
        (SUPER_ADMIN, '系统超级管理员'),
        (POLITICAL_OFFICE_ADMIN, '政治处管理员'),
        (DEPT_MANAGER, '部门/支部负责人'),
        (ANALYST, '研判/统计人员'),
        (CADRE_SELF, '本人账号'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField('角色代码', max_length=50, unique=True, choices=ROLE_CHOICES)
    name = models.CharField('角色名称', max_length=50)
    description = models.TextField('角色描述', blank=True)
    is_active = models.BooleanField('启用', default=True)
    permissions = models.JSONField('权限点', default=list, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '角色'
        verbose_name_plural = '角色'
        ordering = ['code']

    def __str__(self):
        return self.name


class UserRole(models.Model):
    """用户角色关联"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_users')
    assigned_at = models.DateTimeField('分配时间', auto_now_add=True)
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='assigned_roles',
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = '用户角色'
        verbose_name_plural = '用户角色'
        unique_together = ['user', 'role']

    def __str__(self):
        return f"{self.user.real_name} - {self.role.name}"


class ScopeType(models.TextChoices):
    ALL = 'ALL', '全部'
    ORG_UNIT = 'ORG_UNIT', '组织单元'
    SELF = 'SELF', '本人'


class DataScope(models.Model):
    """数据范围"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='data_scope')
    scope_type = models.CharField(
        '范围类型',
        max_length=20,
        choices=ScopeType.choices,
        default=ScopeType.SELF
    )
    org_units = models.ManyToManyField(
        'orgs.OrgUnit',
        related_name='data_scopes',
        blank=True,
        verbose_name='可访问的组织单元'
    )
    note = models.CharField('备注', max_length=200, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '数据范围'
        verbose_name_plural = '数据范围'

    def __str__(self):
        return f"{self.user.real_name} - {self.get_scope_type_display()}"
