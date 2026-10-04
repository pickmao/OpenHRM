"""Synthetic campaign fixtures, restricted to the demo context's people and units."""
from datetime import timedelta


def _person(ctx, index):
    person = ctx.rosters[index]
    return {
        'id': str(person.pk), 'name': person.name, 'department': person.department,
        'position': person.position, 'position_label': person.position,
        'position_category': person.position_category, 'position_rank': person.position_rank,
        'police_rank': person.police_rank,
        'target_group': ('chief', 'deputy', 'team', 'police')[index % 4],
        'department_position': f'{person.department} {person.position}',
        'gender': person.gender, 'political_status': person.political_status,
    }


def _filled_payload(form_type, context, variation, date):
    from knowing_people.form_defs import default_payload

    payload = default_payload(form_type, context)
    text = '【演示】完成岗位练兵、业务培训和流程优化；内容为虚构测试案例。'
    grade = ('优', '良', '良', '中')[variation % 4]
    for field in ('self_eval_date', 'fill_date', 'eval_date'):
        if field in payload:
            payload[field] = date
    for field in ('performance', 'rectification', 'team_requests', 'personal_requests'):
        if field in payload:
            payload[field] = text
    for field in ('shortcomings', 'other_issues'):
        if field in payload:
            payload[field] = '【演示】下一阶段加强跨部门协作和经验交流。'
    for row in payload.get('dimensions', []):
        row.update(grade=grade, performance=text, shortcomings='【演示】持续改进业务流程。')
    for row in payload.get('targets', []):
        row['scores'] = dict.fromkeys(row['scores'], grade)
        if 'recognition' in row:
            row['recognition'] = ('认可', '基本认可', '认可', '不了解')[variation % 4]
    for field in ('scores', 'branch_scores'):
        if field in payload:
            payload[field] = dict.fromkeys(payload[field], grade)
    if 'recognition' in payload:
        payload['recognition'] = ('认可', '基本认可', '认可', '不了解')[variation % 4]
    if form_type == 'ATTACHMENT_3':
        payload['items'] = [{'experience': '【演示】本年度岗位实践', 'key_work': '【演示】业务流程优化',
                             'roles': ['主导者'], 'details': text}]
    elif form_type == 'ATTACHMENT_4':
        payload.update(leadership_current=2, leadership_vacancy=0, team_leader_current=1,
                       team_leader_vacancy=0, experience_counts={'office': 1, 'balanced': 1, 'prison': 1},
                       adjustment_needed='否', adjustment_suggestion='【演示】保持现有分工，定期复盘。')
        for row in payload['items']:
            row.update(grade=grade, performance=text, shortcomings='【演示】加强培训。')
    elif form_type == 'ATTACHMENT_5':
        payload['works'] = [{'title': '【演示】年度培训与岗位练兵', 'description': text,
                             'people': [{'name': context['roster']['name'], 'roles': ['主导者'],
                                         'task_and_role': '【演示】协调安排培训，完成复盘总结。'}]}]
    elif form_type == 'ATTACHMENT_1':
        payload['personnel_category'] = '党支部全体民警职工'
        for row in payload['overall']:
            row['grade'] = '较好'
        payload['issues'] = ['issue_13']
        payload['other'] = '【演示】访谈意见仅用于系统功能测试。'
    return payload


def _seed_knowing(ctx):
    from knowing_people.form_defs import default_payload
    from knowing_people.models import InspectionCampaign, InspectionTask, FormType, FillerRole
    from knowing_people.payload_validation import validate_task_payload

    people = [_person(ctx, i) for i in range(len(ctx.users))]
    branches = [{'id': str(b.pk), 'name': b.name, 'department': b.name} for b in ctx.branches]
    local_roles = [FillerRole.BRANCH_SECRETARY, FillerRole.BRANCH_DEPUTY_SECRETARY,
                   FillerRole.BRANCH_COMMITTEE, FillerRole.BRANCH_STAFF]
    plan = []
    for i in range(len(ctx.users)):
        b = i // 4
        if i % 4 != 3:
            for form in (FormType.ATTACHMENT_2, FormType.ATTACHMENT_3):
                plan.append((form, i, None, FillerRole.MIDDLE_LEADER, []))
        if i % 4 == 0:
            for form in (FormType.ATTACHMENT_4, FormType.ATTACHMENT_5):
                plan.append((form, i, b, FillerRole.BRANCH_LEADERSHIP, []))
        plan.append((FormType.ATTACHMENT_6_2, i, b, FillerRole.BRANCH_STAFF, [branches[b]]))
        plan.append((FormType.ATTACHMENT_7_4, i, b, local_roles[i % 4], people[b * 4:b * 4 + 4]))
        if i % 4 == 3:
            plan.append((FormType.ATTACHMENT_1, i, b, FillerRole.INSPECTION_TALKER, people[b * 4:b * 4 + 4]))
    # Roles below are confined to synthetic campaign snapshots, not account permissions.
    for i, role in [(0, FillerRole.BRANCH_SECRETARY), (4, FillerRole.BRANCH_SECRETARY),
                    (8, FillerRole.BRANCH_SECRETARY), (3, FillerRole.PRINCIPAL_LEADER),
                    (7, FillerRole.PRISON_LEADER)]:
        plan.append((FormType.ATTACHMENT_6_1, i, None, role, branches))
        plan.append((FormType.ATTACHMENT_7_1, i, None, role, people[0::4]))
        plan.append((FormType.ATTACHMENT_7_2, i, None, role, people[1::4]))
    for i, role in [(3, FillerRole.POLITICAL_DIRECTOR), (7, FillerRole.POLITICAL_EXECUTIVE_DEPUTY),
                    (11, FillerRole.POLITICAL_DEPUTY)]:
        plan.append((FormType.ATTACHMENT_7_3, i, None, role, people[2::4]))

    for closed in (False, True):
        suffix = 'results' if closed else 'open'
        campaign = ctx.put(InspectionCampaign, f'knowing/{suffix}',
                           name=f'{ctx.prefix}知事识人—' + ('完整统计样例' if closed else '填报流程体验'),
                           year=str(ctx.now.year), period_start=(ctx.now - timedelta(days=90)).date(),
                           period_end=ctx.now.date(), form_types=list(FormType.values),
                           description='全部为虚构数据；评价身份仅为统计流程演示，不代表真实任职。',
                           status='CLOSED' if closed else 'PUBLISHED', created_by=ctx.admin,
                           deadline_at=ctx.now + timedelta(days=-1 if closed else 90),
                           published_at=ctx.now - timedelta(days=7),
                           closed_at=ctx.now if closed else None)
        for number, (form, i, branch_index, role, targets) in enumerate(plan):
            b = i // 4 if branch_index is None else branch_index
            context = {'roster': people[i], 'branch': branches[b], 'targets': targets,
                       'roster_people': people[b * 4:b * 4 + 4], 'campaign_year': str(ctx.now.year),
                       'period_start': campaign.period_start.isoformat(),
                       'period_end': campaign.period_end.isoformat()}
            status = 'SUBMITTED' if closed else ('PENDING', 'DRAFT', 'SUBMITTED', 'RETURNED')[number % 4]
            payload = (default_payload(form, context) if status == 'PENDING' else
                       _filled_payload(form, context, number, ctx.now.date().isoformat()))
            # Exercise the same immutable-object and required-field contract as submission.
            probe = InspectionTask(form_type=form, context_json=context)
            payload = validate_task_payload(probe, payload, strict=status == 'SUBMITTED')
            ctx.put(InspectionTask, f'knowing/{suffix}/task/{number}', campaign=campaign,
                    form_type=form, filler_role=role, assignee=ctx.users[i], roster=ctx.rosters[i],
                    branch=ctx.branches[branch_index] if branch_index is not None else None,
                    status=status, assignee_name_snapshot=people[i]['name'],
                    org_unit_name_snapshot=people[i]['department'], branch_name_snapshot=branches[b]['name'],
                    payload_json=payload, context_json=context,
                    submitted_at=ctx.now - timedelta(days=2) if status == 'SUBMITTED' else None,
                    return_reason='【演示】请补充工作具体事例。' if status == 'RETURNED' else '',
                    returned_by=ctx.admin if status == 'RETURNED' else None,
                    returned_at=ctx.now - timedelta(days=1) if status == 'RETURNED' else None)
        if not closed:
            for form in FormType.values:
                targets = (branches if form == FormType.ATTACHMENT_6_1 else
                           [branches[0]] if form == FormType.ATTACHMENT_6_2 else
                           people[0::4] if form == FormType.ATTACHMENT_7_1 else
                           people[1::4] if form == FormType.ATTACHMENT_7_2 else
                           people[2::4] if form == FormType.ATTACHMENT_7_3 else people[:4])
                context = {'roster': {'name': ctx.admin.real_name,
                                      'department': ctx.departments[0].name,
                                      'position_label': '演示管理员'},
                           'branch': branches[0], 'targets': targets, 'roster_people': people[:4]}
                role = {FormType.ATTACHMENT_2: FillerRole.MIDDLE_LEADER,
                        FormType.ATTACHMENT_3: FillerRole.MIDDLE_LEADER,
                        FormType.ATTACHMENT_4: FillerRole.BRANCH_LEADERSHIP,
                        FormType.ATTACHMENT_5: FillerRole.BRANCH_LEADERSHIP,
                        FormType.ATTACHMENT_6_2: FillerRole.BRANCH_STAFF,
                        FormType.ATTACHMENT_7_3: FillerRole.POLITICAL_DIRECTOR,
                        FormType.ATTACHMENT_1: FillerRole.INSPECTION_TALKER}.get(form, FillerRole.BRANCH_SECRETARY)
                ctx.put(InspectionTask, f'knowing/{suffix}/admin/{form}', campaign=campaign,
                        form_type=form, filler_role=role, assignee=ctx.admin, branch=ctx.branches[0],
                        status='PENDING', assignee_name_snapshot=ctx.admin.real_name,
                        org_unit_name_snapshot=ctx.departments[0].name, branch_name_snapshot=branches[0]['name'],
                        payload_json=default_payload(form, context), context_json=context)
    return {'knowing_people_campaigns': 2, 'knowing_people_tasks': len(plan) * 2 + 11}


def _seed_anonymous(ctx):
    from anonymous_evaluations.models import (
        EvaluationCampaign, EvaluationTarget, EvaluationEligibility, EvaluationResponse, default_dimensions,
    )

    response_count = 0
    for closed in (False, True):
        suffix = 'results' if closed else 'open'
        campaign = ctx.put(EvaluationCampaign, f'anonymous/{suffix}',
                           name=f'{ctx.prefix}匿名测评—' + ('结果样例' if closed else '填写体验'),
                           description='虚构演示活动；匿名答卷不保存填写人关联。',
                           status='CLOSED' if closed else 'PUBLISHED', dimensions_json=default_dimensions(),
                           min_valid_responses=8, starts_at=ctx.now - timedelta(days=7),
                           deadline_at=ctx.now + timedelta(days=-1 if closed else 90),
                           published_at=ctx.now - timedelta(days=7), closed_at=ctx.now if closed else None,
                           created_by=ctx.admin)
        for target_index in (0, 4, 8):
            person = ctx.rosters[target_index]
            target = ctx.put(EvaluationTarget, f'anonymous/{suffix}/target/{target_index}',
                             campaign=campaign, user=ctx.users[target_index],
                             target_name_snapshot=person.name, org_name_snapshot=person.department)
            evaluators = [user for user in ctx.users if user.pk != target.user_id]
            for n, user in enumerate(evaluators):
                ctx.put(EvaluationEligibility, f'anonymous/{suffix}/eligibility/{target_index}/{n}',
                        campaign=campaign, target=target, evaluator=user, submitted=closed,
                        submitted_on=ctx.now.date() if closed else None)
            if not closed:
                ctx.put(EvaluationEligibility, f'anonymous/{suffix}/eligibility/{target_index}/admin',
                        campaign=campaign, target=target, evaluator=ctx.admin, submitted=False)
            if closed:
                # Response keys are synthetic answer slots, never eligibility/user identifiers.
                for n in range(len(evaluators)):
                    ctx.put(EvaluationResponse, f'anonymous/{suffix}/answer/{target_index}/{n}',
                            campaign=campaign, target=target,
                            scores_json={dimension['key']: 3 + (n + j) % 3
                                         for j, dimension in enumerate(default_dimensions())},
                            comment='【演示】建议加强业务交流和青年人员培养。' if n % 3 == 0 else '',
                            submitted_on=ctx.now.date())
                    response_count += 1
    return {'anonymous_campaigns': 2, 'anonymous_targets': 6,
            'anonymous_eligibilities': 69, 'anonymous_responses': response_count}


def _seed_recommendations(ctx):
    from cadre_recommendations.models import (
        RecommendationCampaign, RecommendationTask, RecommendationNomination, default_slot_config,
    )

    nomination_count = 0
    for closed in (False, True):
        suffix = 'results' if closed else 'open'
        campaign = ctx.put(RecommendationCampaign, f'recommendations/{suffix}',
                           name=f'{ctx.prefix}优秀干部推荐—' + ('统计样例' if closed else '填报体验'),
                           description='虚构演示人员；按所在支部范围推荐，未选岗位可留空。',
                           status='CLOSED' if closed else 'PUBLISHED', slot_config=default_slot_config(),
                           allow_self_recommend=False, receiver_type='USER',
                           receiver_expr_json={'user_ids': [str(user.pk) for user in ctx.users]},
                           deadline_at=ctx.now + timedelta(days=-1 if closed else 90),
                           published_at=ctx.now - timedelta(days=7), closed_at=ctx.now if closed else None,
                           created_by=ctx.admin)
        for i, user in enumerate(ctx.users):
            status = 'SUBMITTED' if closed else ('PENDING', 'DRAFT', 'SUBMITTED')[i % 3]
            category = ('BRANCH_SECRETARY', 'BRANCH_COMMITTEE', 'BRANCH_COMMITTEE', 'BRANCH_STAFF')[i % 4]
            task = ctx.put(RecommendationTask, f'recommendations/{suffix}/task/{i}',
                           campaign=campaign, assignee=user, status=status, recommender_category=category,
                           assignee_name_snapshot=ctx.rosters[i].name,
                           org_unit_name_snapshot=ctx.rosters[i].department,
                           branch_name_snapshot=ctx.branches[i // 4].name,
                           submitted_at=ctx.now - timedelta(days=2) if status == 'SUBMITTED' else None)
            if status == 'PENDING':
                continue
            for j in range((i // 4) * 4, (i // 4) * 4 + 4):
                if i == j:
                    continue
                post = ('section_chief', 'deputy_section_chief', 'team_lead', 'police_officer')[j % 4]
                person = ctx.rosters[j]
                ctx.put(RecommendationNomination, f'recommendations/{suffix}/task/{i}/person/{j}',
                        task=task, post_category=post, slot_index=0, roster=person,
                        name_snapshot=person.name, department_snapshot=person.department,
                        position_snapshot=person.position)
                nomination_count += 1
        if not closed:
            ctx.put(RecommendationTask, f'recommendations/{suffix}/admin', campaign=campaign,
                    assignee=ctx.admin, status='PENDING', recommender_category='BRANCH_STAFF',
                    assignee_name_snapshot=ctx.admin.real_name,
                    org_unit_name_snapshot=ctx.departments[0].name,
                    branch_name_snapshot=ctx.branches[0].name)
    return {'recommendation_campaigns': 2, 'recommendation_tasks': len(ctx.users) * 2 + 1,
            'recommendation_nominations': nomination_count}


def seed(ctx):
    """Idempotently create six demo campaigns without dispatching to real accounts."""
    if len(ctx.users) != 12 or len(ctx.rosters) != 12 or len(ctx.branches) != 3:
        raise ValueError('Campaign demo fixtures require 12 users/rosters and 3 branches.')
    return {**_seed_knowing(ctx), **_seed_anonymous(ctx), **_seed_recommendations(ctx)}
