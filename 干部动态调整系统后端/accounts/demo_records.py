"""Clearly labelled, repeatable sample records for the reporting columns."""

from collections import Counter
from datetime import timedelta

from assessments.models import AssessmentFile, AssessmentRecord, PositionCategory
from inspections.models import WorkRecord
from leadership_assessments.models import LeadershipAssessmentFile, LeadershipAssessmentRecord
from rewards_punishments.models import RewardImportFile, RewardRecipientType, RewardRecord


def _available_period(model, ctx, key, desired):
    existing = model.objects.filter(pk=ctx.key(key)).first()
    if existing:
        return existing.version_date
    # A real imported period must never be adopted or overwritten by sample data.
    occupied = set(model.objects.values_list('version_date', flat=True))
    while desired in occupied:
        desired -= timedelta(days=1)
    return desired


def seed(ctx):
    """Create two reporting periods, rewards, and each demo user's work diary.

    Caller owns the transaction. ctx.put uses stable IDs and preserves edits on
    subsequent runs. No source-file path is fabricated for these generated rows.
    """
    categories = list(PositionCategory.values)
    counts = Counter()
    for period, days_ago in enumerate((90, 0)):
        desired = ctx.now.date() - timedelta(days=days_ago)
        file_key = f'records/assessment-file/{period}'
        version = _available_period(AssessmentFile, ctx, file_key, desired)
        assessment = ctx.put(
            AssessmentFile, file_key, version_date=version,
            file_name=f'{ctx.prefix}中层干部研判（{version:%Y%m%d}）',
            uploaded_by=ctx.admin, total_records=len(ctx.rosters),
            category_counts=dict(Counter(categories[i % len(categories)] for i in range(len(ctx.rosters)))),
        )
        counts['assessment_files'] += 1
        for i, roster in enumerate(ctx.rosters):
            category = categories[i % len(categories)]
            score = round(94 - i * 1.1 + period * 1.5, 2)
            ctx.put(
                AssessmentRecord, f'records/assessment/{period}/{i}', file=assessment,
                name=roster.name, department=ctx.departments[i // 2].name,
                position=PositionCategory(category).label, position_category=category,
                age=roster.age, health_status='良好', education='硕士' if i % 3 == 0 else '本科',
                professional_title=f'{ctx.prefix}业务骨干',
                join_prison_date=version - timedelta(days=365 * (8 + i)),
                service_years=8 + i, office_work_years=3 + i // 2,
                prison_work_years=5 + i - i // 2,
                main_business=f'{ctx.prefix}承担业务协调、制度完善与基层服务工作。',
                annual_assessment_3years=f'{ctx.prefix}称职、优秀、称职',
                quarterly_assessment=f'{ctx.prefix}本季度工作完成率 96%，示例数据。',
                rewards_3years=f'{ctx.prefix}业务比武优秀个人（模拟）',
                penalties_3years=f'{ctx.prefix}无处分，纯模拟记录。',
                personality=f'{ctx.prefix}工作细致、协作主动。',
                ability_assessment=f'{ctx.prefix}能够独立组织业务复盘，推动跨部门协同。',
                performance_2023=f'{ctx.prefix}完成流程规范化试点。',
                performance_2024=f'{ctx.prefix}完善任务台账和问题反馈机制。',
                main_performance=f'{ctx.prefix}完成 {12 + i} 项专项任务，形成 3 项改进建议。',
                shortcomings=f'{ctx.prefix}需进一步加强数据分析和青年人员培养。',
                evaluation_assessment=f'{ctx.prefix}测评反馈整体较好，建议持续跟踪。',
                talk_assessment=f'{ctx.prefix}谈话反映履职认真，协作意识较强。',
                comprehensive_assessment=f'{ctx.prefix}符合岗位要求，建议安排轮岗锻炼。',
                seven_looks_score=score, work_recognition_score=round(score - 1, 2),
                talk_score=round(score + 1, 2), comprehensive_score=score, ranking=i + 1,
                adjustment_suggestion=f'{ctx.prefix}' + ('建议轮岗培养' if i % 3 == 0 else '建议保持岗位并加强培养'),
            )
            counts['assessment_records'] += 1

        leadership_key = f'records/leadership-file/{period}'
        team_version = _available_period(LeadershipAssessmentFile, ctx, leadership_key, desired)
        leadership_file = ctx.put(
            LeadershipAssessmentFile, leadership_key, version_date=team_version,
            file_name=f'{ctx.prefix}领导班子研判（{team_version:%Y%m%d}）',
            uploaded_by=ctx.admin, total_records=len(ctx.branches),
        )
        counts['leadership_files'] += 1
        for i, branch in enumerate(ctx.branches):
            ctx.put(
                LeadershipAssessmentRecord, f'records/leadership/{period}/{i}', file=leadership_file,
                name=branch.name, leadership_count=4, vacancy_count=i % 2,
                team_leader_count=2, team_leader_vacancy_count=0,
                average_age=36 + i * 4, min_age=32 + i * 4, max_age=40 + i * 4,
                postgraduate_count=1, undergraduate_count=3, college_below_count=0,
                over_5_years_count=1, three_to_5_years_count=2, under_3_years_count=1,
                long_term_office_count=1, balanced_count=2, long_term_prison_count=1,
                ability_assessment=f'{ctx.prefix}分工明确，具备组织协调和应急处置能力。',
                performance_2023=f'{ctx.prefix}完成专项工作计划，建立问题整改台账。',
                performance_2024=f'{ctx.prefix}推进制度落实和业务培训。',
                shortcomings=f'{ctx.prefix}专业人才梯队和跨部门协作仍需完善。',
                secretary_score=94 - i * 3 + period, democratic_score=92 - i * 3 + period,
                total_score=93 - i * 3 + period, approval_rate=96 - i * 2,
                ranking=i + 1, adjustment_suggestion=f'{ctx.prefix}建议补充青年业务骨干并开展交流轮岗。',
            )
            counts['leadership_records'] += 1

    reward_file = ctx.put(
        RewardImportFile, 'records/reward-file', file_name=f'{ctx.prefix}个人和集体奖励示例',
        uploaded_by=ctx.admin, total_records=len(ctx.rosters) + len(ctx.branches),
        record_counts={'individual': len(ctx.rosters), 'collective': len(ctx.branches)},
    )
    counts['reward_files'] = 1
    for i, roster in enumerate(ctx.rosters):
        approved = ctx.now.date() - timedelta(days=30 + i * 40)
        ctx.put(
            RewardRecord, f'records/individual-reward/{i}', import_file=reward_file,
            recipient_type=RewardRecipientType.INDIVIDUAL, recipient_name=roster.name,
            award_level=('单位级', '市级', '省级')[i % 3], approval_year=approved.year,
            approval_date=approved, award_content=f'{ctx.prefix}' + ('业务比武优秀个人', '年度先进个人', '岗位练兵标兵')[i % 3],
            document_number=f'演示奖字〔{approved.year}〕{i + 1:03d}号',
            remark=f'{ctx.prefix}仅供功能测试，不代表任何真实奖励。',
            source_sheet='个人', source_row=i + 2, created_by=ctx.admin,
        )
        counts['individual_rewards'] += 1
    for i, branch in enumerate(ctx.branches):
        approved = ctx.now.date() - timedelta(days=60 + i * 90)
        ctx.put(
            RewardRecord, f'records/collective-reward/{i}', import_file=reward_file,
            recipient_type=RewardRecipientType.COLLECTIVE, recipient_name=branch.name,
            award_level='单位级', approval_year=approved.year, approval_date=approved,
            award_content=f'{ctx.prefix}先进工作集体', document_number=f'演示集奖〔{approved.year}〕{i + 1:03d}号',
            remark=f'{ctx.prefix}仅供功能测试，不代表任何真实奖励。',
            source_sheet='集体', source_row=i + 2, created_by=ctx.admin,
        )
        counts['collective_rewards'] += 1

    for i, owner in enumerate([ctx.admin, *ctx.users]):
        for j, category in enumerate(WorkRecord.Category.values):
            ctx.put(
                WorkRecord, f'records/work/{i}/{j}', owner=owner, category=category,
                title=f'{ctx.prefix}' + ('应急协同演练', '业务流程优化专项')[j],
                completed_on=ctx.now.date() - timedelta(days=7 + i * 2 + j),
                role='牵头协调' if j == 0 else '主要参与',
                details=f'{ctx.prefix}制定任务分工，协调资源，跟踪落实情况并组织复盘；全部内容为模拟。',
                outcome=f'{ctx.prefix}完成既定任务，整理 {3 + i % 3} 项改进建议，形成可复用工作清单。',
            )
            counts['work_records'] += 1
    return dict(counts)
