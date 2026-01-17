# Quick Integration Guide

## One-Line Integration

Add this single line to your website, just before the closing `</body>` tag:

```html
<script src="https://your-api-domain.com/static/chatbot-embed.js" 
        data-api-url="https://your-api-domain.com/api"></script>
```

**Replace `https://your-api-domain.com` with your actual API server URL.**

---

## What You Need

1. **API Server Running**
   - Your Flask API server must be running and accessible
   - Default port: 5000
   - Must be accessible from your website domain

2. **CORS Configuration**
   - For production, set `ALLOWED_ORIGINS` environment variable
   - Include your website domain in the allowed list

---

## Setup Steps

### Step 1: Start Your API Server

```bash
# Install dependencies
pip install -r requirements.txt

# Start server
python app.py
```

### Step 2: Configure CORS (Production)

Set environment variable:

```bash
export ALLOWED_ORIGINS=https://yourwebsite.com,https://www.yourwebsite.com
```

Or in `.env` file:

```
ALLOWED_ORIGINS=https://yourwebsite.com,https://www.yourwebsite.com
```

### Step 3: Add to Your Website

Add the embed script to your HTML:

```html
<script src="https://your-api-domain.com/static/chatbot-embed.js" 
        data-api-url="https://your-api-domain.com/api"></script>
```

---

## Configuration Options

### Basic (Auto-detect)

```html
<script src="https://your-api-domain.com/static/chatbot-embed.js" 
        data-api-url="https://your-api-domain.com/api"></script>
```

### With Custom Paths

```html
<script src="https://your-api-domain.com/static/chatbot-embed.js" 
        data-api-url="https://your-api-domain.com/api"
        data-download-path="/custom/downloads"
        data-files-folder-path="/custom/files"></script>
```

---

## Testing

1. Open your website in a browser
2. The chatbot should appear in the bottom-right corner
3. Click to open and test a query
4. Check browser console for any errors

---

## Troubleshooting

**Chatbot doesn't appear:**
- Check browser console for errors
- Verify API URL is correct
- Check CORS settings

**CORS errors:**
- Add your domain to `ALLOWED_ORIGINS`
- Restart the API server

**Connection errors:**
- Verify API server is running
- Check API URL is accessible
- Test: `https://your-api-domain.com/api/health`

---

For detailed documentation, see `INTEGRATION_GUIDE.md`
