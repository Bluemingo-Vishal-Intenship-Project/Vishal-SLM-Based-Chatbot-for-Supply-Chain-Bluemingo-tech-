# Data Analysis Chatbot

A professional, embeddable chatbot system for analyzing Excel/CSV data files. This chatbot provides a query-driven approach to data analysis, allowing users to ask natural language questions about their data and receive accurate, verifiable answers.

## Features

- **Query-Driven Analytics**: Deterministic and verifiable answers through direct data queries
- **Excel/CSV Support**: Process and analyze Excel and CSV files
- **Natural Language Queries**: Ask questions in plain English
- **Easy Integration**: One-line embed script for any website
- **Professional UI**: Clean, responsive design
- **Auto-Complete**: Smart question suggestions
- **FAQ System**: Pre-defined questions organized by difficulty
- **File Upload**: Upload and process data files through the interface
- **Export Results**: Download answers as text files

## Quick Start

### Prerequisites

- Python 3.7 or higher
- pip (Python package manager)

### Installation

1. **Clone the repository:**

```bash
git clone https://github.com/Bluemingo-Vishal-Intenship-Project/Vishal-SLM-Based-Chatbot-for-Supply-Chain-Bluemingo-tech-.git
cd Vishal-SLM-Based-Chatbot-for-Supply-Chain-Bluemingo-tech-
```

2. **Install dependencies:**

```bash
pip install -r requirements.txt
```

3. **Start the server:**

```bash
python app.py
```

The server will start on `http://localhost:5000`

### Configuration (Optional)

Create a `.env` file or set environment variables:

```bash
# Production Configuration
FLASK_DEBUG=false
FLASK_PORT=5000
FLASK_HOST=0.0.0.0
MAX_FILE_SIZE=104857600  # 100MB in bytes
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Optional: Custom paths
DOWNLOAD_PATH=/path/to/downloads
FILES_FOLDER_PATH=/path/to/files
```

## Usage

### Web Interface

1. Open `http://localhost:5000` in your browser
2. Upload an Excel or CSV file
3. Ask questions about your data

### API Integration

The chatbot can be integrated into any website using a single line:

```html
<script src="https://your-api-domain.com/static/chatbot-embed.js" 
        data-api-url="https://your-api-domain.com/api"></script>
```

For detailed integration instructions, see [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)

## Project Structure

```
.
├── app.py                      # Flask API server
├── data_loader.py             # Data loading and management
├── intent_classifier.py       # Query intent classification
├── query_generator.py         # Query generation from intents
├── query_executor.py          # Safe query execution
├── query_driven_pipeline.py   # Main pipeline orchestrator
├── response_formatter.py      # Response formatting
├── static/                    # Frontend assets
│   ├── chatbot.css           # Chatbot styles
│   ├── chatbot.js            # Chatbot widget
│   └── chatbot-embed.js      # Embed script
├── templates/                # HTML templates
│   └── index.html            # Demo page
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Architecture

The system uses a **query-driven architecture** that:

- Executes deterministic queries on actual data
- Provides verifiable and accurate answers
- Uses rule-based intent classification
- Formats results into natural language responses

For detailed architecture documentation, see [COMPLETE_ARCHITECTURE_DOCUMENTATION.md](COMPLETE_ARCHITECTURE_DOCUMENTATION.md)

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/greet` | GET | Get greeting message |
| `/api/query` | POST | Process query |
| `/api/autocomplete` | POST | Get autocomplete suggestions |
| `/api/faqs` | GET | Get all FAQs |
| `/api/upload` | POST | Upload file |
| `/api/files/process` | POST | Process files |
| `/api/files/list` | POST | List files |
| `/api/settings` | GET/POST | Manage settings |
| `/api/download` | POST | Download answer |

## Supported File Formats

- Excel: `.xlsx`, `.xls`, `.xlsm`, `.xlsb`
- CSV: `.csv`

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+
- Opera 76+

## Security

- File size limits (configurable, default: 100MB)
- Path traversal protection
- CORS configuration for production
- Input validation
- File type validation

## Documentation

- [Integration Guide](INTEGRATION_GUIDE.md) - Complete integration instructions
- [Quick Integration](QUICK_INTEGRATION.md) - Quick start guide
- [Architecture Documentation](COMPLETE_ARCHITECTURE_DOCUMENTATION.md) - System architecture
- [API Documentation](API_DOCUMENTATION.md) - API reference
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions

## Development

### Running in Development Mode

```bash
export FLASK_DEBUG=true
python app.py
```

### Running in Production

Use a WSGI server like Gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

[Your License Here]

## Support

For issues, questions, or contributions, please open an issue on GitHub.

---

**Version:** 1.0  
**Last Updated:** 2025-01-16
