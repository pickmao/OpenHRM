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


class PoliticalStatus(models.TextChoices):
    CPC_MEMBER = '中共党员', '中共党员'
    CYL_MEMBER = '共青团员', '共青团员'
    DEMOCRATIC_PARTY = '民主党派', '民主党派'
    MASS = '群众', '群众'
    OTHER = '其他', '其他'


class PoliceRank(models.TextChoices):
    # 警督级别
    LEVEL_1_SUPERINTENDENT = '一级警督', '一级警督'
    LEVEL_2_SUPERINTENDENT = '二级警督', '二级警督'
    LEVEL_3_SUPERINTENDENT = '三级警督', '三级警督'
    # 警司级别
    LEVEL_1_INSPECTOR = '一级警司', '一级警司'
    LEVEL_2_INSPECTOR = '二级警司', '二级警司'
    LEVEL_3_INSPECTOR = '三级警司', '三级警司'
    # 警员级别
    LEVEL_1_OFFICER = '一级警员', '一级警员'
    LEVEL_2_OFFICER = '二级警员', '二级警员'
    LEVEL_3_OFFICER = '三级警员', '三级警员'
    LEVEL_4_OFFICER = '四级警员', '四级警员'


class JobLevel(models.TextChoices):
    # 警长序列
    LEVEL_1_SUPERINTENDENT = '一级警长', '一级警长'
    LEVEL_2_SUPERINTENDENT = '二级警长', '二级警长'
    LEVEL_3_SUPERINTENDENT = '三级警长', '三级警长'
    LEVEL_4_SUPERINTENDENT = '四级警长', '四级警长'


class Cadre(models.Model):
    """干部主档 - 简化版"""
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


class PersonnelRoster(models.Model):
    """花名册 - 完整版干部信息"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    serial_number = models.IntegerField('序号', db_index=True)

    # 基本信息
    name = models.CharField('姓名', max_length=50, db_index=True)
    department = models.CharField('部门', max_length=100, db_index=True)
    gender = models.CharField('性别', max_length=1, choices=Gender.choices)
    age = models.IntegerField('年龄', null=True, blank=True)
    birth_date = models.DateField('出生年月', null=True, blank=True)
    ethnicity = models.CharField('民族', max_length=20, blank=True)
    native_place = models.CharField('籍贯', max_length=100, blank=True)
    household_registration = models.CharField('户籍所在地', max_length=200, blank=True)

    # 工作信息
    working_years = models.IntegerField('工龄', null=True, blank=True)
    join_work_date = models.DateField('参加工作时间', null=True, blank=True)
    join_prison_date = models.DateField('参加监狱工作时间', null=True, blank=True)
    continuous_service_date = models.DateField('连续工龄计算时间', null=True, blank=True)
    has_2years_grassroots = models.CharField('是否有2年基层工作经历', max_length=10, blank=True)

    # 政治信息
    political_status = models.CharField('政治面貌', max_length=20, choices=PoliticalStatus.choices, blank=True)
    join_party_date = models.DateField('入党时间', null=True, blank=True)

    # 职务信息
    position = models.CharField('职务', max_length=100, blank=True)
    promotion_category = models.CharField('晋升四高及以上序列分类', max_length=50, blank=True)
    position_category = models.CharField('职务类别', max_length=50, blank=True)
    current_position_years = models.CharField('任现职年限', max_length=20, blank=True)
    current_position_date = models.DateField('任现职务时间', null=True, blank=True)
    position_level = models.CharField('职务级别', max_length=50, blank=True)
    position_rank = models.CharField('职务层次', max_length=50, blank=True)

    # 领导职务信息
    same_level_leadership_years = models.CharField('任同级领导职务年限', max_length=20, blank=True)
    same_level_leadership_date = models.DateField('任同级领导职务时间', null=True, blank=True)
    same_level_rank_years = models.CharField('任同级领导职务层次时间年限', max_length=20, blank=True)
    same_level_rank_date = models.DateField('任同级领导职务层次时间', null=True, blank=True)

    # 职级信息
    current_rank_years = models.CharField('任现职级年限', max_length=20, blank=True)
    current_rank_date = models.DateField('任现职级时间', null=True, blank=True)
    calculation_start_date = models.DateField('量化计分起算时间', null=True, blank=True)

    # 警员职级信息
    police_rank = models.CharField('现警员职级', max_length=20, choices=JobLevel.choices, blank=True)
    police_rank_start_date = models.DateField('任现警员职级起算时间', null=True, blank=True)
    first_set_rank = models.CharField('首套警员职级', max_length=20, blank=True)
    first_set_rank_date = models.DateField('首套警员职级起算时间', null=True, blank=True)
    first_promote_rank = models.CharField('首晋警员职级', max_length=20, blank=True)
    first_promote_rank_date = models.DateField('首晋警员职级起算时间', null=True, blank=True)

    # 分管工作
    work_charge = models.CharField('分管工作', max_length=200, blank=True)

    # 全日制教育信息
    fulltime_education = models.CharField('全日制教育学历', max_length=50, blank=True)
    fulltime_school = models.CharField('全日制毕业院校', max_length=100, blank=True)
    fulltime_major = models.CharField('全日制专业', max_length=100, blank=True)
    fulltime_degree = models.CharField('全日制学位', max_length=50, blank=True)
    fulltime_start_date = models.DateField('全日制入学时间', null=True, blank=True)
    fulltime_graduate_date = models.DateField('全日制毕业时间', null=True, blank=True)

    # 在职教育信息
    inservice_education = models.CharField('在职学历', max_length=50, blank=True)
    inservice_school = models.CharField('在职毕业院校', max_length=100, blank=True)
    inservice_form = models.CharField('学习形式', max_length=50, blank=True)
    inservice_major = models.CharField('在职专业', max_length=100, blank=True)
    inservice_degree = models.CharField('在职学位', max_length=50, blank=True)
    inservice_start_date = models.DateField('在职入学时间', null=True, blank=True)
    inservice_graduate_date = models.DateField('在职毕业时间', null=True, blank=True)

    # 警衔警号
    police_title = models.CharField('警衔', max_length=20, choices=PoliceRank.choices, blank=True)
    police_number = models.CharField('警号', max_length=20, unique=True, null=True, blank=True)

    # 专业资格
    profession_name = models.CharField('专业资格名称', max_length=100, blank=True)
    profession_level = models.CharField('专业资格级别', max_length=50, blank=True)
    technical_title = models.CharField('专业技术职务', max_length=100, blank=True)
    counseling_cert_level = models.CharField('心理咨询证书级别', max_length=50, blank=True)
    english_level = models.CharField('英语专业', max_length=50, blank=True)

    # 备注
    remark = models.TextField('备注', blank=True)
    quarterly_remark = models.CharField('季度报表备注', max_length=200, blank=True)

    # 部门工作信息
    dept_work_years = models.CharField('在本部门工作年限', max_length=20, blank=True)
    dept_work_date = models.DateField('本部门工作时间', null=True, blank=True)
    unit_work_years = models.CharField('在本单位年限', max_length=20, blank=True)
    enter_unit_date = models.DateField('进入本单位时间', null=True, blank=True)
    enter_unit_form = models.CharField('进入本单位形式', max_length=50, blank=True)
    identity_source = models.CharField('身份来源', max_length=50, blank=True)

    # 军转干/部队经历
    military_experience = models.CharField('军转干/部队经历', max_length=100, blank=True)

    # 最高学历信息
    highest_education = models.CharField('最高学历', max_length=50, blank=True)
    highest_school = models.CharField('最高学历毕业院校', max_length=100, blank=True)
    education_level = models.CharField('学历', max_length=50, blank=True)
    highest_major = models.CharField('最高学历专业', max_length=100, blank=True)
    highest_degree = models.CharField('最高学位', max_length=50, blank=True)
    major_category = models.CharField('最高学历专业类别', max_length=50, blank=True)

    # 联系信息
    id_card = models.CharField('身份证号', max_length=18, unique=True, null=True, blank=True)
    id_card_inconsistent = models.BooleanField('出生年月与身份证信息不一致', default=False)
    phone = models.CharField('电话', max_length=20, blank=True)

    # 证书级别
    cert_level = models.CharField('证书级别', max_length=50, blank=True)

    # 系统字段
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_rosters',
        verbose_name='创建人'
    )

    class Meta:
        verbose_name = '花名册'
        verbose_name_plural = '花名册'
        ordering = ['serial_number', 'department', 'name']
        indexes = [
            models.Index(fields=['serial_number']),
            models.Index(fields=['department']),
            models.Index(fields=['name']),
            models.Index(fields=['police_number']),
            models.Index(fields=['id_card']),
        ]

    def __str__(self):
        return f"{self.serial_number} - {self.name} ({self.department})"
