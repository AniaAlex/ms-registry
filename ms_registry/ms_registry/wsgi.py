"""
WSGI config for ms_registry project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ms_registry.settings")

application = get_wsgi_application()
