# src/services/paper_discovery.py
from typing import List, Dict, Any, Set
import logging
from datetime import datetime as dt, timezone, timedelta
import json
import csv
from pathlib import Path

from ..clients.semantic_scholar import SemanticScholarClient
from ..clients.gpt import GPTClient
from ..database.manager import DatabaseManager
from ..config.settings import settings

logger = logging.getLogger(__name__)

class PaperDiscoveryService:
    def __init__(
        self,
        semantic_scholar_client: SemanticScholarClient,
        gpt_client: GPTClient,
        db_manager: DatabaseManager,
        max_papers_per_search: int = 100,
        max_reference_depth: int = 2,
        relevance_threshold: float = 0.7
    ):
        self.semantic_scholar = semantic_scholar_client
        self.gpt = gpt_client
        self.db = db_manager
        self.max_papers_per_search = max_papers_per_search
        self.max_reference_depth = max_reference_depth
        self.relevance_threshold = relevance_threshold
        self.processed_papers: Set[str] = set()
        
    def discover_papers(self, topics: List[str]) -> None:
        """Main discovery process for a list of research topics"""
        logger.info(f"Starting paper discovery for topics: {topics}")
        
        # Process each topic
        for topic in topics:
            self._process_topic(topic)
            
        # Export results
        self._export_results()
        
    def _process_topic(self, topic: str) -> None:
        """Process a single research topic"""
        logger.info(f"Processing topic: {topic}")
        
        # Generate search queries using GPT
        search_queries = self.gpt.generate_search_queries(topic)
        
        # Process each search query
        for query in search_queries:
            logger.info(f"Processing search query: {query}")
            
            # Initialize pagination
            offset = 0
            total_results = []
            max_results = min(self.max_papers_per_search, 1000)  # Respect API limit
            
            # Fetch papers with pagination
            while offset < max_results:
                papers = self.semantic_scholar.search_papers(
                    query,
                    limit=min(max_results, 100)
                )
                
                if not papers:
                    break
                    
                total_results.extend(papers)
                offset += len(papers)
                
                if len(total_results) >= max_results:
                    break
            
            try:
                # Log the search and get the ID
                search_log = self.db.log_search(query, len(total_results), "keyword")
                search_log_id = search_log.id if search_log else None
                
                if search_log_id is not None:
                    # Process each paper
                    for paper in total_results:
                        self._process_paper(paper, depth=0)
                        # Link paper to search query with the ID
                        self.db.link_paper_to_query(paper['paper_id'], search_log_id)
            except Exception as e:
                logger.error(f"Error processing query {query}: {str(e)}")
                continue
                
    def _process_paper(self, paper_data: Dict[str, Any], depth: int) -> None:
        """Process a single paper and its references"""
        paper_id = paper_data['paper_id']
        
        # Skip if already processed
        if paper_id in self.processed_papers:
            logger.debug(f"Skipping already processed paper: {paper_id}")
            return
            
        logger.info(f"Processing paper: {paper_id} at depth {depth}")
        self.processed_papers.add(paper_id)
        
        # Get full paper details if we don't have them
        if 'abstract' not in paper_data:
            paper_details = self.semantic_scholar.get_paper_details(paper_id)
            if not paper_details:
                logger.warning(f"Could not get details for paper: {paper_id}")
                return
            paper_data.update(paper_details)
        
        # Analyze relevance using GPT
        if paper_data.get('abstract'):
            relevance = self.gpt.analyze_relevance(
                paper_data['title'],
                paper_data['abstract'],
                paper_data.get('year', 0)
            )
        else:
            relevance = {'score': 0.5, 'reasoning': 'No abstract available'}
        
        # Save paper to database FIRST
        paper_data['relevance_score'] = relevance['score']
        paper_data['relevance_reasoning'] = relevance['reasoning']
        try:
            self.db.save_paper(paper_data)
            
            # Extract and save concepts AFTER paper is saved
            if paper_data.get('abstract'):
                try:
                    concepts = self.gpt.extract_concepts(
                        paper_data['title'],
                        paper_data['abstract']
                    )
                    self.db.save_paper_concepts(paper_id, concepts)
                except Exception as e:
                    logger.error(f"Failed to extract/save concepts for paper {paper_id}: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to save paper {paper_id}: {str(e)}")
            return

        # If paper is relevant enough and we haven't hit depth limit,
        # process references and generate new searches
        if relevance['score'] >= self.relevance_threshold and depth < self.max_reference_depth:
            # Save and process references
            if 'references' in paper_data:
                self.db.save_references(paper_id, paper_data['references'])
                for ref_id in paper_data['references']:
                    ref_paper = self.semantic_scholar.get_paper_details(ref_id)
                    if ref_paper:
                        self._process_paper(ref_paper, depth + 1)
            
            # Save citations
            if 'citations' in paper_data:
                self.db.save_citations(paper_id, paper_data['citations'])
            
            # Generate new search queries based on paper content
            if depth == 0:  # Only expand search space from top-level papers
                new_queries = self.gpt.expand_search_space(paper_data)
                for query in new_queries:
                    papers = self.semantic_scholar.search_papers(
                        query,
                        limit=self.max_papers_per_search
                    )
                    search_log = self.db.log_search(query, len(papers), "expansion")
                    for paper in papers:
                        self._process_paper(paper, depth + 1)
                        # Link paper to search query
                        self.db.link_paper_to_query(paper['paper_id'], search_log.id) # type: ignore
                        
    def _export_results(self) -> None:
        """Export discovered papers to CSV files"""
        timestamp = dt.now(timezone(timedelta(hours=-8))).strftime("%Y%m%d_%H%M%S")
        output_dir = Path("output") / timestamp
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Export papers
        papers = self.db.get_processed_papers()
        papers_file = output_dir / "papers.csv"
        with open(papers_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'paper_id', 'title', 'authors', 'abstract', 
                'year', 'citation_count', 'reference_count',
                'relevance_score', 'relevance_reasoning'
            ])
            writer.writeheader()
            for paper in papers:
                writer.writerow({
                    'paper_id': paper.paper_id,
                    'title': paper.title,
                    'authors': paper.authors,  # This is JSON string
                    'abstract': paper.abstract,
                    'year': paper.year,
                    'citation_count': paper.citation_count,
                    'reference_count': paper.reference_count,
                    'relevance_score': getattr(paper, 'relevance_score', None),
                    'relevance_reasoning': getattr(paper, 'relevance_reasoning', None)
                })
                
        logger.info(f"Exported {len(papers)} papers to {papers_file}")