
# src/tasks/paper_tasks.py
from celery import chain, group
from .celery_app import celery_app
from src.database.manager import DatabaseManager
from src.services.paper_discovery import PaperDiscoveryService
from src.config.settings import settings

@celery_app.task(bind=True, name='process_paper')
def process_paper(self, paper_data, depth):
    """Process a single paper asynchronously"""
    try:
        # Initialize services (should use dependency injection in production)
        db = DatabaseManager(settings.DATABASE_URL)
        service = PaperDiscoveryService(...)
        
        # Process paper
        paper_id = paper_data['paper_id']
        
        # Check if already processed
        if paper_id in service.processed_papers:
            return
            
        # Get paper details
        paper_details = get_paper_details.delay(paper_id).get()
        if not paper_details:
            return
            
        # Analyze relevance
        relevance = analyze_paper_relevance.delay(
            paper_details['title'],
            paper_details['abstract'],
            paper_details.get('year', 0)
        ).get()
        
        # Save to database
        db.save_paper({**paper_details, **relevance})
        
        # Process references if relevant enough
        if depth < settings.MAX_REFERENCE_DEPTH and \
           relevance['score'] >= settings.RELEVANCE_THRESHOLD:
            # Process references in parallel
            reference_tasks = group(
                process_paper.s(ref_id, depth + 1)
                for ref_id in paper_details.get('references', [])
            )
            reference_tasks.apply_async()
            
    except Exception as exc:
        # Retry with exponential backoff
        self.retry(exc=exc, countdown=2 ** self.request.retries)

