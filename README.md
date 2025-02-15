# Open Deep Paper Research

An AI-powered research assistant that performs iterative, deep research on any topic by combining search engines, web scraping, and large language models.

The goal of this repo is to provide a minimal and robust implementation of a deep research agent – one that refines its research direction over time while deep diving into topics. The repository builds on the unofficial Semantic Scholar API (https://github.com/danielnsilva/semanticscholar) to enhance academic discovery.

If you like this project, please consider starring it and following for updates.

## How It Works
```mermaid
graph TD
    subgraph Input
        T[Topics] --> PD
        CF[Config Settings] --> PD
    end

    subgraph "Paper Discovery Service"
        PD[Paper Discovery] -->|Generate Queries| GPT
        GPT -->|Search Queries| SS[Unofficial Semantic Scholar API]
        SS -->|Paper Results| PD
        PD -->|Analyze Relevance| GPT
        PD -->|Extract Concepts| GPT
        PD -->|Generate New Queries| GPT
    end

    subgraph "Database Layer"
        DB[(PostgreSQL DB)]
        PD -->|Save Papers| DB
        PD -->|Save References| DB
        PD -->|Save Concepts| DB
        PD -->|Log Searches| DB
    end

    subgraph "Paper Filter Service"
        PF[Paper Filter] -->|Get Papers| DB
        PF -->|Evaluate Support| GPT
        PF -->|Update Evaluations| DB
    end

    subgraph "External APIs"
        GPT[LLM]
        SS
    end

    subgraph "Output"
        DB -->|Filtered Papers| CSV[CSV Export]
        DB -->|Paper Network| NET[Network Analysis]
    end
```
## Database Schema

```mermaid
erDiagram
    PAPERS {
        STRING paper_id PK
        STRING title
        STRING abstract
        INTEGER state
        STRING authors
        INTEGER citation_count
        INTEGER reference_count
        INTEGER year
        DATETIME created_at
        DATETIME updated_at
        STRING venue
        STRING journal
        STRING url
        BOOLEAN is_open_access
        STRING pdf_url
    }
    
    SEARCH_LOGS {
        INTEGER id PK
        STRING query
        DATETIME timestamp
        INTEGER results_count
        STRING search_type
    }
    
    PAPER_QUERY_SOURCES {
        INTEGER id PK
        STRING paper_id FK
        INTEGER search_log_id FK
        DATETIME created_at
    }
    
    PAPER_EVALUATIONS {
        INTEGER id PK
        STRING paper_id
        INTEGER support_level
        STRING reasoning
        DATETIME created_at
    }
    
    PAPER_CONCEPTS {
        INTEGER id PK
        STRING paper_id FK
        STRING concept
        DATETIME created_at
    }
    
    PAPER_REFERENCES {
        STRING paper_id FK
        STRING reference_id FK
    }
    
    PAPER_CITATIONS {
        STRING paper_id FK
        STRING citation_id FK
    }
    
    PAPERS ||--o{ PAPER_REFERENCES : references
    PAPERS ||--o{ PAPER_CITATIONS : citations
    PAPERS ||--o{ PAPER_QUERY_SOURCES : queries
    SEARCH_LOGS ||--o{ PAPER_QUERY_SOURCES : papers
    PAPERS ||--o{ PAPER_CONCEPTS : concepts
    PAPERS ||--o{ PAPER_EVALUATIONS : evaluations
```

### Key Tables
- **Paper**: Stores paper metadata and content
- **SearchLog**: Records search queries and their metadata
- **PaperQuerySource**: Links papers to their search origins
- **PaperEvaluation**: Stores AI evaluations of papers
- **PaperConcept**: Maps papers to their key concepts

### Key Relationships
- Papers can reference or cite other papers (many-to-many)
- Each paper can be found through multiple searches
- Papers can have multiple evaluations and concepts
- Search logs track which papers were found in each query

## Features

- **Iterative Research**: Iteratively builds on search results to refine and dive deeper into topics.
- **Intelligent Query Generation**: Uses LLM models to generate contextual, targeted queries.
- **Depth & Breadth Control**: Configurable control parameters to tune research breadth and depth.
- **Smart Follow-ups**: Automatically generates follow-up queries from previous results.
- **Comprehensive Markdown Reports**: Produces detailed reports with findings and sources.
- **Parallel Processing**: Supports concurrent processing for efficiency.

## Requirements

- Python 3.8+
- API keys for:
  - Unofficial Semantic Scholar API (see https://github.com/danielnsilva/semanticscholar)
  - OPENAI API (for LLM models)

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/harveylijh/deep-paper-research.git
   cd deep-paper-research
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables in a `.env` file:
   ```bash
   OPENAI_API_KEY="your_open_ai_key"
   DATABASE_URL="your_postgres_db_url"
   ```

## Usage

1. Initialize the database:
   ```bash
   python scripts/db.py init
   python scripts/db.py migrate "/+ year for paper"
   python scripts/db.py upgrade
   ```

2. Run the discovery process:
   ```bash
   # Test connection only
   python scripts/run.py --check-only

   # Run with default settings
   python scripts/run.py

   # Run with custom parameters
   python scripts/run.py --max-papers 100 --max-depth 3 --topics-file custom_topics.json
   python scripts/run.py --filter-papers --support-threshold 6.0
   ```

3. Reset the database:
   ```bash
   python scripts/manage_db.py reset
   ```

## Roadmap
1. Automated literature review generation with:
   - Executive summary
   - Key findings synthesis
   - Research gaps identification
   - Future directions suggestions
2. Auto TL;DR generation for papers with:
   - Key takeaways
   - Methodology overview
   - Main contributions
   - Critical analysis
3. Compatible for LLM other than OpenAI
4. Support local DeepSeek model
5. Reflection while fetching instead of a separate action
6. Citation graph visualization and analysis
7. Export results in various formats (BibTeX, CSV, JSON)
8. Integration with reference management tools (Zotero, Mendeley)
9. Custom filtering by impact factor and citation count
10. Author network analysis and collaboration recommendations
11. Research trend analysis and prediction

## Contributing

Feel free to fork the repository and submit pull requests. Please adhere to the code style and add tests where applicable.

## License

MIT License
