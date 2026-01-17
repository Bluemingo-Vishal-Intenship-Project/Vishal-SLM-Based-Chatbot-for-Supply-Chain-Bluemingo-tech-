"""
RAG Ingestion Module
Handles document ingestion, normalization, and chunking.

This module is responsible for:
- Accepting new documents (PDF/DOC/TXT/structured text)
- Normalizing text (cleaning, formatting)
- Chunking content (overlapping chunks preferred)
- Preparing chunks for embedding

Design Philosophy:
- Ingestion is separate from embedding and storage
- New data becomes instantly searchable via retrieval
- No model retraining or FAQ regeneration on new data upload
"""

import pandas as pd
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import json


class RAGIngestion:
    """Handles document ingestion and chunking for RAG system."""
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100):
        """
        Initialize ingestion module.
        
        Args:
            chunk_size: Maximum chunk size in characters (reduced for better granularity)
            chunk_overlap: Overlap between chunks for better context continuity
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def normalize_text(self, text: str) -> str:
        """
        Normalize text by cleaning and formatting.
        
        Args:
            text: Raw text content
            
        Returns:
            Normalized text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special control characters but keep newlines
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', '', text)
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        # Remove trailing whitespace from lines
        lines = [line.rstrip() for line in text.split('\n')]
        return '\n'.join(lines)
    
    def read_excel_file(self, file_path: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
        """
        Read Excel or CSV file.
        
        Args:
            file_path: Path to the file
            sheet_name: Optional sheet name for Excel files
            
        Returns:
            DataFrame with the file contents
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_ext = file_path.suffix.lower()
        
        if file_ext == '.csv':
            # Try different encodings for CSV
            for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    df = pd.read_csv(file_path, encoding=encoding, low_memory=False)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                df = pd.read_csv(file_path, encoding='utf-8', errors='ignore', low_memory=False)
        
        elif file_ext in ['.xlsx', '.xls', '.xlsm', '.xlsb']:
            try:
                if file_ext == '.xls':
                    engine = 'xlrd'
                else:
                    engine = 'openpyxl'
                
                if sheet_name is not None:
                    df = pd.read_excel(file_path, sheet_name=sheet_name, engine=engine)
                else:
                    df = pd.read_excel(file_path, engine=engine)
            except Exception as e:
                raise ValueError(f"Could not read {file_ext} file: {e}")
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")
        
        # Clean up the DataFrame
        df = df.dropna(how='all').dropna(axis=1, how='all').reset_index(drop=True)
        
        return df
    
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
        
        if file_ext == '.xls':
            engine = 'xlrd'
        else:
            engine = 'openpyxl'
        
        excel_file = pd.ExcelFile(file_path, engine=engine)
        sheets_dict = {}
        
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            df = df.dropna(how='all').dropna(axis=1, how='all').reset_index(drop=True)
            sheets_dict[sheet_name] = df
        
        return sheets_dict
    
    def convert_dataframe_to_markdown(self, df: pd.DataFrame, 
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
        import numpy as np
        
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
        
        # Add data preview
        md_lines.append("## Data Preview\n")
        md_lines.append("### First 5 Rows\n")
        md_lines.append(self._dataframe_to_markdown_table(df.head(5)))
        md_lines.append("")
        
        # Add complete data section
        md_lines.append("## Complete Data\n")
        md_lines.append("### Row-by-Row Data\n")
        md_lines.append("")
        
        for idx, row in df.iterrows():
            md_lines.append(f"### Row {idx}\n")
            md_lines.append("| Column | Value |")
            md_lines.append("|--------|-------|")
            
            for col in df.columns:
                value = row[col]
                if pd.isna(value):
                    value_str = "NULL"
                else:
                    if hasattr(value, 'item'):
                        try:
                            value = value.item()
                        except (ValueError, AttributeError):
                            pass
                    
                    if isinstance(value, (int, np.integer)):
                        value_str = str(int(value))
                    elif isinstance(value, (float, np.floating)):
                        if float(value).is_integer():
                            value_str = str(int(value))
                        else:
                            value_str = repr(float(value))
                            if '.' in value_str and 'e' not in value_str.lower():
                                value_str = value_str.rstrip('0').rstrip('.')
                    else:
                        value_str = str(value)
                
                md_lines.append(f"| `{col}` | {value_str} |")
            md_lines.append("")
        
        # Add summary statistics
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
        import numpy as np
        
        df_display = df.copy()
        df_display = df_display.fillna("NULL")
        
        lines = []
        lines.append("| " + " | ".join([str(col) for col in df.columns]) + " |")
        lines.append("| " + " | ".join(["---" for _ in df.columns]) + " |")
        
        for _, row in df_display.iterrows():
            row_values = []
            for col in df.columns:
                val = row[col]
                if val != "NULL":
                    if hasattr(val, 'item'):
                        try:
                            val = val.item()
                        except (ValueError, AttributeError):
                            pass
                    
                    if isinstance(val, (int, np.integer)):
                        row_values.append(str(int(val)))
                    elif isinstance(val, (float, np.floating)):
                        float_val = float(val)
                        if float_val.is_integer():
                            row_values.append(str(int(float_val)))
                        else:
                            val_str = repr(float_val)
                            if '.' in val_str and 'e' not in val_str.lower():
                                val_str = val_str.rstrip('0').rstrip('.')
                            row_values.append(val_str)
                    else:
                        row_values.append(str(val))
                else:
                    row_values.append("NULL")
            lines.append("| " + " | ".join(row_values) + " |")
        
        return "\n".join(lines)
    
    def chunk_markdown(self, md_content: str) -> List[Dict[str, Any]]:
        """
        Chunk Markdown content into smaller sections with overlap.
        Optimized for Excel/CSV data with row-by-row information.
        
        This method creates multiple chunks to ensure good retrieval:
        - One chunk per row for row-by-row data
        - Separate chunks for each major section
        - Table data chunked by rows
        
        Args:
            md_content: Markdown content
            
        Returns:
            List of chunk dictionaries with metadata
        """
        chunks = []
        
        # Normalize content first
        md_content = self.normalize_text(md_content)
        
        # Strategy 1: Extract row-by-row data first (most important for queries)
        row_chunks = self._extract_row_chunks(md_content)
        if row_chunks:
            chunks.extend(row_chunks)
            print(f"[Chunking] Created {len(row_chunks)} row chunks")
        
        # Strategy 2: Chunk by major sections (## headers)
        section_chunks = self._chunk_by_sections(md_content)
        if section_chunks:
            chunks.extend(section_chunks)
            print(f"[Chunking] Created {len(section_chunks)} section chunks")
        
        # Strategy 3: Chunk table views
        table_chunks = self._chunk_table_views(md_content)
        if table_chunks:
            chunks.extend(table_chunks)
            print(f"[Chunking] Created {len(table_chunks)} table chunks")
        
        # If still very few chunks, use aggressive chunking
        if len(chunks) < 5:
            print(f"[Chunking] WARNING: Only {len(chunks)} chunks created, using aggressive chunking")
            aggressive_chunks = self._aggressive_chunk(md_content)
            if aggressive_chunks:
                chunks = aggressive_chunks
                print(f"[Chunking] Aggressive chunking created {len(chunks)} chunks")
        
        # Remove duplicates (same content)
        seen_content = set()
        unique_chunks = []
        for chunk in chunks:
            content_hash = hash(chunk['content'][:100])  # Hash first 100 chars
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_chunks.append(chunk)
        
        print(f"[Chunking] Final: {len(unique_chunks)} unique chunks (from {len(chunks)} total)")
        return unique_chunks if unique_chunks else [{
            "content": md_content[:self.chunk_size * 2],
            "section": "Content",
            "chunk_index": 0,
            "metadata": {"section": "Content", "chunk_type": "fallback"}
        }]
    
    def _extract_row_chunks(self, md_content: str) -> List[Dict[str, Any]]:
        """Extract individual row chunks from row-by-row data section."""
        chunks = []
        
        # Find the "Row-by-Row Data" section
        row_section_match = re.search(
            r'## Complete Data\s*\n### Row-by-Row Data\s*\n(.*?)(?=\n##|\Z)',
            md_content,
            re.DOTALL
        )
        
        if not row_section_match:
            return chunks
        
        row_section_content = row_section_match.group(1)
        
        # Extract each row using pattern: ### Row X followed by table
        row_pattern = r'### Row (\d+)\n(\| Column \| Value \|\n\|[^\n]+\|\n((?:\|[^\n]+\|\n?)+))'
        row_matches = re.finditer(row_pattern, row_section_content, re.MULTILINE)
        
        for match in row_matches:
            row_num = int(match.group(1))
            row_table = match.group(2)
            
            chunk_content = f"### Row {row_num}\n{row_table}"
            chunks.append({
                "content": chunk_content,
                "section": f"Row {row_num}",
                "chunk_index": len(chunks),
                "metadata": {
                    "section": "Row-by-Row Data",
                    "chunk_type": "single_row",
                    "row_number": row_num
                }
            })
        
        return chunks
    
    def _chunk_by_sections(self, md_content: str) -> List[Dict[str, Any]]:
        """Chunk content by major sections (## headers)."""
        chunks = []
        
        # Split by ## headers
        sections = re.split(r'\n(##\s+[^\n]+)\n', md_content)
        
        current_section = ""
        section_title = "Introduction"
        
        for i, part in enumerate(sections):
            if i == 0:
                if part.strip():
                    current_section = part.strip()
                continue
            
            if part.startswith('##'):
                # Save previous section
                if current_section.strip() and 'Row-by-Row Data' not in section_title:
                    section_chunks = self._split_section(
                        current_section, section_title, self.chunk_size, self.chunk_overlap
                    )
                    chunks.extend(section_chunks)
                
                # Start new section
                section_title = part.strip('#').strip()
                current_section = ""
            else:
                if current_section:
                    current_section += "\n\n" + part.strip()
                else:
                    current_section = part.strip()
        
        # Add last section
        if current_section.strip() and 'Row-by-Row Data' not in section_title:
            section_chunks = self._split_section(
                current_section, section_title, self.chunk_size, self.chunk_overlap
            )
            chunks.extend(section_chunks)
        
        return chunks
    
    def _chunk_table_views(self, md_content: str) -> List[Dict[str, Any]]:
        """Chunk table views (Complete Table View section)."""
        chunks = []
        
        # Find "Complete Table View" section
        table_match = re.search(
            r'## Complete Table View\s*\n(.*?)(?=\n##|\Z)',
            md_content,
            re.DOTALL
        )
        
        if not table_match:
            return chunks
        
        table_content = table_match.group(1)
        lines = table_content.split('\n')
        
        current_chunk_lines = []
        chunk_idx = 0
        lines_per_chunk = 3  # 3 lines per chunk (header + 2 data rows)
        
        for line in lines:
            if '|' in line and not line.strip().startswith('|---'):
                current_chunk_lines.append(line)
                
                if len(current_chunk_lines) >= lines_per_chunk:
                    chunk_content = '\n'.join(current_chunk_lines)
                    chunks.append({
                        "content": chunk_content,
                        "section": "Complete Table View",
                        "chunk_index": chunk_idx,
                        "metadata": {
                            "section": "Complete Table View",
                            "chunk_type": "table_rows",
                            "chunk_index": chunk_idx
                        }
                    })
                    chunk_idx += 1
                    # Keep last line for overlap
                    current_chunk_lines = current_chunk_lines[-1:] if current_chunk_lines else []
        
        # Add remaining lines
        if current_chunk_lines:
            chunk_content = '\n'.join(current_chunk_lines)
            chunks.append({
                "content": chunk_content,
                "section": "Complete Table View",
                "chunk_index": chunk_idx,
                "metadata": {
                    "section": "Complete Table View",
                    "chunk_type": "table_rows",
                    "chunk_index": chunk_idx
                }
            })
        
        return chunks
    
    def _split_section(self, content: str, section_title: str,
                      chunk_size: int, chunk_overlap: int) -> List[Dict[str, Any]]:
        """Split a section into smaller chunks if needed."""
        chunks = []
        
        # Always split, even if content is small - create at least 2-3 chunks for better retrieval
        if len(content) <= chunk_size:
            # Even small content should be split if possible
            # Split by lines or paragraphs
            lines = content.split('\n')
            if len(lines) > 3:
                # Split into 2-3 chunks
                lines_per_chunk = max(2, len(lines) // 3)
                for i in range(0, len(lines), lines_per_chunk):
                    chunk_lines = lines[i:i + lines_per_chunk]
                    chunk_content = '\n'.join(chunk_lines)
                    if chunk_content.strip():
                        chunks.append({
                            "content": chunk_content,
                            "section": section_title,
                            "chunk_index": len(chunks),
                            "metadata": {
                                "section": section_title,
                                "chunk_type": "section",
                                "chunk_index": len(chunks)
                            }
                        })
            else:
                # Too small to split meaningfully
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
                para = para.strip()
                if not para:
                    continue
                
                # If adding this paragraph would exceed chunk size, save current chunk
                if current_chunk and len(current_chunk) + len(para) + 2 > chunk_size:
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
                else:
                    # Add paragraph to current chunk
                    if current_chunk:
                        current_chunk += "\n\n" + para
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
    
    def _aggressive_chunk(self, content: str) -> List[Dict[str, Any]]:
        """Aggressively chunk content when normal chunking fails."""
        chunks = []
        
        # Split by double newlines (paragraphs)
        paragraphs = content.split('\n\n')
        
        current_chunk = ""
        chunk_idx = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # If adding this paragraph would exceed chunk size, save current chunk
            if current_chunk and len(current_chunk) + len(para) + 2 > self.chunk_size:
                chunks.append({
                    "content": current_chunk,
                    "section": "Content",
                    "chunk_index": chunk_idx,
                    "metadata": {
                        "section": "Content",
                        "chunk_type": "paragraph",
                        "chunk_index": chunk_idx
                    }
                })
                chunk_idx += 1
                # Start new chunk with overlap
                if chunks and self.chunk_overlap > 0:
                    overlap = chunks[-1]["content"][-self.chunk_overlap:]
                    current_chunk = overlap + "\n\n" + para
                else:
                    current_chunk = para
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
        
        # Add last chunk
        if current_chunk:
            chunks.append({
                "content": current_chunk,
                "section": "Content",
                "chunk_index": chunk_idx,
                "metadata": {
                    "section": "Content",
                    "chunk_type": "paragraph",
                    "chunk_index": chunk_idx
                }
            })
        
        return chunks if chunks else [{
            "content": content[:self.chunk_size * 2],
            "section": "Content",
            "chunk_index": 0,
            "metadata": {"section": "Content", "chunk_type": "fallback"}
        }]
