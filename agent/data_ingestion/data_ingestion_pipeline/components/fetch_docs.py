
# ruff: noqa

"""
Component to fetch Mozilla data-docs and prepare for Vertex AI Search import.

This component:
1. Fetches the SUMMARY.md file from the data-docs GitHub repository
2. Parses it to extract all page paths
3. Downloads each markdown file from GitHub (main branch)
4. Converts markdown to HTML for layout parser structure detection
5. Uploads HTML files to GCS
6. Generates a JSONL metadata file for Vertex AI Search import

Using markdown source instead of rendered HTML because:
- Clean content (no navigation chrome, sidebar, CSS, JS)
- Fast (GitHub raw files, no rate limiting needed)
- Small files (~10KB vs ~150KB)
- Layout parser still gets proper HTML structure after conversion
"""

from kfp.dsl import Dataset, Output, component


@component(
    base_image="python:3.11-slim",
    packages_to_install=[
        "requests>=2.31.0",
        "markdown>=3.5.0",
        "google-cloud-storage>=2.14.0",
        "backoff>=2.2.0",
    ],
)
def fetch_docs(
    project_id: str,
    output_files: Output[Dataset],
    gcs_bucket: str,
    gcs_prefix: str = "data-docs",
    docs_base_url: str = "https://docs.telemetry.mozilla.org",
    github_raw_base: str = "https://raw.githubusercontent.com/mozilla/data-docs/main/src",
    summary_url: str = "https://raw.githubusercontent.com/mozilla/data-docs/main/src/SUMMARY.md",
    max_retries: int = 3,
) -> None:
    """
    Fetches Mozilla data-docs markdown files, converts to HTML, and uploads to GCS.

    Args:
        project_id: Google Cloud project ID
        output_files: Output dataset path for the metadata JSONL file
        gcs_bucket: GCS bucket name for storing HTML documents
        gcs_prefix: Prefix path within the bucket for HTML files
        docs_base_url: Base URL for citation links (live docs site)
        github_raw_base: Base URL for fetching raw markdown from GitHub
        summary_url: URL to the SUMMARY.md file containing page index
        max_retries: Maximum number of retry attempts for HTTP requests
    """
    import json
    import logging
    import re
    from urllib.parse import urljoin

    import backoff
    import markdown
    import requests
    from google.cloud import storage

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Initialize GCS client
    storage_client = storage.Client(project=project_id)
    bucket = storage_client.bucket(gcs_bucket)

    # Configure markdown converter with useful extensions
    md_converter = markdown.Markdown(
        extensions=[
            "tables",
            "fenced_code",
            "codehilite",
            "toc",
            "sane_lists",
        ]
    )

    def parse_summary_md(summary_content: str) -> list[str]:
        """Extract .md file paths from SUMMARY.md content.

        Args:
            summary_content: Raw content of SUMMARY.md file

        Returns:
            List of unique markdown file paths
        """
        # Match markdown links like [Title](path/to/file.md)
        pattern = r"\[.*?\]\((.*?\.md)\)"
        paths = re.findall(pattern, summary_content)
        # Deduplicate while preserving order
        seen = set()
        unique_paths = []
        for path in paths:
            if path not in seen:
                seen.add(path)
                unique_paths.append(path)
        return unique_paths

    def extract_title_from_markdown(md_content: str) -> str:
        """Extract page title from first heading in markdown content.

        Args:
            md_content: Raw markdown content

        Returns:
            Page title string
        """
        # Look for first # heading
        match = re.search(r"^#\s+(.+)$", md_content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return "Untitled"

    def convert_markdown_to_html(md_content: str, title: str) -> str:
        """Convert markdown content to HTML with proper structure.

        Args:
            md_content: Raw markdown content
            title: Page title for HTML document

        Returns:
            HTML string
        """
        # Reset the converter state for each document
        md_converter.reset()

        # Convert markdown to HTML body
        html_body = md_converter.convert(md_content)

        # Wrap in minimal HTML structure for layout parser
        html_doc = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
</head>
<body>
{html_body}
</body>
</html>"""
        return html_doc

    @backoff.on_exception(
        backoff.expo, requests.RequestException, max_tries=max_retries
    )
    def fetch_url(url: str) -> requests.Response:
        """Fetch URL with retry logic.

        Args:
            url: URL to fetch

        Returns:
            Response object

        Raises:
            requests.RequestException: If all retries fail
        """
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response

    def generate_doc_id(md_path: str) -> str:
        """Generate a document ID from the markdown path.

        Args:
            md_path: Path to markdown file

        Returns:
            URL-safe document ID
        """
        # Remove .md extension and replace / with -
        doc_id = md_path.replace(".md", "").replace("/", "-")
        # Remove any characters that might cause issues
        doc_id = re.sub(r"[^a-zA-Z0-9_-]", "", doc_id)
        return doc_id

    def md_path_to_docs_url(md_path: str) -> str:
        """Convert markdown path to live documentation URL.

        Args:
            md_path: Path to markdown file (e.g., 'concepts/glean.md')

        Returns:
            Full URL to the live documentation page
        """
        html_path = md_path.replace(".md", ".html")
        return urljoin(docs_base_url + "/", html_path)

    # Step 1: Fetch SUMMARY.md
    logger.info(f"Fetching SUMMARY.md from {summary_url}")
    summary_response = fetch_url(summary_url)
    md_paths = parse_summary_md(summary_response.text)
    logger.info(f"Found {len(md_paths)} pages to fetch")

    # Step 2: Fetch each markdown file, convert to HTML, and upload to GCS
    documents = []
    failed_pages = []

    for md_path in md_paths:
        github_url = f"{github_raw_base}/{md_path}"
        doc_id = generate_doc_id(md_path)
        gcs_path = f"{gcs_prefix}/{md_path.replace('.md', '.html')}"
        docs_url = md_path_to_docs_url(md_path)

        try:
            logger.info(f"Fetching {github_url}")
            response = fetch_url(github_url)
            md_content = response.text

            # Extract title from markdown
            title = extract_title_from_markdown(md_content)

            # Convert markdown to HTML
            html_content = convert_markdown_to_html(md_content, title)

            # Upload to GCS
            blob = bucket.blob(gcs_path)
            blob.upload_from_string(html_content, content_type="text/html")
            logger.info(f"Uploaded to gs://{gcs_bucket}/{gcs_path}")

            # Extract section from path (first directory)
            section = md_path.split("/")[0] if "/" in md_path else "root"

            # Build document metadata for Vertex AI Search import
            # URL points to live docs for citations
            documents.append(
                {
                    "id": doc_id,
                    "structData": {
                        "title": title,
                        "url": docs_url,
                        "section": section,
                        "source_path": md_path,
                    },
                    "content": {
                        "mimeType": "text/html",
                        "uri": f"gs://{gcs_bucket}/{gcs_path}",
                    },
                }
            )

        except Exception as e:
            logger.error(f"Failed to fetch {github_url}: {e}")
            failed_pages.append(md_path)
            continue

    logger.info(f"Successfully fetched {len(documents)} pages")
    if failed_pages:
        logger.warning(f"Failed to fetch {len(failed_pages)} pages: {failed_pages}")

    # Step 3: Generate JSONL metadata file and upload to GCS
    jsonl_content = "\n".join(json.dumps(doc) for doc in documents)
    metadata_path = f"{gcs_prefix}/metadata.jsonl"
    metadata_blob = bucket.blob(metadata_path)
    metadata_blob.upload_from_string(jsonl_content, content_type="application/jsonl")

    # Set output URI for next pipeline step
    output_files.uri = f"gs://{gcs_bucket}/{metadata_path}"
    logger.info(f"Metadata file uploaded to {output_files.uri}")
    logger.info(f"Total documents prepared for import: {len(documents)}")
