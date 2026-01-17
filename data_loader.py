"""
Data Loader Module
Handles loading and managing structured data (CSV/Excel) into Pandas DataFrames.
Maintains schema registry for query generation.

Design Philosophy:
- Data = Source of Truth
- All data stored in Pandas DataFrames
- Schema metadata maintained for query generation
- No embeddings, no vector DB - just structured data
- Accuracy bounded by data correctness
"""

import pandas as pd
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import json
from datetime import datetime


class DataLoader:
    """Loads and manages structured data files."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize data loader.
        
        Args:
            db_path: Optional path to SQLite database for persistence
        """
        self.dataframes: Dict[str, pd.DataFrame] = {}  # {file_id: DataFrame}
        self.schemas: Dict[str, Dict[str, Any]] = {}  # {file_id: schema_info}
        self.db_path = db_path or "./data_cache.db"
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for data persistence."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.close()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not initialize database: {e}")
    
    def load_file(self, file_path: str, file_id: Optional[str] = None) -> Tuple[str, pd.DataFrame]:
        """
        Load a CSV or Excel file into a DataFrame.
        
        Args:
            file_path: Path to the file
            file_id: Optional identifier for the file
            
        Returns:
            Tuple of (file_id, DataFrame)
        """
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if file_id is None:
            file_id = file_path_obj.stem
        
        file_ext = file_path_obj.suffix.lower()
        
        # Load data based on file type
        if file_ext == '.csv':
            # Try different encodings
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            df = None
            last_error = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding, low_memory=False)
                    break
                except UnicodeDecodeError as e:
                    last_error = e
                    continue
                except Exception as e:
                    last_error = e
                    # For non-encoding errors, don't try other encodings
                    raise
            
            if df is None:
                # Last resort: try with errors='ignore'
                try:
                    df = pd.read_csv(file_path, encoding='utf-8', errors='ignore', low_memory=False)
                except Exception as e:
                    error_msg = f"Failed to read CSV file. Tried encodings: {', '.join(encodings)}"
                    if last_error:
                        error_msg += f" Last error: {str(last_error)}"
                    raise ValueError(error_msg) from e
        elif file_ext in ['.xlsx', '.xls', '.xlsm', '.xlsb']:
            engine = 'xlrd' if file_ext == '.xls' else 'openpyxl'
            try:
                # For large files, use optimized loading
                df = pd.read_excel(file_path, engine=engine, low_memory=False)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Error loading Excel file with engine {engine}: {e}")
                # Fallback: try without engine specification
                df = pd.read_excel(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")
        
        # Clean DataFrame
        df = df.dropna(how='all').dropna(axis=1, how='all').reset_index(drop=True)
        
        # Store DataFrame
        self.dataframes[file_id] = df
        
        # Register schema
        self._register_schema(file_id, df, file_path)
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Loaded file: {file_id} ({len(df)} rows, {len(df.columns)} columns)")
        return file_id, df
    
    def load_all_sheets(self, file_path: str, base_file_id: Optional[str] = None) -> Dict[str, pd.DataFrame]:
        """
        Load all sheets from an Excel file.
        
        Args:
            file_path: Path to the Excel file
            base_file_id: Optional base identifier
            
        Returns:
            Dictionary mapping sheet names to DataFrames
        """
        file_path_obj = Path(file_path)
        if base_file_id is None:
            base_file_id = file_path_obj.stem
        
        file_ext = file_path_obj.suffix.lower()
        if file_ext not in ['.xlsx', '.xls', '.xlsm', '.xlsb']:
            raise ValueError(f"Cannot load multiple sheets from {file_ext} file")
        
        engine = 'xlrd' if file_ext == '.xls' else 'openpyxl'
        excel_file = pd.ExcelFile(file_path, engine=engine)
        
        sheets_dict = {}
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            df = df.dropna(how='all').dropna(axis=1, how='all').reset_index(drop=True)
            
            file_id = f"{base_file_id}_{sheet_name}"
            self.dataframes[file_id] = df
            self._register_schema(file_id, df, file_path, sheet_name=sheet_name)
            sheets_dict[sheet_name] = df
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Loaded sheet: {file_id} ({len(df)} rows, {len(df.columns)} columns)")
        
        return sheets_dict
    
    def _register_schema(self, file_id: str, df: pd.DataFrame, file_path: str, sheet_name: Optional[str] = None):
        """
        Register schema metadata for a DataFrame.
        
        Args:
            file_id: File identifier
            df: DataFrame
            file_path: Original file path
            sheet_name: Optional sheet name
        """
        schema = {
            'file_id': file_id,
            'file_path': str(file_path),
            'sheet_name': sheet_name,
            'row_count': len(df),
            'column_count': len(df.columns),
            'columns': {},
            'sample_values': {},
            'data_types': {},
            'loaded_at': datetime.now().isoformat()
        }
        
        # Extract column information
        for col in df.columns:
            schema['columns'][col] = {
                'name': col,
                'dtype': str(df[col].dtype),
                'non_null_count': df[col].notna().sum(),
                'null_count': df[col].isna().sum(),
                'unique_count': df[col].nunique()
            }
            
            # Sample values (first 5 non-null values)
            sample = df[col].dropna().head(5).tolist()
            schema['sample_values'][col] = sample
            
            # Data type
            schema['data_types'][col] = str(df[col].dtype)
        
        self.schemas[file_id] = schema
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Registered schema for {file_id}: {len(df.columns)} columns")
    
    def get_dataframe(self, file_id: str) -> Optional[pd.DataFrame]:
        """Get a DataFrame by file_id."""
        return self.dataframes.get(file_id)
    
    def get_schema(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get schema metadata for a file."""
        return self.schemas.get(file_id)
    
    def get_all_file_ids(self) -> List[str]:
        """Get list of all loaded file IDs."""
        return list(self.dataframes.keys())
    
    def get_column_names(self, file_id: Optional[str] = None) -> List[str]:
        """
        Get column names for a file or all files.
        
        Args:
            file_id: Optional file ID. If None, returns columns from all files.
        """
        if file_id:
            if file_id in self.dataframes:
                return list(self.dataframes[file_id].columns)
            return []
        else:
            # Return unique column names from all files
            all_columns = set()
            for df in self.dataframes.values():
                all_columns.update(df.columns)
            return sorted(list(all_columns))
    
    def clear_data(self, file_id: Optional[str] = None):
        """
        Clear data for a specific file or all files.
        
        Args:
            file_id: Optional file ID. If None, clears all data.
        """
        if file_id:
            if file_id in self.dataframes:
                del self.dataframes[file_id]
            if file_id in self.schemas:
                del self.schemas[file_id]
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Cleared data for {file_id}")
        else:
            self.dataframes.clear()
            self.schemas.clear()
            import logging
            logger = logging.getLogger(__name__)
            logger.info("Cleared all data")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about loaded data."""
        total_rows = sum(len(df) for df in self.dataframes.values())
        total_files = len(self.dataframes)
        
        return {
            'total_files': total_files,
            'total_rows': total_rows,
            'file_ids': list(self.dataframes.keys()),
            'schemas': {fid: {
                'row_count': schema['row_count'],
                'column_count': schema['column_count'],
                'columns': list(schema['columns'].keys())
            } for fid, schema in self.schemas.items()}
        }
