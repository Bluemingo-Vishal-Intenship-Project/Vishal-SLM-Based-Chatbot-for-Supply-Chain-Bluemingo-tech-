"""
Query-Driven Pipeline Module
Main orchestrator for the query-driven analytics chatbot.

Design Philosophy:
- Data = Source of Truth
- Queries = Accuracy Guarantee (deterministic and verifiable)
- FAQs = Intent Shortcuts (static, data-agnostic)
- SLM = Assistive Intelligence (similarity scoring, formatting assistance)
  - NOT used for answer generation or data computation
  - Used only for intent matching and response formatting enhancement

Core Flow:
User Question OR FAQ Click
    ↓
Intent Classification (Rule-based + Optional MiniLM similarity)
    ↓
Query Generation (Pandas operations)
    ↓
Execute Query on Actual CSV / Excel Data
    ↓
Validate Result
    ↓
Response Formatting (Templates + Optional SLM enhancement)
"""

from typing import Dict, List, Any, Optional, Tuple
import logging
from data_loader import DataLoader
from intent_classifier import IntentClassifier
from query_generator import QueryGenerator
from query_executor import QueryExecutor
from response_formatter import ResponseFormatter

logger = logging.getLogger(__name__)


class QueryDrivenPipeline:
    """
    Main pipeline for query-driven analytics chatbot.
    
    Provides deterministic, verifiable answers through query execution on actual data.
    Accuracy is bounded by data correctness - queries are deterministic and verifiable.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize query-driven pipeline.
        
        Args:
            db_path: Optional path to SQLite database
        """
        self.data_loader = DataLoader(db_path)
        self.intent_classifier = IntentClassifier()
        self.query_generator = QueryGenerator(self.data_loader)
        self.query_executor = QueryExecutor()
        self.response_formatter = ResponseFormatter()
    
    def process_query(self, query: str, file_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a user query or FAQ click through the complete pipeline.
        
        Args:
            query: User query or FAQ text
            file_id: Optional file ID to query
            
        Returns:
            Dictionary with answer and metadata
        """
        try:
            # Step 1: Intent Classification (with confidence scoring)
            intent, intent_params, classification_metadata = self.intent_classifier.classify(query)
            confidence = classification_metadata.get('confidence', 0.5)
            is_ambiguous = classification_metadata.get('is_ambiguous', False)
            
            logger.debug(f"Intent: {intent}, Confidence: {confidence:.2f}, Params: {intent_params}")
            
            # Handle ambiguous intents
            if is_ambiguous and confidence < self.intent_classifier.MEDIUM_CONFIDENCE:
                alternative = classification_metadata.get('alternative_intents', [])
                alt_text = ", ".join([a['intent'] for a in alternative])
                clarification = f"I detected multiple possible intents for your query.\n\nDetected: {intent} (confidence: {confidence:.0%})\nAlternative: {alt_text}\n\nProceeding with {intent}. If this isn't what you meant, please rephrase your question."
                logger.warning(f"Ambiguous intent detected: {intent} (confidence: {confidence:.2f})")
            else:
                clarification = None
            
            # Step 2: Query Generation
            query_type, query_spec = self.query_generator.generate_query(
                intent, intent_params, file_id
            )
            logger.debug(f"Generated {query_type} query: {query_spec.get('operation')}")
            
            # Step 3: Execute Query
            query_result = self.query_executor.execute(query_type, query_spec)
            logger.debug(f"Query executed: success={query_result.get('success')}")
            
            # Step 4: Format Response
            answer = self.response_formatter.format_response(query_result, query)
            
            # Add clarification if needed
            if clarification:
                answer = clarification + "\n\n" + answer
            
            logger.debug("Response formatted successfully")
            
            return {
                'answer': answer,
                'success': query_result.get('success', False),
                'intent': intent,
                'confidence': confidence,
                'is_ambiguous': is_ambiguous,
                'query_result': query_result,
                'has_data': True,
                'classification_metadata': classification_metadata
            }
            
        except ValueError as e:
            # Column not found, file not found, etc.
            error_msg = str(e)
            logger.warning(f"ValueError in query processing: {error_msg}")
            return {
                'answer': f"The requested information is not available in the current dataset.\n\n{error_msg}\n\nPlease check:\n- Column names are correct\n- File is loaded\n- Query parameters are valid",
                'success': False,
                'error': error_msg,
                'has_data': False
            }
        except Exception as e:
            # Other errors
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"Error processing query '{query[:100]}...': {str(e)}")
            logger.debug(f"Traceback: {error_trace}")
            return {
                'answer': f"I encountered an error processing your query: {str(e)}\n\nPlease try rephrasing your question or contact support if the issue persists.",
                'success': False,
                'error': str(e),
                'has_data': False
            }
    
    def load_file(self, file_path: str, file_id: Optional[str] = None, 
                  process_all_sheets: bool = True) -> Dict[str, Any]:
        """
        Load a file into the system.
        
        Args:
            file_path: Path to the file
            file_id: Optional file ID
            process_all_sheets: Whether to process all sheets (for Excel)
            
        Returns:
            Dictionary with load status
        """
        try:
            from pathlib import Path
            file_path_obj = Path(file_path)
            file_ext = file_path_obj.suffix.lower()
            
            if file_ext in ['.xlsx', '.xls', '.xlsm', '.xlsb'] and process_all_sheets:
                sheets = self.data_loader.load_all_sheets(file_path, file_id)
                return {
                    'success': True,
                    'message': f'Loaded {len(sheets)} sheet(s)',
                    'file_ids': list(sheets.keys())
                }
            else:
                fid, df = self.data_loader.load_file(file_path, file_id)
                return {
                    'success': True,
                    'message': f'Loaded file: {fid}',
                    'file_id': fid,
                    'rows': len(df),
                    'columns': len(df.columns)
                }
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"Error loading file '{file_path}': {str(e)}")
            logger.debug(f"Traceback: {error_trace}")
            return {
                'success': False,
                'error': str(e),
                'traceback': error_trace
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        return self.data_loader.get_stats()
    
    def clear_data(self, file_id: Optional[str] = None):
        """Clear data for a file or all files."""
        self.data_loader.clear_data(file_id)
    
    def get_column_names(self, file_id: Optional[str] = None) -> List[str]:
        """Get column names for a file or all files."""
        return self.data_loader.get_column_names(file_id)
