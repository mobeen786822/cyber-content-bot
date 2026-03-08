import feedparser


def fetch_arxiv_papers():
    query = "cat:cs.CR+AND+(LLM+OR+prompt+injection+OR+AI+security)"
    url = (
        f"http://export.arxiv.org/api/query"
        f"?search_query={query}"
        f"&sortBy=submittedDate&sortOrder=descending&max_results=5"
    )

    feed = feedparser.parse(url)
    if feed.bozo:
        print(f"arXiv feed error: {feed.bozo_exception}")

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
