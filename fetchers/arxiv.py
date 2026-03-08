import feedparser


def fetch_arxiv_papers():
    query = "cat:cs.CR+AND+(LLM+OR+prompt+injection+OR+AI+security)"
    url = (
        f"http://export.arxiv.org/api/query"
        f"?search_query={query}"
        f"&sortBy=submittedDate&sortOrder=descending&max_results=5"
    )

    try:
        feed = feedparser.parse(url)
    except Exception as e:
        print(f"arXiv fetch error: {e}")
        return []

    papers = []
    for entry in feed.entries:
        authors = [a.get("name", "") for a in entry.get("authors", [])]
        papers.append({
            "title": entry.get("title", "").replace("\n", " ").strip(),
            "summary": entry.get("summary", "").replace("\n", " ").strip()[:500],
            "authors": authors[:5],
            "link": entry.get("link", ""),
        })

    return papers
