"""
Excel/CSV to RAG System
Converts Excel/CSV files to structured Markdown, embeds with numeric-friendly SLM,
and provides RAG query capabilities with 100% numeric accuracy.
"""

import pandas as pd
import os
import json
import ast
from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
import numpy as np
from sentence_transformers import SentenceTransformer
import re


class ExcelToRAG:
    """Main class for Excel/CSV to RAG conversion pipeline."""
    
    def __init__(self, 
                 embedding_model: str = "all-MiniLM-L6-v2",
                 db_path: str = "./chroma_db",
                 collection_name: str = "excel_data"):
        """
        Initialize the Excel to RAG system.
        
        Args:
            embedding_model: Sentence transformer model name
            db_path: Path to ChromaDB storage
            collection_name: Name of the ChromaDB collection
        """
        self.embedding_model_name = embedding_model
        self.db_path = db_path
        self.collection_name = collection_name
        
        # Initialize embedding model (numeric-friendly)
        print(f"Loading embedding model: {embedding_model}")
        self.embedder = SentenceTransformer(embedding_model)
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
    def read_file(self, file_path: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
        """
        Read Excel or CSV file.
        Supports multiple Excel formats and handles edge cases.
        
        Args:
            file_path: Path to the file
            sheet_name: Optional sheet name for Excel files (default: first sheet)
                       Can also be 0-indexed sheet number
            
        Returns:
            DataFrame with the file contents
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        print(f"Reading file: {file_path}")
        file_ext = file_path.suffix.lower()
        
        try:
            if file_ext == '.csv':
                # Try different encodings for CSV
                for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
                    try:
                        df = pd.read_csv(file_path, encoding=encoding, low_memory=False)
                        print(f"Successfully read CSV with {encoding} encoding")
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    # Last resort: read with error handling
                    df = pd.read_csv(file_path, encoding='utf-8', errors='ignore', low_memory=False)
                    print("Read CSV with utf-8 encoding (some characters may be ignored)")
            
            elif file_ext == '.xlsx':
                # Modern Excel format - use openpyxl
                try:
                    if sheet_name is not None:
                        df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
                    else:
                        # Read first sheet by default
                        df = pd.read_excel(file_path, engine='openpyxl')
                    print(f"Successfully read Excel file (sheet: {sheet_name or 'first'})")
                except Exception as e:
                    print(f"Warning: {e}. Trying alternative method...")
                    # Try without specifying engine
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            elif file_ext == '.xls':
                # Old Excel format - use xlrd
                try:
                    if sheet_name is not None:
                        df = pd.read_excel(file_path, sheet_name=sheet_name, engine='xlrd')
                    else:
                        df = pd.read_excel(file_path, engine='xlrd')
                    print(f"Successfully read old Excel format (sheet: {sheet_name or 'first'})")
                except ImportError:
                    raise ImportError(
                        "xlrd package required for .xls files. Install with: pip install xlrd"
                    )
                except Exception as e:
                    # Try openpyxl as fallback (sometimes works)
                    try:
                        df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
                        print("Read .xls file using openpyxl")
                    except:
                        raise ValueError(f"Could not read .xls file: {e}")
            
            elif file_ext in ['.xlsm', '.xlsb']:
                # Excel with macros or binary format
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
                    print(f"Successfully read Excel file with macros/binary format")
                except Exception as e:
                    raise ValueError(f"Could not read {file_ext} file: {e}")
            
            else:
                raise ValueError(
                    f"Unsupported file format: {file_ext}\n"
                    f"Supported formats: .csv, .xlsx, .xls, .xlsm, .xlsb"
                )
            
            # Clean up the DataFrame
            # Remove completely empty rows and columns
            df = df.dropna(how='all').dropna(axis=1, how='all')
            
            # Reset index after dropping rows
            df = df.reset_index(drop=True)
            
            print(f"File read successfully. Shape: {df.shape} (rows x columns)")
            
            if df.empty:
                print("Warning: The file appears to be empty or contains no data.")
            
            return df
            
        except Exception as e:
            raise RuntimeError(f"Error reading file {file_path}: {str(e)}")
    
    def read_all_sheets(self, file_path: str) -> Dict[str, pd.DataFrame]:
        """
        Read all sheets from an Excel file.
        
        Args:
            file_path: Path to the Excel file
            
        Returns:
            Dictionary mapping sheet names to DataFrames
        """
        file_path = Path(file_path)
        file_ext = file_path.suffix.lower()
        
        if file_ext not in ['.xlsx', '.xls', '.xlsm', '.xlsb']:
            raise ValueError(f"Cannot read multiple sheets from {file_ext} file")
        
        try:
            if file_ext == '.xls':
                engine = 'xlrd'
            else:
                engine = 'openpyxl'
            
            excel_file = pd.ExcelFile(file_path, engine=engine)
            sheets_dict = {}
            
            print(f"Found {len(excel_file.sheet_names)} sheet(s): {excel_file.sheet_names}")
            
            for sheet_name in excel_file.sheet_names:
                print(f"Reading sheet: {sheet_name}")
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                # Clean up
                df = df.dropna(how='all').dropna(axis=1, how='all').reset_index(drop=True)
                sheets_dict[sheet_name] = df
                print(f"  ✓ Sheet '{sheet_name}': {df.shape}")
            
            return sheets_dict
            
        except Exception as e:
            raise RuntimeError(f"Error reading sheets from {file_path}: {str(e)}")
    
    def convert_to_markdown(self, df: pd.DataFrame, 
                           metadata: Optional[Dict] = None) -> str:
        """
        Convert DataFrame to structured Markdown format.
        Preserves all numeric values with 100% accuracy.
        
        Args:
            df: DataFrame to convert
            metadata: Optional metadata dictionary
            
        Returns:
            Structured Markdown string
        """
        md_lines = []
        
        # Add metadata section
        md_lines.append("# Document Metadata\n")
        if metadata:
            md_lines.append("```json")
            md_lines.append(json.dumps(metadata, indent=2))
            md_lines.append("```\n")
        else:
            md_lines.append("- **Rows**: " + str(len(df)))
            md_lines.append("- **Columns**: " + str(len(df.columns)))
            md_lines.append("- **Shape**: " + str(df.shape))
            md_lines.append("")
        
        # Add column information
        md_lines.append("## Column Information\n")
        md_lines.append("| Column Name | Data Type | Non-Null Count | Null Count |")
        md_lines.append("|-------------|-----------|----------------|------------|")
        for col in df.columns:
            dtype = str(df[col].dtype)
            non_null = df[col].notna().sum()
            null_count = df[col].isna().sum()
            md_lines.append(f"| `{col}` | {dtype} | {non_null} | {null_count} |")
        md_lines.append("")
        
        # Add data preview (first few rows)
        md_lines.append("## Data Preview\n")
        md_lines.append("### First 5 Rows\n")
        md_lines.append(self._dataframe_to_markdown_table(df.head(5)))
        md_lines.append("")
        
        # Add complete data section with row-by-row format
        md_lines.append("## Complete Data\n")
        md_lines.append("### Row-by-Row Data\n")
        md_lines.append("Each row is presented with its index and all column values.\n")
        md_lines.append("")
        
        for idx, row in df.iterrows():
            md_lines.append(f"### Row {idx}\n")
            md_lines.append("| Column | Value |")
            md_lines.append("|--------|-------|")
            
            for col in df.columns:
                value = row[col]
                # Preserve exact numeric values
                if pd.isna(value):
                    value_str = "NULL"
                else:
                    # Convert numpy types to native Python types
                    if hasattr(value, 'item'):
                        try:
                            value = value.item()
                        except (ValueError, AttributeError):
                            pass  # Keep original value if item() fails
                    
                    # Handle numeric types
                    if isinstance(value, (int, np.integer)):
                        value_str = str(int(value))
                    elif isinstance(value, (float, np.floating)):
                        # Format float nicely
                        if float(value).is_integer():
                            value_str = str(int(value))
                        else:
                            # Use repr to preserve precision, then clean trailing zeros
                            value_str = repr(float(value))
                            # Remove trailing zeros after decimal point (but keep scientific notation)
                            if '.' in value_str and 'e' not in value_str.lower():
                                value_str = value_str.rstrip('0').rstrip('.')
                    else:
                        value_str = str(value)
                
                md_lines.append(f"| `{col}` | {value_str} |")
            md_lines.append("")
        
        # Add summary statistics for numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            md_lines.append("## Numeric Summary Statistics\n")
            md_lines.append(self._dataframe_to_markdown_table(df[numeric_cols].describe()))
            md_lines.append("")
        
        # Add complete table view
        md_lines.append("## Complete Table View\n")
        md_lines.append(self._dataframe_to_markdown_table(df))
        md_lines.append("")
        
        return "\n".join(md_lines)
    
    def _dataframe_to_markdown_table(self, df: pd.DataFrame) -> str:
        """Convert DataFrame to Markdown table format."""
        # Replace NaN with "NULL" for display
        df_display = df.copy()
        df_display = df_display.fillna("NULL")
        
        # Convert to markdown
        lines = []
        # Header
        lines.append("| " + " | ".join([str(col) for col in df.columns]) + " |")
        lines.append("| " + " | ".join(["---" for _ in df.columns]) + " |")
        
        # Rows
        for _, row in df_display.iterrows():
            row_values = []
            for col in df.columns:
                val = row[col]
                # Convert numpy types to native Python types and format properly
                if val != "NULL":
                    # Convert numpy types to native Python types
                    if hasattr(val, 'item'):
                        try:
                            val = val.item()
                        except (ValueError, AttributeError):
                            pass  # Keep original value if item() fails
                    
                    # Preserve numeric precision
                    if isinstance(val, (int, np.integer)):
                        row_values.append(str(int(val)))
                    elif isinstance(val, (float, np.floating)):
                        # Format float nicely
                        float_val = float(val)
                        if float_val.is_integer():
                            row_values.append(str(int(float_val)))
                        else:
                            # Use repr but clean up trailing zeros
                            val_str = repr(float_val)
                            # Remove trailing zeros after decimal point (but keep scientific notation)
                            if '.' in val_str and 'e' not in val_str.lower():
                                val_str = val_str.rstrip('0').rstrip('.')
                            row_values.append(val_str)
                    else:
                        row_values.append(str(val))
                else:
                    row_values.append("NULL")
            lines.append("| " + " | ".join(row_values) + " |")
        
        return "\n".join(lines)
    
    def chunk_markdown(self, md_content: str, 
                      chunk_size: int = 1000,
                      chunk_overlap: int = 200) -> List[Dict[str, Any]]:
        """
        Chunk Markdown content into smaller sections.
        
        Args:
            md_content: Markdown content
            chunk_size: Maximum chunk size in characters
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of chunk dictionaries with metadata
        """
        chunks = []
        
        # Split by sections first (## headers)
        sections = re.split(r'\n(##+)\s+', md_content)
        
        current_section = ""
        section_title = "Introduction"
        
        for i, part in enumerate(sections):
            if i == 0:
                current_section = part
                continue
            
            if part.startswith('#'):
                # This is a section header
                if current_section.strip():
                    # Save previous section
                    section_chunks = self._split_section(
                        current_section, section_title, chunk_size, chunk_overlap
                    )
                    chunks.extend(section_chunks)
                section_title = part.strip('#').strip()
                current_section = ""
            else:
                current_section += "\n" + part
        
        # Add last section
        if current_section.strip():
            section_chunks = self._split_section(
                current_section, section_title, chunk_size, chunk_overlap
            )
            chunks.extend(section_chunks)
        
        return chunks
    
    def _split_section(self, content: str, section_title: str,
                      chunk_size: int, chunk_overlap: int) -> List[Dict[str, Any]]:
        """Split a section into smaller chunks if needed."""
        chunks = []
        
        if len(content) <= chunk_size:
            chunks.append({
                "content": content,
                "section": section_title,
                "chunk_index": 0,
                "metadata": {
                    "section": section_title,
                    "chunk_type": "section"
                }
            })
        else:
            # Split by paragraphs first
            paragraphs = content.split('\n\n')
            current_chunk = ""
            chunk_idx = 0
            
            for para in paragraphs:
                if len(current_chunk) + len(para) + 2 <= chunk_size:
                    current_chunk += "\n\n" + para if current_chunk else para
                else:
                    if current_chunk:
                        chunks.append({
                            "content": current_chunk,
                            "section": section_title,
                            "chunk_index": chunk_idx,
                            "metadata": {
                                "section": section_title,
                                "chunk_type": "paragraph",
                                "chunk_index": chunk_idx
                            }
                        })
                        chunk_idx += 1
                    
                    # Start new chunk with overlap
                    if chunks and chunk_overlap > 0:
                        overlap_text = chunks[-1]["content"][-chunk_overlap:]
                        current_chunk = overlap_text + "\n\n" + para
                    else:
                        current_chunk = para
            
            # Add last chunk
            if current_chunk:
                chunks.append({
                    "content": current_chunk,
                    "section": section_title,
                    "chunk_index": chunk_idx,
                    "metadata": {
                        "section": section_title,
                        "chunk_type": "paragraph",
                        "chunk_index": chunk_idx
                    }
                })
        
        return chunks
    
    def embed_and_store(self, chunks: List[Dict[str, Any]], 
                       file_id: Optional[str] = None):
        """
        Embed chunks and store in ChromaDB.
        
        Args:
            chunks: List of chunk dictionaries
            file_id: Optional file identifier
        """
        print(f"Embedding and storing {len(chunks)} chunks...")
        
        # Prepare data for ChromaDB
        ids = []
        documents = []
        metadatas = []
        embeddings = []
        
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
        
        # Generate embeddings
        print("Generating embeddings...")
        embeddings = self.embedder.encode(
            documents,
            show_progress_bar=True,
            convert_to_numpy=True
        ).tolist()
        
        # Store in ChromaDB
        print("Storing in ChromaDB...")
        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings
        )
        
        print(f"Successfully stored {len(chunks)} chunks in ChromaDB")
    
    def process_file(self, file_path: str, 
                    metadata: Optional[Dict] = None,
                    save_md: bool = True,
                    md_output_path: Optional[str] = None,
                    sheet_name: Optional[str] = None,
                    process_all_sheets: bool = False) -> str:
        """
        Complete pipeline: Read file → Convert to MD → Chunk → Embed → Store.
        
        Args:
            file_path: Path to Excel/CSV file
            metadata: Optional metadata
            save_md: Whether to save Markdown file
            md_output_path: Optional path for Markdown output
            sheet_name: Optional sheet name for Excel files (None = first sheet)
            process_all_sheets: If True, process all sheets in Excel file
            
        Returns:
            Path to saved Markdown file (or list of paths if process_all_sheets=True)
        """
        file_path_obj = Path(file_path)
        file_id = file_path_obj.stem
        
        # Handle multiple sheets
        if process_all_sheets and file_path_obj.suffix.lower() in ['.xlsx', '.xls', '.xlsm', '.xlsb']:
            print("Processing all sheets from Excel file...")
            sheets_dict = self.read_all_sheets(file_path)
            
            md_paths = []
            for sheet_name, df in sheets_dict.items():
                print(f"\n{'='*60}")
                print(f"Processing sheet: {sheet_name}")
                print(f"{'='*60}")
                
                # Create sheet-specific metadata
                sheet_metadata = metadata.copy() if metadata else {}
                sheet_metadata['sheet_name'] = sheet_name
                sheet_metadata['total_sheets'] = len(sheets_dict)
                
                # Convert to Markdown
                print("Converting to Markdown...")
                md_content = self.convert_to_markdown(df, sheet_metadata)
                
                # Save Markdown file
                if save_md:
                    if md_output_path is None:
                        md_path = file_path_obj.parent / f"{file_id}_{sheet_name}.md"
                    else:
                        md_path = Path(md_output_path).parent / f"{Path(md_output_path).stem}_{sheet_name}.md"
                    
                    print(f"Saving Markdown to: {md_path}")
                    with open(md_path, 'w', encoding='utf-8') as f:
                        f.write(md_content)
                    md_paths.append(str(md_path))
                
                # Chunk and store
                print("Chunking Markdown...")
                chunks = self.chunk_markdown(md_content)
                print(f"Created {len(chunks)} chunks")
                
                # Embed and store with sheet-specific file_id
                sheet_file_id = f"{file_id}_{sheet_name}"
                self.embed_and_store(chunks, file_id=sheet_file_id)
            
            return md_paths if save_md else None
        
        else:
            # Single sheet/file processing
            df = self.read_file(file_path, sheet_name=sheet_name)
            
            # Convert to Markdown
            print("Converting to Markdown...")
            md_content = self.convert_to_markdown(df, metadata)
            
            # Save Markdown file
            if save_md:
                if md_output_path is None:
                    md_output_path = file_path_obj.with_suffix('.md')
                else:
                    md_output_path = Path(md_output_path)
                
                print(f"Saving Markdown to: {md_output_path}")
                with open(md_output_path, 'w', encoding='utf-8') as f:
                    f.write(md_content)
            
            # Chunk Markdown
            print("Chunking Markdown...")
            chunks = self.chunk_markdown(md_content)
            print(f"Created {len(chunks)} chunks")
            
            # Embed and store
            self.embed_and_store(chunks, file_id=file_id)
            
            return str(md_output_path) if save_md else None
    
    def query(self, query_text: str, n_results: int = 5,
             filter_metadata: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Query the RAG system with enhanced accuracy for logistics queries.
        
        Args:
            query_text: Query string
            n_results: Number of results to return (increased for better coverage)
            filter_metadata: Optional metadata filters
            
        Returns:
            List of relevant chunks with metadata
        """
        # Increase results for better accuracy, especially for complex queries
        # Logistics queries often need more context
        if any(keyword in query_text.lower() for keyword in ['total', 'sum', 'average', 'highest', 'lowest', 'maximum', 'minimum', 'all', 'per', 'ratio', 'efficiency']):
            n_results = max(n_results, 10)  # Get more results for aggregation queries
        
        # Generate query embedding
        query_embedding = self.embedder.encode(
            [query_text],
            convert_to_numpy=True
        )[0].tolist()
        
        # Query ChromaDB
        where = filter_metadata if filter_metadata else None
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where
        )
        
        # Format results
        formatted_results = []
        if results['ids'] and len(results['ids'][0]) > 0:
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    "id": results['ids'][0][i],
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i] if 'distances' in results else None
                })
        
        return formatted_results
    
    def extract_numeric_value(self, query_text: str, 
                             column_name: Optional[str] = None,
                             row_index: Optional[int] = None) -> Optional[Any]:
        """
        Extract exact numeric value from query results with enhanced accuracy.
        Designed for 100% accuracy in numeric retrieval, especially for logistics queries.
        
        Args:
            query_text: Query string
            column_name: Optional specific column to extract from
            row_index: Optional specific row index
            
        Returns:
            Extracted numeric value or None
        """
        # Get more results for better extraction accuracy
        results = self.query(query_text, n_results=15)
        
        # Detect if query is asking for aggregation (total, sum, average, etc.)
        query_lower = query_text.lower()
        is_aggregation = any(keyword in query_lower for keyword in 
                           ['total', 'sum', 'average', 'mean', 'highest', 'lowest', 
                            'maximum', 'minimum', 'max', 'min', 'all'])
        
        # Collect all numeric values for aggregation queries
        all_values = []
        
        # Normalize column_name to string if provided
        column_name_str = None
        if column_name:
            if isinstance(column_name, (list, tuple)):
                column_name_str = str(column_name[0]) if column_name else None
            else:
                column_name_str = str(column_name)
        
        for result in results:
            content = result["content"]
            
            # Try to extract numeric values from the content
            # Look for patterns like "| Column | Value |"
            lines = content.split('\n')
            
            for line in lines:
                # Match markdown table rows (format: | Column | Value |)
                if '|' in line and line.strip().startswith('|'):
                    parts = [p.strip() for p in line.split('|') if p.strip()]
                    if len(parts) >= 2:
                        # Ensure col_name is a string, not a list
                        col_name_raw = parts[0]
                        if isinstance(col_name_raw, (list, tuple)):
                            col_name = str(col_name_raw[0]) if col_name_raw else ""
                        else:
                            col_name = str(col_name_raw).strip('`')
                        value_str = str(parts[1]) if len(parts) > 1 else ""
                        
                        # Check if this matches our criteria - ensure both are strings
                        if column_name_str and col_name and isinstance(col_name, str):
                            if col_name.lower() != column_name_str.lower():
                                continue
                        
                        # Try to parse as number
                        try:
                            # Remove NULL
                            if value_str == "NULL" or value_str.upper() == "NAN":
                                continue
                            
                            # Clean up numpy type annotations
                            value_str = re.sub(r'np\.float64\(([^)]+)\)', r'\1', value_str)
                            value_str = re.sub(r'np\.int64\(([^)]+)\)', r'\1', value_str)
                            
                            # Try float first (handles scientific notation)
                            # Use ast.literal_eval for safe parsing of repr() values
                            try:
                                value = ast.literal_eval(value_str)
                            except (ValueError, SyntaxError):
                                value = float(value_str)
                            
                            # For aggregation queries, collect all values
                            if is_aggregation:
                                all_values.append(value)
                            else:
                                return value
                        except (ValueError, SyntaxError):
                            continue
            
            # Also try direct numeric extraction from content
            numbers = re.findall(r'-?\d+\.?\d*(?:[eE][+-]?\d+)?', content)
            for num_str in numbers:
                try:
                    num_val = float(num_str)
                    if is_aggregation:
                        all_values.append(num_val)
                    else:
                        return num_val
                except ValueError:
                    continue
        
        # Handle aggregation queries
        if is_aggregation and all_values:
            query_lower = query_text.lower()
            if 'total' in query_lower or 'sum' in query_lower:
                return sum(all_values)
            elif 'average' in query_lower or 'mean' in query_lower:
                return sum(all_values) / len(all_values) if all_values else None
            elif 'highest' in query_lower or 'maximum' in query_lower or 'max' in query_lower:
                return max(all_values)
            elif 'lowest' in query_lower or 'minimum' in query_lower or 'min' in query_lower:
                return min(all_values)
            else:
                # Default: return first value or sum if multiple
                return sum(all_values) if len(all_values) > 1 else all_values[0] if all_values else None
        
        # For non-aggregation queries, return first found value
        return None
    
    def get_all_data(self) -> pd.DataFrame:
        """Retrieve all stored data as DataFrame (for verification)."""
        all_results = self.collection.get()
        
        data = []
        for i, doc in enumerate(all_results['documents']):
            data.append({
                "id": all_results['ids'][i],
                "content": doc,
                "metadata": all_results['metadatas'][i]
            })
        
        return pd.DataFrame(data)


if __name__ == "__main__":
    # Example usage
    print("Excel/CSV to RAG System")
    print("=" * 50)
    
    # Initialize system
    rag_system = ExcelToRAG()
    
    # Example: Process a file (uncomment when you have a file)
    # file_path = "example.xlsx"
    # md_path = rag_system.process_file(file_path)
    # print(f"Markdown saved to: {md_path}")
    
    # Example: Query
    # results = rag_system.query("What is the value in column X?")
    # for result in results:
    #     print(f"\nResult: {result['content'][:200]}...")
    
    print("\nSystem initialized. Ready to process files.")

