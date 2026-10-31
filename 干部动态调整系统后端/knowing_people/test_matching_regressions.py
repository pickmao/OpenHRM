from django.test import TestCase

from accounts.models import User
from cadres.models import PersonnelRoster
from orgs.models import Membership, OrgUnit
from .matching import build_context_for_recipient, match_form_type, match_user_for_roster, users_by_real_name
from .models import FillerRole, FormType


class MatchingRegressions(TestCase):
    def setUp(self):
        self.a = OrgUnit.objects.create(name='甲支部', unit_type='BRANCH')
        self.b = OrgUnit.objects.create(name='乙支部', unit_type='BRANCH')
        self.office = OrgUnit.objects.create(name='甲办公室', parent=self.a, unit_type='DEPARTMENT')
        self.user = User.objects.create_user(username='user', real_name='填报人')
        Membership.objects.create(user=self.user, unit=self.office, position='警员')

    def person(self, name, department, **extra):
        return PersonnelRoster.objects.create(serial_number=PersonnelRoster.objects.count()+1,
                                               name=name, department=department, **extra)

    def context(self, form, branch=None, user=None):
        item = {'user_id': str((user or self.user).id), 'form_type': form}
        if branch:
            item['branch_id'] = str(branch.id)
        return build_context_for_recipient(item)

    def test_selected_branch_replaces_primary_and_missing_scope_stays_empty(self):
        self.person('甲民警', self.office.name)
        other = self.person('乙民警', self.b.name)
        for form in [FormType.ATTACHMENT_1, FormType.ATTACHMENT_7_4]:
            self.assertEqual([x['id'] for x in self.context(form, self.b)['targets']], [str(other.id)])
            no_scope = User.objects.create_user(username='none'+form)
            self.assertEqual(self.context(form, user=no_scope)['targets'], [])
        empty = OrgUnit.objects.create(name='空支部', unit_type='BRANCH')
        self.assertEqual(self.context(FormType.ATTACHMENT_7_4, empty)['targets'], [])

    def test_leader_lists_are_global_and_rank_precedes_job_title(self):
        chief = self.person('正职', self.b.name, position='副主任', position_rank='正科级', position_category='领导职务')
        deputy = self.person('副职', self.b.name, position='主任', position_rank='副科级', position_category='领导职务')
        team = self.person('团队', self.b.name, position='负责人', position_category='监区工作团队正职')
        self.person('普通警员', self.b.name, position='警员', position_rank='正科级')
        for form, expected in [(FormType.ATTACHMENT_7_1, chief), (FormType.ATTACHMENT_7_2, deputy), (FormType.ATTACHMENT_7_3, team)]:
            self.assertEqual([x['id'] for x in self.context(form)['targets']], [str(expected.id)])

    def test_inactive_and_generic_manager_never_become_secretary(self):
        Membership.objects.filter(user=self.user).update(is_manager=True)
        inactive = User.objects.create_user(username='inactive', is_active=False)
        Membership.objects.create(user=inactive, unit=self.a, position='党支部书记')
        self.assertEqual(match_form_type(FormType.ATTACHMENT_6_1)['recipients'], [])
        self.assertNotIn(str(inactive.id), [x['user_id'] for x in match_form_type(FormType.ATTACHMENT_6_2)['recipients']])

    def test_secretary_priority_and_all_memberships_committee_classification(self):
        deputy = User.objects.create_user(username='deputy', real_name='副书记')
        Membership.objects.create(user=deputy, unit=self.a, position='党支部副书记', is_manager=True)
        Membership.objects.create(user=self.user, unit=self.a, position='党支部书记', is_primary=False)
        selected = match_form_type(FormType.ATTACHMENT_6_1)['recipients']
        self.assertEqual([x['user_id'] for x in selected], [str(self.user.id)])
        members = match_form_type(FormType.ATTACHMENT_7_4)['recipients']
        self.assertEqual(len(members), 2)
        self.assertEqual({x['user_id']: x['filler_role'] for x in members}, {
            str(self.user.id): FillerRole.BRANCH_SECRETARY,
            str(deputy.id): FillerRole.BRANCH_DEPUTY_SECRETARY,
        })

    def test_ambiguous_names_require_unique_department_evidence(self):
        person = self.person('重名', self.office.name, position_category='领导职务')
        one = User.objects.create_user(username='one', real_name='重名')
        two = User.objects.create_user(username='two', real_name='重名')
        self.assertIsNone(match_user_for_roster(person, users_by_real_name()))
        Membership.objects.create(user=one, unit=self.office)
        self.assertEqual(match_user_for_roster(person, users_by_real_name()), one)
        Membership.objects.create(user=two, unit=self.office)
        self.assertIsNone(match_user_for_roster(person, users_by_real_name()))
        self.assertTrue(match_form_type(FormType.ATTACHMENT_2)['unmatched'])

    def test_roster_members_without_memberships_and_unmatched_people_are_visible(self):
        account = User.objects.create_user(username='roster', real_name='花名册成员')
        self.person(account.real_name, self.b.name)
        self.person('缺账号', self.b.name)
        result = match_form_type(FormType.ATTACHMENT_6_2, branch_ids=[self.b.id])
        self.assertEqual([x['user_id'] for x in result['recipients']], [str(account.id)])
        self.assertEqual([x['name'] for x in result['unmatched']], ['缺账号'])

    def test_multibranch_secretary_retains_one_task_for_each_branch(self):
        Membership.objects.create(user=self.user, unit=self.a, position='党支部书记')
        Membership.objects.create(user=self.user, unit=self.b, position='党支部书记')
        result = match_form_type(FormType.ATTACHMENT_5)
        self.assertEqual({x['branch_id'] for x in result['recipients']}, {str(self.a.id), str(self.b.id)})
        for form in [FormType.ATTACHMENT_6_1, FormType.ATTACHMENT_7_1, FormType.ATTACHMENT_7_2]:
            self.assertEqual(len(match_form_type(form)['recipients']), 1)

    def test_current_roster_department_prevents_stale_staff_dispatch(self):
        self.person(self.user.real_name, self.b.name)
        result = match_form_type(FormType.ATTACHMENT_7_4)
        self.assertEqual([(x['user_id'], x['branch_id']) for x in result['recipients']],
                         [(str(self.user.id), str(self.b.id))])

    def test_branch_rating_does_not_default_to_all_branches(self):
        no_scope = User.objects.create_user(username='unaffiliated')
        self.assertEqual(self.context(FormType.ATTACHMENT_6_2, user=no_scope)['targets'], [])
        self.assertEqual([x['id'] for x in self.context(FormType.ATTACHMENT_6_2, self.b)['targets']],
                         [str(self.b.id)])
