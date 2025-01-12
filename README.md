## Directory

```paper_discovery/
.
├── README.md
├── demo.py
├── main.py
├── migrations
│   ├── alembic.ini
│   └── versions
├── requirements.txt
├── results.txt
├── scripts
│   ├── db.py
│   └── run.py
├── src
│   ├── __init__.py
│   ├── clients
│   │   ├── __init__.py
│   │   ├── gpt.py
│   │   └── semantic_scholar.py
│   ├── config
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── database
│   │   ├── __init__.py
│   │   ├── manager.py
│   │   └── models.py
│   ├── monitoring
│   │   └── metrics.py
│   ├── services
│   │   ├── __init__.py
│   │   ├── exporters.py
│   │   └── paper_discovery.py
│   ├── tasks
│   │   ├── api_tasks.py
│   │   ├── celery_app.py
│   │   └── paper_tasks.py
│   └── utils
│       ├── __init__.py
│       └── logger.py
└── tests
    ├── __init__.py
    ├── conftest.py
    └── test_services

14 directories, 28 files

```

## commands

1. First initialize the database:

```bash
python scripts/db.py init
python scripts/db.py migrate "/+ year for paper"
python scripts/db.py upgrade
```

2. Run the discovery process:

```bash
# Test connection only
python scripts/run.py --check-only

# Run with default settings
python scripts/run.py

# Run with custom parameters
python scripts/run.py --max-papers 100 --max-depth 3 --topics-file custom_topics.json

python scripts/run.py --filter-papers --support-threshold 6.0
```

3. reset database

```bash
# Reset database
python scripts/manage_db.py reset
```
