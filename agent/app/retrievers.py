"""
Retriever configuration for Vertex AI Search.

This module provides retriever and compressor instances for RAG functionality,
using Vertex AI Search's native embeddings and ranking capabilities.
"""

from unittest.mock import MagicMock

from langchain_google_community import VertexAISearchRetriever
from langchain_google_community.vertex_rank import VertexAIRank


def get_retriever(
    project_id: str,
    data_store_id: str,
    data_store_region: str,
    max_documents: int = 10,
) -> VertexAISearchRetriever:
    """
    Creates and returns an instance of the retriever service.

    Uses Vertex AI Search's native embeddings and layout-based chunking
    for document retrieval. The datastore should be configured with
    chunking enabled for optimal RAG performance.

    Args:
        project_id: Google Cloud project ID
        data_store_id: Vertex AI Search datastore ID
        data_store_region: Region of the datastore (e.g., 'us', 'eu')
        max_documents: Maximum number of documents to retrieve before reranking

    Returns:
        VertexAISearchRetriever instance or mock if unavailable
    """
    try:
        return VertexAISearchRetriever(
            project_id=project_id,
            data_store_id=data_store_id,
            location_id=data_store_region,
            engine_data_type=1,  # Document type
            max_documents=max_documents,
            beta=True,
        )
    except Exception:
        retriever = MagicMock()

        def raise_exception(*args, **kwargs) -> None:
            """Function that raises an exception when the retriever is not available."""
            raise Exception("Retriever not available")

        retriever.invoke = raise_exception
        return retriever


def get_compressor(project_id: str, top_n: int = 5) -> VertexAIRank:
    """
    Creates and returns an instance of the compressor service.

    Args:
        project_id: Google Cloud project ID
        top_n: Number of top documents to return after ranking

    Returns:
        VertexAIRank instance or mock if unavailable
    """
    try:
        return VertexAIRank(
            project_id=project_id,
            location_id="global",
            ranking_config="default_ranking_config",
            title_field="id",
            top_n=top_n,
        )
    except Exception:
        compressor = MagicMock()
        compressor.compress_documents = lambda x: []
        return compressor
