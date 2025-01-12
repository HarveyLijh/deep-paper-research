# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base
from src.database.manager import DatabaseManager
from src.clients.semantic_scholar import SemanticScholarClient
from src.clients.gpt import GPTClient

@pytest.fixture
def test_db():
    """Create a test database"""
    TEST_DB_URL = "postgresql://test:test@localhost:5432/test_paper_discovery"
    engine = create_engine(TEST_DB_URL)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    
    yield TEST_DB_URL
    
    # Cleanup
    Base.metadata.drop_all(engine)

@pytest.fixture
def db_manager(test_db):
    """Create a database manager with test database"""
    return DatabaseManager(test_db)

@pytest.fixture
def mock_semantic_scholar():
    """Create a mock Semantic Scholar client"""
    class MockSemanticScholar:
        def search_papers(self, query, limit=100):
            return [{
                'paper_id': 'test123',
                'title': 'Test Paper',
                'year': 2023,
                'authors': [{'name': 'Test Author', 'id': 'author123'}]
            }]
            
        def get_paper_details(self, paper_id):
            return {
                'paper_id': paper_id,
                'title': 'Test Paper',
                'abstract': 'This is a test paper.',
                'year': 2023,
                'authors': [{'name': 'Test Author', 'id': 'author123'}],
                'references': ['ref1', 'ref2'],
                'citations': ['cit1', 'cit2']
            }
    
    return MockSemanticScholar()

@pytest.fixture
def mock_gpt():
    """Create a mock GPT client"""
    class MockGPT:
        def generate_search_queries(self, topic):
            return [
                f"{topic} research",
                f"{topic} analysis",
                f"{topic} review"
            ]
            
        def analyze_relevance(self, title, abstract, year):
            return {
                'score': 0.8,
                'reasoning': 'Test reasoning'
            }
            
        def extract_concepts(self, title, abstract):
            return ['concept1', 'concept2']
            
    return MockGPT()

# tests/test_services/test_paper_discovery.py
import pytest
from src.services.paper_discovery import PaperDiscoveryService

def test_paper_discovery_basic_flow(db_manager, mock_semantic_scholar, mock_gpt):
    """Test basic paper discovery workflow"""
    service = PaperDiscoveryService(
        semantic_scholar_client=mock_semantic_scholar,
        gpt_client=mock_gpt,
        db_manager=db_manager
    )
    
    # Run discovery on a test topic
    service.discover_papers(['test topic'])
    
    # Verify papers were saved
    papers = db_manager.get_processed_papers()
    assert len(papers) > 0
    
    # Verify paper details
    paper = papers[0]
    assert paper.title == 'Test Paper'
    assert paper.paper_id == 'test123'
    
def test_paper_discovery_depth_limit(db_manager, mock_semantic_scholar, mock_gpt):
    """Test that reference processing respects depth limit"""
    service = PaperDiscoveryService(
        semantic_scholar_client=mock_semantic_scholar,
        gpt_client=mock_gpt,
        db_manager=db_manager,
        max_reference_depth=1
    )
    
    service.discover_papers(['test topic'])
    
    # Verify we didn't process references beyond depth 1
    papers = db_manager.get_processed_papers()
    reference_chains = []
    for paper in papers:
        if paper.references:
            for ref in paper.references:
                assert not ref.references, "Should not have processed depth 2 references"

def test_paper_discovery_duplicate_handling(db_manager, mock_semantic_scholar, mock_gpt):
    """Test that papers aren't processed multiple times"""
    service = PaperDiscoveryService(
        semantic_scholar_client=mock_semantic_scholar,
        gpt_client=mock_gpt,
        db_manager=db_manager
    )
    
    # Run discovery twice
    service.discover_papers(['test topic'])
    initial_count = len(db_manager.get_processed_papers())
    
    service.discover_papers(['test topic'])
    final_count = len(db_manager.get_processed_papers())
    
    assert final_count == initial_count, "Should not reprocess same papers"

def test_paper_discovery_relevance_threshold(db_manager, mock_semantic_scholar, mock_gpt):
    """Test that relevance threshold filters papers correctly"""
    service = PaperDiscoveryService(
        semantic_scholar_client=mock_semantic_scholar,
        gpt_client=mock_gpt,
        db_manager=db_manager,
        relevance_threshold=0.9  # Set high threshold
    )
    
    service.discover_papers(['test topic'])
    papers = db_manager.get_processed_papers()
    
    # Verify no references were processed due to high threshold
    for paper in papers:
        assert not paper.references, "Should not process references due to high threshold"