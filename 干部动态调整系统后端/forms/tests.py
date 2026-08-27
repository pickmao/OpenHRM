from django.test import SimpleTestCase

from .serializers import FormTaskSerializer


class FormTaskSerializerTests(SimpleTestCase):
    def test_reports_whether_the_template_has_an_excel_source_file(self):
        class Template:
            source_file = None

        class Task:
            template = Template()

        serializer = FormTaskSerializer()

        self.assertFalse(serializer.get_template_has_source_file(Task()))

        Task.template.source_file = 'forms/templates/source.xlsx'
        self.assertTrue(serializer.get_template_has_source_file(Task()))
