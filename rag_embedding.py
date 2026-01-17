"""
RAG Embedding Module
Handles embedding generation for documents and queries.

This module is responsible for:
- Generating embeddings for document chunks
- Generating embeddings for user questions
- Generating embeddings for FAQ intent queries
- Using the embedding model (Sentence Transformers)

Design Philosophy:
- Embedding Model = Knowledge Representation
- Same embedding model used for documents, questions, and FAQ intents
- Embeddings enable semantic search in vector database
"""

from typing import List, Optional
from sentence_transformers import SentenceTransformer
import numpy as np


class RAGEmbedding:
    """Handles embedding generation for RAG system."""
    
    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding module.
        
        Args:
            embedding_model: Sentence transformer model name
        """
        self.embedding_model_name = embedding_model
        print(f"Loading embedding model: {embedding_model}")
        self.embedder = SentenceTransformer(embedding_model)
    
    def embed_documents(self, documents: List[str], 
                       show_progress: bool = True) -> List[List[float]]:
        """
        Generate embeddings for document chunks.
        
        Args:
            documents: List of document text chunks
            show_progress: Whether to show progress bar
            
        Returns:
            List of embedding vectors (each is a list of floats)
        """
        if not documents:
            return []
        
        embeddings = self.embedder.encode(
            documents,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )
        
        # Convert to list of lists for ChromaDB compatibility
        return embeddings.tolist()
    
    def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a single query.
        Used for both typed questions and FAQ intent queries.
        
        Args:
            query: Query text (user question or FAQ intent)
            
        Returns:
            Embedding vector as list of floats
        """
        embedding = self.embedder.encode(
            [query],
            convert_to_numpy=True
        )[0]
        
        return embedding.tolist()
    
    def embed_queries(self, queries: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple queries.
        
        Args:
            queries: List of query texts
            
        Returns:
            List of embedding vectors
        """
        if not queries:
            return []
        
        embeddings = self.embedder.encode(
            queries,
            convert_to_numpy=True
        )
        
        return embeddings.tolist()
