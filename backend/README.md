# Lintech Backend

Django REST API for ISP billing, customer management, MikroTik integration,
OLT/ONU monitoring, bandwidth tracking, SMS, scheduling, reporting, and
customer self-service.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver