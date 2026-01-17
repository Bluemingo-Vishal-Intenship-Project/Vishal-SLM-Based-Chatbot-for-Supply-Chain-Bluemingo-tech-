"""
Query Generator Module
Generates Pandas queries from classified intents.

Design Philosophy:
- Queries = Accuracy Guarantee (deterministic and verifiable)
- All queries are deterministic and read-only
- Queries are validated before execution
- Never infers values not present in data
- Accuracy bounded by data correctness
"""

from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import re


class QueryGenerator:
    """Generates queries from intents."""
    
    def __init__(self, data_loader):
        """
        Initialize query generator.
        
        Args:
            data_loader: DataLoader instance
        """
        self.data_loader = data_loader
    
    def generate_query(self, intent: str, intent_params: Dict[str, Any], 
                      file_id: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Generate a query from intent and parameters.
        
        Args:
            intent: Intent type
            intent_params: Intent parameters
            file_id: Optional file ID to query
            
        Returns:
            Tuple of (query_type, query_spec)
            query_type: 'pandas' or 'sql'
            query_spec: Dictionary with query details
        """
        # Get available dataframes
        if file_id:
            df = self.data_loader.get_dataframe(file_id)
            if df is None:
                raise ValueError(f"File {file_id} not found")
            dataframes = {file_id: df}
        else:
            dataframes = self.data_loader.dataframes
            if not dataframes:
                raise ValueError("No data loaded")
        
        # Generate query based on intent
        if intent == "column_names":
            return self._generate_column_names_query(dataframes)
        elif intent == "row_count":
            return self._generate_row_count_query(dataframes, intent_params)
        elif intent == "aggregation":
            return self._generate_aggregation_query(dataframes, intent_params)
        elif intent == "group_by":
            return self._generate_group_by_query(dataframes, intent_params)
        elif intent == "list":
            return self._generate_list_query(dataframes, intent_params)
        elif intent == "ranking":
            return self._generate_ranking_query(dataframes, intent_params)
        elif intent == "preview":
            return self._generate_preview_query(dataframes, intent_params)
        elif intent == "time_based":
            return self._generate_time_query(dataframes, intent_params)
        elif intent == "data_types":
            return self._generate_data_types_query(dataframes)
        elif intent == "missing_values":
            return self._generate_missing_values_query(dataframes)
        elif intent == "operational":
            return self._generate_operational_query(dataframes, intent_params)
        elif intent == "calculation":
            return self._generate_calculation_query(dataframes, intent_params)
        elif intent == "filter":
            return self._generate_filter_query(dataframes, intent_params)
        else:
            # General query - try to infer from query text
            return self._generate_general_query(dataframes, intent_params)
    
    def _generate_column_names_query(self, dataframes: Dict[str, pd.DataFrame]) -> Tuple[str, Dict[str, Any]]:
        """Generate query to get column names."""
        # Get all unique column names from all dataframes
        all_columns = set()
        for df in dataframes.values():
            all_columns.update(df.columns)
        
        return 'pandas', {
            'operation': 'column_names',
            'columns': sorted(list(all_columns)),
            'dataframes': list(dataframes.keys())
        }
    
    def _generate_row_count_query(self, dataframes: Dict[str, pd.DataFrame], intent_params: Optional[Dict[str, Any]] = None) -> Tuple[str, Dict[str, Any]]:
        """Generate query to get row count or column count."""
        # Check if this is asking for column count
        query_text = intent_params.get('query_text', '').lower() if intent_params else ''
        
        if 'columns' in query_text or 'column' in query_text and 'count' in query_text:
            # Get column count from first dataframe
            file_id = list(dataframes.keys())[0]
            df = dataframes[file_id]
            column_count = len(df.columns)
            
            return 'pandas', {
                'operation': 'row_count',
                'counts': {},
                'total': 0,
                'column_count': column_count,
                'dataframes': list(dataframes.keys())
            }
        
        # Regular row count
        counts = {}
        for file_id, df in dataframes.items():
            counts[file_id] = len(df)
        
        total = sum(counts.values())
        
        return 'pandas', {
            'operation': 'row_count',
            'counts': counts,
            'total': total,
            'dataframes': list(dataframes.keys())
        }
    
    def _generate_aggregation_query(self, dataframes: Dict[str, pd.DataFrame], 
                                    params: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Generate aggregation query."""
        agg_type = params.get('agg_type', 'sum')
        column = params.get('column')
        
        # Find column in dataframes
        target_column = self._find_column(column, dataframes)
        if not target_column:
            raise ValueError(f"Column '{column}' not found in data")
        
        file_id, col_name = target_column
        
        return 'pandas', {
            'operation': 'aggregation',
            'agg_type': agg_type,
            'column': col_name,
            'file_id': file_id,
            'dataframe': dataframes[file_id]
        }
    
    def _generate_list_query(self, dataframes: Dict[str, pd.DataFrame], 
                            params: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Generate list query for unique values."""
        column = params.get('column')
        
        # Find column in dataframes
        target_column = self._find_column(column, dataframes)
        if not target_column:
            raise ValueError(f"Column '{column}' not found in data")
        
        file_id, col_name = target_column
        
        return 'pandas', {
            'operation': 'list_unique',
            'column': col_name,
            'file_id': file_id,
            'dataframe': dataframes[file_id]
        }
    
    def _generate_ranking_query(self, dataframes: Dict[str, pd.DataFrame], 
                               params: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Generate ranking query."""
        column = params.get('column')
        order = params.get('order', 'desc')
        limit = params.get('limit', 1)
        
        # Find column in dataframes
        target_column = self._find_column(column, dataframes)
        if not target_column:
            raise ValueError(f"Column '{column}' not found in data")
        
        file_id, col_name = target_column
        
        return 'pandas', {
            'operation': 'ranking',
            'column': col_name,
            'order': order,
            'limit': limit,
            'file_id': file_id,
            'dataframe': dataframes[file_id]
        }
    
    def _generate_preview_query(self, dataframes: Dict[str, pd.DataFrame], 
                               params: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Generate preview query."""
        limit = params.get('limit', 5)
        
        # Use first dataframe
        file_id = list(dataframes.keys())[0]
        df = dataframes[file_id]
        
        return 'pandas', {
            'operation': 'preview',
            'limit': limit,
            'file_id': file_id,
            'dataframe': df
        }
    
    def _generate_time_query(self, dataframes: Dict[str, pd.DataFrame], 
                            params: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Generate time-based query."""
        column = params.get('column')
        
        # Find column in dataframes
        target_column = self._find_column(column, dataframes)
        if not target_column:
            raise ValueError(f"Column '{column}' not found in data")
        
        file_id, col_name = target_column
        
        return 'pandas', {
            'operation': 'time_range',
            'column': col_name,
            'file_id': file_id,
            'dataframe': dataframes[file_id]
        }
    
    def _generate_filter_query(self, dataframes: Dict[str, pd.DataFrame], 
                              params: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Generate filter query."""
        # This would be more complex - for now return general
        file_id = list(dataframes.keys())[0]
        return 'pandas', {
            'operation': 'filter',
            'file_id': file_id,
            'dataframe': dataframes[file_id],
            'params': params
        }
    
    def _generate_general_query(self, dataframes: Dict[str, pd.DataFrame], 
                               params: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Generate general query."""
        file_id = list(dataframes.keys())[0]
        return 'pandas', {
            'operation': 'general',
            'file_id': file_id,
            'dataframe': dataframes[file_id],
            'params': params
        }
    
    def _find_column(self, column_name: str, dataframes: Dict[str, pd.DataFrame]) -> Optional[Tuple[str, str]]:
        """
        Find a column in dataframes by name (fuzzy matching).
        
        Args:
            column_name: Column name to find
            dataframes: Dictionary of dataframes
            
        Returns:
            Tuple of (file_id, actual_column_name) or None
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if not column_name:
            logger.debug("Column name is empty, returning None")
            return None
        
        column_lower = column_name.lower()
        available_columns = []
        
        # Collect all available columns for logging
        for file_id, df in dataframes.items():
            available_columns.extend([(file_id, col) for col in df.columns])
        
        # Try exact match first
        for file_id, df in dataframes.items():
            for col in df.columns:
                if col.lower() == column_lower:
                    logger.debug(f"Found exact match for '{column_name}': '{col}' in file '{file_id}'")
                    return (file_id, col)
        
        # Try partial match
        for file_id, df in dataframes.items():
            for col in df.columns:
                col_lower = col.lower()
                if column_lower in col_lower or col_lower in column_lower:
                    logger.debug(f"Found partial match for '{column_name}': '{col}' in file '{file_id}'")
                    return (file_id, col)
        
        # Try common column name variations - match actual column names from the dataset
        column_variations = {
            'cost': ['cost', 'price', 'amount', 'total cost', 'transportation cost', 'total transportation cost (rs)'],
            'total_transportation_cost': ['total transportation cost (rs)', 'total transportation cost', 'transportation cost'],
            'weight': ['weight', 'total weight', 'kg', 'ton', 'sku_weight', 'sku weight'],
            'total_weight': ['total weight'],
            'sku_weight': ['sku_weight', 'sku weight'],
            'volume': ['volume', 'total volume', 'cubic'],
            'total_volume': ['total volume'],
            'source_name': ['source name', 'source location'],
            'source_type': ['source type'],
            'source_code': ['source code'],
            'destination_name': ['destination name', 'destination location'],
            'destination_type': ['destination type'],
            'destination_code': ['destination code'],
            'product_name': ['product name'],
            'product_code': ['product code'],
            'mode': ['mode', 'transportation mode', 'transport mode'],
            'customer_name': ['customer name'],
            'consignment_no': ['consignment no', 'consignment number'],
            'order': ['order'],
            'no_of_cases': ['no of cases', 'cases'],
            'total_no_of_cases': ['total no of cases', 'total cases'],
            'mrp': ['mrp', 'value', 'total mrp', 'consignment mrp value', 'total consignment mrp value'],
            'total_consignment_mrp_value': ['total consignment mrp value'],
            'consignment_mrp_value': ['consignment mrp value'],
            'load_type': ['load type'],
            'plan_name': ['plan name'],
            'date_of_dispatch': ['date of dispatch', 'dispatch date'],
            'expected_date_of_arrival': ['expected date of arrival', 'arrival date', 'expected arrival date'],
            'consignment_date': ['consignment date']
        }
        
        for key, variations in column_variations.items():
            # Check if the requested column matches this key
            if column_lower == key or column_lower in variations:
                for file_id, df in dataframes.items():
                    for col in df.columns:
                        col_lower = col.lower()
                        # Try exact match first (handle spaces vs underscores)
                        col_normalized = col_lower.replace(' ', '_').replace('-', '_')
                        key_normalized = key.replace(' ', '_').replace('-', '_')
                        if col_normalized == key_normalized:
                            return (file_id, col)
                        # Then try partial match with variations
                        if any(var in col_lower for var in variations):
                            logger.debug(f"Found variation match for '{column_name}': '{col}' in file '{file_id}'")
                            return (file_id, col)
        
        # Log failure for debugging
        available_cols_str = ", ".join([col for _, col in available_columns[:10]])  # Show first 10
        if len(available_columns) > 10:
            available_cols_str += f", ... ({len(available_columns)} total)"
        logger.warning(
            f"Could not find column '{column_name}'. "
            f"Available columns: {available_cols_str}"
        )
        return None
    
    def _generate_group_by_query(self, dataframes: Dict[str, pd.DataFrame], 
                                 params: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Generate group by aggregation query."""
        agg_type = params.get('agg_type', 'sum')
        agg_column = params.get('column')
        group_by_column = params.get('group_by')
        
        # Use first dataframe
        file_id = list(dataframes.keys())[0]
        df = dataframes[file_id]
        
        # Find columns
        target_agg_col = self._find_column(agg_column, dataframes) if agg_column else None
        target_group_col = self._find_column(group_by_column, dataframes) if group_by_column else None
        
        if agg_column and not target_agg_col:
            raise ValueError(f"Column '{agg_column}' not found in data")
        if group_by_column and not target_group_col:
            raise ValueError(f"Column '{group_by_column}' not found in data")
        
        agg_col_name = target_agg_col[1] if target_agg_col else None
        group_col_name = target_group_col[1] if target_group_col else None
        
        return 'pandas', {
            'operation': 'group_by',
            'agg_type': agg_type,
            'agg_column': agg_col_name,
            'group_by_column': group_col_name,
            'file_id': file_id,
            'dataframe': df
        }
    
    def _generate_data_types_query(self, dataframes: Dict[str, pd.DataFrame]) -> Tuple[str, Dict[str, Any]]:
        """Generate query to get data types of columns."""
        # Use first dataframe
        file_id = list(dataframes.keys())[0]
        df = dataframes[file_id]
        
        return 'pandas', {
            'operation': 'data_types',
            'file_id': file_id,
            'dataframe': df
        }
    
    def _generate_missing_values_query(self, dataframes: Dict[str, pd.DataFrame]) -> Tuple[str, Dict[str, Any]]:
        """Generate query to analyze missing values."""
        # Use first dataframe
        file_id = list(dataframes.keys())[0]
        df = dataframes[file_id]
        
        return 'pandas', {
            'operation': 'missing_values',
            'file_id': file_id,
            'dataframe': df
        }
    
    def _generate_operational_query(self, dataframes: Dict[str, pd.DataFrame], 
                                   params: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Generate operational query (delays, inefficiencies, outliers)."""
        # Use first dataframe
        file_id = list(dataframes.keys())[0]
        df = dataframes[file_id]
        
        query_type = params.get('operational_type', 'general')
        
        return 'pandas', {
            'operation': 'operational',
            'operational_type': query_type,
            'file_id': file_id,
            'dataframe': df,
            'params': params
        }
    
    def _generate_calculation_query(self, dataframes: Dict[str, pd.DataFrame], 
                                   params: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Generate calculation query (ratios, per-unit, etc.)."""
        # Use first dataframe
        file_id = list(dataframes.keys())[0]
        df = dataframes[file_id]
        
        calc_type = params.get('calc_type', 'general')
        numerator = params.get('numerator')
        denominator = params.get('denominator')
        group_by = params.get('group_by')
        
        # Find columns
        target_num = self._find_column(numerator, dataframes) if numerator else None
        target_den = self._find_column(denominator, dataframes) if denominator else None
        target_group = self._find_column(group_by, dataframes) if group_by else None
        
        num_col = target_num[1] if target_num else None
        den_col = target_den[1] if target_den else None
        group_col = target_group[1] if target_group else None
        
        if not num_col or not den_col:
            raise ValueError(f"Could not find columns for calculation: numerator={numerator}, denominator={denominator}")
        
        return 'pandas', {
            'operation': 'calculation',
            'calc_type': calc_type,
            'numerator': num_col,
            'denominator': den_col,
            'group_by_column': group_col,
            'file_id': file_id,
            'dataframe': df
        }
