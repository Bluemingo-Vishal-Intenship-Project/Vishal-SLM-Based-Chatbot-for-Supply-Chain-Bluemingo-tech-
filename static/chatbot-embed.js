/**
 * Chatbot Embed Script
 * Simple script for clients to embed the chatbot on their website
 * 
 * Usage:
 * <script src="https://your-domain.com/static/chatbot-embed.js" 
 *         data-api-url="https://your-api-domain.com/api"></script>
 */

(function() {
    'use strict';
    
    // Get configuration from script tag
    const script = document.currentScript || document.querySelector('script[data-api-url]');
    const config = {
        apiUrl: script?.dataset?.apiUrl || 'http://localhost:5000/api',
        downloadPath: script?.dataset?.downloadPath || '',
        filesFolderPath: script?.dataset?.filesFolderPath || ''
    };
    
    // Load CSS
    const cssLink = document.createElement('link');
    cssLink.rel = 'stylesheet';
    cssLink.href = script?.src?.replace('chatbot-embed.js', 'chatbot.css') || 
                   window.location.origin + '/static/chatbot.css';
    document.head.appendChild(cssLink);
    
    // Load main chatbot script
    const jsScript = document.createElement('script');
    jsScript.src = script?.src?.replace('chatbot-embed.js', 'chatbot.js') || 
                   window.location.origin + '/static/chatbot.js';
    jsScript.onload = function() {
        // Initialize chatbot after script loads
        if (window.ChatbotWidget) {
            window.chatbot = new window.ChatbotWidget(config);
        }
    };
    document.head.appendChild(jsScript);
    
    // Fallback: if scripts are already loaded
    if (window.ChatbotWidget && !window.chatbot) {
        window.chatbot = new window.ChatbotWidget(config);
    }
})();







