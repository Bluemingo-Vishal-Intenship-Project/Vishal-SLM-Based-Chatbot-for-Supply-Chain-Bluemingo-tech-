"""
Intent Classifier Module
Classifies user queries and FAQ clicks into intent categories for query generation.

Design Philosophy:
- FAQs = Intent Shortcuts (static, data-agnostic)
- All queries (typed or FAQ) map to query templates
- Intent classification combines rule-based detection (primary) with SLM similarity (secondary)
- Confidence scoring and ambiguity detection ensure reliable classification

SLM Usage (MiniLM):
- Used ONLY for semantic similarity scoring in intent matching
- Used for ranking candidate intents
- NOT used for answer generation or data computation
- System must function with rule-based fallback if SLM unavailable
"""

from typing import Dict, List, Optional, Tuple, Any
import re
import numpy as np

# Try to import MiniLM for similarity scoring, but allow fallback to rule-based
try:
    from sentence_transformers import SentenceTransformer
    MINILM_AVAILABLE = True
except ImportError:
    MINILM_AVAILABLE = False
    print("[IntentClassifier] MiniLM not available, using rule-based classification only")


class IntentClassifier:
    """
    Classifies queries into intent categories.
    
    Uses hybrid approach:
    - Rule-based detection (primary, always available)
    - MiniLM similarity scoring (secondary, optional enhancement)
    - Confidence scoring for reliability
    - Ambiguity detection for clarification
    """
    
    # Intent categories
    INTENT_COLUMN_NAMES = "column_names"
    INTENT_ROW_COUNT = "row_count"
    INTENT_AGGREGATION = "aggregation"  # sum, count, average, etc.
    INTENT_GROUP_BY = "group_by"  # aggregations by category (by mode, location, etc.)
    INTENT_FILTER = "filter"  # filter by condition
    INTENT_RANKING = "ranking"  # top, bottom, highest, lowest
    INTENT_LIST = "list"  # list unique values
    INTENT_PREVIEW = "preview"  # show first N rows
    INTENT_TIME_BASED = "time_based"  # date range queries
    INTENT_DATA_TYPES = "data_types"  # column data types
    INTENT_MISSING_VALUES = "missing_values"  # null/missing value analysis
    INTENT_OPERATIONAL = "operational"  # delays, inefficiencies, outliers
    INTENT_CALCULATION = "calculation"  # calculated fields (ratios, per-unit, etc.)
    INTENT_GENERAL = "general"  # general query
    
    # Confidence thresholds
    HIGH_CONFIDENCE = 0.8
    MEDIUM_CONFIDENCE = 0.5
    AMBIGUITY_THRESHOLD = 0.15  # If top 2 intents are within this, consider ambiguous
    
    def __init__(self):
        """Initialize intent classifier."""
        # FAQ to intent mapping (static - never changes)
        self.faq_intent_map = self._build_faq_intent_map()
        
        # Initialize MiniLM for similarity scoring (optional)
        self.minilm = None
        if MINILM_AVAILABLE:
            try:
                self.minilm = SentenceTransformer('all-MiniLM-L6-v2')
                print("[IntentClassifier] MiniLM loaded for similarity scoring")
            except Exception as e:
                print(f"[IntentClassifier] Could not load MiniLM: {e}, using rule-based only")
                self.minilm = None
    
    def _build_faq_intent_map(self) -> Dict[str, str]:
        """Build static mapping of FAQ questions to intent types."""
        # This map will be populated with all FAQs from app.py
        # For now, return empty - FAQs will be matched via pattern matching
        return {}
    
    def classify(self, query: str) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
        """
        Classify a query into an intent category with confidence scoring.
        
        Uses hybrid approach:
        1. Rule-based detection (primary, always available)
        2. MiniLM similarity scoring (secondary, optional enhancement)
        3. Confidence scoring and ambiguity detection
        
        Args:
            query: User query or FAQ text
            
        Returns:
            Tuple of (intent_type, intent_params, metadata)
            metadata contains: confidence, is_ambiguous, alternative_intents
        """
        query_lower = query.lower().strip()
        metadata = {
            'confidence': 1.0,
            'is_ambiguous': False,
            'alternative_intents': [],
            'classification_method': 'rule_based'
        }
        
        # Check if it's a known FAQ (highest confidence)
        if query in self.faq_intent_map:
            intent = self.faq_intent_map[query]
            params = self._extract_params(query, intent)
            metadata['confidence'] = 1.0
            metadata['classification_method'] = 'faq_exact_match'
            return intent, params, metadata
        
        # Step 1: Rule-based classification (primary method)
        rule_based_scores = self._rule_based_classification(query_lower)
        
        # Step 2: MiniLM similarity scoring (optional enhancement)
        if self.minilm is not None:
            similarity_scores = self._minilm_similarity_scoring(query)
            # Combine scores: 70% rule-based, 30% similarity
            combined_scores = {}
            for intent in rule_based_scores:
                rule_score = rule_based_scores[intent]
                sim_score = similarity_scores.get(intent, 0.0)
                combined_scores[intent] = (rule_score * 0.7) + (sim_score * 0.3)
            final_scores = combined_scores
            metadata['classification_method'] = 'hybrid_rule_minilm'
        else:
            final_scores = rule_based_scores
            metadata['classification_method'] = 'rule_based'
        
        # Step 3: Select best intent
        if not final_scores:
            # No matches, default to general
            intent = self.INTENT_GENERAL
            params = {}
            metadata['confidence'] = 0.3
        else:
            # Sort by score
            sorted_intents = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
            intent, confidence = sorted_intents[0]
            
            # Check for ambiguity
            if len(sorted_intents) > 1:
                second_intent, second_confidence = sorted_intents[1]
                score_diff = confidence - second_confidence
                
                if score_diff < self.AMBIGUITY_THRESHOLD:
                    # Ambiguous - multiple intents have similar scores
                    metadata['is_ambiguous'] = True
                    metadata['alternative_intents'] = [
                        {'intent': second_intent, 'confidence': second_confidence}
                    ]
                    # Choose safest default (usually general or most common)
                    if intent == self.INTENT_GENERAL:
                        # Keep general if it's one of the ambiguous options
                        pass
                    elif second_intent == self.INTENT_GENERAL and confidence < 0.6:
                        # If general is close and current is low confidence, prefer general
                        intent = self.INTENT_GENERAL
                        confidence = second_confidence
                        metadata['chose_safe_default'] = True
            
            metadata['confidence'] = confidence
            params = self._extract_params(query, intent)
            # Add original query text for column count detection
            params['query_text'] = query
        
        return intent, params, metadata
    
    def _rule_based_classification(self, query_lower: str) -> Dict[str, float]:
        """
        Rule-based intent classification with confidence scores.
        
        Returns:
            Dictionary mapping intent types to confidence scores (0.0-1.0)
        """
        scores = {}
        
        # Check each intent type with pattern matching
        if self._is_column_names_query(query_lower):
            scores[self.INTENT_COLUMN_NAMES] = 0.95
        
        if self._is_row_count_query(query_lower):
            scores[self.INTENT_ROW_COUNT] = 0.95
        
        if self._is_aggregation_query(query_lower):
            scores[self.INTENT_AGGREGATION] = 0.90
        
        if self._is_list_query(query_lower):
            scores[self.INTENT_LIST] = 0.90
        
        if self._is_ranking_query(query_lower):
            scores[self.INTENT_RANKING] = 0.90
        
        if self._is_preview_query(query_lower):
            scores[self.INTENT_PREVIEW] = 0.95
        
        if self._is_time_based_query(query_lower):
            scores[self.INTENT_TIME_BASED] = 0.85
        
        if self._is_filter_query(query_lower):
            scores[self.INTENT_FILTER] = 0.80
        
        if self._is_data_types_query(query_lower):
            scores[self.INTENT_DATA_TYPES] = 0.90
        
        if self._is_missing_values_query(query_lower):
            scores[self.INTENT_MISSING_VALUES] = 0.90
        
        if self._is_group_by_query(query_lower):
            scores[self.INTENT_GROUP_BY] = 0.85
        
        if self._is_operational_query(query_lower):
            scores[self.INTENT_OPERATIONAL] = 0.85
        
        if self._is_calculation_query(query_lower):
            scores[self.INTENT_CALCULATION] = 0.90
        
        # If no matches, assign low confidence to general
        if not scores:
            scores[self.INTENT_GENERAL] = 0.3
        
        return scores
    
    def _minilm_similarity_scoring(self, query: str) -> Dict[str, float]:
        """
        Use MiniLM to score similarity between query and known FAQ patterns.
        
        This is assistive only - helps rank candidate intents.
        Does NOT generate answers or compute values.
        
        Returns:
            Dictionary mapping intent types to similarity scores (0.0-1.0)
        """
        if not self.minilm:
            return {}
        
        try:
            # Get example queries for each intent type
            intent_examples = {
                self.INTENT_COLUMN_NAMES: [
                    "What are all the column names in this file?",
                    "List all columns",
                    "Show me column names"
                ],
                self.INTENT_ROW_COUNT: [
                    "How many rows are there?",
                    "What is the total number of rows?",
                    "Count of records"
                ],
                self.INTENT_AGGREGATION: [
                    "What is the total cost?",
                    "Sum of all values",
                    "What is the average?"
                ],
                self.INTENT_LIST: [
                    "What are all the source locations?",
                    "List unique values",
                    "Show me all different products"
                ],
                self.INTENT_RANKING: [
                    "Which has the highest cost?",
                    "Top consignment",
                    "Most frequent"
                ],
                self.INTENT_PREVIEW: [
                    "Show me the first 5 rows",
                    "Preview data",
                    "Sample rows"
                ],
                self.INTENT_TIME_BASED: [
                    "What is the date range?",
                    "Dispatch dates",
                    "Time period"
                ],
                self.INTENT_FILTER: [
                    "Show consignments going to Mumbai",
                    "Filter by destination",
                    "Where condition"
                ]
            }
            
            # Compute similarity scores
            query_embedding = self.minilm.encode([query])[0]
            intent_scores = {}
            
            for intent, examples in intent_examples.items():
                # Encode examples
                example_embeddings = self.minilm.encode(examples)
                
                # Compute max similarity (best match)
                similarities = np.dot(example_embeddings, query_embedding) / (
                    np.linalg.norm(example_embeddings, axis=1) * np.linalg.norm(query_embedding)
                )
                max_similarity = float(np.max(similarities))
                
                # Normalize to 0-1 range (cosine similarity is -1 to 1, we want 0 to 1)
                intent_scores[intent] = (max_similarity + 1) / 2
            
            return intent_scores
            
        except Exception as e:
            # Log the error with full context for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Error in MiniLM similarity scoring: {e}. "
                f"Falling back to rule-based classification only. "
                f"Query: {query[:100]}..."
            )
            # Return empty dict to fallback to rule-based only
            return {}
    
    def _is_column_names_query(self, query_lower: str) -> bool:
        """Check if query is asking for column names."""
        patterns = [
            r'column\s+name',
            r'what\s+are\s+(all\s+)?the\s+columns',
            r'list\s+(all\s+)?columns',
            r'show\s+(me\s+)?(all\s+)?columns'
        ]
        return any(re.search(pattern, query_lower) for pattern in patterns)
    
    def _is_row_count_query(self, query_lower: str) -> bool:
        """Check if query is asking for row count."""
        patterns = [
            r'how\s+many\s+(rows|records|entries|consignments)',
            r'total\s+(number\s+of\s+)?(rows|records|entries)',
            r'count\s+(of\s+)?(rows|records|entries)'
        ]
        return any(re.search(pattern, query_lower) for pattern in patterns)
    
    def _is_aggregation_query(self, query_lower: str) -> bool:
        """Check if query is an aggregation query."""
        patterns = [
            r'\b(total|sum|average|mean|avg|maximum|max|minimum|min|count)\b',
            r'how\s+much\s+(total|sum)',
            r'what\s+is\s+the\s+(total|sum|average)'
        ]
        return any(re.search(pattern, query_lower) for pattern in patterns)
    
    def _is_list_query(self, query_lower: str) -> bool:
        """Check if query is asking for a list of values."""
        patterns = [
            r'what\s+are\s+(all\s+)?the',
            r'list\s+(all\s+)?',
            r'show\s+me\s+(all\s+)?',
            r'what\s+(are|is)\s+(all\s+)?(the\s+)?(different|unique)'
        ]
        return any(re.search(pattern, query_lower) for pattern in patterns)
    
    def _is_ranking_query(self, query_lower: str) -> bool:
        """Check if query is asking for ranking (top, bottom, highest, lowest)."""
        patterns = [
            r'\b(highest|lowest|top|bottom|maximum|minimum|max|min)\b',
            r'which\s+.*\s+(has|is)\s+(the\s+)?(highest|lowest|most|least)',
            r'most\s+frequent',
            r'least\s+frequent'
        ]
        return any(re.search(pattern, query_lower) for pattern in patterns)
    
    def _is_preview_query(self, query_lower: str) -> bool:
        """Check if query is asking for data preview."""
        patterns = [
            r'show\s+me\s+(the\s+)?(first|last)\s+\d+\s+rows',
            r'preview',
            r'first\s+\d+\s+rows',
            r'sample\s+data'
        ]
        return any(re.search(pattern, query_lower) for pattern in patterns)
    
    def _is_time_based_query(self, query_lower: str) -> bool:
        """Check if query is time-based."""
        patterns = [
            r'date\s+range',
            r'between\s+.*\s+and\s+',
            r'from\s+.*\s+to\s+',
            r'dispatch\s+date',
            r'arrival\s+date'
        ]
        return any(re.search(pattern, query_lower) for pattern in patterns)
    
    def _is_filter_query(self, query_lower: str) -> bool:
        """Check if query is a filter query."""
        patterns = [
            r'where\s+',
            r'with\s+',
            r'that\s+(have|are|is)',
            r'going\s+to\s+',
            r'coming\s+from\s+'
        ]
        return any(re.search(pattern, query_lower) for pattern in patterns)
    
    def _is_data_types_query(self, query_lower: str) -> bool:
        """Check if query is asking about data types."""
        patterns = [
            r'data\s+type',
            r'data\s+types',
            r'which\s+columns\s+contain\s+(numerical|text|date|time)',
            r'columns\s+contain\s+(numerical|text|date|time)',
            r'what\s+are\s+the\s+data\s+types'
        ]
        return any(re.search(pattern, query_lower) for pattern in patterns)
    
    def _is_missing_values_query(self, query_lower: str) -> bool:
        """Check if query is asking about missing/null values."""
        patterns = [
            r'missing\s+value',
            r'null\s+value',
            r'which\s+columns\s+have\s+missing',
            r'how\s+many\s+missing',
            r'are\s+there\s+any\s+missing',
            r'null\s+values'
        ]
        return any(re.search(pattern, query_lower) for pattern in patterns)
    
    def _is_group_by_query(self, query_lower: str) -> bool:
        """Check if query involves group by operations."""
        patterns = [
            r'by\s+(transportation\s+mode|source\s+location|destination|mode|location|customer|product)',
            r'per\s+(transportation\s+mode|source|destination|mode|location|customer)',
            r'each\s+(transportation\s+mode|source|destination|mode|location|customer)',
            r'distribution\s+by',
            r'grouped\s+by',
            r'vary\s+by',  # "how does X vary by Y"
            r'how\s+does.*vary\s+by'  # "how does average weight vary by mode"
        ]
        return any(re.search(pattern, query_lower) for pattern in patterns)
    
    def _is_operational_query(self, query_lower: str) -> bool:
        """Check if query is about operational issues (delays, inefficiencies, outliers)."""
        patterns = [
            r'delay',
            r'inefficiency',
            r'outlier',
            r'underutilized',
            r'low\s+(weight|volume)\s+fill',
            r'high\s+cost',
            r'capacity\s+threshold',
            r'optimal\s+(weight|volume)',
            r'operational\s+cost'
        ]
        return any(re.search(pattern, query_lower) for pattern in patterns)
    
    def _is_calculation_query(self, query_lower: str) -> bool:
        """Check if query involves calculations (ratios, per-unit, etc.)."""
        patterns = [
            r'per\s+(case|kg|kilogram|unit|consignment)',
            r'ratio',
            r'per\s+unit',
            r'cost\s+per',
            r'weight\s+per',
            r'volume\s+per',
            r'efficiency',
            r'cost\s+per\s+(case|kg|kilogram)',
            r'weight\s+per\s+case'
        ]
        return any(re.search(pattern, query_lower) for pattern in patterns)
    
    def _extract_aggregation_params(self, query_lower: str) -> Dict[str, Any]:
        """Extract parameters for aggregation queries."""
        params = {}
        
        # Extract aggregation type
        if re.search(r'\b(total|sum)\b', query_lower):
            params['agg_type'] = 'sum'
        elif re.search(r'\b(average|mean|avg)\b', query_lower):
            params['agg_type'] = 'mean'
        elif re.search(r'\b(maximum|max)\b', query_lower):
            params['agg_type'] = 'max'
        elif re.search(r'\b(minimum|min)\b', query_lower):
            params['agg_type'] = 'min'
        elif re.search(r'\b(count)\b', query_lower):
            params['agg_type'] = 'count'
        else:
            params['agg_type'] = 'sum'  # default
        
        # Extract column name
        # Look for common column names in query
        common_columns = [
            'cost', 'weight', 'volume', 'cases', 'mrp', 'value',
            'price', 'amount', 'quantity', 'count'
        ]
        for col in common_columns:
            if col in query_lower:
                params['column'] = col
                break
        
        return params
    
    def _extract_list_params(self, query_lower: str) -> Dict[str, Any]:
        """Extract parameters for list queries."""
        params = {}
        
        # Extract what to list - be more specific
        if 'source location' in query_lower or ('source' in query_lower and 'location' in query_lower):
            params['column'] = 'source_name'  # Match "Source Name" column
        elif 'source type' in query_lower or ('source' in query_lower and 'type' in query_lower):
            params['column'] = 'source_type'  # Match "Source Type" column
        elif 'destination location' in query_lower or ('destination' in query_lower and 'location' in query_lower):
            params['column'] = 'destination_name'  # Match "Destination Name" column
        elif 'destination type' in query_lower or ('destination' in query_lower and 'type' in query_lower):
            params['column'] = 'destination_type'  # Match "Destination Type" column
        elif 'source' in query_lower or 'origin' in query_lower:
            params['column'] = 'source_name'  # Default to source name for "source"
        elif 'destination' in query_lower:
            params['column'] = 'destination_name'  # Default to destination name for "destination"
        elif 'product' in query_lower:
            params['column'] = 'product_name'  # Match "Product Name" column
        elif 'product code' in query_lower:
            params['column'] = 'product_code'  # Match "Product Code" column
        elif 'mode' in query_lower or 'transportation' in query_lower:
            params['column'] = 'mode'  # Match "Mode" column
        elif 'customer' in query_lower:
            params['column'] = 'customer_name'  # Match "Customer Name" column
        elif 'consignment' in query_lower:
            params['column'] = 'consignment_no'  # Match "Consignment No" column
        elif 'order' in query_lower:
            params['column'] = 'order'  # Match "Order" column
        elif 'unit' in query_lower:
            params['column'] = 'unit'  # Match "Unit" column
        elif 'plan name' in query_lower or 'plan names' in query_lower:
            params['column'] = 'plan_name'  # Match "Plan Name" column
        
        params['unique'] = True
        return params
    
    def _extract_ranking_params(self, query_lower: str) -> Dict[str, Any]:
        """Extract parameters for ranking queries."""
        params = {}
        
        # Extract ranking type
        if 'highest' in query_lower or 'maximum' in query_lower or 'max' in query_lower or 'most' in query_lower:
            params['order'] = 'desc'
        elif 'lowest' in query_lower or 'minimum' in query_lower or 'min' in query_lower or 'least' in query_lower:
            params['order'] = 'asc'
        else:
            params['order'] = 'desc'  # default
        
        # Extract column - be more specific
        if 'cases' in query_lower and 'order' in query_lower:
            params['column'] = 'no_of_cases'  # For "which orders contain the most cases"
        elif 'cost' in query_lower:
            params['column'] = 'total_transportation_cost'
        elif 'weight' in query_lower:
            params['column'] = 'total_weight'
        elif 'volume' in query_lower:
            params['column'] = 'total_volume'
        elif 'mrp' in query_lower or 'value' in query_lower:
            params['column'] = 'total_consignment_mrp_value'
        elif 'price' in query_lower:
            params['column'] = 'total_transportation_cost'
        elif 'cases' in query_lower:
            params['column'] = 'total_no_of_cases'
        else:
            # Try common columns
            common_columns = ['cost', 'weight', 'volume', 'mrp', 'value', 'price', 'cases']
            for col in common_columns:
                if col in query_lower:
                    params['column'] = col
                    break
        
        # Extract limit if specified
        limit_match = re.search(r'(top|first|last)\s+(\d+)', query_lower)
        if limit_match:
            params['limit'] = int(limit_match.group(2))
        else:
            params['limit'] = 10  # Default to top 10 for ranking queries
        
        return params
    
    def _extract_preview_params(self, query_lower: str) -> Dict[str, Any]:
        """Extract parameters for preview queries."""
        params = {}
        
        # Extract number of rows
        match = re.search(r'(\d+)\s+rows?', query_lower)
        if match:
            params['limit'] = int(match.group(1))
        else:
            params['limit'] = 5  # default
        
        return params
    
    def _extract_time_params(self, query_lower: str) -> Dict[str, Any]:
        """Extract parameters for time-based queries."""
        params = {}
        
        if 'dispatch' in query_lower:
            params['column'] = 'dispatch_date'
        elif 'arrival' in query_lower or 'expected' in query_lower:
            params['column'] = 'arrival_date'
        
        return params
    
    def _extract_filter_params(self, query_lower: str) -> Dict[str, Any]:
        """Extract parameters for filter queries."""
        params = {}
        # This would be more complex - for now return empty
        return params
    
    def _extract_group_by_params(self, query_lower: str) -> Dict[str, Any]:
        """Extract parameters for group by queries."""
        params = {}
        
        # Extract aggregation type
        if re.search(r'\b(total|sum)\b', query_lower):
            params['agg_type'] = 'sum'
        elif re.search(r'\b(average|mean|avg)\b', query_lower):
            params['agg_type'] = 'mean'
        elif re.search(r'\b(count)\b', query_lower):
            params['agg_type'] = 'count'
        elif re.search(r'\b(maximum|max)\b', query_lower):
            params['agg_type'] = 'max'
        elif re.search(r'\b(minimum|min)\b', query_lower):
            params['agg_type'] = 'min'
        else:
            params['agg_type'] = 'sum'  # default
        
        # Extract aggregation column - be more specific
        if 'average' in query_lower and 'weight' in query_lower and 'per' in query_lower:
            params['column'] = 'total_weight'  # For "average weight per consignment"
            params['agg_type'] = 'mean'  # Ensure it's mean, not sum
        elif 'weight' in query_lower and 'per' in query_lower:
            params['column'] = 'total_weight'
        elif 'cost' in query_lower:
            params['column'] = 'total_transportation_cost'
        elif 'weight' in query_lower:
            params['column'] = 'total_weight'
        elif 'volume' in query_lower:
            params['column'] = 'total_volume'
        elif 'cases' in query_lower:
            params['column'] = 'total_no_of_cases'
        elif 'mrp' in query_lower or 'value' in query_lower:
            params['column'] = 'total_consignment_mrp_value'
        else:
            # Try common columns
            agg_columns = ['cost', 'weight', 'volume', 'cases', 'mrp', 'value', 'price', 'amount']
            for col in agg_columns:
                if col in query_lower:
                    params['column'] = col
                    break
        
        # Extract group by column - be more specific
        if 'transportation mode' in query_lower or ('mode' in query_lower and 'transportation' in query_lower):
            params['group_by'] = 'mode'
        elif 'source location' in query_lower or ('source' in query_lower and 'location' in query_lower and 'type' not in query_lower):
            params['group_by'] = 'source_name'  # Match "Source Name" column
        elif 'source type' in query_lower or ('source' in query_lower and 'type' in query_lower):
            params['group_by'] = 'source_type'  # Match "Source Type" column
        elif 'destination location' in query_lower or ('destination' in query_lower and 'location' in query_lower and 'type' not in query_lower):
            params['group_by'] = 'destination_name'  # Match "Destination Name" column
        elif 'destination type' in query_lower or ('destination' in query_lower and 'type' in query_lower):
            params['group_by'] = 'destination_type'  # Match "Destination Type" column
        elif 'customer' in query_lower:
            params['group_by'] = 'customer_name'
        elif 'product' in query_lower:
            params['group_by'] = 'product_name'
        elif 'load type' in query_lower:
            params['group_by'] = 'load_type'
        elif 'mode' in query_lower:
            params['group_by'] = 'mode'  # Fallback for just "mode"
        
        return params
    
    def _extract_operational_params(self, query_lower: str) -> Dict[str, Any]:
        """Extract parameters for operational queries."""
        params = {}
        
        # Determine operational type
        if 'delay' in query_lower:
            params['operational_type'] = 'delays'
        elif 'inefficiency' in query_lower or ('low' in query_lower and ('fill' in query_lower or 'utilization' in query_lower)):
            params['operational_type'] = 'inefficiency'
        elif 'outlier' in query_lower:
            params['operational_type'] = 'outliers'
        elif 'underutilized' in query_lower:
            params['operational_type'] = 'underutilization'
        elif 'optimal' in query_lower or 'threshold' in query_lower:
            params['operational_type'] = 'thresholds'
        elif 'operational cost' in query_lower:
            params['operational_type'] = 'operational_costs'
        else:
            params['operational_type'] = 'general'
        
        return params
    
    def _extract_calculation_params(self, query_lower: str) -> Dict[str, Any]:
        """Extract parameters for calculation queries (ratios, per-unit, etc.)."""
        params = {}
        
        # Determine calculation type
        if 'per case' in query_lower or 'case ratio' in query_lower:
            params['calc_type'] = 'per_case'
            if 'cost' in query_lower:
                params['numerator'] = 'total_transportation_cost'
                params['denominator'] = 'total_no_of_cases'
            elif 'weight' in query_lower:
                params['numerator'] = 'total_weight'
                params['denominator'] = 'total_no_of_cases'
        elif 'per kg' in query_lower or 'per kilogram' in query_lower:
            params['calc_type'] = 'per_kg'
            if 'cost' in query_lower:
                params['numerator'] = 'total_transportation_cost'
                params['denominator'] = 'total_weight'
        elif 'weight per case' in query_lower or 'weight/case' in query_lower or ('weight' in query_lower and 'case' in query_lower and 'ratio' in query_lower):
            params['calc_type'] = 'weight_per_case'
            params['numerator'] = 'total_weight'
            params['denominator'] = 'total_no_of_cases'
        elif 'ratio' in query_lower:
            params['calc_type'] = 'ratio'
            if 'weight' in query_lower and 'case' in query_lower:
                params['numerator'] = 'total_weight'
                params['denominator'] = 'total_no_of_cases'
            elif 'cost' in query_lower and 'case' in query_lower:
                params['numerator'] = 'total_transportation_cost'
                params['denominator'] = 'total_no_of_cases'
        else:
            params['calc_type'] = 'general'
        
        # Determine grouping
        if 'each product' in query_lower or 'per product' in query_lower:
            params['group_by'] = 'product_name'
        elif 'each consignment' in query_lower or 'per consignment' in query_lower:
            params['group_by'] = 'consignment_no'
        elif 'each order' in query_lower or 'per order' in query_lower:
            params['group_by'] = 'order'
        
        return params
    
    def _extract_params(self, query: str, intent: str) -> Dict[str, Any]:
        """Extract parameters based on intent type."""
        query_lower = query.lower()
        
        if intent == self.INTENT_AGGREGATION:
            return self._extract_aggregation_params(query_lower)
        elif intent == self.INTENT_GROUP_BY:
            return self._extract_group_by_params(query_lower)
        elif intent == self.INTENT_LIST:
            return self._extract_list_params(query_lower)
        elif intent == self.INTENT_RANKING:
            return self._extract_ranking_params(query_lower)
        elif intent == self.INTENT_PREVIEW:
            return self._extract_preview_params(query_lower)
        elif intent == self.INTENT_TIME_BASED:
            return self._extract_time_params(query_lower)
        elif intent == self.INTENT_FILTER:
            return self._extract_filter_params(query_lower)
        elif intent == self.INTENT_OPERATIONAL:
            return self._extract_operational_params(query_lower)
        elif intent == self.INTENT_CALCULATION:
            return self._extract_calculation_params(query_lower)
        
        return {}
