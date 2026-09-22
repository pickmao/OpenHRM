from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from .form_defs import default_payload, merge_payload, validate_payload, schema_for
from .models import FormType


class OriginalWorkbookAlignmentTests(SimpleTestCase):
    def test_seven_dimensions_and_four_self_grades(self):
        payload = default_payload(FormType.ATTACHMENT_2)
        payload.update(name='测试', unit='一支部')
        self.assertEqual(len(payload['dimensions']), 7)
        for row in payload['dimensions']:
            row.update(grade='差', performance='待改进')
        validate_payload(FormType.ATTACHMENT_2, payload, strict=True)
        schema = schema_for(FormType.ATTACHMENT_6_2)
        self.assertEqual(len(schema['team_dimensions']), 7)
        self.assertEqual(schema['team_dimensions'][-1]['key'], 'performance')

    def test_recognition_and_seventh_dimension_required_on_submit(self):
        payload = default_payload(FormType.ATTACHMENT_6_2, {'branch': {'id': 1, 'name': '一支部'}})
        payload['scores'] = {key: '良' for key in payload['scores']}
        with self.assertRaises(ValidationError):
            validate_payload(FormType.ATTACHMENT_6_2, payload, strict=True)
        payload['recognition'] = '不了解'
        validate_payload(FormType.ATTACHMENT_6_2, payload, strict=True)
        del payload['scores']['performance']
        with self.assertRaises(ValidationError):
            validate_payload(FormType.ATTACHMENT_6_2, payload, strict=True)
        validate_payload(FormType.ATTACHMENT_6_2, payload, strict=False)

    def test_recognition_is_per_cadre(self):
        ctx = {'targets': [{'id': 1, 'name': '甲'}, {'id': 2, 'name': '乙'}]}
        payload = default_payload(FormType.ATTACHMENT_7_4, ctx)
        for target in payload['targets']:
            target['scores'] = {key: '优' for key in target['scores']}
        payload['targets'][0]['recognition'] = '认可'
        with self.assertRaises(ValidationError):
            validate_payload(FormType.ATTACHMENT_7_4, payload, strict=True)
        payload['targets'][1]['recognition'] = '不认可'
        validate_payload(FormType.ATTACHMENT_7_4, payload, strict=True)
        merged = merge_payload(FormType.ATTACHMENT_7_4, payload, ctx)
        self.assertEqual([t['recognition'] for t in merged['targets']], ['认可', '不认可'])

    def test_old_talk_answers_not_relabelled_or_discarded(self):
        stored = {'overall': [{'key': 'overall', 'label': '对班子的总体评价', 'grade': '好'}], 'issues': ['weak_politics']}
        merged = merge_payload(FormType.ATTACHMENT_1, stored, {})
        self.assertEqual(len(merged['overall']), 3)
        self.assertTrue(all(not row['grade'] for row in merged['overall']))
        self.assertEqual(merged['legacy_overall'], stored['overall'])
        self.assertEqual(merged['legacy_issues'], ['weak_politics'])
        self.assertEqual(merged['issues'], [])
        self.assertEqual(len(merged['branch_scores']), 5)
        self.assertEqual(merge_payload(FormType.ATTACHMENT_1, merged, {})['legacy_overall'], stored['overall'])

    def test_missing_fields_and_legacy_experience_preserved(self):
        team = merge_payload(FormType.ATTACHMENT_4, {'experience_structure': '长期在机关'}, {})
        self.assertEqual(team['experience_structure'], '长期在机关')
        self.assertEqual(team['experience_counts'], {'office': None, 'balanced': None, 'prison': None})
        for field in ['rectification', 'team_requests', 'adjustment_needed', 'adjustment_suggestion']:
            self.assertIn(field, team)
        story = default_payload(FormType.ATTACHMENT_3)
        self.assertIn('signature', story)
        self.assertIn('fill_date', story)
        self.assertIn('description', default_payload(FormType.ATTACHMENT_5)['works'][0])

    def test_original_guidance_restored_but_answers_preserved(self):
        stored = {'items': [{'key': 'political_direction', 'content': '旧要点', 'grade': '良', 'performance': '原填报', 'shortcomings': '原不足'}]}
        merged = merge_payload(FormType.ATTACHMENT_4, stored, {})
        self.assertIn('旗帜鲜明讲政治', merged['items'][0]['content'])
        self.assertEqual(merged['items'][0]['performance'], '原填报')
        self.assertEqual(merged['items'][0]['grade'], '良')
