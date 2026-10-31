import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


POST_CATEGORIES = [
    {'key': 'section_chief', 'label': '正科级领导干部', 'stats_label': '正科级领导干部', 'default_slots': 1},
    {'key': 'deputy_section_chief', 'label': '副科级领导干部', 'stats_label': '副科级领导干部', 'default_slots': 1},
    {'key': 'team_lead', 'label': '工作团队负责人（正职）', 'stats_label': '团队负责人正职', 'default_slots': 1},
    {'key': 'deputy_team_lead', 'label': '工作团队负责人（副职）', 'stats_label': '团队负责人副职', 'default_slots': 1},
    {'key': 'police_officer', 'label': '警员职级警察', 'stats_label': '警员职级警察', 'default_slots': 1},
]

POST_CATEGORY_KEYS = [item['key'] for item in POST_CATEGORIES]
POST_CATEGORY_MAP = {item['key']: item for item in POST_CATEGORIES}

RECOMMENDER_CATEGORIES = [
    {'key': 'BRANCH_SECRETARY', 'label': '党支部书记'},
    {'key': 'BRANCH_COMMITTEE', 'label': '党支部支委'},
    {'key': 'BRANCH_STAFF', 'label': '党支部全体民警职工'},
]


def default_slot_config():
    return {item['key']: item['default_slots'] for item in POST_CATEGORIES}


def normalize_slot_config(value):
    if value in (None, ''):
        value = {}
    if not isinstance(value, dict):
        raise ValidationError('每个岗位类别的推荐人数必须是对象。')
    result = {}
    for item in POST_CATEGORIES:
        raw = value.get(item['key'], item['default_slots'])
        if raw is None:
            raw = item['default_slots']
        if isinstance(raw, bool) or not isinstance(raw, int) or not 0 <= raw <= 20:
            raise ValidationError(f'{item["label"]} 的推荐人数必须是 0 至 20 的整数。')
        result[item['key']] = raw
    if sum(result.values()) < 1:
        raise ValidationError('至少需要为一个岗位类别设置推荐人数。')
    return result


def validate_slot_config(value):
    normalize_slot_config(value)


class CampaignStatus(models.TextChoices):
    DRAFT = 'DRAFT', '草稿'
    PUBLISHED = 'PUBLISHED', '填写中'
    CLOSED = 'CLOSED', '已关闭'


class TaskStatus(models.TextChoices):
    PENDING = 'PENDING', '待填报'
    DRAFT = 'DRAFT', '草稿'
    SUBMITTED = 'SUBMITTED', '已提交'


class ReceiverType(models.TextChoices):
    USER = 'USER', '指定用户'
    ORG_UNIT = 'ORG_UNIT', '指定单位'
    ORG_ROLE = 'ORG_ROLE', '单位角色'


class RecommenderCategory(models.TextChoices):
    BRANCH_SECRETARY = 'BRANCH_SECRETARY', '党支部书记'
    BRANCH_COMMITTEE = 'BRANCH_COMMITTEE', '党支部支委'
    BRANCH_STAFF = 'BRANCH_STAFF', '党支部全体民警职工'


class PostCategory(models.TextChoices):
    SECTION_CHIEF = 'section_chief', '正科级领导干部'
    DEPUTY_SECTION_CHIEF = 'deputy_section_chief', '副科级领导干部'
    TEAM_LEAD = 'team_lead', '工作团队负责人（正职）'
    DEPUTY_TEAM_LEAD = 'deputy_team_lead', '工作团队负责人（副职）'
    POLICE_OFFICER = 'police_officer', '警员职级警察'


class RecommendationCampaign(models.Model):
    """一次优秀干部推荐活动。"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('活动名称', max_length=200)
    description = models.TextField('活动说明', blank=True)
    status = models.CharField(
        '状态', max_length=20, choices=CampaignStatus.choices,
        default=CampaignStatus.PUBLISHED, db_index=True,
    )
    slot_config = models.JSONField('各类岗位推荐人数', default=default_slot_config, validators=[validate_slot_config])
    allow_self_recommend = models.BooleanField('允许推荐本人', default=False)
    receiver_type = models.CharField('接收人类型', max_length=20, choices=ReceiverType.choices, default=ReceiverType.USER)
    receiver_expr_json = models.JSONField('接收人条件', default=dict, blank=True)
    deadline_at = models.DateTimeField('截止时间')
    published_at = models.DateTimeField('发布时间', null=True, blank=True)
    closed_at = models.DateTimeField('关闭时间', null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_recommendation_campaigns', verbose_name='创建人',
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '优秀干部推荐活动'
        verbose_name_plural = '优秀干部推荐活动'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['status', 'deadline_at'])]

    def clean(self):
        self.slot_config = normalize_slot_config(self.slot_config)

    def is_open(self):
        from django.utils import timezone
        now = timezone.now()
        return self.status == CampaignStatus.PUBLISHED and now <= self.deadline_at

    def __str__(self):
        return self.name


class RecommendationTask(models.Model):
    """一名填报人在一次活动中的推荐表。"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(RecommendationCampaign, on_delete=models.CASCADE, related_name='tasks')
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='recommendation_tasks', verbose_name='填报人',
    )
    status = models.CharField(
        '状态', max_length=20, choices=TaskStatus.choices,
        default=TaskStatus.PENDING, db_index=True,
    )
    recommender_category = models.CharField(
        '人员类别', max_length=30, choices=RecommenderCategory.choices, blank=True,
    )
    assignee_name_snapshot = models.CharField('填报人姓名快照', max_length=100)
    org_unit_name_snapshot = models.CharField('所属部门快照', max_length=100, blank=True)
    branch_name_snapshot = models.CharField('所属支部快照', max_length=100, blank=True)
    submitted_at = models.DateTimeField('提交时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '优秀干部推荐任务'
        verbose_name_plural = '优秀干部推荐任务'
        ordering = ['campaign', 'assignee_name_snapshot']
        constraints = [
            models.UniqueConstraint(fields=['campaign', 'assignee'], name='unique_recommendation_task_per_assignee'),
        ]
        indexes = [models.Index(fields=['campaign', 'status'])]

    def __str__(self):
        return f'{self.campaign.name} - {self.assignee_name_snapshot}'


class RecommendationNomination(models.Model):
    """推荐表中的一个岗位空位选择。"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(RecommendationTask, on_delete=models.CASCADE, related_name='nominations')
    post_category = models.CharField('岗位类别', max_length=40, choices=PostCategory.choices, db_index=True)
    slot_index = models.PositiveSmallIntegerField('空位序号', validators=[MinValueValidator(0)])
    roster = models.ForeignKey(
        'cadres.PersonnelRoster', on_delete=models.PROTECT,
        related_name='recommendation_nominations', verbose_name='被推荐人',
    )
    name_snapshot = models.CharField('姓名快照', max_length=50)
    department_snapshot = models.CharField('部门快照', max_length=100, blank=True)
    position_snapshot = models.CharField('职务职级快照', max_length=200, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '优秀干部推荐人选'
        verbose_name_plural = '优秀干部推荐人选'
        ordering = ['task', 'post_category', 'slot_index']
        constraints = [
            models.UniqueConstraint(fields=['task', 'post_category', 'slot_index'], name='unique_recommendation_slot'),
            models.UniqueConstraint(fields=['task', 'roster'], name='unique_recommendation_person_per_task'),
        ]
