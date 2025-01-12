# src/database/manager.py
from typing import List, Dict, Any, Optional
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from .models import Base, Paper, SearchLog, PaperQuerySource, PaperEvaluation, PaperConcept
import logging

logger = logging.getLogger(__name__)
class DatabaseManager:
    def __init__(self, connection_string: str):
        self.engine = create_engine(connection_string)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def get_session(self) -> Session:
        return self.SessionLocal()

    def save_paper(self, paper_data: Dict[str, Any]) -> Paper:
        with self.get_session() as session:
            paper = Paper(
                paper_id=paper_data['paper_id'],
                title=paper_data['title'],
                abstract=paper_data.get('abstract'),
                authors=json.dumps(paper_data.get('authors', [])),
                citation_count=paper_data.get('citation_count', 0),
                reference_count=paper_data.get('reference_count', 0)
            )
            
            try:
                session.merge(paper)
                session.commit()
                return paper
            except IntegrityError:
                session.rollback()
                raise

    def save_references(self, paper_id: str, reference_ids: List[str]) -> None:
        with self.get_session() as session:
            paper = session.query(Paper).filter(Paper.paper_id == paper_id).first()
            if not paper:
                return

            # Get or create reference papers
            for ref_id in reference_ids:
                ref_paper = session.query(Paper).filter(Paper.paper_id == ref_id).first()
                if not ref_paper:
                    ref_paper = Paper(paper_id=ref_id)
                    session.add(ref_paper)
                
                if ref_paper not in paper.references:
                    paper.references.append(ref_paper)

            session.commit()

    def save_citations(self, paper_id: str, citation_ids: List[str]) -> None:
        with self.get_session() as session:
            paper = session.query(Paper).filter(Paper.paper_id == paper_id).first()
            if not paper:
                return

            # Get or create citation papers
            for cit_id in citation_ids:
                cit_paper = session.query(Paper).filter(Paper.paper_id == cit_id).first()
                if not cit_paper:
                    cit_paper = Paper(paper_id=cit_id)
                    session.add(cit_paper)
                
                if cit_paper not in paper.citations:
                    paper.citations.append(cit_paper)

            session.commit()

    def log_search(self, query: str, results_count: int, search_type: str) -> SearchLog:
        """Log a search query and return the search log ID"""
        session = self.get_session()
        try:
            log = SearchLog(
                query=query,
                results_count=results_count,
                search_type=search_type
            )
            session.add(log)
            session.commit()
            # Get the ID and create a new instance
            log_id = log.id
            return session.get(SearchLog, log_id)  # This ensures we get a fresh instance
        finally:
            session.close()

    def link_paper_to_query(self, paper_id: str, search_log_id: int) -> None:
        """Link a paper to a search query using a new session"""
        session = self.get_session()
        try:
            source = PaperQuerySource(
                paper_id=paper_id,
                search_log_id=search_log_id
            )
            session.add(source)
            session.commit()
        finally:
            session.close()

    def get_processed_papers(self) -> List[Paper]:
        with self.get_session() as session:
            return session.query(Paper).all()

    def get_paper_by_id(self, paper_id: str) -> Optional[Paper]:
        with self.get_session() as session:
            return session.query(Paper).filter(Paper.paper_id == paper_id).first()

    def get_papers_with_abstracts(self) -> List[Paper]:
        """Get all papers that have non-null abstracts"""
        with self.get_session() as session:
            return session.query(Paper).filter(
                Paper.abstract.isnot(None)
            ).all()

    def update_paper_state(self, paper_id: str, state: int) -> None:
        """Update the state of a paper"""
        with self.get_session() as session:
            try:
                paper = session.query(Paper).filter(Paper.paper_id == paper_id).first()
                if paper:
                    paper.state = state # type: ignore
                    session.commit()
                    logger.info(f"Updated state for paper {paper_id} to {state}")
                else:
                    logger.warning(f"Paper {paper_id} not found")
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to update paper state: {str(e)}")
                raise

    def save_paper_evaluation(self, paper_id: str, support_level: float, reasoning: str) -> None:
        """Save paper evaluation results"""
        with self.get_session() as session:
            try:
                evaluation = PaperEvaluation(
                    paper_id=paper_id,
                    support_level=support_level,
                    reasoning=reasoning
                )
                session.add(evaluation)
                session.commit()
                logger.info(f"Saved evaluation for paper {paper_id}")
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to save paper evaluation: {str(e)}")
                raise

    def save_paper_concepts(self, paper_id: str, concepts: List[str]) -> None:
        """Save extracted concepts for a paper"""
        with self.get_session() as session:
            try:
                # Delete existing concepts for this paper
                session.query(PaperConcept).filter(
                    PaperConcept.paper_id == paper_id
                ).delete()
                
                # Add new concepts
                for concept in concepts:
                    concept_entry = PaperConcept(
                        paper_id=paper_id,
                        concept=concept
                    )
                    session.add(concept_entry)
                    
                session.commit()
                logger.info(f"Saved {len(concepts)} concepts for paper {paper_id}")
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to save paper concepts: {str(e)}")
                raise