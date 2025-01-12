# src/clients/gpt.py
from typing import List, Dict, Any
import logging
import time
from functools import wraps
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

SEARCH_QUERY_PROMPT = """
You are an AI research assistant with expertise in AI visualization in educational contexts.
Your task is to generate 3-5 distinct search queries to locate academic papers pertinent to the given research topic.
Ensure the queries:
- Employ diverse phrasings and synonyms
- Cover related concepts to provide comprehensive search results

Research topic: {topic}

Output the search queries as a Python list of strings.
"""

RELEVANCE_ANALYSIS_PROMPT = """
You are a research assistant specializing in evaluating academic papers for relevance to AI visualization in educational contexts.
Evaluate if the following paper aligns with research on visualizing student-AI interactions and its impact on learning and collaboration.

Title: {title}
Abstract: {abstract}
Year: {year}

Rate the relevance on a scale of 0-10, with a brief explanation considering:
1. Visualizing AI-student interactions to enhance learning
2. Reflection and progress tracking through AI visualization
3. Exploring learning theories influenced by AI visualization

Provide output in the format:
score: <float between 0-10>
reasoning: <your explanation>
"""

CONCEPT_EXTRACTION_PROMPT = """
You are an AI research assistant analyzing academic papers on AI-driven visualization in education.
Extract key concepts and themes from the following paper, focusing on visualizing AI interactions and enhancing learning outcomes.

Paper Details:
- Title: {title}
- Abstract: {abstract}

Identify and list:
- Visualization techniques or frameworks
- Foundational learning theories or concepts
- Methods promoting student reflection or understanding
- Themes of collaborative learning or comparative analysis
- Potential applications in educational technology

Present the extracted concepts as a list of strings, ONE PER LINE, starting with a double quote and ending with a double quote.
For example:
"Concept 1"
"Concept 2"
"Concept 3"
"""

PHD_RESEARCH_PROMPT = """
You are an AI research assistant evaluating the relevance of academic papers to PhD research in AI visualization for education.
The research focuses on:
1. Visualization techniques for AI interactions in educational contexts
2. Supporting student and instructor reflection and understanding through visualization
3. Exploring the impact of visualization on learning theories and processes

Paper Details:
- Title: {title}
- Abstract: {abstract}
- Year: {year}

Evaluate the paper's contribution to these research goals by providing:
1. A support level score between 0 and 10
2. An explanation addressing the specified research focuses

Format your response as:
support_level: <float between 0 and 10>
reasoning: <your explanation>
"""

class GPTClient:
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.model = model
        self.client = OpenAI(api_key=api_key)

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def _call_gpt(self, prompt: str) -> str:
        """Make an API call to GPT with retry logic"""
        try:
            chat_completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful research assistant.",
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            if (
                chat_completion.choices
                and chat_completion.choices[0].message
                and chat_completion.choices[0].message.content
            ):
                return chat_completion.choices[0].message.content
            else:
                raise Exception("Empty response from GPT API")
        except Exception as e:
            logger.error(f"GPT API call failed: {str(e)}")
            raise

    def generate_search_queries(self, topic: str) -> List[str]:
        """Generate search queries for a given research topic"""
        logger.info(f"Generating search queries for topic: {topic}")
        prompt = SEARCH_QUERY_PROMPT.format(topic=topic)

        try:
            response = self._call_gpt(prompt)
            # Extract list from response
            queries = eval(
                response.strip()
            )  # Safe since we asked for Python list format
            return queries
        except Exception as e:
            logger.error(f"Failed to generate search queries: {str(e)} {str(response)}")
            return [topic]  # Fall back to original topic

    def analyze_relevance(self, title: str, abstract: str, year: int) -> Dict[str, Any]:
        """Analyze paper relevance to research topic"""
        logger.info(f"Analyzing relevance for paper: {title}")
        prompt = RELEVANCE_ANALYSIS_PROMPT.format(
            title=title, abstract=abstract, year=year
        )

        try:
            response = self._call_gpt(prompt)
            lines = response.strip().split("\n")
            score = float(lines[0].split(": ")[1])
            reasoning = lines[1].split(": ")[1]

            return {"score": score, "reasoning": reasoning}
        except Exception as e:
            logger.error(f"Failed to analyze relevance: {str(e)}")
            return {"score": 0.5, "reasoning": "Analysis failed"}

    def extract_concepts(self, title: str, abstract: str) -> List[str]:
        """Extract key concepts from paper for further research"""
        logger.info(f"Extracting concepts from paper: {title}")
        prompt = CONCEPT_EXTRACTION_PROMPT.format(title=title, abstract=abstract)

        try:
            response = self._call_gpt(prompt)
            logger.info(f"Concept extraction response: {response}")
            
            # Parse the response line by line
            concepts = []
            for line in response.strip().split('\n'):
                line = line.strip()
                if line.startswith('"') and line.endswith('"'):
                    # Remove quotes and any potential list markers
                    concept = line.strip('"-• ').strip()
                    if concept:
                        concepts.append(concept)
                        
            if not concepts:
                logger.warning(f"No valid concepts extracted from response: {response}")
                
            return concepts
            
        except Exception as e:
            logger.error(f"Failed to extract concepts: {str(e)}")
            return []

    def expand_search_space(self, paper_data: Dict[str, Any]) -> List[str]:
        """Generate additional search terms based on paper content"""
        concepts = self.extract_concepts(
            paper_data["title"], paper_data.get("abstract", "")
        )

        # Generate search queries for each concept
        search_queries = []
        for concept in concepts:
            queries = self.generate_search_queries(concept)
            search_queries.extend(queries)

        return list(set(search_queries))  # Remove duplicates

    def evaluate_phd_research_support(self, title: str, abstract: str, year: int) -> Dict[str, Any]:
        """Evaluate how well a paper supports PhD research areas"""
        logger.info(f"Evaluating PhD research support for paper: {title}")
        prompt = PHD_RESEARCH_PROMPT.format(
            title=title, abstract=abstract, year=year
        )

        try:
            response = self._call_gpt(prompt)
            lines = response.strip().split("\n")
            support_level = float(lines[0].split(": ")[1])
            reasoning = lines[1].split(": ")[1]

            return {"support_level": support_level, "reasoning": reasoning}
        except Exception as e:
            logger.error(f"Failed to evaluate PhD research support: {str(e)}")
            return {"support_level": 5.0, "reasoning": "Evaluation failed"}
