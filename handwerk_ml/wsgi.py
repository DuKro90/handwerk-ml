"""
WSGI config for handwerk_ml project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'handwerk_ml.settings')

application = get_wsgi_application()
