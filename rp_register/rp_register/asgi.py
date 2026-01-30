"""
ASGI config for rp_register project.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rp_register.settings")

application = get_asgi_application()
