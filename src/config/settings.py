# src/config/settings.py
import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GPT_MODEL: str = "gpt-4"

    # Search Settings
    MAX_PAPERS_PER_SEARCH: int = 100
    MAX_REFERENCE_DEPTH: int = 2
    BATCH_SIZE: int = 50

    # Topics
    SEARCH_TOPICS: List[str] = [
        "Visualization in AI Education: Focus on studies that explore the use of visualization to support reflection, understanding, and analysis in AI-enhanced learning activities.",
        "Student Reflection and Progress: Include research examining how visualizing interactions (e.g., chat data) aids students in reflecting on their learning process, identifying strengths, and recognizing areas for improvement.",
        "Comparative Analysis of Interactions: Look for studies that investigate the effects of comparing similar student conversations or AI interactions on learning outcomes, particularly understanding and retention.",
        "Learning Theories for Students and Instructors: Seek papers discussing how visualization impacts broader learning theories, considering its role in shaping educational practices for both students and instructors.",
        "Interactive and Dynamic Systems: Focus on research presenting dynamic or interactive visualization systems that enhance the educational experience, including their design and evaluation."
    ]

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "paper_discovery.log"

    class Config:
        env_file = ".env"


settings = Settings()
