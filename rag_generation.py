"""
RAG Generation Module
Handles answer generation from retrieved context using SLM.

This module is responsible for:
- Constructing prompts with retrieved context
- Generating answers using SLM (Small Language Model)
- Ensuring answers are grounded in retrieved documents
- Providing safe fallbacks when context is missing

Design Philosophy:
- SLM = Reasoning Engine (not knowledge store)
- Answers must be grounded in retrieved context
- If relevant context is missing, respond with safe fallback
- No hallucination beyond retrieved context
"""

from typing import List, Dict, Any, Optional
import re


class RAGGeneration:
    """Handles answer generation from retrieved context."""
    
    def __init__(self):
        """Initialize generation module."""
        pass
    
    def construct_prompt(self, query: str, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """
        Construct prompt with retrieved context for SLM.
        
        Args:
            query: User query or FAQ intent
            retrieved_chunks: List of retrieved chunks with content
            
        Returns:
            Formatted prompt string
        """
        if not retrieved_chunks:
            return self._construct_fallback_prompt(query)
        
        # Build context from retrieved chunks
        context_parts = []
        for i, chunk in enumerate(retrieved_chunks[:5], 1):  # Use top 5 chunks
            content = chunk.get('content', '').strip()
            if content:
                context_parts.append(f"Context {i}:\n{content}\n")
        
        context = "\n".join(context_parts)
        
        # Construct prompt
        prompt = f"""Based on the following context from the uploaded documents, answer the question accurately.

Context:
{context}

Question: {query}

Instructions:
- Answer strictly based on the provided context
- If the information is not available in the context, say "The information is not available in the provided data."
- Be precise and factual
- Include specific numbers and details from the context when available

Answer:"""
        
        return prompt
    
    def _construct_fallback_prompt(self, query: str) -> str:
        """Construct fallback prompt when no context is retrieved."""
        return f"""Question: {query}

Answer: The information is not available in the provided data. Please make sure relevant documents are uploaded and processed."""
    
    def generate_answer(self, query: str, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """
        Generate answer from retrieved context.
        
        This method intelligently extracts and formats information from retrieved chunks
        to produce clear, readable answers based on the query type.
        
        Args:
            query: User query or FAQ intent
            retrieved_chunks: List of retrieved chunks
            
        Returns:
            Generated answer string
        """
        if not retrieved_chunks:
            return "The information is not available in the provided data. Please make sure relevant documents are uploaded and processed."
        
        query_lower = query.lower()
        
        # Handle different query types intelligently
        # Check for column names FIRST (before list queries) since column queries often contain "what are all"
        if 'column names' in query_lower or 'column name' in query_lower or ('column' in query_lower and 'name' in query_lower):
            # Column names query - extract and list clearly
            return self._generate_column_names_answer(retrieved_chunks)
        elif any(phrase in query_lower for phrase in ['what are all', 'what are the', 'list', 'show me all', 'all the']):
            # List queries - extract unique values
            return self._generate_list_answer(query, retrieved_chunks)
        elif any(phrase in query_lower for phrase in ['total', 'sum', 'average', 'mean', 'highest', 'lowest', 'maximum', 'minimum']):
            # Aggregation queries - calculate and present clearly
            return self._generate_aggregation_answer(query, retrieved_chunks)
        else:
            # General queries - extract relevant information and format clearly
            return self._generate_general_answer(query, retrieved_chunks)
    
    def _clean_content(self, content: str) -> str:
        """Clean and format content for display."""
        if not content:
            return ""
        
        # Remove numpy type annotations
        content = re.sub(r'np\.\w+\(([^)]+)\)', r'\1', content)
        
        # Remove excessive separators
        content = re.sub(r'-{3,}', '', content)
        content = re.sub(r'={3,}', '', content)
        
        # Fix spacing issues
        content = re.sub(r'(\d+\.?\d*)([a-zA-Z])', r'\1 \2', content)
        content = re.sub(r'([a-zA-Z])(\d+\.?\d*)', r'\1 \2', content)
        
        # Remove random text artifacts
        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                cleaned_lines.append('')
                continue
            
            # Skip empty table rows
            if line == '|||' or line == '|' or (line.startswith('|') and line.endswith('|') and len(line.split('|')) <= 3):
                continue
            
            # Skip casual text
            line_lower = line.lower()
            skip_patterns = [
                r'^(hi|hello|hey|bro|dude|man)\s+',
                r'\b(how are you|what\'?s up|wassup)\b',
                r'^(thanks|thank you|thx)',
                r'^(ok|okay|alright|sure|yeah|yes|no)\s*$'
            ]
            
            should_skip = any(re.search(pattern, line_lower) for pattern in skip_patterns)
            if not should_skip:
                cleaned_lines.append(line)
        
        content = '\n'.join(cleaned_lines).strip()
        
        # Clean up whitespace
        content = re.sub(r' {2,}', ' ', content)
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content.strip()
    
    def _generate_list_answer(self, query: str, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """Generate answer for list queries (e.g., 'What are all the source locations?')."""
        import re
        
        query_lower = query.lower()
        extracted_items = set()
        
        # Determine what to extract based on query
        if 'source location' in query_lower or 'source name' in query_lower:
            key_column = 'Source Name'
        elif 'destination location' in query_lower or 'destination name' in query_lower:
            key_column = 'Destination Name'
        elif 'product' in query_lower and 'code' not in query_lower:
            key_column = 'Product Name'
        elif 'transportation mode' in query_lower or ('mode' in query_lower and 'utilization' not in query_lower):
            key_column = 'Mode'
        elif 'load type' in query_lower:
            key_column = 'Load Type'
        elif 'customer' in query_lower:
            key_column = 'Customer Name'
        elif 'consignment number' in query_lower or 'consignment no' in query_lower:
            key_column = 'Consignment No'
        else:
            # Fallback to general extraction
            return self._generate_general_answer(query, retrieved_chunks)
        
        # Extract values from chunks - look for row-by-row format first
        for chunk in retrieved_chunks:
            content = chunk.get('content', '')
            lines = content.split('\n')
            
            # Method 1: Extract from row-by-row format "| `Column` | Value |"
            for line in lines:
                if '|' in line and (f'`{key_column}`' in line or f'`{key_column.lower()}`' in line):
                    parts = [p.strip().strip('`') for p in line.split('|') if p.strip()]
                    if len(parts) >= 2:
                        value = parts[1].strip('`').strip()
                        if value and value not in ['NULL', 'Value', 'Column', '---', '']:
                            extracted_items.add(value)
            
            # Method 2: Extract from table format - find column index first
            header_found = False
            col_index = None
            for line in lines:
                if '|' in line:
                    parts = [p.strip().strip('`') for p in line.split('|') if p.strip()]
                    # Check if this is a header row
                    if any(key_column.lower() in p.lower() for p in parts):
                        header_found = True
                        # Find column index
                        for idx, part in enumerate(parts):
                            if key_column.lower() in part.lower():
                                col_index = idx
                                break
                        continue
                    
                    # If we found the header, extract values from data rows
                    if header_found and col_index is not None and len(parts) > col_index:
                        value = parts[col_index].strip('`').strip()
                        if value and value not in ['NULL', '---', ''] and not value.startswith('-'):
                            # Check if it's a meaningful value (not just a number if we expect text)
                            if key_column in ['Source Name', 'Destination Name', 'Product Name', 'Mode', 'Load Type', 'Customer Name']:
                                if not value.replace('.', '').replace('-', '').isdigit():
                                    extracted_items.add(value)
                            else:
                                extracted_items.add(value)
        
        if extracted_items:
            items_list = sorted(list(extracted_items))
            answer = f"**{query}**\n\n"
            for i, item in enumerate(items_list, 1):
                answer += f"{i}. {item}\n"
            return answer.strip()
        else:
            # Fallback: try to extract from general content
            return self._generate_general_answer(query, retrieved_chunks)
    
    def _generate_column_names_answer(self, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """Generate answer for column names query."""
        import re
        column_names = set()
        
        print(f"[Generation] _generate_column_names_answer called with {len(retrieved_chunks)} chunks")
        
        # Process all chunks to extract column names
        for chunk_idx, chunk in enumerate(retrieved_chunks):
            content = chunk.get('content', '')
            if not content:
                print(f"[Generation] Chunk {chunk_idx} has no content")
                continue
            
            print(f"[Generation] Processing chunk {chunk_idx}, content length: {len(content)}")
            
            # Method 1: Use regex to extract ALL column names from backticks
            # Pattern: | `ColumnName` | (works even if table is compressed)
            column_pattern = r'\|\s*`([^`]+)`\s*\|'
            matches = re.findall(column_pattern, content)
            print(f"[Generation] Regex found {len(matches)} potential column names")
            
            for match in matches:
                col_name = match.strip()
                if col_name and len(col_name) > 1:
                    # Skip table headers
                    skip_reasons = []
                    if col_name.lower() in ['column name', '---', 'data type', 'non-null count', 'null count']:
                        skip_reasons.append("table header")
                    elif all(c in '-=' for c in col_name):
                        skip_reasons.append("separator")
                    elif col_name.startswith('#'):
                        skip_reasons.append("markdown header")
                    elif 'json' in col_name.lower() or 'metadata' in col_name.lower() or 'file_path' in col_name.lower() or 'sheet_name' in col_name.lower():
                        skip_reasons.append("metadata")
                    else:
                        column_names.add(col_name)
                        print(f"[Generation] ✓ Added column: '{col_name}'")
                    if skip_reasons:
                        print(f"[Generation] ✗ Skipped '{col_name}': {', '.join(skip_reasons)}")
            
            # Method 2: Line-by-line parsing (for properly formatted content)
            lines = content.split('\n')
            in_column_section = False
            found_column_table_header = False
            skip_metadata = False
            
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                line_lower = line_stripped.lower()
                
                # Skip metadata JSON blocks
                if line_stripped.startswith('```'):
                    skip_metadata = not skip_metadata
                    continue
                if skip_metadata:
                    continue
                
                # Skip markdown headers that aren't column information
                if line_stripped.startswith('##') and 'column information' not in line_lower:
                    continue
                
                # Detect column information section
                if 'column information' in line_lower:
                    in_column_section = True
                    continue
                
                # Look for the Column Information table header: | Column Name | Data Type | ...
                if in_column_section and '|' in line_stripped:
                    parts = [p.strip() for p in line_stripped.split('|') if p.strip()]
                    # Check if this is the table header row
                    if len(parts) >= 2 and 'column name' in line_lower:
                        found_column_table_header = True
                        continue
                    # Skip separator row (---)
                    if '---' in line_stripped or all(p.strip().replace('-', '').strip() == '' for p in parts):
                        continue
                    
                    # Extract column name from table row: | `ColumnName` | dtype | count | count |
                    if found_column_table_header and len(parts) >= 1:
                        # Column name is in first part, wrapped in backticks
                        first_part = parts[0].strip()
                        # Remove backticks
                        col_name = first_part.strip('`').strip()
                        
                        # Validate it's a real column name
                        if col_name and len(col_name) > 1:
                            # Skip table headers and separators
                            if col_name.lower() not in ['column name', '---', 'data type', 'non-null count', 'null count', '']:
                                # Skip if it's just dashes
                                if not all(c in '-=' for c in col_name):
                                    # Skip markdown headers
                                    if not col_name.startswith('#'):
                                        column_names.add(col_name)
                
                # Also extract from data preview/complete table view headers
                # These are the actual column headers from the data
                if ('data preview' in line_lower or 'complete table view' in line_lower or 
                    'first 5 rows' in line_lower):
                    # Next few lines should have the table header
                    # Look ahead for the header row
                    for j in range(i+1, min(i+5, len(lines))):
                        next_line = lines[j].strip()
                        if '|' in next_line and '---' not in next_line:
                            parts = [p.strip().strip('`') for p in next_line.split('|') if p.strip()]
                            if len(parts) >= 3:  # At least 3 columns for a data table
                                # Check if it's likely a header (mostly text, not numbers)
                                text_parts = [p for p in parts if not re.search(r'^-?\d+\.?\d*$', p.strip())]
                                if len(text_parts) > len(parts) * 0.6:  # 60% text = likely header
                                    for part in parts:
                                        part_clean = part.strip('`').strip()
                                        if part_clean and len(part_clean) > 1:
                                            # Skip common non-column words
                                            if part_clean.lower() not in ['---', 'column', 'value', 'row', 'data', 'null', 'type']:
                                                # Skip if it's clearly a number
                                                if not re.match(r'^-?\d+\.?\d*$', part_clean):
                                                    # Skip markdown headers
                                                    if not part_clean.startswith('#'):
                                                        column_names.add(part_clean)
                            break
                
                # Extract from row-by-row format: | `Column Name` | Value |
                # This format appears in "Row-by-Row Data" section
                if '|' in line_stripped and '`' in line_stripped:
                    parts = [p.strip() for p in line_stripped.split('|') if p.strip()]
                    if len(parts) >= 2:
                        # First part should be column name wrapped in backticks
                        first_part = parts[0].strip()
                        col_name = first_part.strip('`').strip()
                        
                        # Validate it's a column name (not a value)
                        if col_name and len(col_name) > 1:
                            # Skip table headers
                            if col_name.lower() not in ['column', 'value', '---', 'row']:
                                # Skip if it's a number
                                if not re.match(r'^-?\d+\.?\d*$', col_name):
                                    # Skip markdown headers
                                    if not col_name.startswith('#'):
                                        column_names.add(col_name)
        
        # Filter out invalid entries (markdown headers, metadata, etc.)
        filtered_columns = []
        seen_lower = set()
        
        print(f"[Generation] Before filtering: {len(column_names)} columns found")
        print(f"[Generation] Column names found: {sorted(column_names)}")
        
        for col in sorted(column_names):
            col_lower = col.lower()
            
            # Skip if it's clearly not a column name
            skip_patterns = [
                'document metadata', 'column information', 'data preview', 
                'complete data', 'row-by-row data', 'complete table view',
                'numeric summary statistics', 'first 5 rows', 'sheet_name',
                'file_path', 'json', 'metadata', 'column name', 'data type',
                'non-null count', 'null count'
            ]
            
            should_skip = False
            skip_reason = None
            for pattern in skip_patterns:
                if pattern in col_lower:
                    should_skip = True
                    skip_reason = f"contains '{pattern}'"
                    break
            
            # Skip if it starts with # (markdown header)
            if not should_skip and col.startswith('#'):
                should_skip = True
                skip_reason = "starts with #"
            
            # Skip if it's just symbols (but allow columns like "Unnamed: 0")
            if not should_skip and not re.search(r'[a-zA-Z0-9]', col):
                should_skip = True
                skip_reason = "no alphanumeric characters"
            
            if not should_skip and col_lower not in seen_lower:
                seen_lower.add(col_lower)
                filtered_columns.append(col)
                print(f"[Generation] ✓ Kept column after filtering: '{col}'")
            elif should_skip:
                print(f"[Generation] ✗ Filtered out '{col}': {skip_reason}")
        
        print(f"[Generation] After filtering: {len(filtered_columns)} columns remain")
        
        if filtered_columns:
            answer = "**Column Names in this file:**\n\n"
            for i, col in enumerate(filtered_columns, 1):
                answer += f"{i}. {col}\n"
            return answer.strip()
        else:
            # Fallback: extract from any table header found
            print("[Generation] No valid columns found, using general answer fallback...")
            return self._generate_general_answer("column names", retrieved_chunks)
    
    def _generate_aggregation_answer(self, query: str, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """Generate answer for aggregation queries (total, sum, average, etc.)."""
        import re
        
        query_lower = query.lower()
        
        # Check if it's a "per X" query (e.g., "total cost per source location")
        if 'per' in query_lower:
            return self._generate_per_group_answer(query, retrieved_chunks)
        
        values = []
        answer_type = None
        
        # Determine aggregation type
        if 'total' in query_lower or 'sum' in query_lower:
            answer_type = 'total'
        elif 'average' in query_lower or 'mean' in query_lower:
            answer_type = 'average'
        elif 'highest' in query_lower or 'maximum' in query_lower or 'max' in query_lower:
            answer_type = 'highest'
        elif 'lowest' in query_lower or 'minimum' in query_lower or 'min' in query_lower:
            answer_type = 'lowest'
        
        # Determine what to aggregate
        if 'cost' in query_lower:
            key_term = 'cost'
        elif 'weight' in query_lower:
            key_term = 'weight'
        elif 'volume' in query_lower:
            key_term = 'volume'
        elif 'cases' in query_lower:
            key_term = 'cases'
        elif 'consignment' in query_lower and 'mrp' in query_lower:
            key_term = 'mrp'
        else:
            key_term = None
        
        # Extract numeric values from chunks - look for row-by-row format
        for chunk in retrieved_chunks:
            content = chunk.get('content', '')
            lines = content.split('\n')
            
            # Method 1: Extract from row-by-row format
            current_row_data = {}
            for line in lines:
                if '|' in line and '`' in line:
                    parts = [p.strip().strip('`') for p in line.split('|') if p.strip()]
                    if len(parts) >= 2:
                        col_name = parts[0]
                        value = parts[1]
                        current_row_data[col_name.lower()] = value
                        
                        # Check if we found the key term column
                        if key_term and key_term in col_name.lower():
                            # Extract number from value
                            numbers = re.findall(r'-?\d+\.?\d*', value)
                            for num_str in numbers:
                                try:
                                    val = float(num_str)
                                    if val > 0:
                                        values.append(val)
                                except:
                                    pass
            
            # Method 2: Extract from table format
            for line in lines:
                if '|' in line and '---' not in line:
                    parts = [p.strip().strip('`') for p in line.split('|') if p.strip()]
                    for i, part in enumerate(parts):
                        part_lower = part.lower()
                        if key_term and key_term in part_lower:
                            # Try adjacent cells for value
                            for j in range(max(0, i-1), min(len(parts), i+2)):
                                val_str = parts[j].strip('`').strip()
                                numbers = re.findall(r'-?\d+\.?\d*', val_str.replace(',', ''))
                                for num_str in numbers:
                                    try:
                                        val = float(num_str)
                                        if val > 0 and val < 1e10:
                                            values.append(val)
                                    except:
                                        pass
        
        # Calculate result
        if values:
            # Remove duplicates and outliers
            unique_values = []
            seen = set()
            for v in values:
                if v not in seen and 0 < v < 1e10:
                    unique_values.append(v)
                    seen.add(v)
            
            if unique_values:
                if answer_type == 'total' or answer_type is None:
                    result = sum(unique_values)
                    answer = f"**Total:** {result:,.2f}"
                elif answer_type == 'average':
                    result = sum(unique_values) / len(unique_values)
                    answer = f"**Average:** {result:,.2f}"
                elif answer_type == 'highest':
                    result = max(unique_values)
                    answer = f"**Highest:** {result:,.2f}"
                elif answer_type == 'lowest':
                    result = min(unique_values)
                    answer = f"**Lowest:** {result:,.2f}"
                else:
                    result = sum(unique_values)
                    answer = f"**Result:** {result:,.2f}"
                
                return answer
        
        return self._generate_general_answer(query, retrieved_chunks)
    
    def _generate_per_group_answer(self, query: str, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """Generate answer for 'per X' queries (e.g., 'total cost per source location')."""
        import re
        
        query_lower = query.lower()
        
        # Determine grouping column
        if 'source location' in query_lower or 'source name' in query_lower:
            group_col = 'Source Name'
        elif 'destination location' in query_lower or 'destination name' in query_lower:
            group_col = 'Destination Name'
        elif 'customer' in query_lower:
            group_col = 'Customer Name'
        elif 'consignment' in query_lower:
            group_col = 'Consignment No'
        else:
            group_col = None
        
        # Determine value column
        if 'cost' in query_lower:
            value_col = 'Total Transportation Cost'
        elif 'weight' in query_lower:
            value_col = 'Total Weight'
        elif 'volume' in query_lower:
            value_col = 'Total Volume'
        elif 'mrp' in query_lower:
            value_col = 'Total Consignment MRP Value'
        else:
            value_col = None
        
        if not group_col or not value_col:
            return self._generate_general_answer(query, retrieved_chunks)
        
        # Extract grouped data
        grouped_data = {}
        
        for chunk in retrieved_chunks:
            content = chunk.get('content', '')
            lines = content.split('\n')
            
            current_group = None
            current_value = None
            
            # Extract from row-by-row format
            for line in lines:
                if '|' in line and '`' in line:
                    parts = [p.strip().strip('`') for p in line.split('|') if p.strip()]
                    if len(parts) >= 2:
                        col_name = parts[0]
                        value = parts[1]
                        
                        if group_col.lower() in col_name.lower():
                            current_group = value.strip('`').strip()
                        if value_col.lower() in col_name.lower():
                            # Extract number
                            numbers = re.findall(r'-?\d+\.?\d*', value.replace(',', ''))
                            if numbers:
                                try:
                                    current_value = float(numbers[0])
                                except:
                                    pass
                        
                        # When we have both, store it
                        if current_group and current_value is not None:
                            if current_group not in grouped_data:
                                grouped_data[current_group] = []
                            grouped_data[current_group].append(current_value)
                            current_group = None
                            current_value = None
        
        # Calculate totals per group
        if grouped_data:
            answer = f"**{query}**\n\n"
            for group in sorted(grouped_data.keys()):
                total = sum(grouped_data[group])
                answer += f"**{group}:** {total:,.2f}\n"
            return answer.strip()
        else:
            return self._generate_general_answer(query, retrieved_chunks)
    
    def _generate_general_answer(self, query: str, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """Generate answer for general queries - extract relevant info without markdown noise."""
        import re
        
        if not retrieved_chunks:
            return "The information is not available in the provided data. Please make sure the file is uploaded and processed correctly."
        
        # Extract most relevant information from top chunks
        answer_parts = []
        query_lower = query.lower()
        
        # Always show something from retrieved chunks if they exist
        for chunk in retrieved_chunks[:3]:  # Use top 3 chunks for better coverage
            content = chunk.get('content', '').strip()
            if not content:
                continue
            
            lines = content.split('\n')
            relevant_lines = []
            skip_next = False
            in_metadata = False
            
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                # Skip metadata JSON blocks
                if line.startswith('```'):
                    in_metadata = not in_metadata
                    continue
                if in_metadata:
                    continue
                
                # Skip document metadata headers
                if 'document metadata' in line.lower():
                    continue
                
                # Keep simplified section headers
                if line.startswith('##') or line.startswith('###'):
                    header = line.replace('#', '').strip()
                    # Skip generic headers, keep specific ones
                    if header.lower() not in ['document metadata', 'column information', 'row-by-row data']:
                        if any(keyword in header.lower() for keyword in ['data', 'table', 'preview', 'summary', 'statistics']):
                            relevant_lines.append(f"\n**{header}**")
                    continue
                
                # Extract data from tables
                if '|' in line:
                    # Skip separator rows
                    if '---' in line or line.replace('|', '').replace('-', '').strip() == '':
                        continue
                    
                    parts = [p.strip().strip('`') for p in line.split('|') if p.strip()]
                    if len(parts) >= 2:
                        # For column information table, extract column names
                        if 'column' in query_lower and 'name' in query_lower:
                            # This is a column info row
                            col_name = parts[0] if len(parts) > 0 else ''
                            if col_name and col_name.lower() not in ['column name', '---', '']:
                                relevant_lines.append(f"• {col_name}")
                        else:
                            # Regular data row - show data by default
                            line_lower = line.lower()
                            is_relevant = True  # Show data by default
                            
                            # Check if query keywords appear
                            query_words = [w for w in query_lower.split() if len(w) > 3]
                            if query_words:
                                # Prefer rows that match query
                                matches = sum(1 for word in query_words if word in line_lower)
                                if matches > 0 or len(relevant_lines) < 15:
                                    # Format table row
                                    formatted_row = ' | '.join(parts[:8])  # Show more columns
                                    if len(parts) > 8:
                                        formatted_row += ' | ...'
                                    relevant_lines.append(formatted_row)
                            else:
                                # No specific keywords, show data anyway
                                formatted_row = ' | '.join(parts[:8])
                                if len(parts) > 8:
                                    formatted_row += ' | ...'
                                relevant_lines.append(formatted_row)
            
            if relevant_lines:
                chunk_answer = '\n'.join(relevant_lines[:25])  # Show more lines
                if chunk_answer.strip():
                    answer_parts.append(chunk_answer)
        
        if answer_parts:
            answer = '\n\n'.join(answer_parts)
            # Clean up
            answer = re.sub(r'\n{3,}', '\n\n', answer)
            return answer.strip()
        else:
            # Last resort: show first chunk content cleaned up
            if retrieved_chunks:
                first_chunk = retrieved_chunks[0].get('content', '')
                if first_chunk:
                    cleaned = self._clean_content(first_chunk)
                    # Extract table data and relevant info
                    lines = cleaned.split('\n')
                    relevant = []
                    skip_metadata = False
                    
                    for line in lines:
                        if '```' in line:
                            skip_metadata = not skip_metadata
                            continue
                        if skip_metadata or 'document metadata' in line.lower():
                            continue
                        if line.strip() and not line.startswith('#'):
                            # Keep table rows and data
                            if '|' in line or len(line.strip()) > 10:
                                relevant.append(line)
                                if len(relevant) >= 30:  # Show more lines
                                    break
                    
                    if relevant:
                        return '\n'.join(relevant)
            
            # If we have chunks but couldn't extract anything, show a diagnostic message
            return f"I found data in the database, but couldn't extract the specific information you're looking for.\n\nPlease try:\n- Rephrasing your question\n- Asking about specific columns or data points\n- Checking if the data contains the information you need\n\nDebug: Found {len(retrieved_chunks)} chunks in database."
    
    def _remove_duplicate_headers(self, content: str) -> str:
        """Remove duplicate section headers from content."""
        if not content:
            return content
        
        lines = content.split('\n')
        cleaned = []
        seen_headers = {}
        last_header_line = -10
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            is_header = False
            header_key = None
            
            if line_stripped.startswith('#'):
                header_key = line_stripped.lower()
                is_header = True
            elif line_stripped.lower() in ['column information', 'description', 'details', 
                                          'data preview', 'complete data', 'row-by-row data']:
                header_key = line_stripped.lower()
                is_header = True
            
            if is_header and header_key:
                if header_key in seen_headers and (i - seen_headers[header_key]) < 5:
                    continue
                seen_headers[header_key] = i
                last_header_line = i
            
            if not is_header and line_stripped and (i - last_header_line) > 10:
                seen_headers = {}
            
            cleaned.append(line)
        
        return '\n'.join(cleaned)
