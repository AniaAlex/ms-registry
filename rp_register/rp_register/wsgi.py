"""
WSGI config for rp_register project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rp_register.settings")

application = get_wsgi_application()
