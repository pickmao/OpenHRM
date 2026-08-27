import re
import uuid

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models


User = get_user_model()


class PositionCategory(models.TextChoices):
    LEADERSHIP = 'LEADERSHIP', '监狱领导班子成员'
    CORPORATE = 'CORPORATE', '企业副总、工会主席（四高）'
    SECTION_CHIEF = 'SECTION_CHIEF', '科室正职（含企业）'
    SECTION_DEPUTY = 'SECTION_DEPUTY', '科室副职（含企业）'
    INSTITUTION_2 = 'INSTITUTION_2', '事业单位、群团组织、工作团队（二级）'
    INSTITUTION_4 = 'INSTITUTION_4', '事业单位、群团组织、工作团队（四级）'
    PRISON_WARDEN = 'PRISON_WARDEN', '监区长'
    INSTRUCTOR = 'INSTRUCTOR', '教导员'
    DEPUTY_PRISON = 'DEPUTY_PRISON', '副区（狱政）'
    DEPUTY_PRODUCTION = 'DEPUTY_PRODUCTION', '副区（生产）'
    DEPUTY_EDUCATION = 'DEPUTY_EDUCATION', '副区（教育）'
    PRISON_TEAM = 'PRISON_TEAM', '监区工作团队'


class AssessmentFile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version_date = models.DateField(unique=True)
    file_name = models.CharField(max_length=255, db_index=True)
    source_file = models.FileField(upload_to='assessments/source/', null=True, blank=True)
    upload_time = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='uploaded_assessments')
    total_records = models.IntegerField(default=0)
    category_counts = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-version_date', '-upload_time']
        indexes = [models.Index(fields=['version_date']), models.Index(fields=['is_active'])]

    def __str__(self):
        return f'{self.file_name} ({self.version_date})'

    @classmethod
    def validate_file_name(cls, file_name):
        match = re.search(r'[（(](\d{8})[）)]', file_name)
        if not match:
            raise ValidationError('未能从文件名识别日期，请在上传时选择研判期间')
        from datetime import datetime
        try:
            return datetime.strptime(match.group(1), '%Y%m%d').date()
        except ValueError as exc:
            raise ValidationError('文件名中的日期必须为YYYYMMDD格式') from exc


class AssessmentRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.ForeignKey(AssessmentFile, on_delete=models.CASCADE, related_name='records')
    name = models.CharField(max_length=50, db_index=True)
    department = models.CharField(max_length=100, db_index=True)
    position = models.CharField(max_length=100)
    position_category = models.CharField(max_length=50, choices=PositionCategory.choices, db_index=True)
    age = models.IntegerField(null=True, blank=True)
    health_status = models.CharField(max_length=50, blank=True)
    education = models.CharField(max_length=50, blank=True)
    professional_title = models.CharField(max_length=100, blank=True)
    join_prison_date = models.DateField(null=True, blank=True)
    service_years = models.IntegerField(null=True, blank=True)
    office_work_years = models.IntegerField(null=True, blank=True)
    prison_work_years = models.IntegerField(null=True, blank=True)
    main_business = models.TextField(blank=True)
    annual_assessment_3years = models.TextField(blank=True)
    quarterly_assessment = models.TextField(blank=True)
    rewards_3years = models.TextField(blank=True)
    penalties_3years = models.TextField(blank=True)
    personality = models.TextField(blank=True)
    ability_assessment = models.TextField(blank=True)
    performance_2023 = models.TextField(blank=True)
    performance_2024 = models.TextField(blank=True)
    main_performance = models.TextField(blank=True)
    shortcomings = models.TextField(blank=True)
    evaluation_assessment = models.TextField(blank=True)
    talk_assessment = models.TextField(blank=True)
    comprehensive_assessment = models.TextField(blank=True)
    seven_looks_score = models.FloatField(null=True, blank=True)
    work_recognition_score = models.FloatField(null=True, blank=True)
    talk_score = models.FloatField(null=True, blank=True)
    comprehensive_score = models.FloatField(null=True, blank=True)
    ranking = models.IntegerField(null=True, blank=True, db_index=True)
    adjustment_suggestion = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['file', 'position_category', 'ranking', 'name']
        indexes = [
            models.Index(fields=['file', 'position_category']),
            models.Index(fields=['file', 'ranking']),
            models.Index(fields=['name']),
            models.Index(fields=['department']),
        ]
        unique_together = [['file', 'name', 'department']]

    def __str__(self):
        return f'{self.name} - {self.department} ({self.file.version_date})'


class AssessmentChangeLog(models.Model):
    """不可修改的逐条研判数据修改记录。"""

    class ResourceType(models.TextChoices):
        CADRE_RECORD = 'CADRE_RECORD', '中层领导干部分析研判'
        LEADERSHIP_RECORD = 'LEADERSHIP_RECORD', '中层领导班子分析研判'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resource_type = models.CharField(max_length=32, choices=ResourceType.choices)
    resource_id = models.UUIDField(db_index=True)
    version_date = models.DateField(db_index=True)
    record_name = models.CharField(max_length=100)
    changed_fields = models.JSONField(default=list)
    before_values = models.JSONField(default=dict)
    after_values = models.JSONField(default=dict)
    editor = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                               related_name='assessment_change_logs')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['resource_type', 'resource_id', '-created_at'])]

    def __str__(self):
        return f'{self.get_resource_type_display()}：{self.record_name}（{self.created_at:%Y-%m-%d %H:%M}）'
