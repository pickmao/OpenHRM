from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Role, User, UserRole

from .models import EvaluationEligibility, EvaluationResponse


class AnonymousEvaluationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(username='evaluation_admin', password='password', real_name='测评管理员')
        self.target = User.objects.create_user(username='target', password='password', real_name='被评价人')
        self.role = Role.objects.create(
            code='EVALUATOR', name='参评人员',
            permissions=['anonymous_evaluations:task:view', 'anonymous_evaluations:task:submit'],
        )
        self.raters = []
        for index in range(8):
            user = User.objects.create_user(username=f'rater_{index}', password='password', real_name=f'参评人{index}')
            UserRole.objects.create(user=user, role=self.role)
            self.raters.append(user)

    def create_and_publish_campaign(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post('/api/evaluations/campaigns/', {
            'name': '年度匿名测评',
            'deadline_at': (timezone.now() + timedelta(days=1)).isoformat(),
            'min_valid_responses': 8,
            'target_user_ids': [str(self.target.id)],
            'evaluator_user_ids': [str(user.id) for user in self.raters] + [str(self.target.id)],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['target_count'], 1)
        self.assertEqual(response.data['progress']['total'], 8)
        self.assertEqual(EvaluationEligibility.objects.count(), 8)
        campaign_id = response.data['id']
        response = self.client.post(f'/api/evaluations/campaigns/{campaign_id}/publish/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return campaign_id

    def submit(self, campaign_id, user):
        self.client.force_authenticate(user)
        tasks = self.client.get('/api/evaluations/tasks/my/')
        self.assertEqual(tasks.status_code, status.HTTP_200_OK)
        task = tasks.data[0]
        self.assertEqual(task['campaign_id'], campaign_id)
        response = self.client.post(
            f"/api/evaluations/tasks/{campaign_id}/{task['target_id']}/submit/",
            {'scores': {'political_quality': 4, 'performance': 5, 'integrity': 4}, 'comment': '建议保持务实作风。'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, {'detail': '匿名评价已提交。'})
        return task

    def test_submission_is_unlinked_and_results_are_threshold_protected(self):
        campaign_id = self.create_and_publish_campaign()
        for user in self.raters[:7]:
            self.submit(campaign_id, user)

        self.assertEqual(EvaluationResponse.objects.count(), 7)
        response = EvaluationResponse.objects.first()
        self.assertFalse(hasattr(response, 'submitted_by'))
        self.assertFalse(hasattr(response, 'eligibility'))

        self.client.force_authenticate(self.admin)
        results = self.client.get(f'/api/evaluations/campaigns/{campaign_id}/results/')
        self.assertEqual(results.status_code, status.HTTP_400_BAD_REQUEST)

        self.client.post(f'/api/evaluations/campaigns/{campaign_id}/close/')
        results = self.client.get(f'/api/evaluations/campaigns/{campaign_id}/results/')
        self.assertEqual(results.status_code, status.HTTP_200_OK)
        self.assertFalse(results.data['results'][0]['available'])
        self.assertNotIn('valid_response_count', results.data['results'][0])

    def test_duplicate_submission_is_rejected_and_aggregate_never_contains_raw_answers(self):
        campaign_id = self.create_and_publish_campaign()
        task = self.submit(campaign_id, self.raters[0])
        duplicate = self.client.post(
            f"/api/evaluations/tasks/{campaign_id}/{task['target_id']}/submit/",
            {'scores': {'political_quality': 4}}, format='json',
        )
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)

        for user in self.raters[1:]:
            self.submit(campaign_id, user)
        self.client.force_authenticate(self.admin)
        self.client.post(f'/api/evaluations/campaigns/{campaign_id}/close/')
        results = self.client.get(f'/api/evaluations/campaigns/{campaign_id}/results/')
        item = results.data['results'][0]
        self.assertTrue(item['available'])
        self.assertEqual(item['valid_response_count'], 8)
        self.assertNotIn('scores_json', item)
        self.assertNotIn('comment', item)
        self.assertNotIn('submitted_by', item)
