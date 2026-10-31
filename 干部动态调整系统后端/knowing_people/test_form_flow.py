from copy import deepcopy

from django.test import TestCase

from . import tests as existing_tests
from .models import FormType, InspectionTask


class AllFormsFlowTests(TestCase):
    setUp = existing_tests.KnowingPeopleApiTests.setUp
    dispatch = existing_tests.KnowingPeopleApiTests.dispatch

    def test_all_eleven_forms_save_submit_reload_and_return(self):
        campaign = self.dispatch(list(FormType.values), recipients=[
            {'form_type': form, 'user_id': str(self.middle.id), 'branch_id': str(self.branch.id)}
            for form in FormType.values
        ])
        self.assertEqual(campaign['progress']['total'], 11)
        self.client.force_authenticate(self.middle)
        matrix_scores = dict.fromkeys(['political', 'integrity', 'responsibility', 'style', 'thinking', 'frontline', 'performance'], '良')
        talk_scores = dict.fromkeys(['belief', 'serve', 'diligent', 'courage', 'clean'], '优')
        for task in InspectionTask.objects.all():
            with self.subTest(form=task.form_type):
                url = f'/api/knowing-people/tasks/{task.id}/'
                payload = deepcopy(self.client.get(url).data['payload'])
                payload.update(performance='实际完成情况', shortcomings='改进事项', other_issues='无')
                for target in payload.get('targets', []):
                    target['scores'] = dict(talk_scores if task.form_type == 'ATTACHMENT_1' else matrix_scores)
                    target['recognition'] = '不了解'
                if task.form_type == 'ATTACHMENT_2':
                    for row in payload['dimensions']:
                        row.update(grade='中', performance='按原表记录')
                elif task.form_type == 'ATTACHMENT_3':
                    payload.update(signature='中层乙', fill_date='2026-09-22', items=[
                        dict(experience='本年度任职', key_work='重点工作', roles=['主导者', '执行者'], details='完成任务')])
                elif task.form_type == 'ATTACHMENT_4':
                    payload.update(experience_counts=dict(office=1, balanced=2, prison=3), rectification='整改措施',
                                   team_requests='班子诉求', adjustment_needed='是', adjustment_suggestion='调整建议')
                    for row in payload['items']:
                        row.update(grade='差', performance='按原表记录')
                elif task.form_type == 'ATTACHMENT_5':
                    payload['works'] = [dict(title='重点工作', description='工作简要表述', people=[
                        dict(name='中层乙', roles=['主导者', '执行者'], task_and_role='具体任务')])]
                elif task.form_type == 'ATTACHMENT_6_2':
                    payload.update(scores=dict(matrix_scores), recognition='不了解')
                elif task.form_type == 'ATTACHMENT_1':
                    payload.update(personnel_category='党支部书记', branch_scores=dict(talk_scores))
                    for row in payload['overall']:
                        row['grade'] = '较好'
                saved = self.client.post(url + 'save-draft/', {'payload': payload}, format='json')
                self.assertEqual(saved.status_code, 200, saved.data)
                submitted = self.client.post(url + 'submit/', {'payload': payload}, format='json')
                self.assertEqual(submitted.status_code, 200, submitted.data)
                loaded = self.client.get(url)
                self.assertTrue(loaded.data['readonly'])
                for key in ('signature', 'fill_date', 'experience_counts', 'rectification', 'team_requests', 'adjustment_suggestion', 'works', 'recognition', 'branch_scores', 'personnel_category'):
                    if key in payload:
                        self.assertEqual(loaded.data['payload'][key], payload[key])
                self.assertEqual(self.client.post(url + 'save-draft/', {'payload': payload}, format='json').status_code, 400)
        self.client.force_authenticate(self.admin)
        progress = self.client.get(f'/api/knowing-people/campaigns/{campaign["id"]}/progress/')
        self.assertEqual(progress.status_code, 200, progress.data)
        self.assertEqual(progress.data['submitted_count'], 11)
        export = self.client.get(f'/api/knowing-people/campaigns/{campaign["id"]}/statistics-export/')
        self.assertEqual(export.status_code, 200)
        self.assertTrue(export.content.startswith(b'PK'))
        task = InspectionTask.objects.get(form_type='ATTACHMENT_7_4')
        returned = self.client.post(f'/api/knowing-people/tasks/{task.id}/return/', {'reason': '补充说明'}, format='json')
        self.assertEqual(returned.status_code, 200)
        progress = self.client.get(f'/api/knowing-people/campaigns/{campaign["id"]}/progress/')
        self.assertEqual(progress.data['submitted_count'], 10)
