import re
import uuid

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models


User = get_user_model()


class LeadershipAssessmentFile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version_date = models.DateField(unique=True)
    file_name = models.CharField(max_length=255, db_index=True)
    source_file = models.FileField(upload_to='leadership_assessments/source/', null=True, blank=True)
    upload_time = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='uploaded_leadership_assessments')
    total_records = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-version_date', '-upload_time']
        indexes = [models.Index(fields=['version_date']), models.Index(fields=['is_active'])]

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

    def __str__(self):
        return f'{self.file_name} ({self.version_date})'


class LeadershipAssessmentRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.ForeignKey(LeadershipAssessmentFile, on_delete=models.CASCADE, related_name='records')
    name = models.CharField(max_length=100, db_index=True)
    leadership_count = models.IntegerField(null=True, blank=True)
    vacancy_count = models.IntegerField(null=True, blank=True)
    team_leader_count = models.IntegerField(null=True, blank=True)
    team_leader_vacancy_count = models.IntegerField(null=True, blank=True)
    average_age = models.FloatField(null=True, blank=True)
    max_age = models.IntegerField(null=True, blank=True)
    min_age = models.IntegerField(null=True, blank=True)
    postgraduate_count = models.IntegerField(null=True, blank=True)
    undergraduate_count = models.IntegerField(null=True, blank=True)
    college_below_count = models.IntegerField(null=True, blank=True)
    over_5_years_count = models.IntegerField(null=True, blank=True)
    three_to_5_years_count = models.IntegerField(null=True, blank=True)
    under_3_years_count = models.IntegerField(null=True, blank=True)
    long_term_office_count = models.IntegerField(null=True, blank=True)
    balanced_count = models.IntegerField(null=True, blank=True)
    long_term_prison_count = models.IntegerField(null=True, blank=True)
    ability_assessment = models.TextField(blank=True)
    performance_2023 = models.TextField(blank=True)
    performance_2024 = models.TextField(blank=True)
    shortcomings = models.TextField(blank=True)
    secretary_score = models.FloatField(null=True, blank=True)
    democratic_score = models.FloatField(null=True, blank=True)
    total_score = models.FloatField(null=True, blank=True, db_index=True)
    approval_rate = models.FloatField(null=True, blank=True)
    ranking = models.IntegerField(null=True, blank=True, db_index=True)
    adjustment_suggestion = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['file', 'ranking', 'name']
        indexes = [models.Index(fields=['file', 'ranking']), models.Index(fields=['name']), models.Index(fields=['total_score'])]
        unique_together = [['file', 'name']]

    def __str__(self):
        return f'{self.name} ({self.file.version_date})'
