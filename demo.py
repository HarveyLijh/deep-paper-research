#main.py

from semanticscholar import SemanticScholar

TOPICS = [
    "visualization of ai interactions in education context",
    "ai visualization in classroom",
]

def search_semanticscholar(query):
    sch = SemanticScholar()
    results = sch.search_paper(query)
    return results



def main():
    
    # Example usage
    paper = search_semanticscholar(TOPICS[0])
    print(f"Found paper: {paper[0].title}")

if __name__ == "__main__":
    main()
