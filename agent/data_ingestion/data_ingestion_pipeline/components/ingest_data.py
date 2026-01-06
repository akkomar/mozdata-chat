
# ruff: noqa

"""
Component to ingest documents into Vertex AI Search datastore.

This component imports documents from a JSONL metadata file into Vertex AI Search,
leveraging the native layout parser and chunking capabilities for HTML documents.
"""

from kfp.dsl import Dataset, Input, component


@component(
    base_image="us-docker.pkg.dev/production-ai-template/starter-pack/data_processing:0.2"
)
def ingest_data(
    project_id: str,
    data_store_region: str,
    input_files: Input[Dataset],
    data_store_id: str,
) -> None:
    """Import documents into Vertex AI Search datastore.

    This component imports unstructured documents (HTML files) into Vertex AI Search
    using the native layout parser for content-aware chunking. The datastore must be
    created with chunking enabled before running this pipeline.

    Args:
        project_id: Google Cloud project ID
        data_store_region: Region for Vertex AI Search (e.g., 'us', 'eu')
        input_files: Input dataset containing JSONL metadata file URI
        data_store_id: ID of target datastore (must have chunking enabled)
    """
    import logging
    import time

    from google.api_core.client_options import ClientOptions
    from google.cloud import discoveryengine

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    def import_documents(
        project_id: str,
        location: str,
        data_store_id: str,
        input_files_uri: str,
        client_options: ClientOptions | None = None,
    ) -> None:
        """Import documents into datastore.

        Args:
            project_id: Google Cloud project ID
            location: Google Cloud location
            data_store_id: Target datastore ID
            input_files_uri: URI of JSONL metadata file
            client_options: Client options for API
        """
        client = discoveryengine.DocumentServiceClient(client_options=client_options)

        parent = client.branch_path(
            project=project_id,
            location=location,
            data_store=data_store_id,
            branch="default_branch",
        )

        # Import documents using JSONL metadata file
        # The JSONL file contains document IDs, metadata, and URIs to HTML files in GCS
        request = discoveryengine.ImportDocumentsRequest(
            parent=parent,
            gcs_source=discoveryengine.GcsSource(
                input_uris=[input_files_uri],
                data_schema="document",  # JSONL with URIs pointing to document files
            ),
            # FULL mode replaces all existing documents (full refresh)
            reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.FULL,
        )

        operation = client.import_documents(request=request)
        logger.info(f"Waiting for import operation: {operation.operation.name}")
        operation.result()

    client_options = ClientOptions(
        api_endpoint=f"{data_store_region}-discoveryengine.googleapis.com"
    )

    logger.info(f"Importing documents from {input_files.uri}")
    logger.info(f"Target datastore: {data_store_id} in region {data_store_region}")

    import_documents(
        project_id=project_id,
        location=data_store_region,
        data_store_id=data_store_id,
        client_options=client_options,
        input_files_uri=input_files.uri,
    )

    logger.info("Document import completed successfully")
    logger.info(
        "Sleeping for 3 minutes to allow Vertex AI Search to index the data..."
    )
    time.sleep(180)  # Sleep for 180 seconds (3 minutes)
    logger.info("Sleep completed. Data indexing should now be complete.")
