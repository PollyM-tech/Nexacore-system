##Project structure

billing-system/
│
├── frontend/                  # Your teammate
│
├── backend/                   # Your work
│   ├── app/
│   │   ├── api/
│   │   ├── models/
│   │   ├── services/
│   │   ├── extensions.py
│   │   ├── config.py
│   │   └── __init__.py
│   │
│   ├── tests/
│   ├── migrations/
│   ├── .env
│   ├── .env.example
│   ├── requirements.txt
│   └── wsgi.py
│
├── radius/                    # Later
├── docker/                    # Later
├── docs/
└── README.md


The frontend should never talk directly to PostgreSQL, MikroTik, FreeRADIUS, or M-PESA.

Everything goes through:

React
   │
   │ HTTP / JSON
   ▼
Flask API
   │
   ├── PostgreSQL
   ├── M-PESA
   ├── FreeRADIUS
   └── MikroTik