"""
Flask Backend API for Excel/CSV RAG Chatbot
Provides REST API endpoints for chatbot integration
"""

from flask import Flask, request, jsonify, send_file, render_template, send_from_directory
from flask_cors import CORS
import os
import json
import logging
from pathlib import Path
from datetime import datetime
from excel_to_rag import ExcelToRAG
from rag_pipeline import RAGPipeline
from rag_ingestion import RAGIngestion
from query_driven_pipeline import QueryDrivenPipeline
import pandas as pd
import re
from difflib import SequenceMatcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', template_folder='templates')

# CORS Configuration - Security: Restrict origins in production
# Set ALLOWED_ORIGINS environment variable (comma-separated) to restrict access
# Default: "*" for development, should be restricted in production
allowed_origins = os.getenv('ALLOWED_ORIGINS', '*').split(',')
if allowed_origins == ['*']:
    # Development mode - allow all origins
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "DELETE", "PUT", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
else:
    # Production mode - restrict to specific origins
    CORS(app, resources={
        r"/api/*": {
            "origins": allowed_origins,
            "methods": ["GET", "POST", "DELETE", "PUT", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

# Global RAG system instances (legacy - for backward compatibility)
rag_system = None  # Legacy ExcelToRAG for backward compatibility
rag_pipeline = None  # New unified RAG pipeline
rag_ingestion = None  # Ingestion module

# Query-Driven Pipeline (primary system)
# Provides deterministic and verifiable answers through query execution
# Uses rule-based query engine with optional MiniLM assistance
query_pipeline = None  # Query-driven analytics pipeline

loaded_files = set()

def _get_valid_path(path_key: str, default_subdir: str) -> str:
    """
    Get a valid path for settings, creating directories if needed.
    
    Args:
        path_key: Environment variable key for the path
        default_subdir: Default subdirectory name if path doesn't exist
        
    Returns:
        Valid path string
    """
    # Try environment variable first
    env_path = os.getenv(path_key)
    if env_path and os.path.exists(os.path.dirname(env_path) if os.path.dirname(env_path) else env_path):
        return env_path
    
    # Try home directory
    try:
        home_dir = os.path.expanduser("~")
        if home_dir and os.path.exists(home_dir):
            default_path = os.path.join(home_dir, default_subdir)
            # Create directory if it doesn't exist
            os.makedirs(default_path, exist_ok=True)
            return default_path
    except Exception as e:
        logger.warning(f"Could not create path in home directory: {e}")
    
    # Fallback to current directory
    fallback_path = os.path.join(os.getcwd(), default_subdir)
    os.makedirs(fallback_path, exist_ok=True)
    logger.info(f"Using fallback path for {path_key}: {fallback_path}")
    return fallback_path

settings = {
    'download_path': _get_valid_path('DOWNLOAD_PATH', 'Downloads'),
    'files_folder_path': _get_valid_path('FILES_FOLDER_PATH', 'Documents')
}

# Maximum file size: 100MB (100 * 1024 * 1024 bytes)
# Can be overridden with MAX_FILE_SIZE environment variable
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', '104857600'))  # 100MB default
# Training data storage: {question: answer}
training_data = {}
TRAINING_DATA_FILE = "training_data.json"
# Edited answers storage: {question: answer}
edited_answers = {}
EDITED_ANSWERS_FILE = "edited_answers.json"

# Load settings from app_settings.json if it exists
def load_settings_from_file():
    """Load settings from app_settings.json file."""
    global settings
    settings_file = "app_settings.json"
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                file_settings = json.load(f)
                # Update settings with values from file, but keep defaults if keys are missing
                if 'download_path' in file_settings:
                    settings['download_path'] = file_settings['download_path']
                if 'files_folder_path' in file_settings:
                    settings['files_folder_path'] = file_settings['files_folder_path']
                logger.info(f"Loaded settings from {settings_file}")
                logger.info(f"Files folder path: {settings['files_folder_path']}")
                logger.info(f"Download path: {settings['download_path']}")
        except Exception as e:
            logger.warning(f"Error loading settings from {settings_file}: {e}")

# Load training data from file
def load_training_data():
    """Load training data from training_data.json file."""
    global training_data
    if os.path.exists(TRAINING_DATA_FILE):
        try:
            with open(TRAINING_DATA_FILE, 'r', encoding='utf-8') as f:
                training_data = json.load(f)
                logger.info(f"Loaded {len(training_data)} training entries from {TRAINING_DATA_FILE}")
        except Exception as e:
            logger.warning(f"Error loading training data from {TRAINING_DATA_FILE}: {e}")
            training_data = {}

# Save training data to file
def save_training_data():
    """Save training data to training_data.json file."""
    try:
        with open(TRAINING_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(training_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(training_data)} training entries to {TRAINING_DATA_FILE}")
        return True
    except Exception as e:
        logger.warning(f"Error saving training data to {TRAINING_DATA_FILE}: {e}")
        return False

# Load edited answers from file
def load_edited_answers():
    """Load edited answers from edited_answers.json file."""
    global edited_answers
    if os.path.exists(EDITED_ANSWERS_FILE):
        try:
            with open(EDITED_ANSWERS_FILE, 'r', encoding='utf-8') as f:
                edited_answers = json.load(f)
                logger.info(f"Loaded {len(edited_answers)} edited answers from {EDITED_ANSWERS_FILE}")
        except Exception as e:
            logger.warning(f"Error loading edited answers from {EDITED_ANSWERS_FILE}: {e}")
            edited_answers = {}

# Save edited answers to file
def save_edited_answers():
    """Save edited answers to edited_answers.json file."""
    try:
        with open(EDITED_ANSWERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(edited_answers, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(edited_answers)} edited answers to {EDITED_ANSWERS_FILE}")
        return True
    except Exception as e:
        logger.warning(f"Error saving edited answers to {EDITED_ANSWERS_FILE}: {e}")
        return False

# Load settings, training data, and edited answers on startup
load_settings_from_file()
load_training_data()
load_edited_answers()

# Load FAQs
# IMPORTANT: FAQs are static intent shortcuts, NOT stored answers.
# FAQs are data-agnostic and never change when data changes.
# When a user clicks an FAQ, it is treated as a query input and goes through
# the same query-driven pipeline as a typed question.
# FAQs represent user intent, not document-specific content.
# FAQs are NEVER retrained or regenerated when new data is uploaded.
def load_faqs():
    """
    Load FAQs from the code structure.
    
    Design Philosophy:
    - FAQs are static intent shortcuts, not stored answers
    - FAQs are data-agnostic (same for all users and datasets)
    - FAQ clicks go through the same query-driven pipeline as typed questions
    - FAQs remain static across all data versions
    - New data uploads do NOT regenerate or retrain FAQs
    - Answers come from querying actual data, not from FAQs
    """
    basic = [
        "What are all the column names in this dataset?",
        "How many records are present in the file?",
        "How many columns does this dataset contain?",
        "What is the overall structure and file format of this dataset?",
        "What are the data types of each column?",
        "Which columns contain numerical data?",
        "Which columns contain text data?",
        "Which columns contain date/time information?",
        "What date range is covered in this dataset?",
        "What is the earliest dispatch date in the dataset?",
        "What is the latest dispatch date in the dataset?",
        "Are there any missing or null values in this dataset?",
        "Which columns have missing values?",
        "How many missing values exist in each column?",
        "What is the unique count of consignment numbers?",
        "How many unique orders are there in the dataset?",
        "What are the unique source types available?",
        "What are the unique destination types available?",
        "What are the unique transportation modes available?",
        "What is the unique count of products in the dataset?",
        "How many unique customers are represented?",
        "What is the unique count of source locations?",
        "What is the unique count of destination locations?",
        "What units are used in this dataset?",
        "How many different plan names exist in the dataset?"
    ]
    
    intermediate = [
        "What is the total number of cases shipped across all consignments?",
        "What is the total transportation cost across all consignments?",
        "What is the total weight of all shipments?",
        "What is the average number of cases per consignment?",
        "What is the average transportation cost per consignment?",
        "What is the average weight per consignment?",
        "What is the average volume across all consignments?",
        "What is the minimum and maximum transportation cost observed?",
        "What is the minimum and maximum weight observed?",
        "What is the total consignment MRP value across all records?",
        "What is the average SKU weight?",
        "What is the average mode utilization percentage across all shipments?",
        "What are all unique source locations in the dataset?",
        "What are all unique destination locations in the dataset?",
        "What are all unique customers in the dataset?",
        "What are all unique products in the dataset?",
        "How many consignments use each transportation mode?",
        "How many consignments originate from each source location?",
        "How many consignments are delivered to each destination location?",
        "What is the total transportation cost by transportation mode?",
        "What is the total cases shipped by source location?",
        "What is the total cases shipped to each destination location?",
        "What is the average delivery time (days between dispatch and expected arrival)?",
        "How many consignments fall into each load type category?",
        "What is the total weight handled by each transportation mode?",
        "How many unique orders per source location?",
        "What is the distribution of consignments by source type?",
        "What is the distribution of consignments by destination type?",
        "What is the total volume by transportation mode?",
        "What is the average volume fill percentage across all shipments?"
    ]
    
    advanced = [
        "Which transportation mode has the highest average transportation cost?",
        "Which source location dispatches the most consignments?",
        "Which destination location receives the most consignments?",
        "Which source location has the highest total transportation cost?",
        "Which destination location has the highest total transportation cost?",
        "What is the cost per case for each consignment?",
        "What is the cost per kilogram for each consignment?",
        "What is the weight per case ratio for each product?",
        "Which product appears most frequently in the dataset?",
        "Which product has the highest average SKU weight?",
        "Which customer has the highest number of consignments?",
        "Which customer has the highest total transportation cost?",
        "Which source-destination route has the highest transportation cost?",
        "Which source-destination route has the most consignments?",
        "What is the average mode utilization percentage by transportation mode?",
        "Which transportation mode has the best weight fill percentage?",
        "Which transportation mode has the best volume fill percentage?",
        "How does average weight per consignment vary by transportation mode?",
        "How does average volume per consignment vary by transportation mode?",
        "Which routes (source-destination pairs) are most frequently used?",
        "What is the average delivery window (expected arrival date - dispatch date)?",
        "Which transportation mode has the longest average delivery time?",
        "Which transportation mode has the shortest average delivery time?",
        "Which customer receives consignments from multiple source locations?",
        "Which source location supplies multiple destination locations?",
        "What is the cost efficiency (cost per unit weight) by transportation mode?",
        "What is the volume utilization by transportation mode?",
        "Which orders contain the most cases?",
        "What is the average consignment MRP value by customer?",
        "How does the number of cases relate to transportation mode selection?"
    ]
    
    operational = [
        "Which consignments have actual or potential delivery delays?",
        "Which consignments have a dispatch date after the expected delivery date?",
        "Are there any unusually high transportation costs compared to weight/volume?",
        "Which shipments have low weight fill percentages (indicating inefficiency)?",
        "Which shipments have low volume fill percentages (indicating inefficiency)?",
        "Which routes have consistently low utilization rates?",
        "Which transportation modes are underutilized in this dataset?",
        "Are there any outliers in the cost per case metric?",
        "Which consignments exceed capacity thresholds for their mode?",
        "What percentage of consignments achieve optimal weight fill (above threshold)?",
        "What percentage of consignments achieve optimal volume fill (above threshold)?",
        "Which source locations have the highest operational costs?",
        "Which destination locations have the highest operational costs?",
        "Are there any products with inconsistent case counts across similar shipments?",
        "Which transportation modes are most frequently used vs. available capacity?"
    ]
    
    return {
        'basic': basic,
        'intermediate': intermediate,
        'advanced': advanced,
        'operational': operational,
        'all': basic + intermediate + advanced + operational
    }

FAQS = load_faqs()

# Out-of-scope keywords - expanded list
OUT_OF_SCOPE_KEYWORDS = [
    'my name', 'who am i', 'what is my name', 'who is vishal', 'who created',
    'developer', 'programmer', 'author', 'creator', 'who made', 'who built',
    'personal', 'about me', 'tell me about yourself', 'who are you',
    'your name', 'chatbot name', 'assistant name', 'what is your name',
    'who developed', 'who programmed', 'who designed', 'who coded',
    'about the developer', 'about the creator', 'about the author',
    'personal information', 'my personal', 'my details', 'my info'
]

# Cache for file columns to avoid repeated queries
_file_columns_cache = None
_file_columns_cache_time = None

def get_file_columns():
    """Get column names from the processed files (cached for performance)."""
    global _file_columns_cache, _file_columns_cache_time
    
    if not rag_system or len(loaded_files) == 0:
        _file_columns_cache = []
        return []
    
    # Return cached result if available (cache for 60 seconds)
    import time
    current_time = time.time()
    if _file_columns_cache is not None and _file_columns_cache_time is not None:
        if current_time - _file_columns_cache_time < 60:
            return _file_columns_cache
    
    try:
        # Query for column information
        results = rag_system.query("column names", n_results=3)
        columns = []
        
        # Try to extract column names from results
        for result in results:
            content = result.get('content', '')
            # Look for common patterns in column information
            if 'column' in content.lower() or 'header' in content.lower():
                # Try to extract column names from the content
                lines = content.split('\n')
                for line in lines:
                    if '|' in line:
                        parts = [p.strip() for p in line.split('|')]
                        columns.extend([p for p in parts if p and len(p) > 1 and p.lower() not in ['column name', 'header', '---', '']])
        
        # If we found columns, cache them
        if columns:
            _file_columns_cache = list(set(columns))
            _file_columns_cache_time = current_time
            return _file_columns_cache
        
        # Fallback: return common logistics columns if data exists
        # This is a safe assumption for logistics files
        common_columns = [
            'consignment', 'consignment number', 'order', 'product', 
            'source', 'destination', 'transportation', 'cost', 'weight',
            'volume', 'customer', 'load type', 'mode', 'mrp', 'cases',
            'transportation cost', 'mrp value', 'weight fill', 'volume fill'
        ]
        _file_columns_cache = common_columns
        _file_columns_cache_time = current_time
        return _file_columns_cache
        
    except Exception as e:
        print(f"Error getting file columns: {e}")
        return []

def is_out_of_scope(query):
    """Check if query is out of scope with better detection."""
    query_lower = query.lower().strip()
    
    # Check for exact keyword matches (personal questions)
    if any(keyword in query_lower for keyword in OUT_OF_SCOPE_KEYWORDS):
        return True
    
    # Get file columns to check against
    file_columns = get_file_columns()
    
    # Check for "what is [something]" patterns
    if query_lower.startswith('what is ') or query_lower.startswith('what\'s '):
        # Extract the subject
        subject = query_lower.split('is ', 1)[-1] if 'is ' in query_lower else query_lower.split('\'s ', 1)[-1]
        subject = subject.strip().rstrip('?').strip()
        
        # Check if subject is a file column (data-related question)
        subject_lower = subject.lower()
        is_file_column = False
        
        # Check against known file columns
        if file_columns:
            for col in file_columns:
                if subject_lower in col.lower() or col.lower() in subject_lower:
                    is_file_column = True
                    break
        
        # Also check against common logistics terms that might be in the file
        logistics_terms = [
            'consignment', 'consignments', 'transportation', 'cost', 'weight', 
            'volume', 'product', 'products', 'customer', 'customers', 'source',
            'destination', 'load type', 'mode', 'mrp', 'cases', 'order', 'orders',
            'shipment', 'shipments', 'utilization', 'fill percentage'
        ]
        
        if not is_file_column:
            # Check if it's a logistics term (might be asking about data)
            is_logistics_term = False
            for term in logistics_terms:
                if term in subject_lower:
                    # This could be asking about data, not definition
                    # We'll let it through but check results quality later
                    is_logistics_term = True
                    break
            
            if not is_logistics_term:
                # If not a file column or logistics term, likely general knowledge
                # Common general knowledge subjects
                general_knowledge_indicators = [
                    'chennai', 'mumbai', 'delhi', 'bangalore', 'hyderabad', 'kolkata', 'pune',
                    'city', 'cities', 'country', 'countries', 'state', 'states',
                    'capital', 'population', 'language', 'currency', 'president', 'prime minister',
                    'ocean', 'mountain', 'river', 'planet', 'star', 'atom', 'molecule', 'element',
                    'definition', 'meaning', 'explain', 'describe', 'tell me about',
                    'india', 'usa', 'uk', 'china', 'japan', 'germany', 'france'
                ]
                
                if any(indicator in subject_lower for indicator in general_knowledge_indicators):
                    return True
                
                # Check for common names (personal questions)
                common_names = ['vishal', 'john', 'mike', 'sarah', 'david', 'emily', 'alex', 'chris', 'raj', 'priya']
                if any(name in subject_lower for name in common_names):
                    return True
                
                # If it's a single word and not a logistics term, likely asking for definition
                if len(subject.split()) == 1 and subject_lower not in ['data', 'file', 'row', 'column']:
                    # Single word questions like "what is apple" are likely general knowledge
                    # unless it's clearly a logistics term
                    return True
    
    # Check for "who is" patterns (usually personal/general knowledge)
    if query_lower.startswith('who is '):
        subject = query_lower.split('is ', 1)[-1].strip().rstrip('?').strip()
        subject_lower = subject.lower()
        
        # Check if it's asking about a file column (unlikely but possible)
        file_columns = get_file_columns()
        is_file_column = False
        if file_columns:
            for col in file_columns:
                if subject_lower in col.lower():
                    is_file_column = True
                    break
        
        if not is_file_column:
            return True  # "who is" questions are usually out of scope
    
    # Check for general knowledge question patterns
    general_patterns = [
        'tell me about', 'explain', 'describe', 'what does', 'how does',
        'where is', 'when was', 'why is', 'who created', 'who made'
    ]
    
    # But exclude if it's clearly about file data
    if any(pattern in query_lower for pattern in general_patterns):
        # Check if it contains file-related terms
        file_terms = ['in this file', 'in the file', 'in your data', 'from the data', 
                      'in the dataset', 'in my file', 'column', 'row', 'data']
        if not any(term in query_lower for term in file_terms):
            # Likely general knowledge question
            return True
    
    return False

def get_suggested_questions(query, max_suggestions=5):
    """
    Get suggested questions based on current query with better matching.
    
    Uses rule-based scoring (primary) with optional MiniLM similarity (secondary).
    MiniLM is used only for semantic similarity scoring, not for generating suggestions.
    """
    query_lower = query.lower()
    suggestions = []
    scored_suggestions = []
    
    # Extract key terms from query
    query_words = set([w for w in query_lower.split() if len(w) > 3])
    
    # Score each FAQ based on relevance
    for faq in FAQS['all']:
        faq_lower = faq.lower()
        score = 0
        
        # Word overlap score
        faq_words = set([w for w in faq_lower.split() if len(w) > 3])
        common_words = query_words.intersection(faq_words)
        score += len(common_words) * 10
        
        # Phrase matching (higher score)
        for word in query_words:
            if word in faq_lower:
                # Check if it's at the beginning (higher relevance)
                if faq_lower.find(word) < 20:
                    score += 15
                else:
                    score += 5
        
        # Enhanced semantic similarity for key terms (expanded list)
        key_terms = ['cost', 'price', 'money', 'rupee', 'transportation cost',
                     'weight', 'kg', 'kilogram', 'ton', 'tonne',
                     'volume', 'cubic', 'fill',
                     'consignment', 'consignments', 'order', 'orders',
                     'transportation', 'mode', 'vehicle', 'truck',
                     'destination', 'source', 'location', 'locations',
                     'product', 'products', 'customer', 'customers',
                     'utilization', 'percentage', 'fill',
                     'cases', 'case', 'mrp', 'value',
                     'dispatch', 'arrival', 'date', 'dates',
                     'missing', 'null', 'empty', 'data type', 'types']
        for term in key_terms:
            if term in query_lower and term in faq_lower:
                score += 25  # Increased weight for keyword matches
        
        # Also match partial keywords (e.g., "weight" matches "weight per case")
        for term in key_terms:
            if term in query_lower:
                # Check if FAQ contains related terms
                related_terms = {
                    'weight': ['weight', 'kg', 'kilogram', 'ton'],
                    'cost': ['cost', 'price', 'rupee', 'transportation'],
                    'volume': ['volume', 'cubic', 'fill'],
                    'product': ['product', 'items'],
                    'customer': ['customer', 'clients'],
                    'consignment': ['consignment', 'order', 'shipment'],
                    'source': ['source', 'origin'],
                    'destination': ['destination', 'delivery'],
                    'mode': ['mode', 'transportation', 'vehicle', 'truck']
                }
                if term in related_terms:
                    for related in related_terms[term]:
                        if related in faq_lower:
                            score += 15
                            break
        
        if score > 0:
            scored_suggestions.append((score, faq))
    
    # Sort by score and get top suggestions
    scored_suggestions.sort(key=lambda x: x[0], reverse=True)
    suggestions = [faq for score, faq in scored_suggestions[:max_suggestions]]
    
    # If no matches, return some general ones based on query type (enhanced matching)
    if not suggestions:
        query_words_lower = set(query_lower.split())
        
        if any(word in query_words_lower for word in ['cost', 'price', 'money', 'rupee', 'transportation']):
            suggestions = [q for q in FAQS['all'] if any(t in q.lower() for t in ['cost', 'price', 'transportation'])][:max_suggestions]
        elif any(word in query_words_lower for word in ['weight', 'kg', 'kilogram', 'ton', 'tonne']):
            suggestions = [q for q in FAQS['all'] if 'weight' in q.lower()][:max_suggestions]
        elif any(word in query_words_lower for word in ['volume', 'cubic', 'fill']):
            suggestions = [q for q in FAQS['all'] if 'volume' in q.lower()][:max_suggestions]
        elif any(word in query_words_lower for word in ['consignment', 'order', 'shipment']):
            suggestions = [q for q in FAQS['all'] if any(t in q.lower() for t in ['consignment', 'order'])][:max_suggestions]
        elif any(word in query_words_lower for word in ['product', 'item', 'items']):
            suggestions = [q for q in FAQS['all'] if 'product' in q.lower()][:max_suggestions]
        elif any(word in query_words_lower for word in ['customer', 'client']):
            suggestions = [q for q in FAQS['all'] if 'customer' in q.lower()][:max_suggestions]
        elif any(word in query_words_lower for word in ['source', 'origin']):
            suggestions = [q for q in FAQS['all'] if 'source' in q.lower()][:max_suggestions]
        elif any(word in query_words_lower for word in ['destination', 'delivery']):
            suggestions = [q for q in FAQS['all'] if 'destination' in q.lower()][:max_suggestions]
        else:
            suggestions = FAQS['basic'][:max_suggestions]
    
    return suggestions

def get_auto_complete_suggestions(partial_query, max_suggestions=5):
    """
    Get auto-complete suggestions for partial query with smart matching.
    
    Uses rule-based matching (primary) with optional MiniLM similarity (secondary).
    MiniLM is used only for semantic similarity scoring, not for generating suggestions.
    """
    if not partial_query or len(partial_query) < 2:
        return []
    
    partial_lower = partial_query.lower().strip()
    scored_matches = []
    
    # Score matches based on relevance
    for faq in FAQS['all']:
        faq_lower = faq.lower()
        score = 0
        
        # Exact prefix match gets highest score
        if faq_lower.startswith(partial_lower):
            score = 100
            # Bonus for longer matches
            if len(partial_lower) > 5:
                score += 20
        # Contains at beginning gets high score
        elif faq_lower.find(partial_lower) < 10:
            score = 80
        # Contains anywhere gets medium score
        elif partial_lower in faq_lower:
            score = 50
        # Word-based matching - check if all words in partial query appear in FAQ
        else:
            partial_words = [w for w in partial_lower.split() if len(w) > 2]
            faq_words = set(faq_lower.split())
            matching_words = [w for w in partial_words if w in faq_words]
            if matching_words:
                # Higher score if more words match
                score = len(matching_words) * 15
                # Bonus if words are in order
                if len(matching_words) == len(partial_words):
                    score += 10
        
        # Enhanced keyword matching - expanded list with related terms
        key_terms_map = {
            'cost': ['cost', 'price', 'money', 'rupee', 'transportation cost', 'mrp', 'value'],
            'weight': ['weight', 'kg', 'kilogram', 'ton', 'tonne', 'weight per case'],
            'volume': ['volume', 'cubic', 'fill', 'volume fill', 'utilization'],
            'consignment': ['consignment', 'order', 'orders', 'shipment', 'shipments'],
            'transportation': ['transportation', 'mode', 'modes', 'vehicle', 'truck', 'transport'],
            'product': ['product', 'products', 'item', 'items', 'sku'],
            'customer': ['customer', 'customers', 'client', 'clients'],
            'source': ['source', 'sources', 'origin', 'origins', 'source location', 'source locations'],
            'destination': ['destination', 'destinations', 'delivery', 'destination location', 'destination locations'],
            'case': ['case', 'cases', 'no of cases', 'total cases'],
            'location': ['location', 'locations', 'source location', 'destination location']
        }
        
        # Check if query contains any keyword and FAQ contains related terms
        for keyword, related_terms in key_terms_map.items():
            if any(term in partial_lower for term in related_terms):
                if any(term in faq_lower for term in related_terms):
                    score += 25  # Higher score for keyword matches
                    break
        
        if score > 0:
            scored_matches.append((score, faq))
    
    # Sort by score and return top matches
    scored_matches.sort(key=lambda x: x[0], reverse=True)
    matches = [faq for score, faq in scored_matches[:max_suggestions]]
    
    return matches

def initialize_rag_system():
    """Initialize RAG system (legacy for backward compatibility)."""
    global rag_system
    try:
        db_path = os.path.join(os.getcwd(), 'chroma_db')
        rag_system = ExcelToRAG(
            embedding_model="all-MiniLM-L6-v2",
            db_path=db_path,
            collection_name="excel_data"
        )
        return True
    except Exception as e:
        print(f"Error initializing RAG system: {e}")
        return False

def initialize_rag_pipeline():
    """Initialize unified RAG pipeline."""
    global rag_pipeline, rag_ingestion
    try:
        db_path = os.path.join(os.getcwd(), 'chroma_db')
        rag_pipeline = RAGPipeline(
            embedding_model="all-MiniLM-L6-v2",
            db_path=db_path,
            collection_name="excel_data"
        )
        rag_ingestion = RAGIngestion(chunk_size=500, chunk_overlap=100)
        logger.info("Unified RAG pipeline initialized")
        return True
    except Exception as e:
        print(f"Error initializing RAG pipeline: {e}")
        return False

# Initialize RAG systems on startup
initialize_rag_system()  # Legacy system for backward compatibility
initialize_rag_pipeline()  # New unified pipeline

# Initialize Query-Driven Pipeline
def initialize_query_pipeline():
    """
    Initialize query-driven analytics pipeline.
    
    Provides deterministic and verifiable answers through query execution.
    Uses rule-based query engine with optional MiniLM assistance for intent matching.
    """
    global query_pipeline
    try:
        query_pipeline = QueryDrivenPipeline()
        logger.info("Query-driven analytics pipeline initialized")
        logger.info("Rule-based query engine (primary)")
        logger.info("Optional similarity matching for intent classification (secondary)")
        return True
    except Exception as e:
        print(f"Error initializing query-driven pipeline: {e}")
        return False

initialize_query_pipeline()

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'rag_initialized': rag_system is not None,
        'loaded_files_count': len(loaded_files)
    })

@app.route('/api/greet', methods=['GET'])
def greet():
    """Get greeting message with personalized suggestions."""
    # Check if data is loaded
    has_data = len(loaded_files) > 0 and rag_system is not None
    
    if has_data:
        # Try to get some basic info to personalize greeting
        try:
            # Get a sample query to check if data exists
            test_results = rag_system.query("column names", n_results=1)
            if test_results:
                greeting = "Hello! I'm your Data Assistant. I'm ready to help you analyze your data. What would you like to know?"
            else:
                greeting = "Hello! I can help you analyze your Excel/CSV files. Please upload a file to get started."
        except:
            greeting = "Hello! I can help you analyze your Excel/CSV files. Please upload a file to get started."
    else:
        greeting = "Hello! I can help you analyze your Excel/CSV files and answer questions about your data. Please upload a file to begin."
    
    # Get popular questions as suggestions
    popular_questions = [
        "What are all the column names in this file?",
        "How many consignments are there in total?",
        "What is the total transportation cost?",
        "What are all the source locations?",
        "What products are being shipped?"
    ]
    
    return jsonify({
        'message': greeting,
        'suggestions': popular_questions[:3],  # Changed from 4 to 3
        'show_faqs': True,
        'has_data': has_data
    })

def is_greeting(query):
    """Check if query is a greeting."""
    query_lower = query.lower().strip()
    
    # Common greetings
    greetings = [
        'hi', 'hello', 'hey', 'hi there', 'hello there', 'hey there',
        'good morning', 'good afternoon', 'good evening', 'good night',
        'greetings', 'howdy', 'what\'s up', 'whats up', 'sup',
        'good day', 'morning', 'afternoon', 'evening'
    ]
    
    # Check for exact matches or starts with greeting
    if query_lower in greetings:
        return True
    
    # Check if query starts with a greeting followed by optional punctuation
    for greeting in greetings:
        if query_lower.startswith(greeting):
            # Check if it's just the greeting or greeting + punctuation/whitespace
            remaining = query_lower[len(greeting):].strip()
            if not remaining or remaining in ['.', '!', '?', ',']:
                return True
    
    return False

@app.route('/api/query', methods=['POST'])
def query():
    """
    Handle query requests through query-driven pipeline.
    
    This endpoint processes:
    - User typed questions
    - FAQ clicks (treated as intent shortcuts)
    - All queries go through the same query-driven pipeline
    
    Design: 
    - FAQs = Intent Shortcuts (static, never change)
    - All answers come from actual data queries
    - SLM only formats the answer, never generates data
    """
    try:
        data = request.json
        query_text = data.get('query', '').strip()
        
        if not query_text:
            return jsonify({'error': 'Query is required'}), 400
        
        query_lower = query_text.lower().strip()
        
        # Step 1: Handle greetings first
        if is_greeting(query_text):
            has_data = query_pipeline and len(query_pipeline.data_loader.dataframes) > 0
            if has_data:
                greeting_response = "Hello! I'm your Data Assistant. I'm here to help you analyze your data. What would you like to know?\n\nYou can ask me about:\n• Consignments and shipments\n• Transportation costs and metrics\n• Products and customers\n• Source and destination locations\n• Weight, volume, and utilization statistics"
            else:
                greeting_response = "Hello! I can help you analyze your Excel/CSV files and answer questions about your data. Please upload a file to begin."
            
            return jsonify({
                'answer': greeting_response,
                'is_greeting': True,
                'suggestions': get_suggested_questions("logistics data", max_suggestions=3),
                'show_faqs': True,
                'timestamp': datetime.now().isoformat()
            })
        
        # Check if out of scope
        if is_out_of_scope(query_text):
            return jsonify({
                'answer': "I'm a Data Assistant, and I can only answer questions about the data in your uploaded Excel/CSV files. I don't have general knowledge or information about topics outside your file.\n\nPlease ask me questions about your data, such as:\n• What are all the column names in this file?\n• How many records are there in total?\n• What is the total cost?\n• What are all the source locations?\n• What products are being shipped?\n• Show me the first 5 rows of data",
                'is_out_of_scope': True,
                'suggestions': get_suggested_questions("logistics data", max_suggestions=3),
                'show_faqs': True,
                'ask_about_faqs': True,
                'timestamp': datetime.now().isoformat()
            })
        
        # Step 2: Check if query-driven pipeline is initialized
        if not query_pipeline:
            return jsonify({
                'error': 'Query pipeline not initialized',
                'answer': 'Please wait while the system initializes...'
            }), 503
        
        # Step 3: Check if files are loaded
        stats = query_pipeline.get_stats()
        total_files = stats.get('total_files', 0)
        
        if total_files == 0:
            error_msg = 'No files loaded. Please upload and process at least one Excel/CSV file first.'
            print(f"[Query] {error_msg}")
            return jsonify({
                'error': 'No files loaded',
                'answer': error_msg,
                'suggestions': ['Upload a file', 'View example questions'],
                'total_files': 0
            }), 400
        
        # Step 4: Process query through query-driven pipeline
        # CRITICAL: All queries (typed questions AND FAQ clicks) go through query-driven pipeline
        # FAQs = Intent Shortcuts (static, never change, data-agnostic)
        # All answers come from actual data queries (deterministic and verifiable)
        # MiniLM used only for intent matching and optional formatting, not answer generation
        try:
            logger.info(f"Processing query: {query_text}")
            
            # Process through query-driven pipeline
            result = query_pipeline.process_query(query_text)
            
            answer = result.get('answer', '')
            success = result.get('success', False)
            intent = result.get('intent', '')
            
            logger.info(f"Query processed: success={success}, intent={intent}")
            
            if not success:
                # Query failed - return error message
                return jsonify({
                    'answer': answer,
                    'success': False,
                    'suggestions': get_suggested_questions("logistics data", max_suggestions=3),
                    'show_faqs': True,
                    'timestamp': datetime.now().isoformat()
                })
            
            # Extract numeric value if applicable (for backward compatibility)
            numeric_value = None
            query_result = result.get('query_result', {})
            if query_result.get('result_type') == 'aggregation':
                numeric_value = query_result.get('value')
        
        except Exception as e:
            print(f"Error querying pipeline: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'error': str(e),
                'answer': f'I encountered an error processing your query: {str(e)}. Please make sure files are uploaded and processed.',
                'suggestions': get_suggested_questions(query_text, max_suggestions=3),
                'show_faqs': True,
                'timestamp': datetime.now().isoformat()
            }), 500
        
        # Step 5: Get follow-up suggestions
        suggestions = get_suggested_questions(query_text, max_suggestions=5)
        follow_up_message = None
        if suggestions:
            follow_up_message = "Would you like to explore related questions? Here are some suggestions:"
        
        # Step 6: Return response
        return jsonify({
            'answer': answer,
            'numeric_value': numeric_value,
            'suggestions': suggestions,
            'show_faqs': True,
            'ask_about_faqs': True,
            'follow_up_message': follow_up_message,
            'timestamp': datetime.now().isoformat(),
            'intent': intent if 'intent' in locals() else None
        })
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"ERROR in /api/query: {str(e)}")
        print(f"Traceback: {error_trace}")
        return jsonify({
            'error': str(e),
            'answer': f'I encountered an error processing your query: {str(e)}. Please make sure files are uploaded and processed.',
            'traceback': error_trace
        }), 500

def format_answer(query, results, numeric_value):
    """Format the answer from results."""
    if not results:
        return "I couldn't find relevant information for your query. Please try rephrasing or ask about specific data in your file."
    
    answer_parts = []
    
    # Add numeric value if found and relevant - ensure proper formatting
    if numeric_value is not None:
        # Check if numeric value makes sense for this query
        query_lower = query.lower()
        
        # Don't show numeric value for list queries
        is_list_query = any(phrase in query_lower for phrase in [
            'what are all', 'what are the', 'list', 'show me', 'all the', 
            'different', 'unique', 'column names', 'column name',
            'source locations', 'destination locations', 'products',
            'transportation modes', 'load types', 'customers',
            'consignment numbers', 'dates', 'date range', 'names'
        ])
        
        if not is_list_query:
            # Format numeric value properly
            if isinstance(numeric_value, (int, float)):
                # Remove trailing .0 for whole numbers
                if isinstance(numeric_value, float) and numeric_value.is_integer():
                    numeric_str = str(int(numeric_value))
                else:
                    numeric_str = str(numeric_value)
            else:
                numeric_str = str(numeric_value)
            
            answer_parts.append(f"**Answer:** {numeric_str}")
            answer_parts.append("")
    
    # Add relevant results
    answer_parts.append("**Details:**")
    answer_parts.append("")
    
    for i, result in enumerate(results[:3], 1):
        content = result.get('content', '').strip()
        if content:
            # Clean up content thoroughly
            content = clean_markdown_content(content)
            
            # Remove any remaining artifacts or malformed content
            # Remove content that looks like concatenated text without spaces
            content = re.sub(r'(\d+\.?\d*)([a-zA-Z])', r'\1 \2', content)  # Add space between number and letter
            content = re.sub(r'([a-zA-Z])(\d+\.?\d*)', r'\1 \2', content)  # Add space between letter and number
            
            # Remove any random text that doesn't belong (like "bro how are you")
            # This is a heuristic - remove lines that are clearly not data-related
            lines = content.split('\n')
            cleaned_lines = []
            for line in lines:
                line = line.strip()
                if not line:
                    cleaned_lines.append('')
                    continue
                
                # Skip empty table rows (just separators)
                if line == '|||' or line == '|' or (line.startswith('|') and line.endswith('|') and len(line.split('|')) <= 3):
                    continue
                
                # Skip lines that are clearly not data-related (greetings, random text)
                line_lower = line.lower()
                skip_patterns = [
                    r'^(hi|hello|hey|bro|dude|man)\s+',
                    r'\b(how are you|what\'?s up|sup|wassup)\b',
                    r'^(thanks|thank you|thx)',
                    r'^(ok|okay|alright|sure|yeah|yes|no)\s*$'
                ]
                should_skip = False
                for pattern in skip_patterns:
                    if re.search(pattern, line_lower):
                        should_skip = True
                        break
                
                if not should_skip:
                    cleaned_lines.append(line)
            
            content = '\n'.join(cleaned_lines).strip()
            
            # Only add if content is meaningful (not empty or just whitespace)
            if content and len(content) > 5:
                answer_parts.append(content)
                if i < min(3, len(results)):
                    answer_parts.append("")
    
    # Join and clean up final answer
    final_answer = "\n".join(answer_parts).strip()
    
    # Final cleanup - remove duplicate headers, empty rows, fix formatting
    final_answer = remove_duplicate_headers(final_answer)
    final_answer = re.sub(r' {2,}', ' ', final_answer)  # Multiple spaces to single
    final_answer = re.sub(r'\n{3,}', '\n\n', final_answer)  # Multiple newlines to double
    
    return final_answer

def clean_markdown_content(content):
    """Clean markdown content for display."""
    if not content:
        return ""
    
    # Convert to string if not already
    content = str(content)
    
    # Remove excessive separators
    content = re.sub(r'-{3,}', '', content)
    content = re.sub(r'={3,}', '', content)
    
    # Remove numpy type annotations - match np.float64(value), np.int64(value), etc.
    # Pattern: np.type(value) -> value
    # Handle common numpy types first
    content = re.sub(r'np\.float64\(([^)]+)\)', r'\1', content)
    content = re.sub(r'np\.int64\(([^)]+)\)', r'\1', content)
    content = re.sub(r'np\.float32\(([^)]+)\)', r'\1', content)
    content = re.sub(r'np\.int32\(([^)]+)\)', r'\1', content)
    content = re.sub(r'np\.float\(([^)]+)\)', r'\1', content)
    content = re.sub(r'np\.int\(([^)]+)\)', r'\1', content)
    # Generic numpy type removal (catches any remaining np.type(value) patterns)
    content = re.sub(r'np\.\w+\(([^)]+)\)', r'\1', content)
    
    # Fix spacing issues - add space between numbers and letters
    content = re.sub(r'(\d+\.?\d*)([a-zA-Z])', r'\1 \2', content)
    content = re.sub(r'([a-zA-Z])(\d+\.?\d*)', r'\1 \2', content)
    
    # Remove random text artifacts (greetings, casual text that shouldn't be in data)
    lines = content.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            cleaned_lines.append('')
            continue
        
        # Skip empty table rows (just separators or pipes)
        if line == '|||' or line == '|' or (line.startswith('|') and line.endswith('|') and len([p for p in line.split('|') if p.strip()]) <= 1):
            continue
        
        # Skip lines that are clearly not data-related
        line_lower = line.lower()
        skip_patterns = [
            r'^(hi|hello|hey|bro|dude|man|sup)\s+',
            r'\b(how are you|what\'?s up|wassup|how\'?s it going)\b',
            r'^(thanks|thank you|thx|ty)\s*',
            r'^(ok|okay|alright|sure|yeah|yes|no|yep|nope)\s*$',
            r'^(lol|haha|hehe|lmao)',
            r'^\W+$'  # Lines that are only punctuation/symbols
        ]
        
        should_skip = False
        for pattern in skip_patterns:
            if re.search(pattern, line_lower):
                should_skip = True
                break
        
        if not should_skip:
            # Clean up the line
            # Remove excessive spaces
            line = re.sub(r' {2,}', ' ', line)
            # Fix tab-separated values
            if '\t' in line and 'np.' in line:
                parts = line.split('\t')
                cleaned_parts = []
                for part in parts:
                    cleaned_part = re.sub(r'np\.\w+\(([^)]+)\)', r'\1', part)
                    cleaned_parts.append(cleaned_part)
                line = '\t'.join(cleaned_parts)
            
            cleaned_lines.append(line)
    
    content = '\n'.join(cleaned_lines)
    
    # Clean up trailing zeros in decimal numbers (e.g., 25.0 -> 25, 10.5 -> 10.5)
    # But preserve scientific notation
    def clean_decimal(match):
        num = match.group(0)
        if '.' in num and 'e' not in num.lower():
            # Remove trailing zeros and decimal point if needed
            cleaned = num.rstrip('0').rstrip('.')
            return cleaned if cleaned else num
        return num
    
    # Clean decimals in tables and text
    content = re.sub(r'\b\d+\.\d+\b', clean_decimal, content)
    
    # Clean up extra whitespace and newlines
    content = re.sub(r' {2,}', ' ', content)  # Multiple spaces to single
    content = re.sub(r'\n{3,}', '\n\n', content)  # Multiple newlines to double
    content = re.sub(r'\t+', '\t', content)  # Multiple tabs to single
    
    # Remove leading/trailing whitespace from each line
    lines = content.split('\n')
    cleaned_lines = []
    for line in lines:
        cleaned_line = line.strip()
        # Skip lines that are just artifacts
        if cleaned_line and len(cleaned_line) > 2:
            cleaned_lines.append(cleaned_line)
        elif not cleaned_line:
            # Keep empty lines for spacing, but limit consecutive empty lines
            if not cleaned_lines or cleaned_lines[-1] != '':
                cleaned_lines.append('')
    
    content = '\n'.join(cleaned_lines)
    
    return content.strip()

def remove_duplicate_headers(content):
    """Remove duplicate section headers from content."""
    if not content:
        return content
    
    lines = content.split('\n')
    cleaned = []
    seen_headers = {}
    last_header_line = -10  # Track position of last header
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        # Check if this is a header (starts with # or is "Column Information", etc.)
        is_header = False
        header_key = None
        
        if line_stripped.startswith('#'):
            # Markdown header
            header_key = line_stripped.lower()
            is_header = True
        elif line_stripped.lower() in ['column information', 'description', 'details', 'data preview', 'complete data', 'row-by-row data', 'numeric summary statistics', 'complete table view']:
            # Common section headers
            header_key = line_stripped.lower()
            is_header = True
        
        if is_header and header_key:
            # Check if we've seen this header recently (within last 5 lines)
            if header_key in seen_headers and (i - seen_headers[header_key]) < 5:
                # Skip duplicate header that's too close
                continue
            seen_headers[header_key] = i
            last_header_line = i
        
        # Reset header tracking if we've moved far from headers
        if not is_header and line_stripped and (i - last_header_line) > 10:
            # Clear old header tracking
            seen_headers = {}
        
        cleaned.append(line)
    
    # Also remove consecutive duplicate headers
    final_cleaned = []
    prev_header = None
    for line in cleaned:
        line_stripped = line.strip().lower()
        if line_stripped in ['column information', 'description'] and prev_header == line_stripped:
            continue  # Skip consecutive duplicate
        if line_stripped in ['column information', 'description']:
            prev_header = line_stripped
        else:
            prev_header = None
        final_cleaned.append(line)
    
    return '\n'.join(final_cleaned)

@app.route('/api/autocomplete', methods=['POST'])
def autocomplete():
    """
    Get auto-complete suggestions.
    
    Uses rule-based matching with optional MiniLM semantic similarity.
    MiniLM is used only for similarity scoring, not for generating suggestions.
    """
    try:
        data = request.json
        partial_query = data.get('query', '').strip()
        
        suggestions = get_auto_complete_suggestions(partial_query, max_suggestions=5)
        
        return jsonify({
            'suggestions': suggestions
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/faqs', methods=['GET'])
def get_faqs():
    """Get all FAQs."""
    return jsonify(FAQS)

@app.route('/api/files/list', methods=['POST'])
def list_files():
    """List files in the specified folder."""
    try:
        data = request.json
        folder_path = data.get('folder_path', '')
        
        if not folder_path:
            folder_path = settings.get('files_folder_path', os.path.join(os.path.expanduser("~"), "Documents"))
        
        if not os.path.exists(folder_path):
            return jsonify({
                'error': f'Folder does not exist: {folder_path}',
                'files': []
            }), 400
        
        # Find all Excel and CSV files
        excel_extensions = ('.xlsx', '.xls', '.xlsm', '.xlsb', '.csv')
        files = []
        
        try:
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                if os.path.isfile(file_path) and filename.lower().endswith(excel_extensions):
                    is_loaded = file_path in loaded_files
                    files.append({
                        'filename': filename,
                        'path': file_path,
                        'loaded': is_loaded,
                        'size': os.path.getsize(file_path)
                    })
        except Exception as e:
            return jsonify({
                'error': f'Error reading folder: {str(e)}',
                'files': []
            }), 500
        
        # Sort by filename
        files.sort(key=lambda x: x['filename'])
        
        return jsonify({
            'files': files,
            'folder_path': folder_path,
            'total': len(files)
        })
        
    except Exception as e:
        return jsonify({'error': str(e), 'files': []}), 500

@app.route('/api/files/process', methods=['POST'])
def process_files():
    """
    Process selected files using query-driven pipeline.
    
    New data loading workflow:
    1. Accept documents (Excel/CSV)
    2. Load into Pandas DataFrames
    3. Register schema metadata
    4. Data ready for querying
    
    IMPORTANT: 
    - FAQs are static intent shortcuts (never change)
    - All answers come from actual data queries
    - No embeddings, no vector DB - just structured data
    """
    try:
        data = request.json
        file_paths = data.get('file_paths', [])
        process_all_sheets = data.get('process_all_sheets', True)
        
        if not file_paths:
            return jsonify({'error': 'No files selected'}), 400
        
        if not query_pipeline:
            return jsonify({'error': 'Query pipeline not initialized'}), 503
        
        results = []
        total_processed = 0
        
        for file_path in file_paths:
            try:
                # Validate and sanitize file path
                if not file_path or not isinstance(file_path, str):
                    results.append({
                        'file': 'unknown',
                        'status': 'error',
                        'message': 'Invalid file path provided'
                    })
                    continue
                
                # Prevent path traversal attacks
                file_path = os.path.normpath(file_path)
                if '..' in file_path or file_path.startswith('/'):
                    # Only allow relative paths in allowed directories
                    if not any(file_path.startswith(allowed_dir) for allowed_dir in [settings.get('files_folder_path', ''), os.getcwd()]):
                        results.append({
                            'file': os.path.basename(file_path),
                            'status': 'error',
                            'message': 'Invalid file path: path traversal not allowed'
                        })
                        continue
                
                if not os.path.exists(file_path):
                    results.append({
                        'file': os.path.basename(file_path),
                        'status': 'error',
                        'message': f'File not found: {file_path}'
                    })
                    continue
                
                if not os.path.isfile(file_path):
                    results.append({
                        'file': os.path.basename(file_path),
                        'status': 'error',
                        'message': 'Path is not a file'
                    })
                    continue
                
                # Check file size before processing
                try:
                    file_size = os.path.getsize(file_path)
                    if file_size > MAX_FILE_SIZE:
                        size_mb = MAX_FILE_SIZE / (1024 * 1024)
                        results.append({
                            'file': os.path.basename(file_path),
                            'status': 'error',
                            'message': f'File size ({file_size / (1024*1024):.2f}MB) exceeds maximum allowed size of {size_mb}MB'
                        })
                        continue
                except OSError as e:
                    results.append({
                        'file': os.path.basename(file_path),
                        'status': 'error',
                        'message': f'Cannot access file: {str(e)}'
                    })
                    continue
                
                filename = os.path.basename(file_path)
                
                # Load file into query-driven pipeline
                logger.info(f"Loading file: {filename}")
                load_result = query_pipeline.load_file(
                    file_path, 
                    file_id=None,  # Auto-generate from filename
                    process_all_sheets=process_all_sheets
                )
                
                if load_result.get('success'):
                    loaded_files.add(file_path)
                    total_processed += 1
                    
                    # Get file info
                    file_ids = load_result.get('file_ids', [load_result.get('file_id')])
                    rows = load_result.get('rows', 0)
                    columns = load_result.get('columns', 0)
                    
                    results.append({
                        'file': filename,
                        'status': 'success',
                        'message': load_result.get('message', 'Loaded successfully'),
                        'rows': rows,
                        'columns': columns,
                        'file_ids': file_ids
                    })
                    logger.info(f"Loaded {filename}: {rows} rows, {columns} columns")
                else:
                    error_msg = load_result.get('error', 'Unknown error')
                    results.append({
                        'file': filename,
                        'status': 'error',
                        'message': error_msg
                    })
                    logger.error(f"Error loading {filename}: {error_msg}")
                
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                error_msg = str(e)
                logger.error(f"ERROR processing {os.path.basename(file_path)}: {error_msg}")
                logger.debug(f"Traceback: {error_trace}")
                results.append({
                    'file': os.path.basename(file_path),
                    'status': 'error',
                    'message': error_msg,
                    'traceback': error_trace
                })
        
        return jsonify({
            'message': f'Processed {total_processed}/{len(file_paths)} files',
            'results': results,
            'total_processed': total_processed,
            'success': total_processed > 0
        })
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"CRITICAL ERROR in process_files endpoint: {str(e)}")
        logger.debug(f"Traceback: {error_trace}")
        return jsonify({
            'error': str(e),
            'traceback': error_trace,
            'results': [],
            'total_processed': 0
        }), 500

@app.route('/api/clear-database', methods=['POST', 'GET'])
def clear_database():
    """
    Clear the vector database and query pipeline data to start fresh.
    Use this when you want to remove all old data and start with new files only.
    
    Supports both POST and GET methods for easy access.
    """
    try:
        if not rag_pipeline:
            return jsonify({'error': 'RAG pipeline not initialized'}), 503
        
        # Get stats before clearing
        try:
            stats_before = rag_pipeline.get_stats()
            total_before = stats_before.get('total_chunks', 0)
        except Exception:
            total_before = 'N/A'
        
        success = rag_pipeline.retrieval.clear_collection()
        if success:
            # Also clear loaded_files tracking
            global loaded_files
            loaded_files.clear()
            
            # Clear query pipeline data as well
            if query_pipeline:
                try:
                    query_pipeline.clear_data()
                    logger.info("Cleared query pipeline data")
                except Exception as e:
                    logger.warning(f"Error clearing query pipeline data: {e}")
            
            logger.info(f"Database cleared successfully. Removed {total_before} chunks.")
            return jsonify({
                'message': 'Vector database and query pipeline cleared successfully. You can now upload new files.',
                'success': True,
                'total_chunks_before': total_before,
                'total_chunks_after': 0
            })
        else:
            return jsonify({'error': 'Failed to clear database'}), 500
    except Exception as e:
        logger.error(f"Error clearing database: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/database-stats', methods=['GET'])
def database_stats():
    """Get database statistics to diagnose issues."""
    try:
        if not rag_pipeline:
            return jsonify({'error': 'RAG pipeline not initialized'}), 503
        
        stats = rag_pipeline.get_stats()
        
        # Also try to get a sample chunk to verify data is accessible
        sample_chunk = None
        try:
            all_data = rag_pipeline.retrieval.collection.get()
            if all_data['ids'] and len(all_data['ids']) > 0:
                # Get first chunk as sample
                sample_chunk = {
                    'id': all_data['ids'][0],
                    'content_preview': all_data['documents'][0][:200] if all_data['documents'] else None,
                    'metadata': all_data['metadatas'][0] if all_data['metadatas'] else None
                }
        except Exception as e:
            print(f"[Stats] Error getting sample chunk: {e}")
        
        # Test retrieval with a simple query
        retrieval_test = None
        try:
            test_query = "column names"
            test_embedding = rag_pipeline.embedding.embed_query(test_query)
            test_results = rag_pipeline.retrieval.retrieve(test_embedding, n_results=3)
            retrieval_test = {
                'query': test_query,
                'chunks_retrieved': len(test_results),
                'has_results': len(test_results) > 0
            }
        except Exception as e:
            print(f"[Stats] Error testing retrieval: {e}")
            retrieval_test = {'error': str(e)}
        
        return jsonify({
            'stats': stats,
            'loaded_files_count': len(loaded_files),
            'loaded_files': list(loaded_files),
            'sample_chunk': sample_chunk,
            'retrieval_test': retrieval_test
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file upload."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Check file size before saving
        # Read file content to check size (for in-memory files)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > MAX_FILE_SIZE:
            size_mb = MAX_FILE_SIZE / (1024 * 1024)
            return jsonify({
                'error': f'File size exceeds maximum allowed size of {size_mb}MB'
            }), 400
        
        # Validate file extension
        allowed_extensions = ('.xlsx', '.xls', '.xlsm', '.xlsb', '.csv')
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({
                'error': f'Invalid file type. Allowed types: {", ".join(allowed_extensions)}'
            }), 400
        
        # Check if processing is requested
        process_file = request.form.get('process', 'true').lower() == 'true'
        
        # Save file temporarily
        upload_dir = os.path.join(os.getcwd(), 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Sanitize filename to prevent path traversal
        safe_filename = os.path.basename(file.filename)
        file_path = os.path.join(upload_dir, safe_filename)
        file.save(file_path)
        
        result = {
            'message': f'File "{file.filename}" uploaded successfully!',
            'filename': file.filename,
            'file_path': file_path,
            'processed': False
        }
        
        # Process file if requested
        if process_file:
            if not rag_pipeline or not rag_ingestion:
                initialize_rag_pipeline()
            
            try:
                logger.info(f"Processing uploaded file: {file.filename}")
                # Use new ingestion pipeline
                df = rag_ingestion.read_excel_file(file_path)
                logger.info(f"Read DataFrame: {len(df)} rows, {len(df.columns)} columns")
                md_content = rag_ingestion.convert_dataframe_to_markdown(
                    df, metadata={'file_path': file_path, 'source': 'upload'}
                )
                chunks = rag_ingestion.chunk_markdown(md_content)
                logger.info(f"Created {len(chunks)} chunks")
                file_id = Path(file_path).stem
                rag_pipeline.ingest_document(chunks, file_id=file_id)
                logger.info(f"Stored {len(chunks)} chunks for {file.filename}")
                
                loaded_files.add(file_path)
                result['message'] = f'File "{file.filename}" uploaded and processed successfully!'
                result['processed'] = True
                result['chunks_created'] = len(chunks)
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                logger.error(f"ERROR processing uploaded file: {str(e)}")
                logger.debug(f"Traceback: {error_trace}")
                return jsonify({
                    'error': f'Error processing file: {str(e)}',
                    'traceback': error_trace
                }), 500
        
        return jsonify(result)
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"ERROR uploading file: {str(e)}")
        logger.debug(f"Traceback: {error_trace}")
        return jsonify({'error': str(e), 'traceback': error_trace}), 500

@app.route('/api/uploaded-files', methods=['GET'])
def list_uploaded_files():
    """List files in the uploads directory."""
    try:
        upload_dir = os.path.join(os.getcwd(), 'uploads')
        if not os.path.exists(upload_dir):
            return jsonify({'files': []})
        
        files = []
        for filename in os.listdir(upload_dir):
            file_path = os.path.join(upload_dir, filename)
            if os.path.isfile(file_path):
                # Check if it's a supported file type
                if filename.lower().endswith(('.xlsx', '.xls', '.csv', '.xlsm', '.xlsb')):
                    file_stat = os.stat(file_path)
                    files.append({
                        'filename': filename,
                        'path': file_path,
                        'size': file_stat.st_size,
                        'modified': datetime.fromtimestamp(file_stat.st_mtime).isoformat()
                    })
        
        return jsonify({'files': files})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings', methods=['GET', 'POST'])
def settings_endpoint():
    """Get or update settings."""
    if request.method == 'GET':
        return jsonify(settings)
    else:
        data = request.json
        settings.update(data)
        
        # Save settings to file
        try:
            settings_file = "app_settings.json"
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
            logger.info(f"Saved settings to {settings_file}")
        except Exception as e:
            logger.warning(f"Error saving settings to file: {e}")
        
        return jsonify({'message': 'Settings updated', 'settings': settings})

@app.route('/api/training', methods=['GET', 'POST', 'DELETE'])
def training_endpoint():
    """Manage training data - get all, add new, or delete."""
    global training_data
    
    if request.method == 'GET':
        # Filter out FAQ training data - only return user-added training data
        # Get all FAQ questions
        faq_questions = set()
        if 'basic' in FAQS:
            faq_questions.update(FAQS['basic'])
        if 'intermediate' in FAQS:
            faq_questions.update(FAQS['intermediate'])
        if 'advanced' in FAQS:
            faq_questions.update(FAQS['advanced'])
        if 'operational' in FAQS:
            faq_questions.update(FAQS['operational'])
        
        # Filter training data to exclude FAQ questions
        user_training_data = {
            question: answer 
            for question, answer in training_data.items() 
            if question not in faq_questions
        }
        
        return jsonify({
            'training_data': user_training_data,
            'count': len(user_training_data),
            'total_count': len(training_data),
            'faq_count': len(training_data) - len(user_training_data)
        })
    
    elif request.method == 'POST':
        # Add or update training data
        data = request.json
        question = data.get('question', '').strip()
        answer = data.get('answer', '').strip()
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        if not answer:
            return jsonify({'error': 'Answer is required'}), 400
        
        # Save training data
        training_data[question] = answer
        
        # Save to file
        if save_training_data():
            return jsonify({
                'message': 'Training data saved successfully',
                'question': question,
                'answer': answer,
                'total_training_entries': len(training_data)
            })
        else:
            return jsonify({'error': 'Failed to save training data'}), 500
    
    elif request.method == 'DELETE':
        # Delete training data
        data = request.json
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        if question in training_data:
            del training_data[question]
            save_training_data()
            return jsonify({
                'message': 'Training data deleted successfully',
                'total_training_entries': len(training_data)
            })
        else:
            return jsonify({'error': 'Question not found in training data'}), 404

@app.route('/api/training/upload', methods=['POST'])
def training_upload():
    """Upload Excel/CSV file for training answer."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        question = request.form.get('question', '').strip()
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Save uploaded file temporarily
        upload_dir = 'uploads'
        os.makedirs(upload_dir, exist_ok=True)
        filename = f"training_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        # Read the file and convert to markdown
        try:
            df = pd.read_excel(file_path) if file_path.endswith(('.xlsx', '.xls', '.xlsm', '.xlsb')) else pd.read_csv(file_path)
            
            # Convert DataFrame to markdown format
            if rag_system:
                answer = rag_system.convert_to_markdown(df, metadata={'source': 'training_upload', 'question': question})
            else:
                # Fallback: simple conversion
                answer = f"## Training Data Answer\n\n{df.to_markdown(index=False)}"
            
            # Save as training data
            training_data[question] = answer
            save_training_data()
            
            # Clean up temp file
            try:
                os.remove(file_path)
            except:
                pass
            
            return jsonify({
                'message': 'Training data uploaded and saved successfully',
                'question': question,
                'answer_preview': answer[:200] + '...' if len(answer) > 200 else answer,
                'total_training_entries': len(training_data)
            })
        except Exception as e:
            # Clean up temp file on error
            try:
                os.remove(file_path)
            except:
                pass
            return jsonify({'error': f'Error processing file: {str(e)}'}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/edited-answers', methods=['GET', 'POST', 'DELETE'])
def edited_answers_endpoint():
    """Manage edited answers - get all, add new, or delete."""
    global edited_answers
    
    if request.method == 'GET':
        # Return all edited answers
        return jsonify({
            'edited_answers': edited_answers,
            'count': len(edited_answers)
        })
    
    elif request.method == 'POST':
        # Add or update edited answer
        data = request.json
        question = data.get('question', '').strip()
        answer = data.get('answer', '').strip()
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        if not answer:
            return jsonify({'error': 'Answer is required'}), 400
        
        # Save edited answer
        edited_answers[question] = answer
        
        # Save to file
        if save_edited_answers():
            return jsonify({
                'message': 'Edited answer saved permanently successfully',
                'question': question,
                'answer': answer,
                'total_edited_entries': len(edited_answers)
            })
        else:
            return jsonify({'error': 'Failed to save edited answer'}), 500
    
    elif request.method == 'DELETE':
        # Delete edited answer
        data = request.json
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        if question in edited_answers:
            del edited_answers[question]
            save_edited_answers()
            return jsonify({
                'message': 'Edited answer deleted successfully',
                'total_edited_entries': len(edited_answers)
            })
        else:
            return jsonify({'error': 'Question not found in edited answers'}), 404

@app.route('/api/download', methods=['POST'])
def download_answer():
    """Download answer as text file."""
    try:
        data = request.json
        answer = data.get('answer', '')
        query = data.get('query', 'No query')
        numeric_value = data.get('numeric_value')
        custom_filename = data.get('filename', '')
        
        if not answer:
            return jsonify({'error': 'No answer to download'}), 400
        
        # Create download file
        download_dir = settings.get('download_path', os.path.join(os.path.expanduser("~"), "Downloads"))
        os.makedirs(download_dir, exist_ok=True)
        
        # Use custom filename if provided, otherwise generate one
        if custom_filename:
            # Sanitize filename
            custom_filename = re.sub(r'[<>:"/\\|?*]', '_', custom_filename)
            filename = f"{custom_filename}.txt"
        else:
            filename = f"query_answer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        file_path = os.path.join(download_dir, filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"Query: {query}\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            if numeric_value is not None:
                f.write(f"Numeric Value: {numeric_value}\n")
            f.write("-" * 80 + "\n\n")
            f.write(answer)
        
        return jsonify({
            'message': 'Answer downloaded successfully',
            'file_path': file_path,
            'filename': filename
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    """Demo page for the chatbot."""
    return render_template('index.html')

@app.route('/test')
def test_page():
    """Local test page for the chatbot."""
    return send_from_directory('.', 'test_chatbot_local.html')

@app.route('/test-simple')
def test_simple():
    """Simple test page."""
    return send_from_directory('.', 'test_simple.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files."""
    return send_from_directory(app.static_folder, filename)

if __name__ == '__main__':
    # Use environment variable for debug mode (default: False for production)
    # Set FLASK_DEBUG=true to enable debug mode
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    port = int(os.getenv('FLASK_PORT', '5000'))
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    
    app.run(debug=debug_mode, host=host, port=port)

