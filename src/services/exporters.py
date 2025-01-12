# src/services/exporters.py
from abc import ABC, abstractmethod
import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Iterator
import networkx as nx
import pandas as pd
from tqdm import tqdm

from ..database.models import Paper, SearchLog
from ..database.manager import DatabaseManager

logger = logging.getLogger(__name__)

class BaseExporter(ABC):
    """Base class for data exporters"""
    
    def __init__(self, db_manager: DatabaseManager, output_dir: Path):
        self.db = db_manager
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def _get_timestamp(self) -> str:
        """Get formatted timestamp for filenames"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def _chunk_query(self, query, chunk_size: int = 1000) -> Iterator:
        """Process database queries in chunks to manage memory"""
        offset = 0
        while True:
            chunk = query.limit(chunk_size).offset(offset).all()
            if not chunk:
                break
            yield chunk
            offset += chunk_size
            
    @abstractmethod
    def export(self) -> None:
        """Export data in specific format"""
        pass
        
class CSVExporter(BaseExporter):
    """Export data to CSV files"""
    
    def export(self) -> None:
        """Export all data to CSV files"""
        self._export_papers()
        self._export_relationships()
        self._export_search_logs()
        
    def _export_papers(self) -> None:
        """Export paper details to CSV"""
        papers_file = self.output_dir / f"papers_{self._get_timestamp()}.csv"
        
        fieldnames = [
            'paper_id', 'title', 'authors', 'abstract', 'year',
            'citation_count', 'reference_count', 'relevance_score',
            'relevance_reasoning'
        ]
        
        with open(papers_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            # Process papers in chunks with progress bar
            papers_query = self.db.get_session().query(Paper)
            total_papers = papers_query.count()
            
            with tqdm(total=total_papers, desc="Exporting papers") as pbar:
                for papers_chunk in self._chunk_query(papers_query):
                    for paper in papers_chunk:
                        writer.writerow({
                            'paper_id': paper.paper_id,
                            'title': paper.title,
                            'authors': paper.authors,  # JSON string
                            'abstract': paper.abstract,
                            'year': paper.year,
                            'citation_count': paper.citation_count,
                            'reference_count': paper.reference_count,
                            'relevance_score': getattr(paper, 'relevance_score', None),
                            'relevance_reasoning': getattr(paper, 'relevance_reasoning', None)
                        })
                        pbar.update(1)
                        
        logger.info(f"Exported {total_papers} papers to {papers_file}")
        
    def _export_relationships(self) -> None:
        """Export citation and reference relationships to CSV"""
        citations_file = self.output_dir / f"citations_{self._get_timestamp()}.csv"
        references_file = self.output_dir / f"references_{self._get_timestamp()}.csv"
        
        fieldnames = ['source_id', 'target_id']
        
        # Export citations
        with open(citations_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            papers_query = self.db.get_session().query(Paper)
            total_papers = papers_query.count()
            
            with tqdm(total=total_papers, desc="Exporting citations") as pbar:
                for papers_chunk in self._chunk_query(papers_query):
                    for paper in papers_chunk:
                        for citation in paper.citations:
                            writer.writerow({
                                'source_id': paper.paper_id,
                                'target_id': citation.paper_id
                            })
                        pbar.update(1)
                        
        # Export references
        with open(references_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            with tqdm(total=total_papers, desc="Exporting references") as pbar:
                for papers_chunk in self._chunk_query(papers_query):
                    for paper in papers_chunk:
                        for reference in paper.references:
                            writer.writerow({
                                'source_id': paper.paper_id,
                                'target_id': reference.paper_id
                            })
                        pbar.update(1)
                        
    def _export_search_logs(self) -> None:
        """Export search logs to CSV"""
        logs_file = self.output_dir / f"search_logs_{self._get_timestamp()}.csv"
        
        fieldnames = ['timestamp', 'query', 'results_count', 'search_type']
        
        with open(logs_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            logs_query = self.db.get_session().query(SearchLog)
            total_logs = logs_query.count()
            
            with tqdm(total=total_logs, desc="Exporting search logs") as pbar:
                for logs_chunk in self._chunk_query(logs_query):
                    for log in logs_chunk:
                        writer.writerow({
                            'timestamp': log.timestamp.isoformat(),
                            'query': log.query,
                            'results_count': log.results_count,
                            'search_type': log.search_type
                        })
                        pbar.update(1)

class JSONExporter(BaseExporter):
    """Export data to JSON files"""
    
    def export(self) -> None:
        """Export all data to JSON files"""
        self._export_papers()
        self._export_network()
        self._export_search_logs()
        
    def _export_papers(self) -> None:
        """Export paper details to JSON"""
        papers_file = self.output_dir / f"papers_{self._get_timestamp()}.json"
        
        papers_data = []
        papers_query = self.db.get_session().query(Paper)
        total_papers = papers_query.count()
        
        with tqdm(total=total_papers, desc="Exporting papers to JSON") as pbar:
            for papers_chunk in self._chunk_query(papers_query):
                for paper in papers_chunk:
                    paper_data = {
                        'paper_id': paper.paper_id,
                        'title': paper.title,
                        'authors': json.loads(paper.authors),
                        'abstract': paper.abstract,
                        'year': paper.year,
                        'citation_count': paper.citation_count,
                        'reference_count': paper.reference_count,
                        'relevance_score': getattr(paper, 'relevance_score', None),
                        'relevance_reasoning': getattr(paper, 'relevance_reasoning', None)
                    }
                    papers_data.append(paper_data)
                    pbar.update(1)
                    
        with open(papers_file, 'w', encoding='utf-8') as f:
            json.dump(papers_data, f, indent=2)
            
    def _export_network(self) -> None:
        """Export citation/reference network to JSON"""
        network_file = self.output_dir / f"network_{self._get_timestamp()}.json"
        
        # Create network graph
        G = nx.DiGraph()
        
        papers_query = self.db.get_session().query(Paper)
        total_papers = papers_query.count()
        
        with tqdm(total=total_papers, desc="Building network") as pbar:
            for papers_chunk in self._chunk_query(papers_query):
                for paper in papers_chunk:
                    G.add_node(paper.paper_id, title=paper.title)
                    
                    # Add citation edges
                    for citation in paper.citations:
                        G.add_edge(paper.paper_id, citation.paper_id, type='citation')
                        
                    # Add reference edges
                    for reference in paper.references:
                        G.add_edge(paper.paper_id, reference.paper_id, type='reference')
                        
                    pbar.update(1)
                    
        # Export as JSON
        network_data = nx.node_link_data(G)
        with open(network_file, 'w', encoding='utf-8') as f:
            json.dump(network_data, f, indent=2)
            
    def _export_search_logs(self) -> None:
        """Export search logs to JSON"""
        logs_file = self.output_dir / f"search_logs_{self._get_timestamp()}.json"
        
        logs_data = []
        logs_query = self.db.get_session().query(SearchLog)
        total_logs = logs_query.count()
        
        with tqdm(total=total_logs, desc="Exporting search logs to JSON") as pbar:
            for logs_chunk in self._chunk_query(logs_query):
                for log in logs_chunk:
                    log_data = {
                        'timestamp': log.timestamp.isoformat(),
                        'query': log.query,
                        'results_count': log.results_count,
                        'search_type': log.search_type
                    }
                    logs_data.append(log_data)
                    pbar.update(1)
                    
        with open(logs_file, 'w', encoding='utf-8') as f:
            json.dump(logs_data, f, indent=2)

class ExcelExporter(BaseExporter):
    """Export data to Excel workbook"""
    
    def export(self) -> None:
        """Export all data to Excel file"""
        excel_file = self.output_dir / f"paper_discovery_{self._get_timestamp()}.xlsx"
        
        with pd.ExcelWriter(excel_file) as writer:
            self._export_papers(writer)
            self._export_citations(writer)
            self._export_references(writer)
            self._export_search_logs(writer)
            
    def _export_papers(self, writer: pd.ExcelWriter) -> None:
        """Export papers to Excel worksheet"""
        papers_data = []
        papers_query = self.db.get_session().query(Paper)
        total_papers = papers_query.count()
        
        with tqdm(total=total_papers, desc="Preparing papers for Excel") as pbar:
            for papers_chunk in self._chunk_query(papers_query):
                for paper in papers_chunk:
                    paper_data = {
                        'paper_id': paper.paper_id,
                        'title': paper.title,
                        'authors': paper.authors,
                        'abstract': paper.abstract,
                        'year': paper.year,
                        'citation_count': paper.citation_count,
                        'reference_count': paper.reference_count,
                        'relevance_score': getattr(paper, 'relevance_score', None),
                        'relevance_reasoning': getattr(paper, 'relevance_reasoning', None)
                    }
                    papers_data.append(paper_data)
                    pbar.update(1)
                    
        df = pd.DataFrame(papers_data)
        df.to_excel(writer, sheet_name='Papers', index=False)
        
    def _export_citations(self, writer: pd.ExcelWriter) -> None:
        """Export citations to Excel worksheet"""
        citations_data = []
        papers_query = self.db.get_session().query(Paper)
        
        for papers_chunk in self._chunk_query(papers_query):
            for paper in papers_chunk:
                for citation in paper.citations:
                    citations_data.append({
                        'source_id': paper.paper_id,
                        'target_id': citation.paper_id
                    })
                    
        df = pd.DataFrame(citations_data)
        df.to_excel(writer, sheet_name='Citations', index=False)
        
    def _export_references(self, writer: pd.ExcelWriter) -> None:
        """Export references to Excel worksheet"""
        references_data = []
        papers_query = self.db.get_session().query(Paper)
        
        for papers_chunk in self._chunk_query(papers_query):
            for paper in papers_chunk:
                for reference in paper.references:
                    references_data.append({
                        'source_id': paper.paper_id,
                        'target_id': reference.paper_id
                    })
                    
        df = pd.DataFrame(references_data)
        df.to_excel(writer, sheet_name='References', index=False)
        
    def _export_search_logs(self, writer: pd.ExcelWriter) -> None:
        """Export search logs to Excel worksheet"""
        logs_data = []
        logs_query = self.db.get_session().query(SearchLog)
        
        for logs_chunk in self._chunk_query(logs_query):
            for log in logs_chunk:
                logs_data.append({
                    'timestamp': log.timestamp,
                    'query': log.query,
                    'results_count': log.results_count,
                    'search_type': log.search_type
                })
                
        df = pd.DataFrame(logs_data)
        df.to_excel(writer, sheet_name='Search Logs', index=False)