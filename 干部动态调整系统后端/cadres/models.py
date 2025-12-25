import uuid
from django.db import models
from django.contrib.auth import get_user_model
from orgs.models import OrgUnit


User = get_user_model()


class Gender(models.TextChoices):
    MALE = 'M', '男'
    FEMALE = 'F', '女'
    UNKNOWN = 'U', '未知'


class EducationLevel(models.TextChoices):
    MIDDLE_SCHOOL = 'MIDDLE', '中专'
    COLLEGE = 'COLLEGE', '大专'
    BACHELOR = 'BACHELOR', '本科'
    MASTER = 'MASTER', '硕士'
    DOCTOR = 'DOCTOR', '博士'
    OTHER = 'OTHER', '其他'


class CadreStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', '在职'
    TRANSFERRED = 'TRANSFERRED', '调离'
    RETIRED = 'RETIRED', '退休'
    RESIGNED = 'RESIGNED', '离职'
    SUSPENDED = 'SUSPENDED', '停职'


class Cadre(models.Model):
    """干部主档"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cadre_code = models.CharField('干部编号', max_length=50, unique=True, db_index=True)
    name = models.CharField('姓名', max_length=50, db_index=True)
    gender = models.CharField('性别', max_length=1, choices=Gender.choices, default=Gender.UNKNOWN)
    birth_date = models.DateField('出生日期', null=True, blank=True)
    native_place = models.CharField('籍贯', max_length=100, blank=True)
    ethnicity = models.CharField('民族', max_length=20, blank=True)
    political_status = models.CharField('政治面貌', max_length=50, blank=True)
    education_level = models.CharField(
        '学历层次',
        max_length=20,
        choices=EducationLevel.choices,
        blank=True,
        db_index=True
    )
    degree = models.CharField('学位', max_length=50, blank=True)
    join_work_date = models.DateField('参加工作时间', null=True, blank=True)
    hire_date = models.DateField('入职时间', null=True, blank=True)
    current_position = models.CharField('现任职务', max_length=100, blank=True)
    current_rank = models.CharField('现任职级', max_length=100, blank=True)
    position_start_date = models.DateField('任现职时间', null=True, blank=True)
    status = models.CharField(
        '状态',
        max_length=20,
        choices=CadreStatus.choices,
        default=CadreStatus.ACTIVE,
        db_index=True
    )
    tags = models.JSONField('标签', default=dict, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '干部'
        verbose_name_plural = '干部'
        ordering = ['status', '-position_start_date', 'name']
        indexes = [
            models.Index(fields=['status', 'education_level']),
            models.Index(fields=['position_start_date']),
        ]

    def __str__(self):
        return f"{self.name} ({self.cadre_code})"

    @property
    def age(self):
        """计算年龄"""
        from datetime import date
        if self.birth_date:
            today = date.today()
            return today.year - self.birth_date.year - (
                (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
            )
        return None


class CadreResume(models.Model):
    """干部履历"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cadre = models.ForeignKey(
        Cadre,
        on_delete=models.CASCADE,
        related_name='resumes',
        verbose_name='干部'
    )
    org_unit = models.ForeignKey(
        OrgUnit,
        on_delete=models.PROTECT,
        related_name='cadre_resumes',
        verbose_name='工作单位',
        null=True,
        blank=True
    )
    position_title = models.CharField('岗位职务', max_length=100)
    start_date = models.DateField('开始时间')
    end_date = models.DateField('结束时间', null=True, blank=True)
    remark = models.TextField('备注', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '干部履历'
        verbose_name_plural = '干部履历'
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['cadre', '-start_date']),
        ]

    def __str__(self):
        return f"{self.cadre.name} - {self.position_title} ({self.start_date} - {self.end_date or '至今'})"
