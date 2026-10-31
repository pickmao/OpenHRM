from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from accounts.models import User
from cadres.org_alignment import current_department_name_for_user, current_department_names_for_user_ids

from .models import CampaignStatus, EvaluationCampaign, EvaluationEligibility, EvaluationResponse, EvaluationTarget


def _primary_org_name(user):
    return current_department_name_for_user(user)


@transaction.atomic
def create_campaign(data, creator):
    target_ids = set(data.pop('target_user_ids'))
    evaluator_ids = set(data.pop('evaluator_user_ids'))
    users = {user.id: user for user in User.objects.filter(id__in=target_ids | evaluator_ids, is_active=True)}
    missing_targets = target_ids - users.keys()
    missing_evaluators = evaluator_ids - users.keys()
    if missing_targets:
        raise ValidationError({'target_user_ids': '存在不存在或已停用的评价对象。'})
    if missing_evaluators:
        raise ValidationError({'evaluator_user_ids': '存在不存在或已停用的参评人员。'})

    campaign = EvaluationCampaign.objects.create(
        name=data['name'].strip(),
        description=data.get('description', '').strip(),
        dimensions_json=data['dimensions'],
        min_valid_responses=data['min_valid_responses'],
        starts_at=data.get('starts_at'),
        deadline_at=data['deadline_at'],
        created_by=creator,
    )
    targets = []
    for user_id in target_ids:
        user = users[user_id]
        targets.append(EvaluationTarget(
            campaign=campaign,
            user=user,
            target_name_snapshot=user.real_name or user.username,
            org_name_snapshot=_primary_org_name(user),
        ))
    EvaluationTarget.objects.bulk_create(targets)
    targets = list(campaign.targets.all())
    eligibilities = []
    for target in targets:
        for evaluator_id in evaluator_ids - {target.user_id}:
            eligibilities.append(EvaluationEligibility(
                campaign=campaign, target=target, evaluator_id=evaluator_id,
            ))
    EvaluationEligibility.objects.bulk_create(eligibilities)
    return campaign


@transaction.atomic
def publish_campaign(campaign):
    campaign = EvaluationCampaign.objects.select_for_update().get(id=campaign.id)
    if campaign.status != CampaignStatus.DRAFT:
        raise ValidationError('只有草稿活动可以发布。')
    if campaign.deadline_at <= timezone.now():
        raise ValidationError('截止时间已过，不能发布。')
    if not campaign.targets.exists() or not campaign.eligibilities.exists():
        raise ValidationError('活动至少需要一个评价对象和一名非本人参评人员。')
    campaign.status = CampaignStatus.PUBLISHED
    campaign.published_at = timezone.now()
    campaign.save(update_fields=['status', 'published_at', 'updated_at'])
    return campaign


@transaction.atomic
def close_campaign(campaign):
    campaign = EvaluationCampaign.objects.select_for_update().get(id=campaign.id)
    if campaign.status != CampaignStatus.PUBLISHED:
        raise ValidationError('只有填写中的活动可以关闭。')
    campaign.status = CampaignStatus.CLOSED
    campaign.closed_at = timezone.now()
    campaign.save(update_fields=['status', 'closed_at', 'updated_at'])
    return campaign


@transaction.atomic
def submit_response(campaign, target, evaluator, scores, comment):
    campaign = EvaluationCampaign.objects.select_for_update().get(id=campaign.id)
    if not campaign.is_open():
        raise ValidationError('该评价活动当前不可提交。')
    eligibility = EvaluationEligibility.objects.select_for_update().filter(
        campaign=campaign, target=target, evaluator=evaluator,
    ).first()
    if not eligibility:
        raise ValidationError('您不在该评价对象的参评范围内。')
    if eligibility.submitted:
        raise ValidationError('您已经完成了该对象的评价。')
    EvaluationResponse.objects.create(
        campaign=campaign, target=target, scores_json=scores, comment=comment.strip(),
    )
    eligibility.submitted = True
    eligibility.submitted_on = timezone.localdate()
    eligibility.save(update_fields=['submitted', 'submitted_on'])


def campaign_summary(campaign, *, include_progress=False):
    result = {
        'id': str(campaign.id),
        'name': campaign.name,
        'description': campaign.description,
        'status': campaign.status,
        'status_display': campaign.get_status_display(),
        'dimensions': campaign.dimensions_json,
        'min_valid_responses': campaign.min_valid_responses,
        'starts_at': campaign.starts_at,
        'deadline_at': campaign.deadline_at,
        'published_at': campaign.published_at,
        'closed_at': campaign.closed_at,
        'target_count': campaign.targets.count(),
    }
    if include_progress:
        total = campaign.eligibilities.count()
        submitted = campaign.eligibilities.filter(submitted=True).count()
        result['progress'] = {
            'total': total,
            'submitted': submitted,
            'completion_rate': round(submitted * 100 / total, 2) if total else 0,
        }
    return result


def build_results(campaign):
    results = []
    dimensions = campaign.dimensions_json
    targets = list(campaign.targets.all().select_related('user').order_by('target_name_snapshot'))
    current_orgs = current_department_names_for_user_ids([target.user_id for target in targets])
    for target in targets:
        responses = list(target.responses.all().only('scores_json', 'comment'))
        org_name = current_orgs.get(target.user_id) or target.org_name_snapshot
        if len(responses) < campaign.min_valid_responses:
            results.append({
                'target_id': str(target.id),
                'target_name': target.target_name_snapshot,
                'org_name': org_name,
                'org_name_snapshot': target.org_name_snapshot,
                'available': False,
                'message': '有效样本不足，暂不生成结果。',
            })
            continue
        dimension_results = []
        weighted_total = 0
        total_weight = 0
        for dimension in dimensions:
            values = [
                response.scores_json.get(dimension['key'])
                for response in responses
                if isinstance(response.scores_json.get(dimension['key']), int)
                and not isinstance(response.scores_json.get(dimension['key']), bool)
                and response.scores_json.get(dimension['key']) in range(1, 6)
            ]
            if not values:
                continue
            average = round(sum(values) / len(values), 2)
            weight = dimension.get('weight', 1)
            weighted_total += average * weight
            total_weight += weight
            dimension_results.append({
                'key': dimension['key'],
                'label': dimension['label'],
                'average_score': average,
                'distribution': {str(score): values.count(score) for score in range(1, 6)},
            })
        results.append({
            'target_id': str(target.id),
            'target_name': target.target_name_snapshot,
            'org_name': org_name,
            'org_name_snapshot': target.org_name_snapshot,
            'available': True,
            'valid_response_count': len(responses),
            'overall_score': round(weighted_total / total_weight, 2) if total_weight else None,
            'dimensions': dimension_results,
            'comment_count': sum(bool(response.comment.strip()) for response in responses),
        })
    return results
