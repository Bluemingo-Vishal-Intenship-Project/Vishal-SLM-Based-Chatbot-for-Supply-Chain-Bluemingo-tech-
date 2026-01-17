"""
Response Formatter Module
Formats query results into natural language answers.

Design Philosophy:
- Templates as base formatting (primary)
- Optional SLM enhancement for phrasing/readability (secondary)
- All data comes from query results
- SLM never introduces new facts or modifies query results
- SLM output strictly grounded in query results
- If SLM unavailable, templates provide complete functionality
"""

from typing import Dict, List, Any, Optional
import json
import pandas as pd
import numpy as np


class ResponseFormatter:
    """
    Formats query results into natural language answers.
    
    Uses template-based formatting as primary method.
    Optional SLM enhancement can be added for phrasing/readability.
    SLM must never introduce new facts or modify query results.
    """
    
    # Unit mapping for common columns
    COLUMN_UNITS = {
        'cost': 'Rs',
        'transportation cost': 'Rs',
        'total transportation cost (rs)': 'Rs',
        'mrp': 'Rs',
        'value': 'Rs',
        'consignment mrp value': 'Rs',
        'total consignment mrp value': 'Rs',
        'weight': 'kg',
        'total weight': 'kg',
        'sku_weight': 'kg',
        'weight per case': 'kg/case',
        'cost per case': 'Rs/case',
        'cost per kg': 'Rs/kg',
        'cost per kilogram': 'Rs/kg',
        'volume': 'm³',
        'total volume': 'm³',
        'cases': '',
        'no of cases': '',
        'total no of cases': '',
        'utilization': '%',
        'mode utilization': '%',
        'mode utilization (%)': '%',
        'fill': '%',
        'weight % fill': '%',
        'volume % fill': '%',
        'total weight % fill': '%',
        'totalvolume % fill': '%'
    }
    
    def _get_unit_for_column(self, column_name: str) -> str:
        """Get unit for a column name."""
        if not column_name:
            return ''
        
        column_lower = column_name.lower().strip()
        
        # Exact match first
        if column_lower in self.COLUMN_UNITS:
            return self.COLUMN_UNITS[column_lower]
        
        # Partial match
        for key, unit in self.COLUMN_UNITS.items():
            if key in column_lower or column_lower in key:
                return unit
        
        # Check for specific patterns
        if 'cost' in column_lower or 'price' in column_lower or 'mrp' in column_lower:
            return 'Rs'
        elif 'weight' in column_lower and 'fill' not in column_lower and 'utilization' not in column_lower:
            return 'kg'
        elif 'volume' in column_lower and 'fill' not in column_lower:
            return 'm³'
        elif 'case' in column_lower:
            return 'cases' if 'per' not in column_lower else ''
        elif '%' in column_name or 'fill' in column_lower or 'utilization' in column_lower:
            return '%'
        
        return ''
    
    def __init__(self):
        """
        Initialize response formatter.
        
        Currently uses template-based formatting (primary, always available).
        SLM enhancement can be added optionally for:
        - Improving phrasing
        - Improving readability
        - Making language more natural
        
        SLM must be strictly grounded in query results.
        """
        # Template-based formatting is primary and always available
        # Optional SLM can be added for enhancement, but templates provide complete functionality
        pass
    
    def format_response(self, query_result: Dict[str, Any], 
                       original_query: str) -> str:
        """
        Format query result into a natural language answer.
        
        Uses template-based formatting (primary method).
        All data comes from query_result - never generates or infers values.
        
        Args:
            query_result: Result from query executor (source of truth)
            original_query: Original user query
            
        Returns:
            Formatted answer string (strictly grounded in query_result)
        """
        if not query_result.get('success', False):
            error = query_result.get('error', 'Unknown error')
            return f"I couldn't find the information you're looking for.\n\nError: {error}\n\nPlease make sure the data contains the requested information."
        
        result_type = query_result.get('result_type')
        data = query_result.get('data')
        
        if result_type == 'column_names':
            return self._format_column_names(data)
        elif result_type == 'row_count':
            return self._format_row_count(data)
        elif result_type == 'aggregation':
            return self._format_aggregation(data, original_query)
        elif result_type == 'group_by':
            return self._format_group_by(data, query_result)
        elif result_type == 'list_unique':
            return self._format_list_unique(data, original_query)
        elif result_type == 'ranking':
            return self._format_ranking(data, original_query)
        elif result_type == 'preview':
            return self._format_preview(data)
        elif result_type == 'time_range':
            return self._format_time_range(data)
        elif result_type == 'data_types':
            return self._format_data_types(data)
        elif result_type == 'missing_values':
            return self._format_missing_values(data)
        elif result_type == 'operational':
            return self._format_operational(data, query_result)
        elif result_type == 'calculation':
            return self._format_calculation(data, query_result)
        elif result_type == 'filter':
            return self._format_filter(data)
        elif result_type == 'general':
            return self._format_general(data)
        else:
            return self._format_general(data)
    
    def _format_column_names(self, data: List[str]) -> str:
        """Format column names result."""
        if not data:
            return "No columns found in the data."
        
        answer = "**Column Names in this file:**\n\n"
        for i, col in enumerate(data, 1):
            answer += f"{i}. {col}\n"
        
        return answer.strip()
    
    def _format_row_count(self, data: Dict[str, Any]) -> str:
        """Format row count result."""
        total = data.get('total', 0)
        by_file = data.get('by_file', {})
        column_count = data.get('column_count')  # For "how many columns" queries
        
        if column_count is not None:
            return f"**Total number of columns:** {column_count}"
        
        if len(by_file) == 1:
            return f"**Total number of records:** {total:,}"
        else:
            answer = f"**Total number of records:** {total:,}\n\n"
            answer += "**Breakdown by file:**\n"
            for file_id, count in by_file.items():
                answer += f"- {file_id}: {count:,} records\n"
            return answer.strip()
    
    def _format_aggregation(self, data: Dict[str, Any], query: str) -> str:
        """Format aggregation result with units."""
        value = data.get('value')
        agg_type = data.get('agg_type', 'sum')
        column = data.get('column', '')
        
        if value is None:
            return f"I couldn't calculate the {agg_type} for {column}."
        
        # Format value
        if isinstance(value, float):
            if value.is_integer():
                value_str = f"{int(value):,}"
            else:
                value_str = f"{value:,.2f}"
        else:
            value_str = f"{value:,}"
        
        # Get unit for column
        unit = self._get_unit_for_column(column)
        if unit:
            value_str = f"{value_str} {unit}"
        
        # Determine label
        agg_labels = {
            'sum': 'Total',
            'mean': 'Average',
            'average': 'Average',
            'max': 'Maximum',
            'maximum': 'Maximum',
            'min': 'Minimum',
            'minimum': 'Minimum',
            'count': 'Count'
        }
        label = agg_labels.get(agg_type, 'Result')
        
        answer = f"**{label} {column}:** {value_str}"
        return answer
    
    def _format_list_unique(self, data: List[str], query: str) -> str:
        """Format list unique values result."""
        if not data:
            return "No unique values found."
        
        # Determine what we're listing from query
        query_lower = query.lower()
        if 'source type' in query_lower:
            title = "Source Types"
        elif 'source location' in query_lower or ('source' in query_lower and 'location' in query_lower):
            title = "Source Locations"
        elif 'destination type' in query_lower:
            title = "Destination Types"
        elif 'destination location' in query_lower or ('destination' in query_lower and 'location' in query_lower):
            title = "Destination Locations"
        elif 'product' in query_lower:
            title = "Products"
        elif 'mode' in query_lower or 'transportation' in query_lower:
            title = "Transportation Modes"
        elif 'customer' in query_lower:
            title = "Customers"
        elif 'consignment' in query_lower:
            title = "Consignment Numbers"
        elif 'unit' in query_lower:
            title = "Units"
        elif 'plan name' in query_lower:
            title = "Plan Names"
        else:
            title = "Unique Values"
        
        answer = f"**{title}:**\n\n"
        for i, value in enumerate(data, 1):
            answer += f"{i}. {value}\n"
        
        return answer.strip()
    
    def _format_ranking(self, data: List[Dict[str, Any]], query: str) -> str:
        """Format ranking result."""
        if not data:
            return "No results found."
        
        # Determine what we're ranking
        query_lower = query.lower()
        if 'order' in query_lower and 'cases' in query_lower:
            # Ranking orders by cases
            answer = "**Orders with Most Cases:**\n\n"
            for i, record in enumerate(data, 1):
                order = record.get('Order', record.get('order', 'N/A'))
                cases = record.get('No of Cases', record.get('no_of_cases', record.get('No of Cases', 'N/A')))
                answer += f"**Rank {i}:**\n"
                answer += f"- Order: {order}\n"
                answer += f"- Number of Cases: {cases}\n"
                answer += "\n"
        else:
            # General ranking
            answer = f"**Top {len(data)} Results:**\n\n"
            for i, record in enumerate(data, 1):
                answer += f"**Rank {i}:**\n"
                for key, value in record.items():
                    if pd.notna(value) if hasattr(pd, 'notna') else value is not None:
                        # Get unit for column
                        unit = self._get_unit_for_column(key)
                        
                        if isinstance(value, float):
                            value_str = f"{value:,.2f}"
                        elif isinstance(value, (int, float)):
                            value_str = f"{value:,}"
                        else:
                            value_str = str(value)
                        
                        # Add unit if applicable
                        if unit and isinstance(value, (int, float)):
                            value_str = f"{value_str} {unit}"
                        
                        answer += f"- {key}: {value_str}\n"
                answer += "\n"
        
        return answer.strip()
    
    def _format_preview(self, data: List[Dict[str, Any]]) -> str:
        """Format preview result."""
        if not data:
            return "No data available for preview."
        
        # Get column names from first record
        columns = list(data[0].keys()) if data else []
        
        answer = f"**Data Preview ({len(data)} rows):**\n\n"
        
        # Format as table
        answer += "| " + " | ".join(columns) + " |\n"
        answer += "| " + " | ".join(["---"] * len(columns)) + " |\n"
        
        for record in data[:10]:  # Show max 10 rows in preview
            row = []
            for col in columns:
                value = record.get(col, '')
                if value is None or (hasattr(pd, 'isna') and pd.isna(value)):
                    value = 'NULL'
                else:
                    value = str(value)
                # Truncate long values
                if len(value) > 50:
                    value = value[:47] + "..."
                row.append(value)
            answer += "| " + " | ".join(row) + " |\n"
        
        if len(data) > 10:
            answer += f"\n... and {len(data) - 10} more rows"
        
        return answer
    
    def _format_time_range(self, data: Dict[str, Any]) -> str:
        """Format time range result."""
        min_date = data.get('min')
        max_date = data.get('max')
        column = data.get('column', 'date')
        
        if not min_date or not max_date:
            return f"Could not determine date range for {column}."
        
        # Parse dates to calculate range (matching training doc format)
        min_dt = None
        max_dt = None
        days_covered = None
        
        try:
            min_dt = pd.to_datetime(min_date)
            max_dt = pd.to_datetime(max_date)
            date_range = max_dt - min_dt
            days_covered = date_range.days + 1  # +1 to include both start and end dates
        except Exception:
            # If date parsing fails, use original string values
            pass
        
        answer = f"**Date Range:**\n\n"
        answer += f"- **From:** {min_dt.date() if min_dt is not None else min_date}\n"
        answer += f"- **To:** {max_dt.date() if max_dt is not None else max_date}\n"
        if days_covered is not None:
            answer += f"- **Days Covered:** {days_covered}\n"
        
        return answer
    
    def _format_filter(self, data: List[Dict[str, Any]]) -> str:
        """Format filter result."""
        if not data:
            return "No results match the specified criteria."
        
        return self._format_preview(data)
    
    def _format_general(self, data: List[Dict[str, Any]]) -> str:
        """Format general result."""
        if not data:
            return "No data available."
        
        return self._format_preview(data)
    
    def _format_group_by(self, data: Dict[str, Any], query_result: Dict[str, Any]) -> str:
        """Format group by aggregation result with units."""
        if not data:
            return "No grouped data available."
        
        agg_type = query_result.get('agg_type', 'sum')
        agg_column = query_result.get('agg_column', 'value')
        group_by_column = query_result.get('group_by_column', 'category')
        
        # Get unit for aggregation column
        unit = self._get_unit_for_column(agg_column)
        
        # Format aggregation type name
        agg_name = {
            'sum': 'Total',
            'mean': 'Average',
            'avg': 'Average',
            'count': 'Count',
            'max': 'Maximum',
            'min': 'Minimum'
        }.get(agg_type, agg_type.title())
        
        answer = f"**{agg_name} {agg_column.replace('_', ' ').title()} by {group_by_column.replace('_', ' ').title()}:**\n\n"
        
        # Sort by value (descending) for better readability
        sorted_items = sorted(data.items(), key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0, reverse=True)
        
        for group, value in sorted_items:
            if isinstance(value, (int, float)):
                if isinstance(value, float):
                    value_str = f"{value:,.2f}"
                else:
                    value_str = f"{value:,}"
                
                # Add unit
                if unit:
                    value_str = f"{value_str} {unit}"
                
                answer += f"- **{group}**: {value_str}\n"
            else:
                answer += f"- **{group}**: {value}\n"
        
        return answer.strip()
    
    def _format_data_types(self, data: Dict[str, Any]) -> str:
        """Format data types result."""
        all_types = data.get('all_types', {})
        numerical = data.get('numerical', [])
        text = data.get('text', [])
        datetime_cols = data.get('datetime', [])
        
        answer = "**Data Types in this Dataset:**\n\n"
        
        if all_types:
            answer += "**All Column Types:**\n"
            for col, dtype in all_types.items():
                answer += f"- {col}: {dtype}\n"
            answer += "\n"
        
        if numerical:
            answer += f"**Numerical Columns ({len(numerical)}):**\n"
            for col in numerical:
                answer += f"- {col}\n"
            answer += "\n"
        
        if text:
            answer += f"**Text Columns ({len(text)}):**\n"
            for col in text:
                answer += f"- {col}\n"
            answer += "\n"
        
        if datetime_cols:
            answer += f"**Date/Time Columns ({len(datetime_cols)}):**\n"
            for col in datetime_cols:
                answer += f"- {col}\n"
        
        return answer.strip()
    
    def _format_missing_values(self, data: Dict[str, Any]) -> str:
        """Format missing values result."""
        missing_counts = data.get('missing_counts', {})
        missing_percentages = data.get('missing_percentages', {})
        columns_with_missing = data.get('columns_with_missing', [])
        total_missing = data.get('total_missing', 0)
        has_missing = data.get('has_missing', False)
        
        if not has_missing:
            return "**Missing Values Analysis:**\n\n✅ No missing or null values found in this dataset."
        
        answer = f"**Missing Values Analysis:**\n\n"
        answer += f"**Total Missing Values:** {total_missing:,}\n\n"
        
        if columns_with_missing:
            answer += f"**Columns with Missing Values ({len(columns_with_missing)}):**\n\n"
            answer += "| Column | Missing Count | Missing % |\n"
            answer += "|--------|---------------|----------|\n"
            
            # Sort by missing count (descending)
            sorted_cols = sorted(columns_with_missing, 
                              key=lambda x: missing_counts.get(x, 0), 
                              reverse=True)
            
            for col in sorted_cols:
                count = missing_counts.get(col, 0)
                pct = missing_percentages.get(col, 0)
                answer += f"| {col} | {count:,} | {pct:.2f}% |\n"
        
        return answer.strip()
    
    def _format_operational(self, data: Dict[str, Any], query_result: Dict[str, Any]) -> str:
        """Format operational query result."""
        operational_type = data.get('type', 'general')
        message = data.get('message', '')
        
        answer = f"**Operational Analysis ({operational_type}):**\n\n"
        
        if message:
            answer += message + "\n"
        else:
            answer += "Operational analysis would be implemented based on specific query requirements.\n"
            answer += "This feature analyzes delays, inefficiencies, outliers, and other operational metrics."
        
        return answer.strip()
    
    def _format_calculation(self, data: Any, query_result: Dict[str, Any]) -> str:
        """Format calculation result (ratios, per-unit, etc.) with units."""
        calc_type = query_result.get('calc_type', 'general')
        numerator = query_result.get('numerator', 'value')
        denominator = query_result.get('denominator', 'unit')
        group_by_column = query_result.get('group_by_column')
        
        # Determine unit based on calculation type
        calc_units = {
            'cost_per_case': 'Rs/case',
            'cost_per_kg': 'Rs/kg',
            'cost_per_kg': 'Rs/kg',
            'cost_efficiency_per_weight': 'Rs/kg',
            'weight_per_case': 'kg/case',
            'volume_utilization': '%',
            'weight_fill_percentage': '%',
            'volume_fill_percentage': '%',
            'delivery_time': 'days',
            'per_case': 'Rs/case',
            'per_kg': 'Rs/kg',
            'weight_per_case': 'kg/case'
        }
        
        unit = calc_units.get(calc_type, '')
        if not unit:
            # Infer from numerator/denominator
            if 'cost' in str(numerator).lower() and 'case' in str(denominator).lower():
                unit = 'Rs/case'
            elif 'cost' in str(numerator).lower() and 'weight' in str(denominator).lower():
                unit = 'Rs/kg'
            elif 'weight' in str(numerator).lower() and 'case' in str(denominator).lower():
                unit = 'kg/case'
        
        # Format calculation name
        calc_names = {
            'cost_per_case': 'Cost Per Case',
            'cost_per_kg': 'Cost Per Kilogram',
            'cost_efficiency_per_weight': 'Cost Efficiency (Cost per Unit Weight)',
            'weight_per_case': 'Weight Per Case Ratio',
            'volume_utilization': 'Volume Utilization',
            'weight_fill_percentage': 'Weight Fill Percentage',
            'volume_fill_percentage': 'Volume Fill Percentage',
            'delivery_time': 'Average Delivery Time',
            'per_case': 'Cost Per Case',
            'per_kg': 'Cost Per Kilogram',
            'ratio': 'Ratio'
        }
        calc_name = calc_names.get(calc_type, 'Calculation')
        
        if isinstance(data, dict):
            # Grouped results
            answer = f"**{calc_name}:**\n\n"
            
            # Sort by value (descending)
            sorted_items = sorted(data.items(), key=lambda x: x[1] if isinstance(x[1], (int, float)) and not np.isnan(x[1]) else 0, reverse=True)
            
            for group, value in sorted_items:
                if isinstance(value, (int, float)) and not np.isnan(value):
                    if isinstance(value, float):
                        value_str = f"{value:,.4f}"
                    else:
                        value_str = f"{value:,}"
                    
                    # Add unit
                    if unit:
                        value_str = f"{value_str} {unit}"
                    
                    answer += f"- **{group}**: {value_str}\n"
            
            return answer.strip()
        elif isinstance(data, list):
            # Per-row results - format as table with units
            if not data:
                return "No calculation results available."
            
            answer = f"**{calc_name}:**\n\n"
            
            # Create table header
            headers = []
            if group_by_column:
                headers.append(group_by_column.replace('_', ' ').title())
            headers.append(f"{calc_name} ({unit})" if unit else calc_name)
            
            answer += "| " + " | ".join(headers) + " |\n"
            answer += "| " + " | ".join(["---"] * len(headers)) + " |\n"
            
            for record in data[:50]:  # Limit to 50 rows
                calc_value = record.get('Calculated Value', record.get('calculated_value', record.get('value', 'N/A')))
                row = []
                
                if group_by_column and group_by_column in record:
                    row.append(str(record[group_by_column]))
                
                if isinstance(calc_value, (int, float)) and not np.isnan(calc_value):
                    if isinstance(calc_value, float):
                        value_str = f"{calc_value:,.4f}"
                    else:
                        value_str = f"{calc_value:,}"
                    if unit:
                        value_str = f"{value_str} {unit}"
                    row.append(value_str)
                else:
                    row.append(str(calc_value))
                
                answer += "| " + " | ".join(row) + " |\n"
            
            if len(data) > 50:
                answer += f"\n... and {len(data) - 50} more results."
            
            return answer.strip()
        else:
            return f"**{calc_name}:** {data}"
