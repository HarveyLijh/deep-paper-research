# src/clients/semantic_scholar.py
from typing import List, Dict, Any, Optional
import time
from functools import wraps
import logging
from semanticscholar import SemanticScholar

logger = logging.getLogger(__name__)

def rate_limit(calls: int, period: float):
    """Rate limiting decorator"""
    min_interval = period / float(calls)
    last_call = [0.0]  # Using list to maintain state in closure

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_call[0]
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            result = func(*args, **kwargs)
            last_call[0] = time.time()
            return result
        return wrapper
    return decorator

class SemanticScholarClient:
    """Wrapper for Semantic Scholar API with rate limiting and error handling"""
    
    def __init__(self, max_retries: int = 3):
        self.client = SemanticScholar()
        self.max_retries = max_retries

    def _handle_request(self, func, *args, **kwargs):
        """Generic error handling wrapper"""
        retries = 0
        while retries < self.max_retries:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                retries += 1
                if retries == self.max_retries:
                    logger.error(f"Failed after {retries} retries: {str(e)}")
                    raise
                logger.warning(f"Attempt {retries} failed: {str(e)}. Retrying...")
                time.sleep(2 ** retries)  # Exponential backoff

    @rate_limit(calls=100, period=60)  # 100 calls per minute
    def search_papers(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Search papers with rate limiting and pagination handling"""
        logger.info(f"Searching papers with query: {query}")
        
        # Ensure limit is within valid range (1-100)
        if limit <= 0:
            limit = 100
        elif limit > 100:
            limit = 100
            
        try:
            response = self._handle_request(
                self.client.search_paper,
                query,
                limit=limit,
                fields=[
                    'paperId',
                    'title',
                    'abstract',
                    'authors',
                    'year',
                    'citationCount',
                    'referenceCount'
                ]
            )
            
            logger.info(f"Received responses {response}\n{str(response)}")
            
            if not response or not hasattr(response, '__iter__'):
                logger.warning(f"No results found for query: {query}")
                return []
            
            papers = []
            for paper in response:
                try:
                    if not hasattr(paper, 'paperId') or not paper.paperId:
                        continue
                        
                    paper_data = {
                        'paper_id': paper.paperId,
                        'title': getattr(paper, 'title', ''),
                        'abstract': getattr(paper, 'abstract', ''),
                        'authors': [
                            {'name': getattr(author, 'name', ''), 
                             'id': getattr(author, 'authorId', '')}
                            for author in (getattr(paper, 'authors', []) or [])
                        ],
                        'year': getattr(paper, 'year', None),
                        'citation_count': getattr(paper, 'citationCount', 0),
                        'reference_count': getattr(paper, 'referenceCount', 0),
                    }
                    papers.append(paper_data)
                except AttributeError as e:
                    logger.warning(f"Failed to process paper: {str(e)}")
                    continue
                    
            return papers
            
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {str(e)}")
            return []

    @rate_limit(calls=100, period=60)
    def get_paper_details(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed paper information"""
        logger.info(f"Fetching details for paper: {paper_id}")
        paper = self._handle_request(
            self.client.get_paper,
            paper_id,
            fields=[
                'paperId',
                'title',
                'abstract',
                'authors',
                'year',
                'citationCount',
                'referenceCount',
                'references',
                'citations',
                'venue',
                'journal',
                'url',
                'isOpenAccess',
                'openAccessPdf'
            ]
        )
        
        if not paper:
            return None
            
        return {
            'paper_id': paper.paperId,
            'title': paper.title,
            'abstract': paper.abstract,
            'authors': [
                {'name': author.name, 'id': author.authorId}
                for author in paper.authors or []
            ],
            'year': paper.year,
            'citation_count': paper.citationCount,
            'reference_count': paper.referenceCount,
            'references': [ref.paperId for ref in paper.references or []],
            'citations': [cit.paperId for cit in paper.citations or []],
            'venue': paper.venue,
            'journal': getattr(paper.journal, 'name', None) if paper.journal else None,
            'url': paper.url,
            'isOpenAccess': paper.isOpenAccess,
            'openAccessPdf': paper.openAccessPdf.get('url') if paper.openAccessPdf else None
        }

    @rate_limit(calls=100, period=60)
    def get_references(self, paper_id: str, limit: int = 100) -> List[str]:
        """Get paper references"""
        logger.info(f"Fetching references for paper: {paper_id}")
        refs = self._handle_request(
            self.client.get_paper_references,
            paper_id,
            limit=limit
        )
        return [ref.paperId for ref in refs or []]

    @rate_limit(calls=100, period=60)
    def get_citations(self, paper_id: str, limit: int = 100) -> List[str]:
        """Get paper citations"""
        logger.info(f"Fetching citations for paper: {paper_id}")
        citations = self._handle_request(
            self.client.get_paper_citations,
            paper_id,
            limit=limit
        )
        return [cit.paperId for cit in citations or []]