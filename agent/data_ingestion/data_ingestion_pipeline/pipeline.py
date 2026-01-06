

"""
Data ingestion pipeline for Mozilla data-docs.

This pipeline fetches markdown from GitHub, converts to HTML,
uploads to GCS, and imports into Vertex AI Search using the
native layout parser for content-aware chunking.
"""

from data_ingestion_pipeline.components.fetch_docs import fetch_docs
from data_ingestion_pipeline.components.ingest_data import ingest_data
from kfp import dsl


@dsl.pipeline(
    description="A pipeline to ingest Mozilla data-docs into Vertex AI Search for RAG"
)
def pipeline(
    project_id: str,
    location: str,
    gcs_bucket: str,
    gcs_prefix: str = "data-docs",
    docs_base_url: str = "https://docs.telemetry.mozilla.org",
    data_store_region: str = "",
    data_store_id: str = "",
) -> None:
    """Fetches Mozilla data-docs and ingests into Vertex AI Search.

    This pipeline:
    1. Fetches markdown from GitHub (mozilla/data-docs main branch)
    2. Converts markdown to HTML for layout parser structure detection
    3. Uploads HTML files to a GCS bucket
    4. Generates JSONL metadata for Vertex AI Search import
    5. Imports documents into Vertex AI Search datastore

    Args:
        project_id: Google Cloud project ID
        location: Vertex AI Pipelines region (e.g., 'us-central1')
        gcs_bucket: GCS bucket for storing HTML documents
        gcs_prefix: Prefix path within the bucket for HTML files
        docs_base_url: Base URL for citation links (live docs site)
        data_store_region: Region for Vertex AI Search datastore
        data_store_id: ID of the target Vertex AI Search datastore
    """

    # Step 1: Fetch markdown from GitHub, convert to HTML, upload to GCS
    fetched_docs = fetch_docs(
        project_id=project_id,
        gcs_bucket=gcs_bucket,
        gcs_prefix=gcs_prefix,
        docs_base_url=docs_base_url,
    ).set_retry(num_retries=2)

    # Step 2: Ingest documents into Vertex AI Search datastore
    ingest_data(
        project_id=project_id,
        data_store_region=data_store_region,
        input_files=fetched_docs.output,
        data_store_id=data_store_id,
    ).set_retry(num_retries=2)
