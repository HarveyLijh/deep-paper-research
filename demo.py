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

def get_paper_details(paper_id):
    sch = SemanticScholar()
    fields = ['title', 'abstract', 'authors', 'year', 'citationCount', 'venue', "openAccessPdf"]
    paper = sch.get_paper(paper_id, fields=fields)
    return paper


def main():
    
    # Example usage
    # paper = search_semanticscholar(TOPICS[0])
    paper = get_paper_details("d732208f21c675d9282967de296f477dbacf72a6")
    # print all fields from paper
    print(paper)

if __name__ == "__main__":
    main()
