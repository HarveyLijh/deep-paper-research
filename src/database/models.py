# src/database/models.py
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

# Association tables for many-to-many relationships
paper_references = Table(
    "paper_references",
    Base.metadata,
    Column("paper_id", String, ForeignKey("papers.paper_id"), primary_key=True),
    Column("reference_id", String, ForeignKey("papers.paper_id"), primary_key=True),
)

paper_citations = Table(
    "paper_citations",
    Base.metadata,
    Column("paper_id", String, ForeignKey("papers.paper_id"), primary_key=True),
    Column("citation_id", String, ForeignKey("papers.paper_id"), primary_key=True),
)


class Paper(Base):
    __tablename__ = "papers"

    paper_id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    abstract = Column(String)
    state = Column(Integer, nullable=False, default=1)  # 1=enabled, -1=disable
    authors = Column(String)  # Stored as JSON string
    citation_count = Column(Integer, default=0)
    reference_count = Column(Integer, default=0)
    year = Column(Integer)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    references = relationship(
        "Paper",
        secondary=paper_references,
        primaryjoin=paper_id == paper_references.c.paper_id,
        secondaryjoin=paper_id == paper_references.c.reference_id,
        backref="referenced_by",
    )

    citations = relationship(
        "Paper",
        secondary=paper_citations,
        primaryjoin=paper_id == paper_citations.c.paper_id,
        secondaryjoin=paper_id == paper_citations.c.citation_id,
        backref="cited_by",
    )

    queries = relationship("PaperQuerySource", back_populates="paper")


class SearchLog(Base):
    __tablename__ = "search_logs"

    id = Column(Integer, primary_key=True)
    query = Column(String, nullable=False)
    timestamp = Column(DateTime, default=func.now())
    results_count = Column(Integer)
    search_type = Column(String)  # 'keyword' or 'reference'
    papers = relationship("PaperQuerySource", back_populates="search")


class PaperQuerySource(Base):
    __tablename__ = "paper_query_sources"

    id = Column(Integer, primary_key=True)
    paper_id = Column(String, ForeignKey("papers.paper_id"))
    search_log_id = Column(Integer, ForeignKey("search_logs.id"))
    created_at = Column(DateTime, default=func.now())

    paper = relationship("Paper", back_populates="queries")
    search = relationship("SearchLog", back_populates="papers")


class PaperEvaluation(Base):
    __tablename__ = "paper_evaluations"

    id = Column(Integer, primary_key=True)
    paper_id = Column(String)  # No foreign key constraint
    support_level = Column(Integer)  # Changed from float to integer for 0-10 scale
    reasoning = Column(String)
    created_at = Column(DateTime, default=func.now())

    # Relationship without foreign key
    paper = relationship(
        "Paper",
        primaryjoin="Paper.paper_id == foreign(PaperEvaluation.paper_id)",
        backref="evaluations"
    )


class PaperConcept(Base):
    __tablename__ = "paper_concepts"

    id = Column(Integer, primary_key=True)
    paper_id = Column(String, ForeignKey("papers.paper_id"))
    concept = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())

    paper = relationship("Paper", backref="concepts")
