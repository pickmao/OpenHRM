from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from .models import AssessmentFile


class AssessmentFileCleanupTests(TestCase):
    def setUp(self):
        self.media_dir = TemporaryDirectory()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(self.media_dir.cleanup)

    def test_delete_removes_source_file_after_transaction_commits(self):
        assessment_file = AssessmentFile.objects.create(
            version_date=date(2099, 1, 1),
            file_name='assessment.xlsx',
            source_file=SimpleUploadedFile('assessment.xlsx', b'workbook-content'),
        )
        source_path = Path(assessment_file.source_file.path)
        self.assertTrue(source_path.exists())

        with self.captureOnCommitCallbacks(execute=True):
            assessment_file.delete()

        self.assertFalse(source_path.exists())
