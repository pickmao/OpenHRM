from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Role, User, UserRole
from cadres.models import PersonnelRoster
from orgs.models import Membership, OrgUnit

from .form_defs import SELF_DIMENSIONS, TEAM_DIMENSIONS
from .models import FormType, InspectionTask, TaskStatus


class KnowingPeopleApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(username='kp_admin', password='password', real_name='考察管理员')
        self.branch = OrgUnit.objects.create(name='一监区党支部', unit_type='BRANCH')
        self.office = OrgUnit.objects.create(name='一监区办公室', unit_type='DEPARTMENT', parent=self.branch)
        self.other_branch = OrgUnit.objects.create(name='二监区党支部', unit_type='BRANCH')

        self.filler_role = Role.objects.create(
            code='KP_FILLER', name='知事识人填报人',
            permissions=['knowing_people:task:view', 'knowing_people:task:submit'],
        )
        self.secretary = User.objects.create_user(username='secretary', password='password', real_name='书记甲')
        self.middle = User.objects.create_user(username='middle', password='password', real_name='中层乙')
        self.staff = User.objects.create_user(username='staff', password='password', real_name='民警丙')
        self.committee = User.objects.create_user(username='committee', password='password', real_name='委员丁')
        for user in [self.secretary, self.middle, self.staff, self.committee]:
            UserRole.objects.create(user=user, role=self.filler_role)

        Membership.objects.create(user=self.secretary, unit=self.branch, is_primary=True, is_manager=True, position='党支部书记')
        Membership.objects.create(user=self.middle, unit=self.office, is_primary=True, position='监区长')
        Membership.objects.create(user=self.staff, unit=self.office, is_primary=True, position='警员')
        Membership.objects.create(user=self.committee, unit=self.branch, is_primary=True, position='组织委员')

        self.chief_roster = PersonnelRoster.objects.create(
            serial_number=1, name='中层乙', department='一监区办公室', gender='M',
            position='监区长', position_rank='正科级', position_category='领导职务',
            current_position_years='3', political_status='中共党员',
        )
        PersonnelRoster.objects.create(
            serial_number=2, name='李副职', department='一监区办公室', gender='M',
            position='副监区长', position_rank='副科级', position_category='领导职务',
        )
        PersonnelRoster.objects.create(
            serial_number=3, name='王团队', department='一监区办公室', gender='M',
            position='工作团队负责人', position_category='监区工作团队正职',
        )
        PersonnelRoster.objects.create(
            serial_number=4, name='民警丙', department='一监区办公室', gender='M',
            position='警员', police_rank='一级警员',
        )

    def preview(self, form_types, **extra):
        self.client.force_authenticate(self.admin)
        payload = {'form_types': form_types, **extra}
        response = self.client.post('/api/knowing-people/campaigns/preview/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return response.data

    def dispatch(self, form_types, **extra):
        payload = {
            'name': '2026年知事识人考察',
            'year': '2026',
            'deadline_at': (timezone.now() + timedelta(days=7)).isoformat(),
            'form_types': form_types,
        }
        payload.update(extra)
        self.client.force_authenticate(self.admin)
        response = self.client.post('/api/knowing-people/campaigns/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return response.data

    def task_for(self, user, form_type):
        return InspectionTask.objects.get(assignee=user, form_type=form_type)

    def test_attachment8_auto_match(self):
        data = self.preview([
            'ATTACHMENT_2', 'ATTACHMENT_3', 'ATTACHMENT_4', 'ATTACHMENT_5',
            'ATTACHMENT_6_1', 'ATTACHMENT_6_2', 'ATTACHMENT_7_1', 'ATTACHMENT_7_2',
            'ATTACHMENT_7_3', 'ATTACHMENT_7_4', 'ATTACHMENT_1',
        ])
        names = {
            group['form_type']: {item['user_name'] for item in group['recipients']}
            for group in data['groups']
        }
        self.assertIn('中层乙', names['ATTACHMENT_2'])
        self.assertEqual(names['ATTACHMENT_2'], names['ATTACHMENT_3'])
        self.assertEqual(names['ATTACHMENT_4'], {'书记甲'})
        self.assertEqual(names['ATTACHMENT_5'], {'书记甲'})
        self.assertEqual(names['ATTACHMENT_6_1'], {'书记甲'})
        self.assertEqual(names['ATTACHMENT_7_1'], {'书记甲'})
        self.assertIn('民警丙', names['ATTACHMENT_6_2'])
        self.assertIn('委员丁', names['ATTACHMENT_7_4'])
        self.assertIn('民警丙', names['ATTACHMENT_7_4'])
        self.assertEqual(names['ATTACHMENT_7_3'], set())
        self.assertEqual(names['ATTACHMENT_1'], set())

    def test_dispatch_creates_tasks_and_prefills(self):
        campaign = self.dispatch(['ATTACHMENT_2', 'ATTACHMENT_7_1'])
        self.assertGreaterEqual(campaign['progress']['total'], 2)
        self.client.force_authenticate(self.middle)
        task = self.task_for(self.middle, FormType.ATTACHMENT_2)
        detail = self.client.get(f'/api/knowing-people/tasks/{task.id}/')
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(detail.data['payload']['name'], '中层乙')
        self.assertEqual(detail.data['payload']['unit'], '一监区办公室')
        self.assertIn('name', detail.data['payload']['prefill_fields'])

        self.client.force_authenticate(self.secretary)
        matrix = self.task_for(self.secretary, FormType.ATTACHMENT_7_1)
        detail = self.client.get(f'/api/knowing-people/tasks/{matrix.id}/')
        target_names = {item['name'] for item in detail.data['payload']['targets']}
        self.assertIn('中层乙', target_names)
        self.assertNotIn('王团队', target_names)

    def test_save_and_submit_self_eval(self):
        self.dispatch(['ATTACHMENT_2'])
        task = self.task_for(self.middle, FormType.ATTACHMENT_2)
        self.client.force_authenticate(self.middle)
        payload = {
            'signature': '中层乙',
            'unit': '一监区办公室',
            'name': '中层乙',
            'position_rank': '监区长 / 正科级',
            'dimensions': [
                {'key': item['key'], 'label': item['label'], 'performance': '表现正常', 'shortcomings': '需改进', 'grade': '优', 'highlights': ''}
                for item in SELF_DIMENSIONS
            ],
            'rectification': '加强一线',
            'personal_requests': '',
        }
        save = self.client.post(f'/api/knowing-people/tasks/{task.id}/save-draft/', {'payload': payload}, format='json')
        self.assertEqual(save.status_code, status.HTTP_200_OK, save.data)
        self.assertEqual(save.data['status'], TaskStatus.DRAFT)
        submit = self.client.post(f'/api/knowing-people/tasks/{task.id}/submit/', {'payload': payload}, format='json')
        self.assertEqual(submit.status_code, status.HTTP_200_OK, submit.data)
        self.assertEqual(submit.data['status'], TaskStatus.SUBMITTED)
        self.assertTrue(submit.data['readonly'])

        again = self.client.post(f'/api/knowing-people/tasks/{task.id}/save-draft/', {'payload': payload}, format='json')
        self.assertEqual(again.status_code, status.HTTP_400_BAD_REQUEST)

    def test_submit_matrix_requires_all_grades(self):
        self.dispatch(['ATTACHMENT_6_1'])
        task = self.task_for(self.secretary, FormType.ATTACHMENT_6_1)
        self.client.force_authenticate(self.secretary)
        detail = self.client.get(f'/api/knowing-people/tasks/{task.id}/')
        payload = detail.data['payload']
        response = self.client.post(f'/api/knowing-people/tasks/{task.id}/submit/', {'payload': payload}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        for target in payload['targets']:
            target['scores'] = {item['key']: '优' for item in TEAM_DIMENSIONS}
        response = self.client.post(f'/api/knowing-people/tasks/{task.id}/submit/', {'payload': payload}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_matrix_open_questions_saved_on_61_and_71(self):
        self.dispatch(['ATTACHMENT_6_1', 'ATTACHMENT_7_1'])
        self.client.force_authenticate(self.secretary)

        task61 = self.task_for(self.secretary, FormType.ATTACHMENT_6_1)
        payload61 = self.client.get(f'/api/knowing-people/tasks/{task61.id}/').data['payload']
        self.assertEqual(payload61.get('performance'), '')
        self.assertEqual(payload61.get('shortcomings'), '')
        self.assertEqual(payload61.get('other_issues'), '')
        payload61['performance'] = '6-1现实表现'
        payload61['shortcomings'] = '6-1存在不足'
        payload61['other_issues'] = '6-1其他情况'
        draft = self.client.post(f'/api/knowing-people/tasks/{task61.id}/save-draft/', {'payload': payload61}, format='json')
        self.assertEqual(draft.status_code, status.HTTP_200_OK, draft.data)
        self.assertEqual(draft.data['payload']['performance'], '6-1现实表现')
        self.assertEqual(draft.data['payload']['shortcomings'], '6-1存在不足')
        self.assertEqual(draft.data['payload']['other_issues'], '6-1其他情况')

        for target in payload61['targets']:
            target['scores'] = {item['key']: '良' for item in TEAM_DIMENSIONS}
        submit61 = self.client.post(f'/api/knowing-people/tasks/{task61.id}/submit/', {'payload': payload61}, format='json')
        self.assertEqual(submit61.status_code, status.HTTP_200_OK, submit61.data)
        self.assertTrue(submit61.data['readonly'])
        self.assertEqual(submit61.data['payload']['performance'], '6-1现实表现')
        self.assertEqual(submit61.data['payload']['other_issues'], '6-1其他情况')

        task71 = self.task_for(self.secretary, FormType.ATTACHMENT_7_1)
        payload71 = self.client.get(f'/api/knowing-people/tasks/{task71.id}/').data['payload']
        payload71['performance'] = '7-1现实表现'
        payload71['shortcomings'] = '7-1存在不足'
        payload71['other_issues'] = '7-1其他情况'
        for target in payload71['targets']:
            target['scores'] = {item['key']: '中' for item in TEAM_DIMENSIONS}
        submit71 = self.client.post(f'/api/knowing-people/tasks/{task71.id}/submit/', {'payload': payload71}, format='json')
        self.assertEqual(submit71.status_code, status.HTTP_200_OK, submit71.data)
        self.assertEqual(submit71.data['payload']['performance'], '7-1现实表现')
        self.assertEqual(submit71.data['payload']['shortcomings'], '7-1存在不足')
        self.assertEqual(submit71.data['payload']['other_issues'], '7-1其他情况')

    def test_progress_return_and_remind(self):
        campaign = self.dispatch(['ATTACHMENT_2', 'ATTACHMENT_3'])
        campaign_id = campaign['id']
        task = self.task_for(self.middle, FormType.ATTACHMENT_2)
        self.client.force_authenticate(self.admin)
        remind = self.client.post(f'/api/knowing-people/tasks/{task.id}/remind/')
        self.assertEqual(remind.status_code, status.HTTP_200_OK)
        self.assertEqual(remind.data['remind_count'], 1)

        self.client.force_authenticate(self.middle)
        payload = {
            'name': '中层乙', 'unit': '一监区',
            'dimensions': [
                {'key': item['key'], 'label': item['label'], 'performance': '有表现', 'grade': '良'}
                for item in SELF_DIMENSIONS
            ],
        }
        self.client.post(f'/api/knowing-people/tasks/{task.id}/submit/', {'payload': payload}, format='json')

        self.client.force_authenticate(self.admin)
        progress = self.client.get(f'/api/knowing-people/campaigns/{campaign_id}/progress/')
        self.assertEqual(progress.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(progress.data['progress']['submitted'], 1)
        self.assertTrue(any(row['form_type'] == 'ATTACHMENT_2' for row in progress.data['votes']))

        returned = self.client.post(
            f'/api/knowing-people/tasks/{task.id}/return/',
            {'reason': '请补充整改措施'},
            format='json',
        )
        self.assertEqual(returned.status_code, status.HTTP_200_OK, returned.data)
        self.assertEqual(returned.data['status'], TaskStatus.RETURNED)

    def test_manual_types_need_extra_users(self):
        self.client.force_authenticate(self.admin)
        empty = self.client.post(
            '/api/knowing-people/campaigns/',
            {
                'name': '仅7-3',
                'deadline_at': (timezone.now() + timedelta(days=3)).isoformat(),
                'form_types': ['ATTACHMENT_7_3'],
            },
            format='json',
        )
        self.assertEqual(empty.status_code, status.HTTP_400_BAD_REQUEST)

        campaign = self.dispatch(
            ['ATTACHMENT_7_3'],
            extra_user_ids_by_type={'ATTACHMENT_7_3': [str(self.admin.id)]},
        )
        self.assertEqual(campaign['progress']['total'], 1)
        self.assertTrue(InspectionTask.objects.filter(form_type='ATTACHMENT_7_3', assignee=self.admin).exists())

    def test_ordinary_user_cannot_dispatch(self):
        self.client.force_authenticate(self.middle)
        response = self.client.post(
            '/api/knowing-people/campaigns/',
            {
                'name': '越权',
                'deadline_at': (timezone.now() + timedelta(days=3)).isoformat(),
                'form_types': ['ATTACHMENT_2'],
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
