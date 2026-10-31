"""Run the local backend using the database port selected by start-system.ps1."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '干部动态调整系统后端'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', '干部动态调整系统.settings')
from django.conf import settings

settings.DATABASES['default']['PORT'] = os.environ.get('OPENHRM_DB_PORT', '15432')
settings.DATABASES['default']['HOST'] = '127.0.0.1'
from django.core.management import execute_from_command_line

execute_from_command_line(['manage.py', 'runserver', '0.0.0.0:8000', '--noreload'])
