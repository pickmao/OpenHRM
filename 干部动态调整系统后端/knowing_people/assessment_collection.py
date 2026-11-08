"""将同一考察批次的已提交信息写入两类研判记录。"""

from calendar import monthrange
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, ROUND_DOWN
from uuid import UUID

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from assessments.audit import record_change
from assessments.models import AssessmentChangeLog, AssessmentFile, AssessmentRecord, PositionCategory
from cadres.models import PersonnelRoster
from leadership_assessments.models import LeadershipAssessmentFile, LeadershipAssessmentRecord
from orgs.models import OrgUnit

from .form_defs import merge_payload
from .matching import is_deputy, is_middle_leader, is_team_lead, roster_in_departments
from .materials import build_materials
from .models import AssessmentCollection, FillerRole, FormType, InspectionCampaign, TaskStatus
from .permissions import has_knowing_people_permission
from .statistics import build_statistics


def can_configure_collection(user):
    if not has_knowing_people_permission(user, 'knowing_people:campaign:manage'):
        return False
    if has_knowing_people_permission(user, 'assessments:manage'):
        return True
    return all(any(has_knowing_people_permission(user, f'{prefix}:{suffix}:manage') for suffix in ('record', 'file'))
               for prefix in ('leadership', 'assessments'))


BRANCH_COUNTS = {
    'leadership_current': 'leadership_count', 'leadership_vacancy': 'vacancy_count',
    'team_leader_current': 'team_leader_count', 'team_leader_vacancy': 'team_leader_vacancy_count',
}
EXPERIENCE_COUNTS = {'office': 'long_term_office_count', 'balanced': 'balanced_count', 'prison': 'long_term_prison_count'}
BRANCH_FIELDS = [*BRANCH_COUNTS.values(), *EXPERIENCE_COUNTS.values(), 'average_age', 'max_age', 'min_age',
                 'postgraduate_count', 'undergraduate_count', 'college_below_count', 'over_5_years_count',
                 'three_to_5_years_count', 'under_3_years_count', 'secretary_score', 'democratic_score',
                 'total_score', 'approval_rate', 'ranking']
TEXT_FIELDS = ['ability_assessment', 'shortcomings', 'performance_2023', 'performance_2024']


def collection_summary(link):
    if not link:
        return None
    return {'version_date': link.leadership_file.version_date, 'leadership_file_id': str(link.leadership_file_id),
            'cadre_file_id': str(link.cadre_file_id), 'include_team_leaders': link.include_team_leaders,
            'include_designated_leaders': link.include_designated_leaders, 'approval_rule': link.approval_rule,
            'member_ids': link.member_ids, 'last_synced_at': link.last_synced_at, 'warnings': link.warnings,
            'leadership_count': link.leadership_file.records.count(), 'cadre_count': link.cadre_file.records.count()}


@transaction.atomic
def configure_collection(campaign, user, data):
    campaign = InspectionCampaign.objects.select_for_update().get(pk=campaign.pk)
    link = AssessmentCollection.objects.filter(campaign=campaign).first()
    version = data['version_date']
    if 'member_ids' in data:
        materials = build_materials(campaign)
        available = defaultdict(set)
        for row in materials['roster_people']:
            available[row['branch_id']].add(row['id'])
        branch_ids = {row['id'] for row in materials['branches']}
        for branch_id, identities in data['member_ids'].items():
            if branch_id not in branch_ids or not {str(value) for value in identities}.issubset(available[branch_id]):
                raise ValidationError('指定的统计成员不在本批次对应支部的花名册中，请重新核对。')
    if link and link.leadership_file.version_date != version:
        raise ValidationError('本批次已关联研判期间，请在原期间更新归集设置。')
    if not link:
        leadership_file, _ = LeadershipAssessmentFile.objects.get_or_create(version_date=version, defaults={
            'file_name': f'{campaign.name} 班子研判（{version:%Y%m%d}）', 'uploaded_by': user})
        cadre_file, _ = AssessmentFile.objects.get_or_create(version_date=version, defaults={
            'file_name': f'{campaign.name} 干部研判（{version:%Y%m%d}）', 'uploaded_by': user})
        LeadershipAssessmentFile.objects.select_for_update().get(pk=leadership_file.pk)
        AssessmentFile.objects.select_for_update().get(pk=cadre_file.pk)
        if AssessmentCollection.objects.filter(leadership_file=leadership_file).exists() or AssessmentCollection.objects.filter(cadre_file=cadre_file).exists():
            raise ValidationError('该研判期间已关联其他考察批次，请选择本批次的研判期间。')
        link = AssessmentCollection(campaign=campaign, leadership_file=leadership_file, cadre_file=cadre_file)
    link.include_team_leaders = data.get('include_team_leaders', True)
    link.include_designated_leaders = data.get('include_designated_leaders', False)
    link.approval_rule = data.get('approval_rule', 'UNCONFIRMED')
    if 'member_ids' in data:
        link.member_ids = {str(key): [str(value) for value in values] for key, values in data['member_ids'].items()}
    link.save()
    return sync_collection(campaign, user)


def _plan(name, *, cadre=False):
    values = {key: None for key in BRANCH_FIELDS} if not cadre else {
        'seven_looks_score': None, 'work_recognition_score': None, 'talk_assessment': '',
        'health_status': '', 'main_business': '', 'rewards_3years': '', 'penalties_3years': '',
        'main_performance': '',
        'office_work_years': None, 'prison_work_years': None,
    }
    values.update({key: '' for key in TEXT_FIELDS})
    values.update(name=name, performance_by_year={})
    if not cadre:
        values['adjustment_suggestion'] = ''
    return {'values': values, 'sources': {}, 'source_task_ids': set(), 'talk_notes': [], 'warnings': []}


def _source(plan, task_id, field):
    task_id = str(task_id)
    plan['source_task_ids'].add(task_id)
    plan['sources'].setdefault(field, [])
    if task_id not in plan['sources'][field]:
        plan['sources'][field].append(task_id)


def _text(plan, field, text, task_id):
    if text:
        previous = plan['values'].get(field) or ''
        plan['values'][field] = '\n'.join(filter(None, [previous, text]))
        _source(plan, task_id, field)


def _annual(plan, year, text, task_id):
    if not year:
        plan['warnings'].append('存在年度未明确的述事材料，请核对来源原表。')
        return
    if year in {'2023', '2024'}:
        _text(plan, f'performance_{year}', text, task_id)
    else:
        annual = plan['values']['performance_by_year']
        annual[year] = '\n'.join(filter(None, [annual.get(year), text]))
        _source(plan, task_id, f'performance_by_year.{year}')


def _anniversary(start, years):
    year = start.year + years
    return date(year, start.month, min(start.day, monthrange(year, start.month)[1]))


def _full_years(start, cutoff):
    if not start or start > cutoff:
        return None
    return cutoff.year - start.year - ((cutoff.month, cutoff.day) < (start.month, start.day))


def _education(value):
    if any(part in value for part in ('研究生', '硕士', '博士')):
        return 'postgraduate_count'
    if any(part in value for part in ('大专', '专科', '中专', '高中', '初中', '小学', '技校')):
        return 'college_below_count'
    if '本科' in value or '大学' in value:
        return 'undergraduate_count'
    return None


def _member_stats(plan, people, link, branch_id):
    override = link.member_ids.get(branch_id)
    if override is not None:
        available = {str(person.id) for person in people}
        if not set(override).issubset(available):
            plan['warnings'].append('指定统计成员的当前归属已变化，请核对统计时点名单。')
        members = list(PersonnelRoster.all_objects.filter(id__in=override))
        if len(members) != len(set(override)):
            plan['warnings'].append('部分指定统计成员的花名册记录已缺失，客观统计待核对。')
            return
    else:
        members = [person for person in people if is_middle_leader(person)
                   and (link.include_team_leaders or not is_team_lead(person))
                   and (link.include_designated_leaders or '内定' not in person.position_category)]
    if not members:
        plan['warnings'].append('班子统计成员为空，年龄、学历和任职年限统计待核对。')
        return
    cutoff = link.leadership_file.version_date
    ages = [_full_years(person.birth_date, cutoff) for person in members]
    education = [_education(person.highest_education or '') for person in members]
    dates = [person.current_position_date for person in members]
    if all(age is not None for age in ages):
        plan['values'].update(average_age=round(sum(ages) / len(ages), 2), max_age=max(ages), min_age=min(ages))
    else:
        plan['warnings'].append('部分统计成员缺少有效出生日期，年龄统计待补。')
    if all(education):
        counts = Counter(education)
        plan['values'].update({key: counts[key] for key in ['postgraduate_count', 'undergraduate_count', 'college_below_count']})
    else:
        plan['warnings'].append('部分统计成员最高学历未明确，学历人数待补。')
    if all(start and start <= cutoff for start in dates):
        plan['values'].update(under_3_years_count=sum(cutoff < _anniversary(start, 3) for start in dates),
                              over_5_years_count=sum(cutoff > _anniversary(start, 5) for start in dates),
                              three_to_5_years_count=sum(_anniversary(start, 3) <= cutoff <= _anniversary(start, 5) for start in dates))
    else:
        plan['warnings'].append('部分统计成员缺少有效任现职时间，任职年限人数待补。')


def _position_category(person):
    position = person.position or ''
    if is_team_lead(person):
        return PositionCategory.PRISON_TEAM if '监区' in person.department else PositionCategory.INSTITUTION_2
    if position == '监区长':
        return PositionCategory.PRISON_WARDEN
    if position == '教导员':
        return PositionCategory.INSTRUCTOR
    if '副' in position and '监区' in position:
        if '生产' in person.work_charge:
            return PositionCategory.DEPUTY_PRODUCTION
        if '教育' in person.work_charge:
            return PositionCategory.DEPUTY_EDUCATION
        return PositionCategory.DEPUTY_PRISON
    return PositionCategory.SECTION_DEPUTY if is_deputy(person) else PositionCategory.SECTION_CHIEF


def _merge_record(record, generated, old, protected):
    changed = {}
    for field, value in generated.items():
        current = getattr(record, field)
        comparable = current.isoformat() if isinstance(current, date) else current
        incoming = value.isoformat() if isinstance(value, date) else value
        if field == 'performance_by_year':
            annual = dict(current or {})
            previous = old.get(field) or {}
            for year in previous.keys() | value.keys():
                key = f'{field}.{year}'
                if key in protected:
                    continue
                if annual.get(year) != previous.get(year) and annual.get(year) != value.get(year):
                    protected.add(key)
                elif year in value:
                    annual[year] = value[year]
                else:
                    annual.pop(year, None)
            value = annual
        elif field in protected:
            continue
        elif comparable != old.get(field) and current not in (None, '', {}) and comparable != incoming:
            protected.add(field)
            continue
        elif field in old and comparable != old[field] and comparable != incoming:
            protected.add(field)
            continue
        if current != value:
            changed[field] = value
    return changed


def _save_plan(model, file, identity, plan, campaign, user):
    values = plan['values']
    record = model.objects.select_for_update().filter(file=file, source_object_id=identity).first()
    if not record:
        matching = {'file': file, 'name': values['name']}
        if model == AssessmentRecord:
            matching['department'] = values['department']
        record = model.objects.select_for_update().filter(**matching).first()
        if record and record.source_object_id and str(record.source_object_id) != identity:
            raise ValidationError(f'{values["name"]} 存在同名来源冲突，请核对研判表对象。')
    created = record is None
    if created:
        record = model(file=file, source_object_id=identity, **values)
        record.save()
        protected = set()
    else:
        previous = record.collection_data or {}
        protected = set(previous.get('protected_fields') or [])
        if not previous.get('campaign_id'):
            for field in values:
                current = getattr(record, field)
                if field == 'performance_by_year':
                    protected.update(f'{field}.{year}' for year in current or {})
                elif current not in (None, '', {}):
                    protected.add(field)
        changed = _merge_record(record, values, previous.get('last_values') or {}, protected)
        if changed:
            record = record_change(instance=record, validated_data=changed, user=user,
                                   resource_type=AssessmentChangeLog.ResourceType.CADRE_RECORD if model == AssessmentRecord
                                   else AssessmentChangeLog.ResourceType.LEADERSHIP_RECORD)
    collection_data = {
        'campaign_id': str(campaign.id), 'campaign_name': campaign.name,
        'source_task_ids': sorted(plan['source_task_ids']), 'field_sources': plan['sources'],
        'last_values': {key: value.isoformat() if isinstance(value, date) else value for key, value in values.items()},
        'protected_fields': sorted(protected), 'talk_notes': '\n'.join(plan['talk_notes']),
        'warnings': list(dict.fromkeys(plan['warnings'])),
    }
    if str(record.source_object_id or '') != identity or record.collection_data != collection_data:
        record.source_object_id = identity
        record.collection_data = collection_data
        record.save(update_fields=['source_object_id', 'collection_data', 'updated_at'])


@transaction.atomic
def sync_collection(campaign, user):
    link = AssessmentCollection.objects.select_for_update().select_related('leadership_file', 'cadre_file').filter(campaign=campaign).first()
    if not link:
        return None
    tasks = list(campaign.tasks.select_related('roster').order_by('created_at', 'id'))
    materials = build_materials(campaign)
    branches = {row['id']: _plan(row['name']) for row in materials['branches']}
    people = {}
    for unit in OrgUnit.objects.filter(id__in=branches):
        branch_id = str(unit.id)
        roster = roster_in_departments([unit.name, *[child.name for child in unit.get_descendants()]])
        _member_stats(branches[branch_id], roster, link, branch_id)
        people.update({str(person.id): person for person in roster if is_middle_leader(person)})
    ids = set()
    for task in tasks:
        context = task.context_json or {}
        for row in [context.get('roster') or {}, *(context.get('targets') or [])]:
            try:
                ids.add(UUID(str(row.get('id'))))
            except (ValueError, TypeError):
                continue
    people.update({str(person.id): person for person in PersonnelRoster.all_objects.filter(id__in=ids) if is_middle_leader(person)})
    cadres = {}
    for identity, person in people.items():
        plan = _plan(person.name, cadre=True)
        plan['values'].update(department=person.department, position=person.position, position_category=_position_category(person),
                              age=_full_years(person.birth_date, link.leadership_file.version_date), education=person.highest_education,
                              professional_title=person.technical_title, join_prison_date=person.join_prison_date,
                              service_years=_full_years(person.current_position_date, link.leadership_file.version_date),
                              main_business=person.work_charge)
        cadres[identity] = plan
    for task in tasks:
        if task.status != TaskStatus.SUBMITTED:
            continue
        context = task.context_json or {}
        payload = merge_payload(task.form_type, task.payload_json or {}, context)
        branch_plan = branches.get(str(task.branch_id or (context.get('branch') or {}).get('id') or ''))
        if task.form_type == FormType.ATTACHMENT_4 and branch_plan:
            branch_plan['values'].update({field: payload.get(key) for key, field in BRANCH_COUNTS.items()})
            branch_plan['values'].update({field: (payload.get('experience_counts') or {}).get(key) for key, field in EXPERIENCE_COUNTS.items()})
            branch_plan['values']['adjustment_suggestion'] = payload.get('adjustment_suggestion') or ''
            for field in [*BRANCH_COUNTS.values(), *EXPERIENCE_COUNTS.values(), 'adjustment_suggestion']:
                _source(branch_plan, task.id, field)
        if task.form_type == FormType.ATTACHMENT_2:
            cadre = cadres.get(str(task.roster_id or (context.get('roster') or {}).get('id') or ''))
            if cadre:
                for key, field in [('health', 'health_status'), ('main_business_lines', 'main_business'),
                                   ('rewards_last_3y', 'rewards_3years'), ('punishments_last_3y', 'penalties_3years')]:
                    if payload.get(key):
                        cadre['values'][field] = payload[key]
                        _source(cadre, task.id, field)
                for key, field in [('office_work_years', 'office_work_years'), ('prison_work_years', 'prison_work_years')]:
                    value = str(payload.get(key) or '')
                    if value.isdigit():
                        cadre['values'][field] = int(value)
                        _source(cadre, task.id, field)
        if task.form_type == FormType.ATTACHMENT_3:
            cadre = cadres.get(str(task.roster_id or (context.get('roster') or {}).get('id') or ''))
            if cadre:
                for item in payload.get('items') or []:
                    text = '\n'.join(filter(None, [item.get('experience'), item.get('key_work'),
                                                   '、'.join(item.get('roles') or []), item.get('details')]))
                    _text(cadre, 'main_performance', text, task.id)
        if task.form_type == FormType.ATTACHMENT_1 and branch_plan and payload.get('other'):
            branch_plan['talk_notes'].append('附件1支部整表其他情况\n' + payload['other'])
            _source(branch_plan, task.id, 'talk_assessment')
    for story in materials['stories']:
        branch = branches.get(story['branch_id'])
        text = '\n'.join(filter(None, [story['title'], story['description']]))
        if branch:
            _annual(branch, story['year'], text, story['source_task_id'])
            if story['year_source'] != '填报年度':
                branch['warnings'].append('旧述事采用批次年度，需核对实际材料年度。')
        for person in story['people']:
            cadre = cadres.get(person.get('roster_id'))
            if cadre:
                contribution = '\n'.join(filter(None, [text, '、'.join(person.get('roles') or []), person.get('task_and_role')]))
                _annual(cadre, story['year'], contribution, story['source_task_id'])
            elif not person.get('roster_id') and branch:
                branch['warnings'].append(f'述事人员「{person.get("name") or "未填姓名"}」尚未关联花名册，个人贡献待核对。')
    for review in materials['reviews']:
        plan = cadres.get(review.get('roster_id')) if review.get('roster_id') else branches.get(review['branch_id'])
        if not plan:
            continue
        for field in ('ability_assessment', 'shortcomings'):
            _text(plan, field, review.get(field) or '', review['source_task_id'])
        notes = review.get('talk_notes') or ''
        if notes:
            notes = f'{review["record_date"]} {review["interviewers"]}\n{notes}'
            plan['talk_notes'].append(notes)
            _source(plan, review['source_task_id'], 'talk_assessment')
            if review.get('roster_id'):
                _text(plan, 'talk_assessment', notes, review['source_task_id'])
    report = build_statistics(campaign)
    branch_scores = []
    for section in report['report_sections']:
        for row in section['rows']:
            identity = row['target_id']
            if section['key'] == 'recognition':
                group, _, identity = identity.partition(':')
                plan = branches.get(identity) if group == 'branch' else cadres.get(identity)
                if not plan:
                    continue
                if group != 'branch':
                    plan['values']['work_recognition_score'] = row['final_score']
                elif link.approval_rule != 'UNCONFIRMED' and row['final_score'] is not None:
                    counts = row['counts']
                    numerator = counts.get('认可', 0) + (counts.get('基本认可', 0) if link.approval_rule == 'RECOGNIZED_AND_BASIC' else 0)
                    plan['values']['approval_rate'] = numerator / sum(counts.values()) if sum(counts.values()) else None
                continue
            if row['dimension_key'] != 'overall':
                continue
            plan = branches.get(identity) if section['key'] == 'branch' else cadres.get(identity)
            if not plan:
                continue
            plan['values']['total_score' if section['key'] == 'branch' else 'seven_looks_score'] = row['final_score']
            if row['reason']:
                plan['warnings'].append(row['reason'])
            if section['key'] == 'branch':
                secretary = row['group_scores'].get(FillerRole.BRANCH_SECRETARY)
                plan['values']['secretary_score'] = float((Decimal(str(secretary)) * Decimal('.2')).quantize(Decimal('.01'), rounding=ROUND_DOWN)) if secretary is not None else None
                plan['values']['democratic_score'] = row['group_scores'].get(FillerRole.BRANCH_STAFF)
                branch_scores.append((identity, row['final_score']))
    for identity, plan in [*branches.items(), *cadres.items()]:
        for task in tasks:
            if task.form_type.startswith(('ATTACHMENT_6_', 'ATTACHMENT_7_')):
                context_ids = {str(row.get('id')) for row in (task.context_json or {}).get('targets') or []}
                if identity in context_ids:
                    _source(plan, task.id, '测评统计')
    if branch_scores and len(branch_scores) == len(branches) and all(score is not None for _, score in branch_scores):
        sorted_scores = sorted((score for _, score in branch_scores), reverse=True)
        for identity, score in branch_scores:
            branches[identity]['values']['ranking'] = sorted_scores.index(score) + 1
    for identity, plan in branches.items():
        _save_plan(LeadershipAssessmentRecord, link.leadership_file, identity, plan, campaign, user)
    for identity, plan in cadres.items():
        _save_plan(AssessmentRecord, link.cadre_file, identity, plan, campaign, user)
    link.leadership_file.total_records = link.leadership_file.records.count()
    link.leadership_file.save(update_fields=['total_records', 'updated_at'])
    link.cadre_file.total_records = link.cadre_file.records.count()
    link.cadre_file.category_counts = dict(Counter(link.cadre_file.records.values_list('position_category', flat=True)))
    link.cadre_file.save(update_fields=['total_records', 'category_counts', 'updated_at'])
    link.last_synced_at = timezone.now()
    link.warnings = ['客观数据取自当前花名册，请核对班子统计成员和历史期间人员情况。',
                     '干部综合研判评分、谈话评分和综合排名待计算口径确认。']
    if link.approval_rule == 'UNCONFIRMED':
        link.warnings.append('认可率口径待确认，已保留有效票数和认可度分数。')
    link.warnings.extend(f'{plan["values"]["name"]}：{warning}' for plan in [*branches.values(), *cadres.values()] for warning in plan['warnings'])
    link.warnings = list(dict.fromkeys(link.warnings))
    link.save(update_fields=['last_synced_at', 'warnings'])
    return collection_summary(link)
