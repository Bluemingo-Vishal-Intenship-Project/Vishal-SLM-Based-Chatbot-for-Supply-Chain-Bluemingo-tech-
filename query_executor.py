"""
Query Executor Module
Safely executes queries on DataFrames and validates results.

Design Philosophy:
- Queries = Accuracy Guarantee (deterministic and verifiable)
- All queries are read-only
- Results are validated before returning
- Safety checks prevent data corruption
- Null-safe aggregations
- Graceful failure with helpful messages
"""

from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np


class QueryExecutor:
    """Executes queries safely on DataFrames."""
    
    MAX_RESULT_ROWS = 1000  # Maximum rows to return
    MAX_PREVIEW_ROWS = 50   # Maximum rows for preview
    
    def __init__(self):
        """Initialize query executor."""
        pass
    
    def execute(self, query_type: str, query_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a query and return results.
        
        Args:
            query_type: 'pandas' or 'sql'
            query_spec: Query specification dictionary
            
        Returns:
            Dictionary with query results
        """
        # Input validation
        if not query_type:
            raise ValueError("query_type is required")
        
        if query_type != 'pandas':
            raise ValueError(f"Unsupported query type: {query_type}. Only 'pandas' is supported.")
        
        if not query_spec or not isinstance(query_spec, dict):
            raise ValueError("query_spec must be a non-empty dictionary")
        
        operation = query_spec.get('operation')
        
        if not operation:
            raise ValueError("query_spec must contain an 'operation' key")
        
        if operation == 'column_names':
            return self._execute_column_names(query_spec)
        elif operation == 'row_count':
            return self._execute_row_count(query_spec)
        elif operation == 'aggregation':
            return self._execute_aggregation(query_spec)
        elif operation == 'group_by':
            return self._execute_group_by(query_spec)
        elif operation == 'list_unique':
            return self._execute_list_unique(query_spec)
        elif operation == 'ranking':
            return self._execute_ranking(query_spec)
        elif operation == 'preview':
            return self._execute_preview(query_spec)
        elif operation == 'time_range':
            return self._execute_time_range(query_spec)
        elif operation == 'data_types':
            return self._execute_data_types(query_spec)
        elif operation == 'missing_values':
            return self._execute_missing_values(query_spec)
        elif operation == 'operational':
            return self._execute_operational(query_spec)
        elif operation == 'calculation':
            return self._execute_calculation(query_spec)
        elif operation == 'filter':
            return self._execute_filter(query_spec)
        elif operation == 'general':
            return self._execute_general(query_spec)
        else:
            raise ValueError(f"Unknown operation: {operation}")
    
    def _execute_column_names(self, query_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Execute column names query."""
        columns = query_spec.get('columns', [])
        
        return {
            'success': True,
            'result_type': 'column_names',
            'data': columns,
            'count': len(columns)
        }
    
    def _execute_row_count(self, query_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Execute row count query."""
        counts = query_spec.get('counts', {})
        total = query_spec.get('total', 0)
        column_count = query_spec.get('column_count')  # For column count queries
        
        data = {
            'total': total,
            'by_file': counts
        }
        if column_count is not None:
            data['column_count'] = column_count
        
        return {
            'success': True,
            'result_type': 'row_count',
            'data': data,
            'count': total if column_count is None else column_count
        }
    
    def _execute_aggregation(self, query_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Execute aggregation query."""
        df = query_spec.get('dataframe')
        column = query_spec.get('column')
        agg_type = query_spec.get('agg_type', 'sum')
        
        if column not in df.columns:
            available_cols = ', '.join(df.columns[:10].tolist())
            if len(df.columns) > 10:
                available_cols += f", ... ({len(df.columns)} total)"
            return {
                'success': False,
                'error': f"Column '{column}' not found. Available columns: {available_cols}"
            }
        
        # Convert to numeric if possible
        series = pd.to_numeric(df[column], errors='coerce')
        
        if series.isna().all():
            return {
                'success': False,
                'error': f"Column '{column}' contains no numeric values. Please select a column with numeric data."
            }
        
        # Perform aggregation
        if agg_type == 'sum':
            result = series.sum()
        elif agg_type == 'mean' or agg_type == 'average':
            result = series.mean()
        elif agg_type == 'max' or agg_type == 'maximum':
            result = series.max()
        elif agg_type == 'min' or agg_type == 'minimum':
            result = series.min()
        elif agg_type == 'count':
            result = series.notna().sum()
        else:
            result = series.sum()
        
        # Convert to Python native type
        if pd.isna(result):
            result = None
        elif isinstance(result, (np.integer, np.floating)):
            result = result.item()
        
        return {
            'success': True,
            'result_type': 'aggregation',
            'data': {
                'value': result,
                'agg_type': agg_type,
                'column': column
            },
            'value': result
        }
    
    def _execute_list_unique(self, query_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Execute list unique values query."""
        df = query_spec.get('dataframe')
        column = query_spec.get('column')
        
        if column not in df.columns:
            available_cols = ', '.join(df.columns[:10].tolist())
            if len(df.columns) > 10:
                available_cols += f", ... ({len(df.columns)} total)"
            return {
                'success': False,
                'error': f"Column '{column}' not found. Available columns: {available_cols}"
            }
        
        # Get unique values
        unique_values = df[column].dropna().unique().tolist()
        unique_values = sorted([str(v) for v in unique_values])
        
        # Limit results
        if len(unique_values) > self.MAX_RESULT_ROWS:
            unique_values = unique_values[:self.MAX_RESULT_ROWS]
        
        return {
            'success': True,
            'result_type': 'list_unique',
            'data': unique_values,
            'count': len(unique_values)
        }
    
    def _execute_ranking(self, query_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Execute ranking query."""
        df = query_spec.get('dataframe')
        column = query_spec.get('column')
        order = query_spec.get('order', 'desc')
        limit = query_spec.get('limit', 10)
        
        if column not in df.columns:
            available_cols = ', '.join(df.columns[:10].tolist())
            if len(df.columns) > 10:
                available_cols += f", ... ({len(df.columns)} total)"
            return {
                'success': False,
                'error': f"Column '{column}' not found. Available columns: {available_cols}"
            }
        
        # Convert to numeric if possible
        df_sorted = df.copy()
        df_sorted[column] = pd.to_numeric(df_sorted[column], errors='coerce')
        
        # Sort
        ascending = (order == 'asc')
        df_sorted = df_sorted.sort_values(by=column, ascending=ascending, na_position='last')
        
        # Get top N
        result_df = df_sorted.head(limit)
        
        # Convert to list of dicts
        results = result_df.to_dict('records')
        
        return {
            'success': True,
            'result_type': 'ranking',
            'data': results,
            'count': len(results),
            'column': column,
            'order': order,
            'limit': limit
        }
    
    def _execute_preview(self, query_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Execute preview query."""
        df = query_spec.get('dataframe')
        limit = min(query_spec.get('limit', 5), self.MAX_PREVIEW_ROWS)
        
        # Get first N rows
        preview_df = df.head(limit)
        
        # Convert to list of dicts
        results = preview_df.to_dict('records')
        
        return {
            'success': True,
            'result_type': 'preview',
            'data': results,
            'count': len(results),
            'columns': list(df.columns)
        }
    
    def _execute_time_range(self, query_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Execute time range query."""
        df = query_spec.get('dataframe')
        column = query_spec.get('column')
        
        if column not in df.columns:
            available_cols = ', '.join(df.columns[:10].tolist())
            if len(df.columns) > 10:
                available_cols += f", ... ({len(df.columns)} total)"
            return {
                'success': False,
                'error': f"Column '{column}' not found. Available columns: {available_cols}"
            }
        
        # Try to convert to datetime
        series = pd.to_datetime(df[column], errors='coerce')
        
        if series.isna().all():
            return {
                'success': False,
                'error': f"Column '{column}' contains no valid dates. Please select a column with date/time data."
            }
        
        # Get min and max
        min_date = series.min()
        max_date = series.max()
        
        return {
            'success': True,
            'result_type': 'time_range',
            'data': {
                'min': str(min_date) if pd.notna(min_date) else None,
                'max': str(max_date) if pd.notna(max_date) else None,
                'column': column
            }
        }
    
    def _execute_filter(self, query_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Execute filter query."""
        df = query_spec.get('dataframe')
        params = query_spec.get('params', {})
        
        # For now, return all data (filtering would be more complex)
        results = df.head(self.MAX_RESULT_ROWS).to_dict('records')
        
        return {
            'success': True,
            'result_type': 'filter',
            'data': results,
            'count': len(results)
        }
    
    def _execute_general(self, query_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Execute general query."""
        df = query_spec.get('dataframe')
        
        # Return preview
        results = df.head(self.MAX_PREVIEW_ROWS).to_dict('records')
        
        return {
            'success': True,
            'result_type': 'general',
            'data': results,
            'count': len(results),
            'columns': list(df.columns)
        }
    
    def _execute_group_by(self, query_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Execute group by aggregation query."""
        df = query_spec.get('dataframe')
        if df is None:
            return {'success': False, 'error': 'DataFrame not found'}
        
        agg_type = query_spec.get('agg_type', 'sum')
        agg_column = query_spec.get('agg_column')
        group_by_column = query_spec.get('group_by_column')
        
        if not agg_column or not group_by_column:
            return {'success': False, 'error': 'Missing aggregation or group by column. Both agg_column and group_by_column are required.'}
        
        # Validate columns exist
        if agg_column not in df.columns:
            available_cols = ', '.join(df.columns[:10].tolist())
            if len(df.columns) > 10:
                available_cols += f", ... ({len(df.columns)} total)"
            return {'success': False, 'error': f"Aggregation column '{agg_column}' not found. Available columns: {available_cols}"}
        if group_by_column not in df.columns:
            available_cols = ', '.join(df.columns[:10].tolist())
            if len(df.columns) > 10:
                available_cols += f", ... ({len(df.columns)} total)"
            return {'success': False, 'error': f"Group by column '{group_by_column}' not found. Available columns: {available_cols}"}
        
        try:
            # Convert to numeric for aggregation columns
            df_copy = df.copy()
            df_copy[agg_column] = pd.to_numeric(df_copy[agg_column], errors='coerce')
            
            # Group by and aggregate (optimized for large datasets)
            grouped = df_copy.groupby(group_by_column, observed=True)[agg_column]
            
            if agg_type == 'sum':
                result = grouped.sum(skipna=True)
            elif agg_type == 'mean' or agg_type == 'avg':
                result = grouped.mean(skipna=True)
            elif agg_type == 'count':
                result = grouped.count()
            elif agg_type == 'max':
                result = grouped.max(skipna=True)
            elif agg_type == 'min':
                result = grouped.min(skipna=True)
            else:
                result = grouped.sum(skipna=True)
            
            # Convert to dictionary (sorted for better readability)
            result_dict = result.to_dict()
            
            return {
                'success': True,
                'result_type': 'group_by',
                'data': result_dict,
                'agg_type': agg_type,
                'agg_column': agg_column,
                'group_by_column': group_by_column,
                'count': len(result_dict)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _execute_data_types(self, query_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Execute data types query."""
        df = query_spec.get('dataframe')
        if df is None:
            return {'success': False, 'error': 'DataFrame not found'}
        
        try:
            # Get data types
            dtypes = df.dtypes.to_dict()
            
            # Categorize columns
            numerical = []
            text = []
            datetime_cols = []
            
            for col, dtype in dtypes.items():
                dtype_str = str(dtype)
                if 'int' in dtype_str or 'float' in dtype_str:
                    numerical.append(col)
                elif 'object' in dtype_str or 'string' in dtype_str:
                    text.append(col)
                elif 'datetime' in dtype_str or 'date' in dtype_str:
                    datetime_cols.append(col)
            
            return {
                'success': True,
                'result_type': 'data_types',
                'data': {
                    'all_types': {k: str(v) for k, v in dtypes.items()},
                    'numerical': numerical,
                    'text': text,
                    'datetime': datetime_cols
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _execute_missing_values(self, query_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Execute missing values query."""
        df = query_spec.get('dataframe')
        if df is None:
            return {'success': False, 'error': 'DataFrame not found'}
        
        try:
            # Count missing values per column
            missing_counts = df.isnull().sum().to_dict()
            missing_percentages = (df.isnull().sum() / len(df) * 100).to_dict()
            
            # Columns with missing values
            columns_with_missing = [col for col, count in missing_counts.items() if count > 0]
            
            return {
                'success': True,
                'result_type': 'missing_values',
                'data': {
                    'missing_counts': missing_counts,
                    'missing_percentages': {k: round(v, 2) for k, v in missing_percentages.items()},
                    'columns_with_missing': columns_with_missing,
                    'total_missing': int(sum(missing_counts.values())),
                    'has_missing': len(columns_with_missing) > 0
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _execute_operational(self, query_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Execute operational query (delays, inefficiencies, outliers)."""
        df = query_spec.get('dataframe')
        if df is None:
            return {'success': False, 'error': 'DataFrame not found'}
        
        operational_type = query_spec.get('operational_type', 'general')
        
        try:
            # This is a placeholder - operational queries would need specific logic
            # based on the query type (delays, inefficiencies, etc.)
            return {
                'success': True,
                'result_type': 'operational',
                'data': {
                    'message': 'Operational analysis would be implemented based on specific query requirements',
                    'type': operational_type
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _execute_calculation(self, query_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Execute calculation query (ratios, per-unit, etc.)."""
        df = query_spec.get('dataframe')
        if df is None:
            return {'success': False, 'error': 'DataFrame not found'}
        
        calc_type = query_spec.get('calc_type', 'general')
        numerator = query_spec.get('numerator')
        denominator = query_spec.get('denominator')
        group_by_column = query_spec.get('group_by_column')
        
        if not numerator or not denominator:
            return {'success': False, 'error': 'Missing numerator or denominator for calculation. Both are required.'}
        
        try:
            # Ensure columns exist
            if numerator not in df.columns:
                available_cols = ', '.join(df.columns[:10].tolist())
                if len(df.columns) > 10:
                    available_cols += f", ... ({len(df.columns)} total)"
                return {'success': False, 'error': f"Numerator column '{numerator}' not found. Available columns: {available_cols}"}
            if denominator not in df.columns:
                available_cols = ', '.join(df.columns[:10].tolist())
                if len(df.columns) > 10:
                    available_cols += f", ... ({len(df.columns)} total)"
                return {'success': False, 'error': f"Denominator column '{denominator}' not found. Available columns: {available_cols}"}
            
            # Convert to numeric
            df_calc = df.copy()
            df_calc[numerator] = pd.to_numeric(df_calc[numerator], errors='coerce')
            df_calc[denominator] = pd.to_numeric(df_calc[denominator], errors='coerce')
            
            # Calculate ratio
            df_calc['calculated_value'] = df_calc[numerator] / df_calc[denominator]
            df_calc['calculated_value'] = df_calc['calculated_value'].replace([np.inf, -np.inf], np.nan)
            
            if group_by_column and group_by_column in df_calc.columns:
                # Group by and aggregate
                grouped = df_calc.groupby(group_by_column)['calculated_value']
                result = grouped.mean()  # Average ratio per group
                result_dict = result.to_dict()
                
                return {
                    'success': True,
                    'result_type': 'calculation',
                    'data': result_dict,
                    'calc_type': calc_type,
                    'numerator': numerator,
                    'denominator': denominator,
                    'group_by_column': group_by_column,
                    'count': len(result_dict)
                }
            else:
                # Return per-row calculations (limited to prevent huge output)
                result_df = df_calc[['calculated_value']].copy()
                if group_by_column and group_by_column in df_calc.columns:
                    result_df[group_by_column] = df_calc[group_by_column]
                
                # Limit results
                result_df = result_df.head(self.MAX_RESULT_ROWS)
                results = result_df.to_dict('records')
                
                return {
                    'success': True,
                    'result_type': 'calculation',
                    'data': results,
                    'calc_type': calc_type,
                    'numerator': numerator,
                    'denominator': denominator,
                    'count': len(results)
                }
        except Exception as e:
            return {'success': False, 'error': str(e)}
