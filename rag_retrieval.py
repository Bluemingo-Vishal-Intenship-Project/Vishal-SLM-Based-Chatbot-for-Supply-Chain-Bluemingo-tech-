"""
RAG Retrieval Module
Handles vector database operations and retrieval.

This module is responsible for:
- Storing embeddings + metadata in Vector Database
- Retrieving top-K relevant chunks based on query embeddings
- Managing vector database (ChromaDB)

Design Philosophy:
- Vector DB = Knowledge Store
- Stores embeddings, chunk text, and source metadata
- Retrieval finds relevant context for answer generation
- No knowledge stored in the model itself
"""

from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings


class RAGRetrieval:
    """Handles vector database operations and retrieval for RAG system."""
    
    def __init__(self, db_path: str = "./chroma_db", collection_name: str = "excel_data"):
        """
        Initialize retrieval module.
        
        Args:
            db_path: Path to ChromaDB storage
            collection_name: Name of the ChromaDB collection
        """
        self.db_path = db_path
        self.collection_name = collection_name
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
    
    def store_chunks(self, chunks: List[Dict[str, Any]], 
                    embeddings: List[List[float]],
                    file_id: Optional[str] = None):
        """
        Store document chunks with embeddings in vector database.
        
        Args:
            chunks: List of chunk dictionaries with content and metadata
            embeddings: List of embedding vectors (one per chunk)
            file_id: Optional file identifier for metadata
        """
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks must match number of embeddings")
        
        # Prepare data for ChromaDB
        ids = []
        documents = []
        metadatas = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{file_id}_chunk_{i}" if file_id else f"chunk_{i}"
            ids.append(chunk_id)
            documents.append(chunk["content"])
            
            # Add file_id to metadata if provided
            metadata = chunk.get("metadata", {}).copy()
            if file_id:
                metadata["file_id"] = file_id
            metadata["chunk_id"] = chunk_id
            metadatas.append(metadata)
        
        # Store in ChromaDB
        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings
        )
        
        print(f"✅ Successfully stored {len(chunks)} chunks in ChromaDB (file_id: {file_id})")
    
    def retrieve(self, query_embedding: List[float], 
                n_results: int = 5,
                filter_metadata: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Retrieve top-K relevant chunks from vector database.
        
        Args:
            query_embedding: Query embedding vector
            n_results: Number of results to return
            filter_metadata: Optional metadata filters
            
        Returns:
            List of relevant chunks with metadata and distance scores
        """
        # First, check if collection has any data
        try:
            collection_stats = self.get_collection_stats()
            total_chunks = collection_stats.get('total_chunks', 0)
            if total_chunks == 0:
                print(f"[Retrieval] WARNING: Collection is empty (0 chunks)")
                return []
        except Exception as e:
            print(f"[Retrieval] Error checking collection stats: {e}")
        
        # Adjust n_results - ensure we get at least some results
        # If collection is small, don't ask for more than available
        try:
            collection_stats = self.get_collection_stats()
            total_chunks = collection_stats.get('total_chunks', 0)
            if total_chunks > 0:
                n_results = min(n_results, total_chunks)
        except:
            pass
        
        where = filter_metadata if filter_metadata else None
        
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where
            )
        except Exception as e:
            print(f"[Retrieval] Error querying collection: {e}")
            return []
        
        # Format results
        formatted_results = []
        if results['ids'] and len(results['ids'][0]) > 0:
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    "id": results['ids'][0][i],
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {},
                    "distance": results['distances'][0][i] if 'distances' in results and results['distances'][0] else None
                })
            print(f"[Retrieval] Retrieved {len(formatted_results)} chunks")
        else:
            print(f"[Retrieval] WARNING: No chunks retrieved. Collection may be empty or query didn't match.")
            # Try to get any chunks from the collection as fallback
            try:
                all_data = self.collection.get()
                if all_data['ids'] and len(all_data['ids']) > 0:
                    print(f"[Retrieval] Collection has {len(all_data['ids'])} chunks but query returned none. Returning first few chunks as fallback.")
                    # Return first few chunks as fallback
                    for i in range(min(3, len(all_data['ids']))):
                        formatted_results.append({
                            "id": all_data['ids'][i],
                            "content": all_data['documents'][i],
                            "metadata": all_data['metadatas'][i] if all_data['metadatas'] else {},
                            "distance": None
                        })
            except Exception as e:
                print(f"[Retrieval] Error getting fallback chunks: {e}")
        
        return formatted_results
    
    def clear_collection(self):
        """
        Clear all data from the collection.
        Use this to start fresh when uploading new files.
        """
        try:
            # Delete the collection
            self.client.delete_collection(name=self.collection_name)
            # Recreate it
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            print(f"✅ Cleared collection: {self.collection_name}")
            return True
        except Exception as e:
            print(f"⚠️ Error clearing collection: {e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the collection.
        
        Returns:
            Dictionary with collection statistics
        """
        all_data = self.collection.get()
        return {
            "total_chunks": len(all_data['ids']) if all_data['ids'] else 0,
            "collection_name": self.collection_name
        }
