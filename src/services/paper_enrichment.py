import logging
from typing import Dict, Any
from datetime import datetime
from ..database.manager import DatabaseManager
from ..clients.semantic_scholar import SemanticScholarClient

logger = logging.getLogger(__name__)

class PaperEnrichmentService:
    def __init__(
        self,
        semantic_scholar_client: SemanticScholarClient,
        db_manager: DatabaseManager,
        support_threshold: float = 6.0
    ):
        self.semantic_scholar = semantic_scholar_client
        self.db = db_manager
        self.support_threshold = support_threshold

    def enrich_papers(self) -> Dict[str, int]:
        """Enrich papers with additional metadata from Semantic Scholar"""
        stats = {
            'processed': 0,
            'enriched': 0,
            'errors': 0
        }

        # Get papers above threshold
        papers = self.db.get_papers_above_threshold(self.support_threshold)
        
        for paper in papers:
            try:
                logger.info(f"Enriching paper {paper.paper_id}")
                
                # Get detailed paper info
                details = self.semantic_scholar.get_paper_details(paper.paper_id)
                if not details:
                    continue

                # Safely get nested values
                pdf_url = None
                if isinstance(details.get('openAccessPdf'), dict):
                    pdf_url = details['openAccessPdf'].get('url')
                elif isinstance(details.get('openAccessPdf'), str):
                    pdf_url = details['openAccessPdf']

                journal_name = None
                if isinstance(details.get('journal'), dict):
                    journal_name = details['journal'].get('name')
                elif isinstance(details.get('journal'), str):
                    journal_name = details['journal']

                # Update paper with new fields
                updates = {
                    'year': details.get('year'),
                    'venue': details.get('venue'),
                    'journal': journal_name,
                    'url': details.get('url'),
                    'is_open_access': bool(details.get('isOpenAccess', False)),
                    'pdf_url': pdf_url
                }
                
                self.db.update_paper_metadata(paper.paper_id, updates)
                stats['enriched'] += 1
                
            except Exception as e:
                logger.error(f"Error enriching paper {paper.paper_id}: {str(e)}")
                stats['errors'] += 1
                continue
                
            stats['processed'] += 1
            
        return stats
