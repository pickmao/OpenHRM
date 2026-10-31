from io import StringIO
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command, CommandError
from django.test import SimpleTestCase, override_settings


@override_settings(DEBUG=False)
class ProductionDemoCommandTests(SimpleTestCase):
    def test_production_requires_explicit_opt_in(self):
        with self.assertRaises(CommandError):
            call_command('seed_demo_data', stdout=StringIO())

    def test_production_requires_explicit_strong_password(self):
        for password in (None, 'short'):
            with self.subTest(password=password), self.assertRaises(CommandError):
                call_command('seed_demo_data', allow_production=True, password=password, stdout=StringIO())

    def test_stdin_password_is_not_printed_and_debug_stays_disabled(self):
        secret = 'Test-only-password-2026'
        output = StringIO()
        def seed(password):
            self.assertEqual(password, secret)
            self.assertFalse(settings.DEBUG)
            return {'created': 1, 'coverage': {}}
        with patch('accounts.management.commands.seed_demo_data.sys.stdin', StringIO(secret+'\n')), \
             patch('accounts.management.commands.seed_demo_data.User.objects.filter') as users, \
             patch('accounts.management.commands.seed_demo_data.seed_all', side_effect=seed) as seeder:
            users.return_value.exists.return_value = False
            call_command('seed_demo_data', allow_production=True, password_stdin=True, stdout=output)
            seeder.assert_called_once()
        self.assertNotIn(secret, output.getvalue())
        self.assertIn('demo_admin', output.getvalue())
