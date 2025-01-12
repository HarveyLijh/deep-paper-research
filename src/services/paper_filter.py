import logging
from typing import List, Dict, Any
from ..clients.gpt import GPTClient
from ..database.manager import DatabaseManager

logger = logging.getLogger(__name__)

class PaperFilterService:
    def __init__(
        self,
        gpt_client: GPTClient,
        db_manager: DatabaseManager,
        support_threshold: float = 6.0  # Changed default threshold to 6.0 for 0-10 scale
    ):
        self.gpt = gpt_client
        self.db = db_manager
        self.support_threshold = support_threshold

    def filter_papers(self) -> Dict[str, int]:
        """Filter papers based on PhD research support level"""
        stats = {"processed": 0, "filtered_out": 0, "errors": 0}
        
        # Get all papers with non-null abstracts
        papers = self.db.get_papers_with_abstracts()
        total_papers = len(papers)
        logger.info(f"Found {total_papers} papers to evaluate")

        for i, paper in enumerate(papers, 1):
            try:
                logger.info(f"Processing paper {i}/{total_papers}: {paper.title}")
                
                evaluation = self.gpt.evaluate_phd_research_support(
                    paper.title,
                    paper.abstract,
                    paper.year
                )

                # Save evaluation results
                self.db.save_paper_evaluation(
                    paper.paper_id,
                    evaluation["support_level"],
                    evaluation["reasoning"]
                )

                stats["processed"] += 1
                
                # Update paper state if support level is below threshold
                if evaluation["support_level"] < self.support_threshold:
                    self.db.update_paper_state(paper.paper_id, -1)
                    stats["filtered_out"] += 1
                    logger.info(f"Filtered out paper {paper.paper_id} - Support level: {evaluation['support_level']}")
                    logger.debug(f"Reasoning: {evaluation['reasoning']}")

            except Exception as e:
                logger.error(f"Error processing paper {paper.paper_id}: {str(e)}")
                stats["errors"] += 1

        return stats
