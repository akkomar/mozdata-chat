DOCS_BASE_URL = "https://docs.telemetry.mozilla.org"


def format_docs(docs: list) -> str:
    """Format retrieved documents with source URLs derived from document IDs.

    The document ID follows the pattern: path-segments-filename
    (e.g., 'cookbooks-live_data' from 'cookbooks/live_data.md')

    We reconstruct the URL by replacing '-' with '/' and adding '.html'
    """
    formatted = "## Context provided:\n"
    for idx, doc in enumerate(docs):
        doc_id = doc.metadata.get("id", "")
        # Convert ID back to URL path: cookbooks-live_data -> cookbooks/live_data.html
        url_path = doc_id.replace("-", "/") + ".html"
        url = f"{DOCS_BASE_URL}/{url_path}"

        formatted += f"""<Document {idx}>
Source: {url}
---
{doc.page_content}
</Document {idx}>
"""
    return formatted
