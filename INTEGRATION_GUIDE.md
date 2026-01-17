# Website Integration Guide

## Data Analysis Chatbot - Integration Instructions

This guide will help you integrate the Data Analysis Chatbot into any website or portal.

---

## Quick Start (One-Line Integration)

### Method 1: Simple Embed Script (Recommended)

Add this single line to your HTML page, just before the closing `</body>` tag:

```html
<script src="https://your-api-domain.com/static/chatbot-embed.js" 
        data-api-url="https://your-api-domain.com/api"></script>
```

**That's it!** The chatbot will automatically appear in the bottom-right corner of your page.

---

## Installation Methods

### Method 1: Embed Script (Easiest)

**Best for:** Quick integration, minimal setup

1. Add the embed script to your HTML:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Your Website</title>
</head>
<body>
    <!-- Your website content -->
    
    <!-- Chatbot Integration - Add before closing </body> tag -->
    <script src="https://your-api-domain.com/static/chatbot-embed.js" 
            data-api-url="https://your-api-domain.com/api"></script>
</body>
</html>
```

2. Replace `https://your-api-domain.com` with your actual API server URL.

3. The chatbot will automatically:
   - Load required CSS and JavaScript files
   - Initialize in the bottom-right corner
   - Connect to your API server
   - Be ready to use

---

### Method 2: Manual Integration (More Control)

**Best for:** Custom styling, advanced configuration

1. **Include CSS** in your HTML `<head>`:

```html
<link rel="stylesheet" href="https://your-api-domain.com/static/chatbot.css">
```

2. **Include JavaScript** before closing `</body>` tag:

```html
<script src="https://your-api-domain.com/static/chatbot.js"></script>
```

3. **Initialize the chatbot** with your configuration:

```html
<script>
    const chatbot = new ChatbotWidget({
        apiUrl: 'https://your-api-domain.com/api',
        downloadPath: '/path/to/downloads',  // Optional
        filesFolderPath: '/path/to/files'      // Optional
    });
</script>
```

---

## Configuration Options

### Basic Configuration

```javascript
const chatbot = new ChatbotWidget({
    apiUrl: 'https://your-api-domain.com/api'  // Required: Your API endpoint
});
```

### Advanced Configuration

```javascript
const chatbot = new ChatbotWidget({
    apiUrl: 'https://your-api-domain.com/api',        // Required
    downloadPath: '/custom/download/path',            // Optional: Custom download directory
    filesFolderPath: '/custom/files/path'             // Optional: Custom files directory
});
```

### Embed Script Configuration (Data Attributes)

```html
<script src="https://your-api-domain.com/static/chatbot-embed.js" 
        data-api-url="https://your-api-domain.com/api"
        data-download-path="/custom/download/path"
        data-files-folder-path="/custom/files/path"></script>
```

---

## API Server Setup

### Prerequisites

- Python 3.7 or higher
- Flask framework
- Required Python packages (see `requirements.txt`)

### Installation

1. **Install dependencies:**

```bash
pip install -r requirements.txt
```

2. **Configure environment variables** (optional):

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

3. **Start the server:**

```bash
python app.py
```

The server will run on `http://localhost:5000` by default.

### Production Deployment

For production, use a WSGI server like Gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Or use uWSGI, Waitress, or any other WSGI-compatible server.

---

## CORS Configuration

The chatbot requires CORS to be properly configured on the API server.

### Development (All Origins)

By default, the server allows all origins for development. This is configured in `app.py`.

### Production (Restricted Origins)

Set the `ALLOWED_ORIGINS` environment variable:

```bash
export ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

Or in your `.env` file:

```
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

---

## Customization

### Styling

The chatbot uses CSS that can be customized. The main CSS file is located at:
- `static/chatbot.css`

You can override styles by adding custom CSS after loading the chatbot CSS:

```html
<link rel="stylesheet" href="https://your-api-domain.com/static/chatbot.css">
<style>
    /* Your custom styles */
    .chatbot-container {
        border-radius: 12px !important;
    }
    .chatbot-header {
        background: linear-gradient(135deg, #your-color-1 0%, #your-color-2 100%) !important;
    }
</style>
```

### Positioning

By default, the chatbot appears in the bottom-right corner. To change position, add custom CSS:

```css
.chatbot-container {
    bottom: 20px;      /* Distance from bottom */
    right: 20px;       /* Distance from right */
    /* Or use left/top for other positions */
}
```

### Size

```css
.chatbot-container {
    width: 400px;      /* Width */
    height: 600px;     /* Height */
}
```

---

## API Endpoints

The chatbot uses the following API endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/greet` | GET | Get greeting message |
| `/api/query` | POST | Send query and get response |
| `/api/autocomplete` | POST | Get autocomplete suggestions |
| `/api/faqs` | GET | Get all FAQs |
| `/api/upload` | POST | Upload Excel/CSV file |
| `/api/files/process` | POST | Process files |
| `/api/files/list` | POST | List files in folder |
| `/api/settings` | GET/POST | Get/update settings |
| `/api/download` | POST | Download answer as file |

---

## Browser Compatibility

The chatbot is compatible with:
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+
- Opera 76+

---

## Troubleshooting

### Chatbot doesn't appear

1. **Check browser console** for errors
2. **Verify API URL** is correct and accessible
3. **Check CORS settings** - ensure your domain is allowed
4. **Verify files are loading** - check Network tab in DevTools

### CORS Errors

If you see CORS errors:

1. **Check `ALLOWED_ORIGINS`** environment variable
2. **Verify your domain** is in the allowed list
3. **Check API server logs** for CORS-related messages

### API Connection Issues

1. **Verify API server is running**
2. **Check API URL** matches your server address
3. **Test API endpoint** directly: `https://your-api-domain.com/api/health`
4. **Check firewall/network** settings

### Files not loading

1. **Verify static file paths** are correct
2. **Check file permissions** on server
3. **Verify HTTPS/HTTP** matches your site protocol

---

## Security Considerations

### Production Checklist

- [ ] Set `FLASK_DEBUG=false` in production
- [ ] Configure `ALLOWED_ORIGINS` to restrict CORS
- [ ] Use HTTPS for API server
- [ ] Set appropriate `MAX_FILE_SIZE` limit
- [ ] Configure proper file upload validation
- [ ] Set up rate limiting (recommended)
- [ ] Use environment variables for sensitive config
- [ ] Regularly update dependencies

### File Upload Security

- File size is limited (default: 100MB)
- Only Excel/CSV files are accepted
- File paths are sanitized to prevent traversal attacks
- Files are validated before processing

---

## Examples

### Example 1: Basic HTML Page

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My Website</title>
</head>
<body>
    <h1>Welcome to My Website</h1>
    <p>This is my website content.</p>
    
    <!-- Chatbot Integration -->
    <script src="https://api.example.com/static/chatbot-embed.js" 
            data-api-url="https://api.example.com/api"></script>
</body>
</html>
```

### Example 2: React Application

```jsx
import React, { useEffect } from 'react';

function App() {
    useEffect(() => {
        // Load chatbot script
        const script = document.createElement('script');
        script.src = 'https://api.example.com/static/chatbot-embed.js';
        script.setAttribute('data-api-url', 'https://api.example.com/api');
        document.body.appendChild(script);
        
        return () => {
            // Cleanup if needed
            document.body.removeChild(script);
        };
    }, []);
    
    return (
        <div>
            <h1>My React App</h1>
            {/* Chatbot will appear automatically */}
        </div>
    );
}
```

### Example 3: WordPress

Add to your theme's `footer.php` or use a plugin:

```php
<!-- Chatbot Integration -->
<script src="https://api.example.com/static/chatbot-embed.js" 
        data-api-url="https://api.example.com/api"></script>
```

### Example 4: Custom Styling

```html
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="https://api.example.com/static/chatbot.css">
    <style>
        /* Custom chatbot styling */
        .chatbot-container {
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        }
        .chatbot-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .chatbot-button {
            background: #667eea;
        }
    </style>
</head>
<body>
    <!-- Your content -->
    
    <script src="https://api.example.com/static/chatbot.js"></script>
    <script>
        new ChatbotWidget({
            apiUrl: 'https://api.example.com/api'
        });
    </script>
</body>
</html>
```

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review API server logs
3. Check browser console for errors
4. Verify API endpoints are accessible

---

## License

[Your License Information]

---

**Version:** 1.0  
**Last Updated:** 2025-01-16
