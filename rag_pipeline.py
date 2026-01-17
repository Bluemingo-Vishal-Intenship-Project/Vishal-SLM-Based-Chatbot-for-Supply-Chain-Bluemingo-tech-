"""
RAG Pipeline Orchestrator
Unified RAG pipeline for all queries (typed questions and FAQ clicks).

This module orchestrates the complete RAG flow:
1. Query Input (User Question OR FAQ Click)
2. Convert input to semantic embedding
3. Retrieve top-K relevant chunks from Vector Database
4. Inject retrieved context into SLM prompt
5. SLM generates answer strictly from retrieved context

Design Philosophy:
- One unified pipeline for all query types
- FAQs are treated as intent prompts (not stored answers)
- All answers grounded in retrieved documents
- No hardcoded answers or FAQ-specific logic branches
"""

from typing import List, Dict, Any, Optional
from rag_embedding import RAGEmbedding
from rag_retrieval import RAGRetrieval
from rag_generation import RAGGeneration


class RAGPipeline:
    """
    Unified RAG pipeline orchestrator.
    
    Handles both typed questions and FAQ clicks through the same pipeline.
    FAQs are treated as intent prompts that go through retrieval and generation.
    """
    
    def __init__(self, 
                 embedding_model: str = "all-MiniLM-L6-v2",
                 db_path: str = "./chroma_db",
                 collection_name: str = "excel_data"):
        """
        Initialize RAG pipeline.
        
        Args:
            embedding_model: Sentence transformer model name
            db_path: Path to ChromaDB storage
            collection_name: Name of the ChromaDB collection
        """
        self.embedding = RAGEmbedding(embedding_model)
        self.retrieval = RAGRetrieval(db_path, collection_name)
        self.generation = RAGGeneration()
    
    def query(self, query_text: str, n_results: int = 5) -> Dict[str, Any]:
        """
        Process a query through the complete RAG pipeline.
        
        This method handles:
        - User typed questions
        - FAQ clicks (treated as intent prompts - same pipeline)
        - Any other query input
        
        RAG Pipeline Flow:
        1. Query Input (User Question OR FAQ Click)
        2. Convert input to semantic embedding
        3. Retrieve top-K relevant chunks from Vector Database
        4. Inject retrieved context into SLM prompt
        5. SLM generates answer strictly from retrieved context
        
        Args:
            query_text: Query string (user question or FAQ intent)
            n_results: Number of chunks to retrieve
            
        Returns:
            Dictionary with answer, retrieved chunks, and metadata
        """
        # Step 1: Convert query to embedding
        # FAQs are treated the same as typed questions - both become embeddings
        query_embedding = self.embedding.embed_query(query_text)
        
        # Step 2: Retrieve relevant chunks from vector database
        # Adjust n_results based on query complexity
        if any(keyword in query_text.lower() for keyword in 
               ['total', 'sum', 'average', 'highest', 'lowest', 'all', 'per', 'ratio']):
            n_results = max(n_results, 10)
        
        retrieved_chunks = self.retrieval.retrieve(
            query_embedding=query_embedding,
            n_results=n_results
        )
        
        # Step 3: Generate answer from retrieved context
        answer = self.generation.generate_answer(query_text, retrieved_chunks)
        
        # Step 4: Return results
        return {
            "answer": answer,
            "retrieved_chunks": retrieved_chunks,
            "query": query_text,
            "num_chunks_retrieved": len(retrieved_chunks),
            "has_context": len(retrieved_chunks) > 0
        }
    
    def ingest_document(self, chunks: List[Dict[str, Any]], file_id: Optional[str] = None):
        """
        Ingest new document chunks into the system.
        
        This is called when new documents are uploaded.
        New data becomes instantly searchable via retrieval.
        
        IMPORTANT: This does NOT:
        - Retrain the SLM
        - Regenerate FAQs
        - Change any existing FAQ text
        
        New data only adds to the vector database for retrieval.
        FAQs remain static intent prompts.
        
        Args:
            chunks: List of chunk dictionaries with content and metadata
            file_id: Optional file identifier
        """
        # Generate embeddings for chunks
        documents = [chunk["content"] for chunk in chunks]
        embeddings = self.embedding.embed_documents(documents, show_progress=True)
        
        # Store in vector database
        self.retrieval.store_chunks(chunks, embeddings, file_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get pipeline statistics.
        
        Returns:
            Dictionary with pipeline statistics
        """
        return self.retrieval.get_collection_stats()
