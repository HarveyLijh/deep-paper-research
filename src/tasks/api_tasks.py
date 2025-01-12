# src/tasks/api_tasks.py
from .celery_app import celery_app
from src.clients.semantic_scholar import SemanticScholarClient
from src.clients.gpt import GPTClient
from src.config.settings import settings

@celery_app.task(
    bind=True,
    name='semantic_scholar_call',
    rate_limit='100/m',
    retry_backoff=True
)
def get_paper_details(self, paper_id):
    """Make rate-limited call to Semantic Scholar API"""
    client = SemanticScholarClient(settings.SEMANTIC_SCHOLAR_API_KEY)
    try:
        return client.get_paper_details(paper_id)
    except Exception as exc:
        self.retry(exc=exc)

@celery_app.task(
    bind=True,
    name='gpt_call',
    rate_limit='60/m',
    retry_backoff=True
)
def analyze_paper_relevance(self, title, abstract, year):
    """Make rate-limited call to GPT API"""
    client = GPTClient(settings.OPENAI_API_KEY)
    try:
        return client.analyze_relevance(title, abstract, year)
    except Exception as exc:
        self.retry(exc=exc)

# Update docker-compose.yml to include Redis and Celery workers