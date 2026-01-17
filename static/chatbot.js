/**
 * Modern Chatbot Widget
 * Embeddable chatbot for any webpage
 */

class ChatbotWidget {
    constructor(config = {}) {
        // Auto-detect API URL from current page if not provided
        let defaultApiUrl = 'http://localhost:5000/api';
        if (typeof window !== 'undefined' && window.location) {
            const host = window.location.hostname;
            // Get port from URL - use window.location.port if available, otherwise infer from protocol
            let port = window.location.port;
            if (!port || port === '') {
                // If no port in URL, check if it's http (80) or https (443)
                // But for explicit URLs with port, use the port from the URL
                const urlMatch = window.location.href.match(/:(\d+)/);
                if (urlMatch) {
                    port = urlMatch[1];
                } else {
                    port = window.location.protocol === 'https:' ? '443' : '5000';
                }
            }
            // Construct API URL using current page's origin
            defaultApiUrl = `${window.location.protocol}//${host}:${port}/api`;
            // Auto-detected API URL from page
            if (window.DEBUG_MODE) {
                console.log('Auto-detected API URL from page:', defaultApiUrl);
                console.log('   Page URL:', window.location.href);
                console.log('   Hostname:', host);
                console.log('   Port:', port);
            }
        }
        
        // Always use detected URL unless explicitly overridden
        // If config.apiUrl is provided, use it; otherwise use detected URL
        if (config.apiUrl) {
            this.apiUrl = config.apiUrl;
            if (window.DEBUG_MODE) {
                console.log('Using configured API URL:', this.apiUrl);
            }
        } else {
            this.apiUrl = defaultApiUrl;
            if (window.DEBUG_MODE) {
                console.log('Using auto-detected API URL:', this.apiUrl);
            }
        }
        
        // Warn if API URL doesn't match current page origin (unless explicitly configured)
        if (!config.apiUrl && typeof window !== 'undefined' && window.location) {
            const currentOrigin = `${window.location.protocol}//${window.location.hostname}:${window.location.port || (window.location.protocol === 'https:' ? '443' : '5000')}`;
            const apiOrigin = this.apiUrl.replace('/api', '');
            if (apiOrigin !== currentOrigin) {
                console.warn('API URL origin does not match current page origin!');
                console.warn('   Current page:', currentOrigin);
                console.warn('   API URL:', apiOrigin);
                console.warn('   This may cause CORS or connection issues.');
            }
        }
        this.container = null;
        this.messages = [];
        this.isMinimized = false;
        this.currentAutocompleteIndex = -1;
        this.autocompleteItems = [];
        this.isFullscreen = false;
        this.suggestionsShown = false; // Track if suggestions are already shown
        this.usedSuggestions = []; // Track which suggestions have been used
        this.autocompleteTimeout = null;
        this.suggestionsTimeout = null;
        this.preventSuggestions = false;
        this.settings = {
            downloadPath: config.downloadPath || '',
            filesFolderPath: config.filesFolderPath || ''
        };
        
        this.init();
    }

    init() {
        this.createWidget();
        // Wait for DOM to be ready before setting up listeners
        setTimeout(async () => {
            // Check API connectivity first
            await this.checkApiConnectivity();
            
            this.setupEventListeners();
            
            // Load saved settings first to restore path permanently
            await this.loadCurrentSettings();
            
            this.loadGreeting();
            
            // CRITICAL: Remove any test messages
            this.removeTestMessages();
            
            // CRITICAL: Remove any white overlays
            this.removeWhiteOverlays();
            
            // Ensure messages container has proper styles
            const messagesEl = document.getElementById('chatbot-messages');
            if (messagesEl) {
                messagesEl.style.cssText = `
                    flex: 1;
                    overflow-y: auto;
                    padding: 20px;
                    display: flex;
                    flex-direction: column;
                    gap: 16px;
                    background: #f8f9fa !important;
                    color: #1f2937 !important;
                `;
            }
            
            // Ensure input is enabled and visible with ALL properties
            const input = document.getElementById('chatbot-input');
            if (input) {
                input.style.cssText = `
                    flex: 1;
                    border: none !important;
                    background: transparent !important;
                    outline: none !important;
                    font-size: 14px !important;
                    color: #1f2937 !important;
                    -webkit-text-fill-color: #1f2937 !important;
                    caret-color: #1f2937 !important;
                    padding: 8px 0;
                    font-family: inherit;
                    opacity: 1 !important;
                    visibility: visible !important;
                    position: relative !important;
                    z-index: 999 !important;
                    mix-blend-mode: normal !important;
                `;
                input.removeAttribute('disabled');
                input.removeAttribute('readonly');
                input.disabled = false;
                input.readOnly = false;
                
                // Force caret to be visible
                input.setAttribute('autocomplete', 'off');
                input.setAttribute('spellcheck', 'false');
                
                // Remove any overlays from wrapper
                const wrapper = input.parentElement;
                if (wrapper) {
                    wrapper.style.setProperty('pointer-events', 'none', 'important');
                    wrapper.querySelectorAll('*').forEach(child => {
                        if (child !== input && child.id !== 'chatbot-autocomplete' && child.id !== 'chatbot-send-btn') {
                            child.style.setProperty('pointer-events', 'auto', 'important');
                        }
                    });
                    input.style.setProperty('pointer-events', 'auto', 'important');
                }
            }
            
            // Force all existing messages to be visible
            const allMessages = document.querySelectorAll('.chatbot-message-bubble');
            allMessages.forEach(bubble => {
                const message = bubble.closest('.chatbot-message');
                if (message) {
                    const textColor = message.classList.contains('user') ? '#ffffff' : '#1f2937';
                    bubble.style.setProperty('color', textColor, 'important');
                    bubble.style.setProperty('-webkit-text-fill-color', textColor, 'important');
                    
                    const children = bubble.querySelectorAll('*');
                    children.forEach(child => {
                        child.style.setProperty('color', textColor, 'important');
                        child.style.setProperty('-webkit-text-fill-color', textColor, 'important');
                    });
                }
            });
        }, 100);
        
        // Also run after a longer delay to catch any late-loading styles
        setTimeout(() => {
            const input = document.getElementById('chatbot-input');
            if (input) {
                input.style.setProperty('color', '#1f2937', 'important');
                input.style.setProperty('-webkit-text-fill-color', '#1f2937', 'important');
                input.style.setProperty('caret-color', '#1f2937', 'important');
            }
        }, 500);
    }
    
    startInputVisibilityMonitor() {
        const input = document.getElementById('chatbot-input');
        if (!input) {
            setTimeout(() => this.startInputVisibilityMonitor(), 200);
            return;
        }
        
        // Monitor for style changes that might hide text
        const observer = new MutationObserver(() => {
            if (input.value && input.value.length > 0) {
                this.setInputTextVisible(input);
            }
        });
        
        observer.observe(input, {
            attributes: true,
            attributeFilter: ['style', 'class', 'disabled', 'readonly'],
            childList: false,
            subtree: false
        });
        
        // Also check periodically (as backup)
        setInterval(() => {
            if (input.value && input.value.length > 0) {
                const computedStyle = window.getComputedStyle(input);
                const textColor = computedStyle.color || computedStyle.webkitTextFillColor;
                // If text color is transparent or white, force it back
                if (!textColor || textColor === 'rgba(0, 0, 0, 0)' || textColor === 'rgb(255, 255, 255)' || textColor === 'transparent') {
                    this.setInputTextVisible(input);
                }
            }
        }, 500);
    }
    
    ensureMessagesVisible() {
        const messagesEl = document.getElementById('chatbot-messages');
        if (!messagesEl) {
            setTimeout(() => this.ensureMessagesVisible(), 200);
            return;
        }
        
        // Ensure messages container is visible
        messagesEl.style.visibility = 'visible';
        messagesEl.style.opacity = '1';
        messagesEl.style.display = 'flex';
        messagesEl.style.color = '#1f2937';
        
        // Fix all existing messages
        const messages = messagesEl.querySelectorAll('.chatbot-message');
        messages.forEach(message => {
            message.style.visibility = 'visible';
            message.style.opacity = '1';
            message.style.display = 'flex';
            
            const bubble = message.querySelector('.chatbot-message-bubble');
            if (bubble) {
                bubble.style.visibility = 'visible';
                bubble.style.opacity = '1';
                bubble.style.display = 'block';
                
                // Set color based on message type
                if (message.classList.contains('user')) {
                    bubble.style.color = 'white';
                    bubble.style.setProperty('-webkit-text-fill-color', 'white', 'important');
                } else {
                    bubble.style.color = '#1f2937';
                    bubble.style.setProperty('-webkit-text-fill-color', '#1f2937', 'important');
                }
                
                // Fix all child elements
                const children = bubble.querySelectorAll('*');
                children.forEach(child => {
                    child.style.color = 'inherit';
                    child.style.setProperty('-webkit-text-fill-color', 'inherit', 'important');
                    child.style.opacity = '1';
                    child.style.visibility = 'visible';
                });
            }
            
            const time = message.querySelector('.chatbot-message-time');
            if (time) {
                time.style.color = '#6b7280';
                time.style.visibility = 'visible';
                time.style.opacity = '1';
            }
        });
        
        console.log('✅ Messages visibility ensured');
    }
    
    forceAllTextVisible() {
        // Force input text visibility
        const input = document.getElementById('chatbot-input');
        if (input) {
            input.style.setProperty('color', '#1f2937', 'important');
            input.style.setProperty('-webkit-text-fill-color', '#1f2937', 'important');
            input.style.setProperty('text-fill-color', '#1f2937', 'important');
            input.style.setProperty('opacity', '1', 'important');
            input.style.setProperty('visibility', 'visible', 'important');
            
            // Also set on input event
            input.addEventListener('input', () => {
                input.style.setProperty('color', '#1f2937', 'important');
                input.style.setProperty('-webkit-text-fill-color', '#1f2937', 'important');
            }, { capture: true });
        }
        
        // Force all message bubbles
        const messages = document.querySelectorAll('.chatbot-message-bubble');
        messages.forEach(bubble => {
            const message = bubble.closest('.chatbot-message');
            if (message) {
                if (message.classList.contains('user')) {
                    bubble.style.setProperty('color', 'white', 'important');
                    bubble.style.setProperty('-webkit-text-fill-color', 'white', 'important');
                } else {
                    bubble.style.setProperty('color', '#1f2937', 'important');
                    bubble.style.setProperty('-webkit-text-fill-color', '#1f2937', 'important');
                }
                
                // Fix all children
                const children = bubble.querySelectorAll('*');
                children.forEach(child => {
                    if (message.classList.contains('user')) {
                        child.style.setProperty('color', 'white', 'important');
                        child.style.setProperty('-webkit-text-fill-color', 'white', 'important');
                    } else {
                        child.style.setProperty('color', '#1f2937', 'important');
                        child.style.setProperty('-webkit-text-fill-color', '#1f2937', 'important');
                    }
                });
            }
        });
        
        console.log('✅ All text visibility forced');
    }
    
    removeWhiteOverlays() {
        // Find any elements that might be covering the chatbot with white background
        const container = document.getElementById('chatbot-widget');
        if (!container) return;
        
        // Check all children for white backgrounds that might be overlaying
        const allElements = container.querySelectorAll('*');
        allElements.forEach(el => {
            const computed = window.getComputedStyle(el);
            const bgColor = computed.backgroundColor;
            const zIndex = parseInt(computed.zIndex) || 0;
            const position = computed.position;
            
            // If element has white/transparent background, high z-index, and is positioned, it might be an overlay
            if ((bgColor === 'rgb(255, 255, 255)' || bgColor === 'rgba(0, 0, 0, 0)' || bgColor === 'transparent') &&
                (position === 'absolute' || position === 'fixed') &&
                zIndex > 10 &&
                el.id !== 'chatbot-input' &&
                el.id !== 'chatbot-messages' &&
                !el.closest('.chatbot-message-bubble')) {
                
                // Check if it's covering the input or messages
                const rect = el.getBoundingClientRect();
                const input = document.getElementById('chatbot-input');
                const messages = document.getElementById('chatbot-messages');
                
                if (input) {
                    const inputRect = input.getBoundingClientRect();
                    if (rect.top <= inputRect.bottom && rect.bottom >= inputRect.top &&
                        rect.left <= inputRect.right && rect.right >= inputRect.left) {
                        console.log('⚠️ Found potential overlay covering input:', el);
                        el.style.setProperty('pointer-events', 'none', 'important');
                        el.style.setProperty('display', 'none', 'important');
                    }
                }
                
                if (messages) {
                    const msgRect = messages.getBoundingClientRect();
                    if (rect.top <= msgRect.bottom && rect.bottom >= msgRect.top &&
                        rect.left <= msgRect.right && rect.right >= msgRect.left) {
                        console.log('⚠️ Found potential overlay covering messages:', el);
                        el.style.setProperty('pointer-events', 'none', 'important');
                        el.style.setProperty('display', 'none', 'important');
                    }
                }
            }
        });
        
        console.log('✅ White overlay check complete');
    }
    
    removeTestMessages() {
        // Remove any test messages from the chat
        const messagesEl = document.getElementById('chatbot-messages');
        if (!messagesEl) return;
        
        const allMessages = messagesEl.querySelectorAll('.chatbot-message');
        let removedCount = 0;
        
        allMessages.forEach(msg => {
            const bubble = msg.querySelector('.chatbot-message-bubble');
            if (bubble) {
                const text = bubble.textContent || '';
                if (text.includes('Test message') || 
                    text.includes('test message') || 
                    text.includes('messages are working')) {
                    msg.remove();
                    removedCount++;
                    // Also remove from messages array
                    const msgId = msg.id;
                    this.messages = this.messages.filter(m => m.id !== msgId);
                }
            }
        });
        
        if (removedCount > 0) {
            console.log(`✅ Removed ${removedCount} test message(s)`);
        }
    }
    
    ensureInputEnabled() {
        const input = document.getElementById('chatbot-input');
        if (input) {
            // Remove any disabled/readonly attributes
            input.removeAttribute('disabled');
            input.removeAttribute('readonly');
            // Ensure input properties are correct
            input.disabled = false;
            input.readOnly = false;
            // Ensure text is visible
            this.setInputTextVisible(input);
            console.log('✅ Input enabled and text color set');
        }
    }
    
    setInputTextVisible(input) {
        if (!input) return;
        // Force text to be visible with multiple methods
        input.style.setProperty('color', '#1f2937', 'important');
        input.style.setProperty('-webkit-text-fill-color', '#1f2937', 'important');
        input.style.setProperty('text-fill-color', '#1f2937', 'important');
        input.style.setProperty('opacity', '1', 'important');
        input.style.setProperty('visibility', 'visible', 'important');
        input.style.setProperty('pointer-events', 'auto', 'important');
        // Force a repaint
        input.offsetHeight; // Trigger reflow
    }
    
    setInputValue(value) {
        const input = document.getElementById('chatbot-input');
        if (input) {
            input.value = value;
            // Force text visibility after setting value
            this.setInputTextVisible(input);
            // Trigger input event to ensure display updates
            const event = new Event('input', { bubbles: true });
            input.dispatchEvent(event);
            console.log('✅ Input value set to:', value, '| Visible:', input.style.color);
        }
    }

    createWidget() {
        // CRITICAL: Check if chatbot already exists to prevent duplicates
        const existingWidget = document.getElementById('chatbot-widget');
        const existingContainer = document.getElementById('chatbot-container');
        const existingSuggestions = document.querySelectorAll('#chatbot-suggestions');
        
        if (existingWidget || existingContainer) {
            console.warn('⚠️ Chatbot widget already exists! Removing duplicate...');
            if (existingWidget) existingWidget.remove();
            if (existingContainer) existingContainer.remove();
        }
        
        // Remove any orphaned suggestion containers and chips
        existingSuggestions.forEach(el => {
            if (!el.closest('#chatbot-widget') && !el.closest('#chatbot-container')) {
                el.remove();
            }
        });
        
        // Remove all suggestion chips from document
        const allChips = document.querySelectorAll('.chatbot-suggestion-chip');
        allChips.forEach(chip => chip.remove());
        
        // Create wrapper container with id="chatbot-container" for guaranteed fix
        const wrapper = document.createElement('div');
        wrapper.id = 'chatbot-container';
        wrapper.className = 'chatbot-container-wrapper';
        
        // Create inner container (keep existing structure for compatibility)
        this.container = document.createElement('div');
        this.container.className = 'chatbot-container';
        this.container.id = 'chatbot-widget';
        
        // CRITICAL: Inject style tag to override ALL parent styles and remove overlays
        const styleTag = document.createElement('style');
        styleTag.id = 'chatbot-guaranteed-fix';
        styleTag.textContent = `
            /* GUARANTEED FIX: Force Color Reset */
            #chatbot-container,
            #chatbot-container *,
            #chatbot-widget,
            #chatbot-widget * {
                box-sizing: border-box;
                visibility: visible !important;
            }
            #chatbot-container,
            #chatbot-widget {
                background: #ffffff !important;
                color: #1f2937 !important;
            }
            #chatbot-container *,
            #chatbot-widget * {
                color: #1f2937 !important;
                background-color: transparent !important;
                -webkit-text-fill-color: #1f2937 !important;
            }
            #chatbot-container *::before,
            #chatbot-container *::after,
            #chatbot-widget *::before,
            #chatbot-widget *::after {
                display: none !important;
                content: none !important;
            }
            /* Fix for input typing box */
            #chatbot-container input,
            #chatbot-container textarea,
            #chatbot-widget input,
            #chatbot-widget textarea {
                color: #1f2937 !important;
                background: transparent !important;
                -webkit-text-fill-color: #1f2937 !important;
                caret-color: #1f2937 !important;
                mix-blend-mode: normal !important;
                position: relative !important;
                z-index: 999 !important;
            }
            #chatbot-input {
                color: #1f2937 !important;
                -webkit-text-fill-color: #1f2937 !important;
                caret-color: #1f2937 !important;
                background: transparent !important;
                mix-blend-mode: normal !important;
                position: relative !important;
                z-index: 999 !important;
            }
            #chatbot-input::placeholder {
                color: #9ca3af !important;
                -webkit-text-fill-color: #9ca3af !important;
            }
            .chatbot-input-wrapper {
                pointer-events: none !important;
            }
            .chatbot-input-wrapper > * {
                pointer-events: auto !important;
            }
            /* Ensure user messages have white text */
            #chatbot-container .chatbot-message.user .chatbot-message-bubble,
            #chatbot-container .chatbot-message.user .chatbot-message-bubble *,
            #chatbot-widget .chatbot-message.user .chatbot-message-bubble,
            #chatbot-widget .chatbot-message.user .chatbot-message-bubble * {
                color: #ffffff !important;
                -webkit-text-fill-color: #ffffff !important;
            }
            /* Ensure assistant messages have dark text - CRITICAL FIX for rgb(31, 41, 55) */
            #chatbot-container .chatbot-message.assistant .chatbot-message-bubble,
            #chatbot-container .chatbot-message.assistant .chatbot-message-bubble *,
            #chatbot-widget .chatbot-message.assistant .chatbot-message-bubble,
            #chatbot-widget .chatbot-message.assistant .chatbot-message-bubble *,
            .chatbot-message.assistant .chatbot-message-bubble,
            .chatbot-message.assistant .chatbot-message-bubble * {
                color: #1f2937 !important;
                -webkit-text-fill-color: #1f2937 !important;
            }
            .chatbot-message-bubble {
                color: #1f2937 !important;
                -webkit-text-fill-color: #1f2937 !important;
                mix-blend-mode: normal !important;
                position: relative !important;
                z-index: 1 !important;
            }
            .chatbot-message-bubble * {
                color: #1f2937 !important;
                -webkit-text-fill-color: #1f2937 !important;
                mix-blend-mode: normal !important;
            }
            .chatbot-message.user .chatbot-message-bubble,
            .chatbot-message.user .chatbot-message-bubble * {
                color: #ffffff !important;
                -webkit-text-fill-color: #ffffff !important;
            }
            .chatbot-messages {
                mix-blend-mode: normal !important;
            }
        `;
        document.head.appendChild(styleTag);
        
        // CRITICAL: Force container styles to prevent inheritance
        this.container.style.cssText = `
            background: #ffffff !important;
            color: #1f2937 !important;
            -webkit-text-fill-color: #1f2937 !important;
            visibility: visible !important;
        `;
        
        // Create HTML structure
        this.container.innerHTML = `
            <div class="chatbot-header" id="chatbot-header">
                <h3>💬 Logistics Assistant</h3>
                <div class="chatbot-header-actions">
                    <button class="chatbot-btn" id="chatbot-fullscreen-btn" title="Fullscreen" type="button">⛶</button>
                    <button class="chatbot-btn" id="chatbot-settings-btn" title="Settings" type="button">⚙️</button>
                    <button class="chatbot-btn" id="chatbot-minimize-btn" title="Minimize" type="button">−</button>
                </div>
            </div>
            <div class="chatbot-body">
                <div class="chatbot-messages" id="chatbot-messages"></div>
                <div class="chatbot-suggestions" id="chatbot-suggestions" style="display: none;">
                    <div class="chatbot-suggestions-header">
                        <div class="chatbot-suggestions-title">Suggested Questions</div>
                        <button class="chatbot-suggestions-toggle" id="chatbot-suggestions-toggle" title="Toggle suggestions">
                            <span class="chatbot-suggestions-arrow">▼</span>
                        </button>
                    </div>
                    <div class="chatbot-suggestion-chips" id="chatbot-suggestion-chips"></div>
                </div>
                <div class="chatbot-input-container">
                    <div class="chatbot-input-wrapper">
                        <input 
                            type="text" 
                            class="chatbot-input" 
                            id="chatbot-input" 
                            placeholder="Type your question here..."
                            autocomplete="off"
                            value=""
                            style="color: #1f2937 !important; -webkit-text-fill-color: #1f2937 !important; caret-color: #1f2937 !important; background: transparent !important; position: relative !important; z-index: 999 !important; mix-blend-mode: normal !important;"
                        />
                        <div class="chatbot-autocomplete" id="chatbot-autocomplete"></div>
                        <button class="chatbot-process-btn" id="chatbot-process-btn" title="Process Files" type="button" style="display: none; margin-right: 5px; padding: 8px 12px; background: #10b981; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 12px;">
                            ⚙️ Process
                        </button>
                        <button class="chatbot-send-btn" id="chatbot-send-btn" title="Send" type="button">
                            ➤
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // Append container to wrapper
        wrapper.appendChild(this.container);
        
        // Append wrapper to body
        document.body.appendChild(wrapper);
        this.wrapper = wrapper;
        
        // CRITICAL: Force input visibility immediately with ALL properties
        setTimeout(() => {
            const input = document.getElementById('chatbot-input');
            if (input) {
                input.style.cssText = `
                    flex: 1;
                    border: none;
                    background: transparent !important;
                    outline: none;
                    font-size: 14px !important;
                    color: #1f2937 !important;
                    -webkit-text-fill-color: #1f2937 !important;
                    caret-color: #1f2937 !important;
                    padding: 8px 0;
                    font-family: inherit;
                    opacity: 1 !important;
                    visibility: visible !important;
                    display: block !important;
                `;
                input.removeAttribute('disabled');
                input.removeAttribute('readonly');
                input.disabled = false;
                input.readOnly = false;
                
                // Force caret to be visible
                input.setAttribute('autocomplete', 'off');
                input.setAttribute('spellcheck', 'false');
            }
            
            // Force messages container
            const messagesEl = document.getElementById('chatbot-messages');
            if (messagesEl) {
                messagesEl.style.cssText = `
                    flex: 1;
                    overflow-y: auto;
                    padding: 20px;
                    display: flex;
                    flex-direction: column;
                    gap: 16px;
                    background: #f8f9fa !important;
                    color: #1f2937 !important;
                    mix-blend-mode: normal !important;
                    position: relative !important;
                    z-index: 1 !important;
                `;
                
                // Remove any overlays from messages
                const allMessages = messagesEl.querySelectorAll('.chatbot-message');
                allMessages.forEach(msg => {
                    msg.style.setProperty('mix-blend-mode', 'normal', 'important');
                    msg.style.setProperty('position', 'relative', 'important');
                    msg.style.setProperty('z-index', '1', 'important');
                });
            }
        }, 50);
        
        // Create settings modal immediately
        this.createSettingsModal();
        
        console.log('Widget created, settings modal should be ready');
    }

    createSettingsModal() {
        const modal = document.createElement('div');
        modal.className = 'chatbot-modal';
        modal.id = 'chatbot-settings-modal';
        modal.innerHTML = `
            <div class="chatbot-modal-content chatbot-settings-content">
                <div class="chatbot-modal-header">
                    <h3>⚙️ Settings</h3>
                    <button class="chatbot-modal-close" id="chatbot-modal-close">×</button>
                </div>
                <div class="chatbot-settings-tabs">
                    <button class="chatbot-tab-btn active" data-tab="files">📁 Files</button>
                    <button class="chatbot-tab-btn" data-tab="download">📥 Download</button>
                    <button class="chatbot-tab-btn" data-tab="train">🎓 Train</button>
                    <button class="chatbot-tab-btn" data-tab="faqs">❓ FAQs</button>
                </div>
                
                <!-- Files Tab -->
                <div class="chatbot-tab-content active" id="tab-files">
                    <div class="chatbot-form-group">
                        <label>Files Folder Path</label>
                        <div class="chatbot-input-with-btn">
                            <input type="text" id="settings-files-folder-path" placeholder="E:/Bluemingo Project/SLM Excel Files Path" />
                        </div>
                        <small>Select folder containing Excel/CSV files. Files in this folder will appear in the list below.</small>
                    </div>
                    
                    <div class="chatbot-form-group">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                            <label style="margin: 0;">Available Files</label>
                        </div>
                        <div class="chatbot-file-list" id="file-list-container">
                            <div class="chatbot-loading-text">Loading files...</div>
                        </div>
                        <div class="chatbot-file-actions">
                            <button class="chatbot-btn-secondary" id="refresh-files-btn">🔄 Refresh</button>
                            <button class="chatbot-btn-secondary" id="select-all-files-btn">✓ Select All</button>
                            <button class="chatbot-btn-secondary" id="deselect-all-files-btn">✗ Deselect All</button>
                            <button class="chatbot-btn-primary" id="process-files-btn" style="font-weight: bold;">⚙️ Process Selected Files</button>
                        </div>
                        <small style="display: block; margin-top: 8px; color: #6b7280;">
                            💡 <strong>Tip:</strong> Select files and click "Process Selected Files" to add them to the database. Files must be processed before you can query them.
                        </small>
                    </div>
                </div>
                
                <!-- Download Tab -->
                <div class="chatbot-tab-content" id="tab-download">
                    <div class="chatbot-form-group">
                        <label>Download Path</label>
                        <div class="chatbot-input-with-btn">
                            <input type="text" id="settings-download-path" placeholder="C:/Users/YourName/Downloads" />
                            <input type="file" id="browse-download-path-input" webkitdirectory directory multiple style="display: none;" />
                            <button class="chatbot-btn-small" id="browse-download-path-btn">Browse</button>
                        </div>
                        <small>Where to save downloaded answers</small>
                    </div>
                </div>
                
                <!-- Train Tab -->
                <div class="chatbot-tab-content" id="tab-train">
                    <div class="chatbot-form-group">
                        <label>Question</label>
                        <input type="text" id="train-question-input" placeholder="e.g., What is the total transportation cost associated with this consignment?" style="width: 100%; padding: 10px; border: 1px solid #e5e7eb; border-radius: 8px; font-size: 14px;" />
                        <small>Enter the question you want to train</small>
                    </div>
                    
                    <div class="chatbot-form-group">
                        <label>Answer</label>
                        <div style="margin-bottom: 10px;">
                            <button class="chatbot-btn-secondary" id="train-answer-type-text" style="margin-right: 5px;">📝 Text</button>
                            <button class="chatbot-btn-secondary" id="train-answer-type-file" style="margin-right: 5px;">📄 Excel File</button>
                        </div>
                        
                        <!-- Text Input -->
                        <div id="train-answer-text-container">
                            <textarea id="train-answer-text-input" placeholder="Paste or type your desired answer here..." style="width: 100%; min-height: 200px; padding: 10px; border: 1px solid #e5e7eb; border-radius: 8px; font-size: 14px; font-family: inherit; resize: vertical;"></textarea>
                        </div>
                        
                        <!-- File Input -->
                        <div id="train-answer-file-container" style="display: none;">
                            <input type="file" id="train-answer-file-input" accept=".xlsx,.xls,.csv,.xlsm,.xlsb" />
                            <small style="display: block; margin-top: 5px;">Upload an Excel/CSV file containing the answer data</small>
                        </div>
                    </div>
                    
                    <div class="chatbot-form-group">
                        <button class="chatbot-btn-primary" id="save-training-btn" style="width: 100%;">💾 Save Training Data</button>
                    </div>
                    
                    <div class="chatbot-form-group" style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
                        <label>Saved Training Data</label>
                        <div class="chatbot-training-list" id="training-list-container" style="max-height: 300px; overflow-y: auto; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; background: #f9fafb;">
                            <div class="chatbot-loading-text">Loading training data...</div>
                        </div>
                    </div>
                </div>
                
                <!-- FAQs Tab -->
                <div class="chatbot-tab-content" id="tab-faqs">
                    <div class="chatbot-faqs-container" id="faqs-container">
                        <div class="chatbot-loading-text">Loading FAQs...</div>
                    </div>
                </div>
                
                <div class="chatbot-form-actions">
                    <button class="chatbot-btn-secondary" id="settings-cancel-btn">Close</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        // Setup tab switching
        this.setupSettingsTabs();
        // Load files and FAQs
        this.loadFilesList();
        this.loadFAQs();
    }

    setupEventListeners() {
        console.log('Setting up event listeners...');
        
        // Use event delegation on the container for better reliability
        if (!this.container) {
            console.error('Container not found!');
            return;
        }
        
        // Minimize button - use delegation
        this.container.addEventListener('click', (e) => {
            if (e.target && (e.target.id === 'chatbot-minimize-btn' || e.target.closest('#chatbot-minimize-btn'))) {
                e.preventDefault();
                e.stopPropagation();
                this.toggleMinimize();
            }
        });
        
        // Header click to toggle
        const header = document.getElementById('chatbot-header');
        if (header) {
            header.addEventListener('click', (e) => {
                // Don't toggle if clicking on buttons
                if (!e.target.closest('.chatbot-header-actions')) {
                    if (this.isMinimized) {
                        this.toggleMinimize();
                    }
                }
            });
        }
        
        // Send button - use delegation
        this.container.addEventListener('click', (e) => {
            if (e.target && (e.target.id === 'chatbot-send-btn' || e.target.closest('#chatbot-send-btn'))) {
                e.preventDefault();
                e.stopPropagation();
                console.log('Send button clicked');
                // Always call sendMessage - it will handle empty input
                this.sendMessage();
            }
        });
        
        // Input - get reference and set up listeners
        const input = document.getElementById('chatbot-input');
        if (!input) {
            console.error('Input element not found!');
            // Try again after a short delay
            setTimeout(() => this.setupEventListeners(), 200);
            return;
        }
        
        console.log('Input found, setting up listeners');
        
        // Make sure input is enabled and can accept text
        input.disabled = false;
        input.readOnly = false;
        input.removeAttribute('disabled');
        input.removeAttribute('readonly');
        input.setAttribute('tabindex', '0');
        input.style.cssText += `
            pointer-events: auto !important;
            opacity: 1 !important;
            visibility: visible !important;
            display: block !important;
            color: #1f2937 !important;
            -webkit-text-fill-color: #1f2937 !important;
            text-fill-color: #1f2937 !important;
            background-color: transparent !important;
            cursor: text !important;
            z-index: 12 !important;
            position: relative !important;
            -webkit-user-select: text !important;
            user-select: text !important;
            font-size: 14px !important;
            width: 100% !important;
        `;
        
        // Remove any overlaying elements that might block input
        const wrapper = input.parentElement;
        if (wrapper) {
            wrapper.style.setProperty('pointer-events', 'auto', 'important');
            wrapper.style.setProperty('z-index', '11', 'important');
            // Check for blocking siblings
            const siblings = Array.from(wrapper.children);
            siblings.forEach(child => {
                if (child !== input && child.id !== 'chatbot-autocomplete' && child.id !== 'chatbot-send-btn') {
                    const computed = window.getComputedStyle(child);
                    if (computed.pointerEvents !== 'none') {
                        child.style.setProperty('pointer-events', 'none', 'important');
                    }
                }
            });
        }
        
        // Check for any overlaying elements at input position
        const rect = input.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        const elementsAtPoint = document.elementsFromPoint(centerX, centerY);
        const blockingElements = elementsAtPoint.filter(el => 
            el !== input && 
            !input.contains(el) && 
            !el.contains(input) &&
            el.id !== 'chatbot-autocomplete' &&
            window.getComputedStyle(el).pointerEvents !== 'none' &&
            window.getComputedStyle(el).zIndex !== 'auto'
        );
        if (blockingElements.length > 0) {
            console.warn('⚠️ Found potentially blocking elements:', blockingElements);
            blockingElements.forEach(el => {
                el.style.setProperty('pointer-events', 'none', 'important');
            });
        }
        
        // Test input - set a test value to verify it works
        console.log('Input enabled:', !input.disabled, 'readonly:', input.readOnly);
        console.log('Input can accept text - testing...');
        
        // Force focus to test
        setTimeout(() => {
            try {
                input.focus();
                input.click();
                console.log('✅ Input focused and clicked');
            } catch (e) {
                console.error('Error focusing input:', e);
            }
        }, 100);
        
        // Add event listeners to verify input works
        input.addEventListener('input', function(e) {
            console.log('✅ Input event fired, value:', e.target.value);
        });
        
        input.addEventListener('focus', function() {
            console.log('✅ Input focused');
        });
        
        input.addEventListener('click', function(e) {
            console.log('✅ Input clicked');
            e.stopPropagation();
        });
        
        // Test typing programmatically
        setTimeout(() => {
            input.focus();
            // Simulate typing 'a' to test
            const keyEvent = new KeyboardEvent('keydown', { key: 'a', bubbles: true });
            input.dispatchEvent(keyEvent);
        }, 200);
        
        // Input enter key - ONLY prevent default for specific keys
        input.addEventListener('keydown', (e) => {
            // Only prevent default for navigation/control keys, NOT for regular typing
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                e.stopPropagation();
                if (this.currentAutocompleteIndex >= 0 && this.autocompleteItems.length > 0) {
                    this.selectAutocompleteItem(this.currentAutocompleteIndex);
                } else {
                    console.log('Enter pressed, input value:', input.value);
                    if (input.value.trim()) {
                        this.sendMessage();
                    } else {
                        console.log('Empty input on Enter');
                    }
                }
            } else if (e.key === 'ArrowDown' && this.autocompleteItems.length > 0) {
                e.preventDefault();
                e.stopPropagation();
                this.navigateAutocomplete(1);
            } else if (e.key === 'ArrowUp' && this.autocompleteItems.length > 0) {
                e.preventDefault();
                e.stopPropagation();
                this.navigateAutocomplete(-1);
            } else if (e.key === 'Tab' && this.autocompleteItems.length > 0) {
                e.preventDefault();
                e.stopPropagation();
                if (this.currentAutocompleteIndex >= 0) {
                    this.selectAutocompleteItem(this.currentAutocompleteIndex);
                } else {
                    this.selectAutocompleteItem(0);
                }
            } else if (e.key === 'Escape') {
                e.preventDefault();
                this.hideAutocomplete();
            }
            // For all other keys (typing), allow default behavior - DON'T prevent default
        });
        
        // Input typing - trigger autocomplete and close suggestions
        input.addEventListener('input', (e) => {
            console.log('✅ INPUT EVENT - Value changed to:', e.target.value);
            
            // CRITICAL: Force text color and caret color on every input event
            e.target.style.setProperty('color', '#1f2937', 'important');
            e.target.style.setProperty('-webkit-text-fill-color', '#1f2937', 'important');
            e.target.style.setProperty('caret-color', '#1f2937', 'important');
            
            // Debug: Log computed styles
            const computed = window.getComputedStyle(e.target);
            console.log('Input computed color:', computed.color, '| webkit-text-fill-color:', computed.webkitTextFillColor);
            
            // Clear any existing timeouts
            if (this.autocompleteTimeout) {
                clearTimeout(this.autocompleteTimeout);
                this.autocompleteTimeout = null;
            }
            if (this.suggestionsTimeout) {
                clearTimeout(this.suggestionsTimeout);
                this.suggestionsTimeout = null;
            }
            
            const value = e.target.value;
            
            if (value && value.trim().length >= 1) {
                // User is typing - hide suggestions immediately and show autocomplete
                this.hideSuggestions();
                // Set flag to prevent suggestions from showing
                this.preventSuggestions = true;
                
                // Trigger autocomplete after a small delay
                this.autocompleteTimeout = setTimeout(() => {
                    // Double-check input still has value (user might have cleared it)
                    const currentValue = input.value;
                    if (currentValue && currentValue.trim().length >= 1) {
                        // Make sure suggestions are hidden before showing autocomplete
                        this.hideSuggestions();
                        this.handleAutocomplete(currentValue);
                    }
                }, 150); // Reduced delay for faster response
            } else {
                // Input is cleared - hide autocomplete immediately
                this.hideAutocomplete();
                // Reset prevent suggestions flag when input is empty
                this.preventSuggestions = false;
                
                // Show suggestions smoothly after a delay, but only if input is still empty
                this.suggestionsTimeout = setTimeout(() => {
                    const currentValue = input.value;
                    // Only show suggestions if input is still empty and not blocked
                    if (!currentValue || currentValue.trim().length === 0) {
                        if (!this.preventSuggestions) {
                            // Make sure autocomplete is hidden before showing suggestions
                            this.hideAutocomplete();
                            this.showSuggestionsIfAvailable();
                        }
                    }
                }, 200);
            }
        });
        
        // Input focus
        input.addEventListener('focus', () => {
            console.log('✅ Input focused, current value:', input.value);
            // CRITICAL: Force text color and caret color on focus
            input.style.setProperty('color', '#1f2937', 'important');
            input.style.setProperty('-webkit-text-fill-color', '#1f2937', 'important');
            input.style.setProperty('caret-color', '#1f2937', 'important');
            
            // Debug: Log computed styles
            const computed = window.getComputedStyle(input);
            console.log('Input focused - computed color:', computed.color, '| webkit-text-fill-color:', computed.webkitTextFillColor, '| caret-color:', computed.caretColor);
            
            if (input.value && input.value.length >= 2) {
                this.handleAutocomplete(input.value);
            }
        });
        
        // Test if input accepts text by programmatically setting value
        setTimeout(() => {
            const testValue = 'test';
            input.value = testValue;
            console.log('Test: Set input value to "test", current value:', input.value);
            if (input.value !== testValue) {
                console.error('❌ Input value was cleared or blocked!');
            } else {
                console.log('✅ Input accepts programmatic value setting');
                input.value = ''; // Clear test value
            }
        }, 500);
        
        // Settings button - use event delegation
        document.addEventListener('click', (e) => {
            const target = e.target;
            if (target && (target.id === 'chatbot-settings-btn' || target.closest('#chatbot-settings-btn'))) {
                e.preventDefault();
                e.stopPropagation();
                console.log('Settings button clicked');
                this.openSettings();
            }
        });
        
        // Click outside to close autocomplete
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.chatbot-input-wrapper')) {
                this.hideAutocomplete();
            }
        });
        
        // Suggestion chips click
        this.container.addEventListener('click', (e) => {
            if (e.target && e.target.classList.contains('chatbot-suggestion-chip')) {
                e.preventDefault();
                e.stopPropagation();
                const suggestion = e.target.textContent;
                
                // Mark this suggestion as used
                if (!this.usedSuggestions.includes(suggestion)) {
                    this.usedSuggestions.push(suggestion);
                    console.log('Marked suggestion as used:', suggestion);
                }
                
                this.setInputValue(suggestion);
                if (input) {
                    input.focus();
                    this.hideSuggestions();
                }
            }
            
            // Suggestions toggle button
            if (e.target && (e.target.id === 'chatbot-suggestions-toggle' || e.target.closest('#chatbot-suggestions-toggle'))) {
                e.preventDefault();
                e.stopPropagation();
                this.toggleSuggestions();
            }
            
            // Fullscreen button
            if (e.target && (e.target.id === 'chatbot-fullscreen-btn' || e.target.closest('#chatbot-fullscreen-btn'))) {
                e.preventDefault();
                e.stopPropagation();
                this.toggleFullscreen();
            }
        });
        
        console.log('Event listeners set up successfully');
    }
    
    setupSettingsTabs() {
        // Use event delegation on the tabs container for better reliability
        const tabsContainer = document.querySelector('.chatbot-settings-tabs');
        if (tabsContainer) {
            tabsContainer.addEventListener('click', (e) => {
                const btn = e.target.closest('.chatbot-tab-btn');
                if (!btn) return;
                
                e.preventDefault();
                e.stopPropagation();
                
                const targetTab = btn.dataset.tab;
                console.log('Tab clicked:', targetTab);
                
                // Remove active class from all
                document.querySelectorAll('.chatbot-tab-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.chatbot-tab-content').forEach(c => c.classList.remove('active'));
                
                // Add active class to clicked tab
                btn.classList.add('active');
                const targetContent = document.getElementById(`tab-${targetTab}`);
                if (targetContent) {
                    targetContent.classList.add('active');
                    console.log('Tab content activated:', `tab-${targetTab}`);
                    
                    // Load training data if train tab is clicked
                    if (targetTab === 'train') {
                        setTimeout(() => {
                            this.loadTrainingData();
                        }, 100);
                    }
                } else {
                    console.error('Tab content not found:', `tab-${targetTab}`);
                }
            });
        } else {
            // Fallback: attach to individual buttons
            const tabButtons = document.querySelectorAll('.chatbot-tab-btn');
            tabButtons.forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    const targetTab = btn.dataset.tab;
                    
                    // Remove active class from all
                    document.querySelectorAll('.chatbot-tab-btn').forEach(b => b.classList.remove('active'));
                    document.querySelectorAll('.chatbot-tab-content').forEach(c => c.classList.remove('active'));
                    
                    // Add active class to clicked tab
                    btn.classList.add('active');
                    const targetContent = document.getElementById(`tab-${targetTab}`);
                    if (targetContent) {
                        targetContent.classList.add('active');
                        if (targetTab === 'train') {
                            setTimeout(() => {
                                this.loadTrainingData();
                            }, 100);
                        }
                    }
                });
            });
        }
        
        // Setup settings modal event listeners
        const modal = document.getElementById('chatbot-settings-modal');
        if (modal) {
            // Close button
            const modalClose = document.getElementById('chatbot-modal-close');
            if (modalClose) {
                modalClose.addEventListener('click', () => this.closeSettings());
            }
            
            // Cancel button
            const settingsCancel = document.getElementById('settings-cancel-btn');
            if (settingsCancel) {
                settingsCancel.addEventListener('click', () => this.closeSettings());
            }
            
            // Close on outside click
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeSettings();
                }
            });
            
            // Files folder path input - auto-save on Enter or blur
            
            const refreshFilesBtn = document.getElementById('refresh-files-btn');
            if (refreshFilesBtn) {
                refreshFilesBtn.addEventListener('click', () => this.loadFilesList());
            }
            
            
            const selectAllBtn = document.getElementById('select-all-files-btn');
            if (selectAllBtn) {
                selectAllBtn.addEventListener('click', () => this.selectAllFiles());
            }
            
            const deselectAllBtn = document.getElementById('deselect-all-files-btn');
            if (deselectAllBtn) {
                deselectAllBtn.addEventListener('click', () => this.deselectAllFiles());
            }
            
            const processFilesBtn = document.getElementById('process-files-btn');
            if (processFilesBtn) {
                processFilesBtn.addEventListener('click', () => this.processSelectedFiles());
            }
            
            // Add event listener for Process button in input box
            const processBtn = document.getElementById('chatbot-process-btn');
            if (processBtn) {
                processBtn.addEventListener('click', () => {
                    // Open settings modal to Files tab
                    this.openSettings();
                    // Switch to Files tab
                    setTimeout(() => {
                        const filesTab = document.querySelector('[data-tab="files"]');
                        if (filesTab) {
                            filesTab.click();
                        }
                        // Select all unprocessed files and process
                        setTimeout(() => {
                            this.selectUnprocessedFiles();
                            this.processSelectedFiles();
                        }, 500);
                    }, 300);
                });
            }
            
            
            // Download tab buttons
            const browseDownloadBtn = document.getElementById('browse-download-path-btn');
            const browseDownloadInput = document.getElementById('browse-download-path-input');
            if (browseDownloadBtn && browseDownloadInput) {
                browseDownloadBtn.addEventListener('click', () => {
                    browseDownloadInput.click();
                });
                browseDownloadInput.addEventListener('change', (e) => {
                    const files = e.target.files;
                    if (files && files.length > 0) {
                        const firstFile = files[0];
                        if (firstFile.path) {
                            const fullPath = firstFile.path;
                            const dirPath = fullPath.substring(0, fullPath.lastIndexOf('\\') || fullPath.lastIndexOf('/'));
                            const input = document.getElementById('settings-download-path');
                            if (input) {
                                input.value = dirPath;
                                this.saveSettings();
                            }
                        } else {
                            // Fallback for web browsers
                            const path = firstFile.webkitRelativePath || '';
                            const pathParts = path.split('/');
                            if (pathParts.length > 1) {
                                pathParts.pop();
                                const dirPath = pathParts.join('/');
                                const input = document.getElementById('settings-download-path');
                                if (input) {
                                    const userPath = prompt('Please enter the full folder path. Selected folder:', dirPath);
                                    if (userPath) {
                                        input.value = userPath;
                                        this.saveSettings();
                                    }
                                }
                            }
                        }
                    }
                });
            }
            
            // Auto-save on input change
            const downloadPathInput = document.getElementById('settings-download-path');
            if (downloadPathInput) {
                downloadPathInput.addEventListener('change', () => this.saveSettings());
            }
            
            const filesFolderInput = document.getElementById('settings-files-folder-path');
            if (filesFolderInput) {
                // Auto-save on Enter key
                filesFolderInput.addEventListener('keypress', async (e) => {
                    if (e.key === 'Enter') {
                        const path = filesFolderInput.value.trim();
                        if (path) {
                            this.settings.filesFolderPath = path;
                            await this.saveSettings();
                            // Reload files after saving
                            setTimeout(() => {
                                this.loadFilesList();
                            }, 300);
                        }
                    }
                });
                // Also trigger on blur (when user leaves the field)
                filesFolderInput.addEventListener('blur', async () => {
                    const path = filesFolderInput.value.trim();
                    if (path && path !== this.settings.filesFolderPath) {
                        this.settings.filesFolderPath = path;
                        await this.saveSettings();
                        setTimeout(() => {
                            this.loadFilesList();
                        }, 300);
                    }
                });
            }
            
            // Train tab event listeners
            const trainAnswerTypeText = document.getElementById('train-answer-type-text');
            const trainAnswerTypeFile = document.getElementById('train-answer-type-file');
            const trainAnswerTextContainer = document.getElementById('train-answer-text-container');
            const trainAnswerFileContainer = document.getElementById('train-answer-file-container');
            
            if (trainAnswerTypeText && trainAnswerTypeFile && trainAnswerTextContainer && trainAnswerFileContainer) {
                // Set initial state - text mode active
                trainAnswerTypeText.style.background = '#667eea';
                trainAnswerTypeText.style.color = 'white';
                trainAnswerTypeText.style.borderRadius = '6px';
                trainAnswerTypeFile.style.borderRadius = '6px';
                
                trainAnswerTypeText.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    trainAnswerTextContainer.style.display = 'block';
                    trainAnswerFileContainer.style.display = 'none';
                    trainAnswerTypeText.style.background = '#667eea';
                    trainAnswerTypeText.style.color = 'white';
                    trainAnswerTypeFile.style.background = '';
                    trainAnswerTypeFile.style.color = '';
                });
                
                trainAnswerTypeFile.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    trainAnswerTextContainer.style.display = 'none';
                    trainAnswerFileContainer.style.display = 'block';
                    trainAnswerTypeFile.style.background = '#667eea';
                    trainAnswerTypeFile.style.color = 'white';
                    trainAnswerTypeText.style.background = '';
                    trainAnswerTypeText.style.color = '';
                });
            }
            
            const saveTrainingBtn = document.getElementById('save-training-btn');
            if (saveTrainingBtn) {
                saveTrainingBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    this.saveTrainingData();
                });
            }
            
            // Load training data when Train tab is clicked
            const trainTabBtn = document.querySelector('[data-tab="train"]');
            if (trainTabBtn) {
                // Remove any existing listener first
                const newTrainTabBtn = trainTabBtn.cloneNode(true);
                trainTabBtn.parentNode.replaceChild(newTrainTabBtn, trainTabBtn);
                
                newTrainTabBtn.addEventListener('click', () => {
                    setTimeout(() => {
                        this.loadTrainingData();
                    }, 100);
                });
            }
            
            // Train tab event listeners - attach after a small delay to ensure elements exist
            setTimeout(() => {
                const trainAnswerTypeText = document.getElementById('train-answer-type-text');
                const trainAnswerTypeFile = document.getElementById('train-answer-type-file');
                const trainAnswerTextContainer = document.getElementById('train-answer-text-container');
                const trainAnswerFileContainer = document.getElementById('train-answer-file-container');
                
                if (trainAnswerTypeText && trainAnswerTypeFile && trainAnswerTextContainer && trainAnswerFileContainer) {
                    // Set initial state - text mode active
                    trainAnswerTypeText.style.background = '#667eea';
                    trainAnswerTypeText.style.color = 'white';
                    trainAnswerTypeText.style.borderRadius = '6px';
                    trainAnswerTypeText.style.padding = '8px 16px';
                    trainAnswerTypeFile.style.borderRadius = '6px';
                    trainAnswerTypeFile.style.padding = '8px 16px';
                    
                    trainAnswerTypeText.addEventListener('click', (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        trainAnswerTextContainer.style.display = 'block';
                        trainAnswerFileContainer.style.display = 'none';
                        trainAnswerTypeText.style.background = '#667eea';
                        trainAnswerTypeText.style.color = 'white';
                        trainAnswerTypeFile.style.background = '';
                        trainAnswerTypeFile.style.color = '';
                    });
                    
                    trainAnswerTypeFile.addEventListener('click', (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        trainAnswerTextContainer.style.display = 'none';
                        trainAnswerFileContainer.style.display = 'block';
                        trainAnswerTypeFile.style.background = '#667eea';
                        trainAnswerTypeFile.style.color = 'white';
                        trainAnswerTypeText.style.background = '';
                        trainAnswerTypeText.style.color = '';
                    });
                }
                
                const saveTrainingBtn = document.getElementById('save-training-btn');
                if (saveTrainingBtn) {
                    // Remove any existing listeners
                    const newSaveBtn = saveTrainingBtn.cloneNode(true);
                    saveTrainingBtn.parentNode.replaceChild(newSaveBtn, saveTrainingBtn);
                    
                    newSaveBtn.addEventListener('click', (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        console.log('Save training button clicked');
                        this.saveTrainingData();
                    });
                }
                
                // Load training data when Train tab is clicked - handled by tab switching
                // Add observer to detect when train tab becomes active
                const trainTabContent = document.getElementById('tab-train');
                if (trainTabContent) {
                    const observer = new MutationObserver((mutations) => {
                        mutations.forEach((mutation) => {
                            if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                                if (trainTabContent.classList.contains('active')) {
                                    setTimeout(() => {
                                        this.loadTrainingData();
                                    }, 100);
                                }
                            }
                        });
                    });
                    observer.observe(trainTabContent, { attributes: true, attributeFilter: ['class'] });
                }
            }, 100);
        }
    }

    toggleMinimize() {
        this.isMinimized = !this.isMinimized;
        this.container.classList.toggle('minimized');
        const minimizeBtn = document.getElementById('chatbot-minimize-btn');
        minimizeBtn.textContent = this.isMinimized ? '+' : '−';
        
        // Show/hide minimized message
        if (this.isMinimized) {
            setTimeout(() => this.showMinimizedMessage(), 300);
        } else {
            this.hideMinimizedMessage();
        }
    }
    
    showMinimizedMessage() {
        // Remove any existing message first
        this.hideMinimizedMessage();
        
        // Create minimized message element
        const messageEl = document.createElement('div');
        messageEl.id = 'chatbot-minimized-message';
        messageEl.className = 'chatbot-minimized-message';
        messageEl.innerHTML = `
            <div class="chatbot-minimized-content">
                <div class="chatbot-minimized-icon">💬</div>
                <div class="chatbot-minimized-text">
                    <div class="chatbot-minimized-title">Hey there! 👋</div>
                    <div class="chatbot-minimized-subtitle">Click here for assistance</div>
                </div>
            </div>
        `;
        
        // Add click handler to restore chatbot
        messageEl.addEventListener('click', () => {
            this.toggleMinimize();
        });
        
        // Insert after the chatbot container wrapper
        if (this.container && this.container.parentElement) {
            this.container.parentElement.appendChild(messageEl);
        } else {
            document.body.appendChild(messageEl);
        }
    }
    
    hideMinimizedMessage() {
        const messageEl = document.getElementById('chatbot-minimized-message');
        if (messageEl) {
            messageEl.remove();
        }
    }
    
    toggleFullscreen() {
        this.isFullscreen = !this.isFullscreen;
        this.container.classList.toggle('fullscreen');
        const fullscreenBtn = document.getElementById('chatbot-fullscreen-btn');
        if (fullscreenBtn) {
            fullscreenBtn.textContent = this.isFullscreen ? '⛶' : '⛶';
            fullscreenBtn.title = this.isFullscreen ? 'Exit Fullscreen' : 'Fullscreen';
        }
    }
    
    toggleSuggestions() {
        const suggestionsEl = document.getElementById('chatbot-suggestions');
        if (suggestionsEl) {
            suggestionsEl.classList.toggle('collapsed');
        }
    }

    async loadGreeting() {
        try {
            console.log('Loading greeting from:', `${this.apiUrl}/greet`);
            const response = await fetch(`${this.apiUrl}/greet`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Greeting data:', data);
            
            // Make sure messages container exists
            const messagesEl = document.getElementById('chatbot-messages');
            if (!messagesEl) {
                console.error('Messages container not found when loading greeting!');
                setTimeout(() => this.loadGreeting(), 500);
                return;
            }
            
            if (data.message) {
                console.log('Adding greeting message:', data.message);
                this.addMessage('assistant', data.message);
            }
            
            // Only show suggestions if data is processed
            if (data.has_data && data.suggestions && data.suggestions.length > 0) {
                // CRITICAL: Remove duplicates and filter out used suggestions
                const uniqueSuggestions = [...new Set(data.suggestions)];
                const unusedSuggestions = uniqueSuggestions.filter(s => !this.usedSuggestions.includes(s));
                // Prefer unused, but allow used ones if not enough unused
                let limitedSuggestions = unusedSuggestions.slice(0, 3);
                if (limitedSuggestions.length < 3) {
                    const usedButAvailable = uniqueSuggestions.filter(s => this.usedSuggestions.includes(s));
                    limitedSuggestions = [...limitedSuggestions, ...usedButAvailable.slice(0, 3 - limitedSuggestions.length)];
                }
                
                // Clear any existing suggestions first - do this immediately
                this.hideSuggestions();
                
                // Small delay to ensure DOM is ready, but prevent multiple calls
                if (!this.suggestionsShown && limitedSuggestions.length > 0) {
                    setTimeout(() => {
                        console.log('Showing suggestions:', limitedSuggestions);
                        this.showSuggestions(limitedSuggestions);
                    }, 500);
                }
            } else {
                // If no data or no suggestions, hide suggestions
                this.hideSuggestions();
            }
            
            // Show/hide Process button based on data status
            const processBtn = document.getElementById('chatbot-process-btn');
            if (processBtn) {
                if (!data.has_data) {
                    processBtn.style.display = 'block';
                } else {
                    processBtn.style.display = 'none';
                }
            }
        } catch (error) {
            console.error('Error loading greeting:', error);
            console.error('API URL was:', this.apiUrl);
            // Use the same greeting format as backend for consistency
            this.addMessage('assistant', '👋 Hello! I\'m your Logistics Data Assistant. I can help you analyze your Excel/CSV files and answer questions about your logistics data. Please upload a file to begin.');
            // Show default suggestions (exactly 3)
            this.showSuggestions([
                "What are all the column names in this file?",
                "How many consignments are there in total?",
                "What is the total transportation cost?"
            ].slice(0, 3));
        }
    }

    async handleAutocomplete(query) {
        if (!query || query.trim().length < 1) {
            this.hideAutocomplete();
            return;
        }
        
        const trimmedQuery = query.trim().toLowerCase();
        
        // Get the last word or phrase for incremental suggestions
        const words = trimmedQuery.split(/\s+/);
        const lastWord = words[words.length - 1];
        
        // If query is too short, use common prefixes
        let searchQuery = trimmedQuery;
        if (trimmedQuery.length < 2) {
            this.hideAutocomplete();
            return;
        }
        
        // Enhanced keyword matching - check for keywords anywhere in query
        const keywordMap = {
            // Question starters
            'what': ['What are all the column names in this dataset?', 'What is the total transportation cost?', 'What are all the source locations?', 'What products are being shipped?', 'What is the total weight?'],
            'how': ['How many consignments are there in total?', 'How many records are present in the file?', 'How many unique customers are represented?', 'How many source locations are there?'],
            'which': ['Which transportation mode has the highest average transportation cost?', 'Which source location dispatches the most consignments?', 'Which destination location receives the most consignments?'],
            'when': ['What is the earliest dispatch date in the dataset?', 'What is the latest dispatch date in the dataset?'],
            'where': ['What are all unique source locations in the dataset?', 'What are all unique destination locations in the dataset?'],
            'show': ['What are all the column names in this dataset?', 'What are all unique products in the dataset?', 'What are all unique customers in the dataset?'],
            'list': ['What are all the column names in this dataset?', 'What are all unique products in the dataset?', 'What are all unique source locations in the dataset?'],
            // Keywords - weight related
            'weight': ['What is the total weight of all shipments?', 'What is the average weight per consignment?', 'How does average weight per consignment vary by transportation mode?', 'What is the weight per case ratio for each product?'],
            'kg': ['What is the total weight of all shipments?', 'What is the average weight per consignment?', 'What is the cost per kilogram for each consignment?'],
            'kilogram': ['What is the total weight of all shipments?', 'What is the average weight per consignment?', 'What is the cost per kilogram for each consignment?'],
            // Keywords - cost related
            'cost': ['What is the total transportation cost across all consignments?', 'What is the average transportation cost per consignment?', 'What is the cost per case for each consignment?', 'What is the cost per kilogram for each consignment?'],
            'price': ['What is the total transportation cost across all consignments?', 'What is the average transportation cost per consignment?'],
            'money': ['What is the total transportation cost across all consignments?', 'What is the total consignment MRP value across all records?'],
            'rupee': ['What is the total transportation cost across all consignments?', 'What is the average transportation cost per consignment?'],
            // Keywords - volume related
            'volume': ['What is the average volume across all consignments?', 'What is the total volume by transportation mode?', 'What is the average volume fill percentage across all shipments?'],
            'cubic': ['What is the average volume across all consignments?', 'What is the total volume by transportation mode?'],
            // Keywords - product related
            'product': ['What is the unique count of products in the dataset?', 'What are all unique products in the dataset?', 'Which product appears most frequently in the dataset?', 'What is the weight per case ratio for each product?'],
            'item': ['What is the unique count of products in the dataset?', 'What are all unique products in the dataset?'],
            // Keywords - customer related
            'customer': ['How many unique customers are represented?', 'What are all unique customers in the dataset?', 'Which customer has the highest number of consignments?', 'Which customer has the highest total transportation cost?'],
            'client': ['How many unique customers are represented?', 'What are all unique customers in the dataset?'],
            // Keywords - consignment related
            'consignment': ['What is the unique count of consignment numbers?', 'How many records are present in the file?', 'What is the average transportation cost per consignment?', 'What is the average weight per consignment?'],
            'order': ['How many unique orders are there in the dataset?', 'Which orders contain the most cases?'],
            'shipment': ['What is the total weight of all shipments?', 'What is the total transportation cost across all consignments?'],
            // Keywords - location related
            'source': ['What is the unique count of source locations?', 'What are all unique source locations in the dataset?', 'What are the unique source types available?', 'How many consignments originate from each source location?'],
            'destination': ['What is the unique count of destination locations?', 'What are all unique destination locations in the dataset?', 'What are the unique destination types available?', 'How many consignments are delivered to each destination location?'],
            'location': ['What is the unique count of source locations?', 'What is the unique count of destination locations?', 'What are all unique source locations in the dataset?', 'What are all unique destination locations in the dataset?'],
            // Keywords - transportation related
            'mode': ['What are the unique transportation modes available?', 'How many consignments use each transportation mode?', 'What is the total transportation cost by transportation mode?'],
            'transportation': ['What are the unique transportation modes available?', 'What is the total transportation cost across all consignments?', 'What is the total transportation cost by transportation mode?'],
            'vehicle': ['What are the unique transportation modes available?', 'How many consignments use each transportation mode?'],
            'truck': ['What are the unique transportation modes available?', 'How many consignments use each transportation mode?'],
            // Keywords - cases related
            'case': ['What is the total number of cases shipped across all consignments?', 'What is the average number of cases per consignment?', 'What is the cost per case for each consignment?', 'What is the weight per case ratio for each product?'],
            'cases': ['What is the total number of cases shipped across all consignments?', 'What is the average number of cases per consignment?', 'Which orders contain the most cases?']
        };
        
        // Check if query contains any keyword (not just at start)
        let suggestions = [];
        const queryWords = trimmedQuery.split(/\s+/);
        
        // First, check for question starters at the beginning
        for (const [keyword, keywordSuggestions] of Object.entries(keywordMap)) {
            if (trimmedQuery.startsWith(keyword)) {
                const matching = keywordSuggestions.filter(s => 
                    s.toLowerCase().startsWith(trimmedQuery) || 
                    s.toLowerCase().includes(lastWord)
                );
                if (matching.length > 0) {
                    suggestions = matching;
                    break;
                }
            }
        }
        
        // If no starter match, check if any keyword appears in the query
        if (suggestions.length === 0) {
            for (const word of queryWords) {
                if (keywordMap[word]) {
                    suggestions = keywordMap[word];
                    break;
                }
            }
        }
        
        // If we have local suggestions, show them immediately
        if (suggestions.length > 0) {
            this.showAutocomplete(suggestions.slice(0, 5), query.trim());
            return;
        }
        
        // Otherwise, fetch from API (which has better keyword matching)
        try {
            const response = await fetch(`${this.apiUrl}/autocomplete`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ query: searchQuery })
            });
            
            if (!response.ok) {
                // If API fails, try with just the last word
                if (lastWord.length >= 2 && lastWord !== trimmedQuery) {
                    const fallbackResponse = await fetch(`${this.apiUrl}/autocomplete`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ query: lastWord })
                    });
                    
                    if (fallbackResponse.ok) {
                        const fallbackData = await fallbackResponse.json();
                        if (fallbackData.suggestions && Array.isArray(fallbackData.suggestions) && fallbackData.suggestions.length > 0) {
                            this.showAutocomplete(fallbackData.suggestions.slice(0, 5), query.trim());
                            return;
                        }
                    }
                }
                this.hideAutocomplete();
                return;
            }
            
            const data = await response.json();
            if (data.suggestions && Array.isArray(data.suggestions) && data.suggestions.length > 0) {
                // Filter suggestions to match the current query better
                const filtered = data.suggestions.filter(s => 
                    s.toLowerCase().includes(trimmedQuery) || 
                    trimmedQuery.split(' ').some(word => s.toLowerCase().includes(word))
                );
                this.showAutocomplete(filtered.length > 0 ? filtered.slice(0, 5) : data.suggestions.slice(0, 5), query.trim());
            } else {
                this.hideAutocomplete();
            }
        } catch (error) {
            console.error('Error fetching autocomplete:', error);
            this.hideAutocomplete();
        }
    }

    showAutocomplete(suggestions, query) {
        // CRITICAL: Close suggestions immediately when autocomplete appears
        this.hideSuggestions();
        
        // Clear any pending suggestions timeout
        if (this.suggestionsTimeout) {
            clearTimeout(this.suggestionsTimeout);
            this.suggestionsTimeout = null;
        }
        
        // Set flag to prevent suggestions from showing
        this.preventSuggestions = true;
        
        // Double-check: ensure suggestions are actually hidden
        const suggestionsEl = document.getElementById('chatbot-suggestions');
        if (suggestionsEl) {
            suggestionsEl.style.display = 'none';
        }
        
        const autocompleteEl = document.getElementById('chatbot-autocomplete');
        autocompleteEl.innerHTML = '';
        this.autocompleteItems = suggestions;
        this.currentAutocompleteIndex = -1;
        
        // CRITICAL: Force background and text colors
        autocompleteEl.style.cssText = `
            position: absolute;
            bottom: 100%;
            left: 0;
            right: 0;
            background: #ffffff !important;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            margin-bottom: 8px;
            max-height: 200px;
            overflow-y: auto;
            z-index: 1002;
            display: block;
            opacity: 1 !important;
            visibility: visible !important;
        `;
        
        suggestions.forEach((suggestion, index) => {
            const item = document.createElement('div');
            item.className = 'chatbot-autocomplete-item';
            item.dataset.index = index;
            
            // CRITICAL: Force text color on each item
            item.style.cssText = `
                padding: 10px 16px;
                cursor: pointer;
                border-bottom: 1px solid #f3f4f6;
                font-size: 13px;
                color: #374151 !important;
                background: #ffffff !important;
                -webkit-text-fill-color: #374151 !important;
                mix-blend-mode: normal !important;
                transition: all 0.15s;
            `;
            
            // Highlight matching text
            const highlighted = this.highlightMatch(suggestion, query);
            item.innerHTML = highlighted;
            
            item.addEventListener('click', () => {
                this.selectAutocompleteItem(index);
            });
            
            // Ensure hover state has correct colors
            item.addEventListener('mouseenter', () => {
                item.style.background = '#f3f4f6 !important';
                item.style.color = '#667eea !important';
                item.style.setProperty('-webkit-text-fill-color', '#667eea', 'important');
            });
            
            item.addEventListener('mouseleave', () => {
                item.style.background = '#ffffff !important';
                item.style.color = '#374151 !important';
                item.style.setProperty('-webkit-text-fill-color', '#374151', 'important');
            });
            
            item.addEventListener('mouseenter', () => {
                this.currentAutocompleteIndex = index;
                this.updateAutocompleteHighlight();
            });
            
            autocompleteEl.appendChild(item);
        });
        
        autocompleteEl.classList.add('show');
    }

    highlightMatch(text, query) {
        const lowerText = text.toLowerCase();
        const lowerQuery = query.toLowerCase().trim();
        const words = lowerQuery.split(/\s+/);
        
        let result = text;
        let offset = 0;
        
        // Highlight all matching words
        words.forEach(word => {
            if (word.length < 2) return;
            
            const regex = new RegExp(`(${word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
            const matches = [...result.matchAll(regex)];
            
            // Replace from end to start to maintain indices
            for (let i = matches.length - 1; i >= 0; i--) {
                const match = matches[i];
                const before = result.substring(0, match.index);
                const matchText = result.substring(match.index, match.index + match[0].length);
                const after = result.substring(match.index + match[0].length);
                
                // Check if already highlighted
                if (!before.includes('<span class="highlight">') || !before.endsWith('</span>')) {
                    result = `${before}<span class="highlight">${matchText}</span>${after}`;
                }
            }
        });
        
        return result || text;
    }

    hideAutocomplete() {
        const autocompleteEl = document.getElementById('chatbot-autocomplete');
        if (autocompleteEl) {
            autocompleteEl.classList.remove('show');
            autocompleteEl.style.display = 'none';
        }
        this.currentAutocompleteIndex = -1;
        
        // Clear autocomplete timeout
        if (this.autocompleteTimeout) {
            clearTimeout(this.autocompleteTimeout);
            this.autocompleteTimeout = null;
        }
        
        // Reset prevent suggestions flag when autocomplete is hidden
        // This allows suggestions to show when input is empty
        // But only if input is actually empty
        const input = document.getElementById('chatbot-input');
        if (input && (!input.value || input.value.trim().length === 0)) {
            setTimeout(() => {
                this.preventSuggestions = false;
            }, 100);
        }
    }
    
    showSuggestionsIfAvailable() {
        // Check if input is empty before showing suggestions
        const input = document.getElementById('chatbot-input');
        if (!input || input.value.trim().length > 0) {
            return; // Don't show if input has text
        }
        
        // Get available suggestions (filter out used ones)
        const allSuggestions = [
            "What are all the column names in this file?",
            "How many consignments are there in total?",
            "What is the total transportation cost?",
            "What are all the source locations?",
            "What products are being shipped?"
        ];
        
        // Filter out used suggestions
        const unusedSuggestions = allSuggestions.filter(s => !this.usedSuggestions.includes(s));
        const suggestionsToShow = unusedSuggestions.length > 0 ? unusedSuggestions.slice(0, 3) : allSuggestions.slice(0, 3);
        
        if (suggestionsToShow.length > 0) {
            console.log('Showing suggestions after input cleared:', suggestionsToShow);
            this.showSuggestions(suggestionsToShow);
        }
    }

    navigateAutocomplete(direction) {
        if (this.autocompleteItems.length === 0) return;
        
        this.currentAutocompleteIndex += direction;
        
        if (this.currentAutocompleteIndex < 0) {
            this.currentAutocompleteIndex = this.autocompleteItems.length - 1;
        } else if (this.currentAutocompleteIndex >= this.autocompleteItems.length) {
            this.currentAutocompleteIndex = 0;
        }
        
        this.updateAutocompleteHighlight();
    }

    updateAutocompleteHighlight() {
        const items = document.querySelectorAll('.chatbot-autocomplete-item');
        items.forEach((item, index) => {
            if (index === this.currentAutocompleteIndex) {
                item.classList.add('highlighted');
                item.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
            } else {
                item.classList.remove('highlighted');
            }
        });
    }

    selectAutocompleteItem(index) {
        if (index >= 0 && index < this.autocompleteItems.length) {
            const input = document.getElementById('chatbot-input');
            this.setInputValue(this.autocompleteItems[index]);
            this.hideAutocomplete();
            if (input) {
                input.focus();
            }
        }
    }

    async sendMessage() {
        console.log('sendMessage called');
        
        // Try multiple ways to get the input
        let input = document.getElementById('chatbot-input');
        if (!input && this.container) {
            input = this.container.querySelector('#chatbot-input');
        }
        if (!input) {
            input = document.querySelector('#chatbot-input');
        }
        
        if (!input) {
            console.error('Input element not found!');
            alert('Input field not found. Please refresh the page.');
            return;
        }
        
        // Get the value - read it immediately
        const query = (input.value || '').trim();
        console.log('Query:', query, '| Input element:', input, '| Input value:', input.value, '| Input type:', input.type);
        
        if (!query) {
            console.log('Empty query - showing feedback');
            input.focus();
            // Show visual feedback
            const originalBorder = input.style.borderColor || '';
            input.style.borderColor = '#ef4444';
            input.style.boxShadow = '0 0 0 3px rgba(239, 68, 68, 0.1)';
            setTimeout(() => {
                input.style.borderColor = originalBorder;
                input.style.boxShadow = '';
            }, 2000);
            
            // Show a helpful message
            this.addMessage('assistant', 'Please type a question before sending. You can also click on suggested questions below!');
            return;
        }
        
        this.sendMessageWithQuery(query, input);
    }
    
    async sendMessageWithQuery(query, inputElement) {
        if (!inputElement) {
            inputElement = document.getElementById('chatbot-input');
        }
        
        console.log('sendMessageWithQuery called with:', query);
        
        // Add user message
        this.addMessage('user', query);
        if (inputElement) {
            // Prevent suggestions from showing immediately after clearing input
            this.preventSuggestions = true;
            // Hide both autocomplete and suggestions before clearing
            this.hideAutocomplete();
            this.hideSuggestions();
            inputElement.value = '';
            inputElement.focus();
            
            // Allow suggestions to show again after a delay (when user might want to type again)
            setTimeout(() => {
                this.preventSuggestions = false;
                // Only show suggestions if input is still empty
                if (!inputElement.value || inputElement.value.trim().length === 0) {
                    // Ensure autocomplete is hidden before showing suggestions
                    this.hideAutocomplete();
                    this.showSuggestionsIfAvailable();
                }
            }, 500);
        } else {
            // If no input element, still hide both
            this.hideAutocomplete();
            this.hideSuggestions();
        }
        
        // Show loading
        const loadingId = this.addLoadingMessage();
        
        try {
            console.log('Sending query to:', `${this.apiUrl}/query`);
            // Create abort controller for timeout (browser compatibility)
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 second timeout
            
            const response = await fetch(`${this.apiUrl}/query`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ query }),
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                let errorMessage = `HTTP error! status: ${response.status}`;
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.error || errorData.answer || errorMessage;
                    console.error('API Error Details:', errorData);
                } catch (e) {
                    console.error('Could not parse error response');
                }
                throw new Error(errorMessage);
            }
            
            const data = await response.json();
            console.log('Response data:', data);
            
            // Remove loading
            this.removeMessage(loadingId);
            
            if (data.error) {
                this.addMessage('assistant', `Error: ${data.answer || data.error}`);
            } else {
                // Filter out personal information from answers
                let answer = data.answer || 'No answer provided';
                
                // Check if answer contains personal information
                const personalInfoPatterns = [
                    /Full Name\s*[^\n]*/gi,
                    /Mobile Number\s*[^\n]*/gi,
                    /Email Address\s*[^\n]*/gi,
                    /Current Company\s*[^\n]*/gi,
                    /Current Designation\s*[^\n]*/gi,
                    /Current CTC\s*[^\n]*/gi,
                    /Exp CTC\s*[^\n]*/gi,
                    /Notice Period\s*[^\n]*/gi,
                    /Work Experience\s*[^\n]*/gi,
                    /Total Experience\s*[^\n]*/gi
                ];
                
                let hasPersonalInfo = false;
                personalInfoPatterns.forEach(pattern => {
                    if (pattern.test(answer)) {
                        hasPersonalInfo = true;
                    }
                });
                
                // If personal info detected, replace with appropriate message
                if (hasPersonalInfo) {
                    answer = "I'm sorry, I don't have access to personal information or individual details. I can only help you with aggregated logistics data, such as:\n\n• Total consignments, costs, and metrics\n• Product information and shipping details\n• Source and destination locations\n• Transportation and utilization statistics\n\nPlease ask questions about your logistics data instead.";
                }
                
                // Add assistant response
                this.addMessage('assistant', answer, {
                    numericValue: data.numeric_value,
                    suggestions: data.suggestions,
                    followUpMessage: data.follow_up_message,
                    askAboutFaqs: data.ask_about_faqs
                });
                
                // Show suggestions if available (filter out used ones, limit to 3)
                // But only if input is empty (for greetings, this ensures suggestions show properly)
                if (data.suggestions && data.suggestions.length > 0) {
                    const uniqueSuggestions = [...new Set(data.suggestions)];
                    const unusedSuggestions = uniqueSuggestions.filter(s => !this.usedSuggestions.includes(s));
                    // Prefer unused, but allow used ones if not enough unused
                    let limitedSuggestions = unusedSuggestions.slice(0, 3);
                    if (limitedSuggestions.length < 3) {
                        const usedButAvailable = uniqueSuggestions.filter(s => this.usedSuggestions.includes(s));
                        limitedSuggestions = [...limitedSuggestions, ...usedButAvailable.slice(0, 3 - limitedSuggestions.length)];
                    }
                    if (limitedSuggestions.length > 0) {
                        setTimeout(() => {
                            // Check if input is empty before showing suggestions
                            const input = document.getElementById('chatbot-input');
                            if (!input || !input.value || input.value.trim().length === 0) {
                                // Ensure autocomplete is hidden before showing suggestions
                                this.hideAutocomplete();
                                this.showSuggestions(limitedSuggestions, data.follow_up_message);
                            }
                        }, 300);
                    }
                }
                
                // Don't show FAQ prompt automatically - only show if user explicitly asks
                // Removed automatic FAQ prompt
            }
        } catch (error) {
            console.error('Error sending message:', error);
            this.removeMessage(loadingId);
            
            // Provide more helpful error messages
            let errorMessage = error.message;
            if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError') || error.name === 'TypeError') {
                errorMessage = `Unable to connect to the API server at ${this.apiUrl}. Please check:\n\n` +
                             `1. The server is running and accessible\n` +
                             `2. The API URL is correct: ${this.apiUrl}\n` +
                             `3. There are no network or firewall issues\n` +
                             `4. CORS is properly configured on the server`;
            } else if (error.message.includes('timeout') || error.name === 'TimeoutError') {
                errorMessage = `Request timed out. The server may be slow or unresponsive. Please try again.`;
            }
            
            this.addMessage('assistant', `Sorry, I encountered an error: ${errorMessage}`);
        }
    }

    async checkApiConnectivity() {
        /** Check if API server is reachable */
        try {
            console.log('🔍 Checking API connectivity to:', `${this.apiUrl}/health`);
            
            // Create abort controller for timeout (browser compatibility)
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000);
            
            const response = await fetch(`${this.apiUrl}/health`, {
                method: 'GET',
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (response.ok) {
                console.log('✅ API server is reachable');
                return true;
            } else {
                console.warn('⚠️ API server responded with status:', response.status);
                return false;
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                console.error('❌ API health check timed out after 5 seconds');
            } else {
                console.error('❌ API server is not reachable:', error.message);
            }
            console.error('   API URL:', this.apiUrl);
            console.error('   Current page:', window.location.href);
            console.error('   Please ensure:');
            console.error('   1. The Flask server is running');
            console.error('   2. The server is accessible from this IP address');
            console.error('   3. CORS is properly configured');
            return false;
        }
    }

    addMessage(type, content, options = {}) {
        const messagesEl = document.getElementById('chatbot-messages');
        const messageId = `msg-${Date.now()}-${Math.random()}`;
        
        const messageEl = document.createElement('div');
        messageEl.className = `chatbot-message ${type}`;
        messageEl.id = messageId;
        
        const bubble = document.createElement('div');
        bubble.className = 'chatbot-message-bubble';
        
        // Force text color based on message type - AGGRESSIVE FIX
        const textColor = type === 'user' ? '#ffffff' : '#1f2937';
        const bgColor = type === 'user' 
            ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' 
            : '#ffffff';
        
        bubble.style.cssText = `
            padding: 12px 16px;
            border-radius: 18px;
            word-wrap: break-word;
            line-height: 1.5;
            font-size: 14px;
            color: ${textColor} !important;
            -webkit-text-fill-color: ${textColor} !important;
            background: ${bgColor} !important;
            opacity: 1 !important;
            visibility: visible !important;
            display: block !important;
            ${type === 'user' ? 'border-bottom-right-radius: 4px;' : 'border: 1px solid #e5e7eb; border-bottom-left-radius: 4px; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);'}
        `;
        
        // CRITICAL: Force all child elements to have correct color
        const forceTextColor = (element, color) => {
            element.style.color = color + ' !important';
            element.style.setProperty('color', color, 'important');
            element.style.setProperty('-webkit-text-fill-color', color, 'important');
            const allChildren = element.querySelectorAll('*');
            allChildren.forEach(child => {
                child.style.color = color + ' !important';
                child.style.setProperty('color', color, 'important');
                child.style.setProperty('-webkit-text-fill-color', color, 'important');
            });
        };
        
        // Format content as markdown-like
        const formattedContent = this.formatMessage(content);
        bubble.innerHTML = formattedContent;
        
        // CRITICAL: Force all child elements to have visible text IMMEDIATELY
        const bubbleTextColor = type === 'user' ? '#ffffff' : '#1f2937';
        
        // Force text color on bubble immediately - use both direct assignment and setProperty
        bubble.style.color = bubbleTextColor;
        bubble.style.cssText += `color: ${bubbleTextColor} !important; -webkit-text-fill-color: ${bubbleTextColor} !important; text-fill-color: ${bubbleTextColor} !important;`;
        
        // Use requestAnimationFrame AND setTimeout to ensure DOM is ready
        requestAnimationFrame(() => {
            setTimeout(() => {
                const allChildren = bubble.querySelectorAll('*');
                allChildren.forEach(child => {
                    child.style.color = bubbleTextColor;
                    child.style.setProperty('color', bubbleTextColor, 'important');
                    child.style.setProperty('-webkit-text-fill-color', bubbleTextColor, 'important');
                    child.style.setProperty('text-fill-color', bubbleTextColor, 'important');
                    child.style.setProperty('opacity', '1', 'important');
                    child.style.setProperty('visibility', 'visible', 'important');
                    
                    // Check computed color and fix if it's white/transparent OR the problematic rgb(31, 41, 55)
                    const computed = window.getComputedStyle(child);
                    const computedColor = computed.color || computed.webkitTextFillColor;
                    // CRITICAL: rgb(31, 41, 55) is Slate-700 which matches background - must fix!
                    if (computedColor === 'rgb(255, 255, 255)' || computedColor === 'rgba(0, 0, 0, 0)' || computedColor === 'transparent' || computedColor === 'white' || computedColor === 'rgb(31, 41, 55)') {
                        if (type === 'assistant') {
                            child.style.color = '#1f2937';
                            child.style.setProperty('color', '#1f2937', 'important');
                            child.style.setProperty('-webkit-text-fill-color', '#1f2937', 'important');
                        }
                    }
                });
                
                // Also check and fix bubble itself - CRITICAL: Check for rgb(31, 41, 55)
                const bubbleComputed = window.getComputedStyle(bubble);
                const bubbleComputedColor = bubbleComputed.color || bubbleComputed.webkitTextFillColor;
                // CRITICAL: rgb(31, 41, 55) is Slate-700 which matches background - must fix!
                if (bubbleComputedColor === 'rgb(255, 255, 255)' || bubbleComputedColor === 'rgba(0, 0, 0, 0)' || bubbleComputedColor === 'transparent' || bubbleComputedColor === 'white' || bubbleComputedColor === 'rgb(31, 41, 55)') {
                    if (type === 'assistant') {
                        bubble.style.color = '#1f2937';
                        bubble.style.setProperty('color', '#1f2937', 'important');
                        bubble.style.setProperty('-webkit-text-fill-color', '#1f2937', 'important');
                    }
                }
            }, 10);
        });
        
        const time = document.createElement('div');
        time.className = 'chatbot-message-time';
        time.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        time.style.cssText = `
            font-size: 11px;
            color: #6b7280 !important;
            -webkit-text-fill-color: #6b7280 !important;
            margin-top: 4px;
            padding: 0 4px;
            visibility: visible !important;
            opacity: 1 !important;
        `;
        
        messageEl.appendChild(bubble);
        messageEl.appendChild(time);
        
        // Add download button ONLY for assistant messages with actual answers
        // Exclude: loading messages, errors, FAQ prompts, system messages, personal info responses, test messages
        const isSystemMessage = content.includes('Would you like to see the complete FAQ') || 
                                content.includes('Please type a question') ||
                                content.includes("I'm sorry, I can only answer") ||
                                content.includes("I don't have information about") ||
                                content.includes('Loading') ||
                                content.includes('Error:') ||
                                content.includes('Sorry, I encountered an error') ||
                                content.includes('Hello! I\'m your') ||
                                content.includes('Please ask me questions about') ||
                                content.includes('Test message') ||
                                content.includes('test message') ||
                                content.includes('messages are working');
        
        const hasPersonalInfo = content.includes('Full Name') && 
                               (content.includes('Mobile Number') || content.includes('Email Address'));
        
        const isActualAnswer = type === 'assistant' && 
                              content && 
                              !isSystemMessage && 
                              !hasPersonalInfo &&
                              content.trim().length > 20; // Minimum length for actual answers
        
        if (isActualAnswer) {
            const actions = document.createElement('div');
            actions.className = 'chatbot-actions';
            
            // Download button
            const downloadBtn = document.createElement('button');
            downloadBtn.className = 'chatbot-action-btn';
            downloadBtn.innerHTML = '📥 Download';
            downloadBtn.title = 'Download this answer';
            downloadBtn.addEventListener('click', () => {
                this.downloadAnswerWithRename(content, options.numericValue, this.messages[this.messages.length - 2]?.content || 'Query');
            });
            actions.appendChild(downloadBtn);
            
            // Edit button
            const editBtn = document.createElement('button');
            editBtn.className = 'chatbot-action-btn';
            editBtn.innerHTML = '✏️ Edit';
            editBtn.title = 'Edit this answer';
            editBtn.style.marginLeft = '8px';
            editBtn.addEventListener('click', () => {
                const query = this.messages[this.messages.length - 2]?.content || 'Query';
                this.openEditAnswerModal(query, content, messageEl);
            });
            actions.appendChild(editBtn);
            
            messageEl.appendChild(actions);
        }
        
        messagesEl.appendChild(messageEl);
        
        // Force visibility with inline styles
        messageEl.style.cssText = `
            display: flex;
            flex-direction: column;
            max-width: 85%;
            visibility: visible;
            opacity: 1;
        `;
        
        if (type === 'user') {
            messageEl.style.alignSelf = 'flex-end';
        } else {
            messageEl.style.alignSelf = 'flex-start';
        }
        
        // Scroll to bottom
        setTimeout(() => {
            messagesEl.scrollTop = messagesEl.scrollHeight;
        }, 50);
        
        // CRITICAL: Final check and fix after message is in DOM
        setTimeout(() => {
            const bubbleComputed = window.getComputedStyle(bubble);
            const bubbleColor = bubbleComputed.color || bubbleComputed.webkitTextFillColor;
            console.log(`[${type}] Bubble computed color:`, bubbleColor, '| Expected:', type === 'user' ? 'white' : '#1f2937');
            
            // If assistant message has white/transparent color, force fix it
            if (type === 'assistant') {
                if (bubbleColor === 'rgb(255, 255, 255)' || bubbleColor === 'white' || bubbleColor === 'rgba(0, 0, 0, 0)' || bubbleColor === 'transparent' || !bubbleColor || bubbleColor === 'rgb(0, 0, 0)') {
                    console.log('⚠️ FIXING: Assistant message has wrong color!');
                    bubble.style.cssText = bubble.style.cssText.replace(/color:[^;]+/g, '') + `color: #1f2937 !important; -webkit-text-fill-color: #1f2937 !important;`;
                    
                    // Fix ALL text nodes and children
                    const walker = document.createTreeWalker(bubble, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
                    let node;
                    while (node = walker.nextNode()) {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            node.style.setProperty('color', '#1f2937', 'important');
                            node.style.setProperty('-webkit-text-fill-color', '#1f2937', 'important');
                        }
                    }
                }
            }
            
            // Also check all children
            const allChildren = bubble.querySelectorAll('*');
            allChildren.forEach(child => {
                const childComputed = window.getComputedStyle(child);
                const childColor = childComputed.color || childComputed.webkitTextFillColor;
                if (type === 'assistant' && (childColor === 'rgb(255, 255, 255)' || childColor === 'white' || childColor === 'rgba(0, 0, 0, 0)' || childColor === 'transparent')) {
                    child.style.setProperty('color', '#1f2937', 'important');
                    child.style.setProperty('-webkit-text-fill-color', '#1f2937', 'important');
                }
            });
        }, 100);
        
        this.messages.push({
            id: messageId,
            type,
            content,
            timestamp: new Date(),
            options
        });
        
        console.log('Message added successfully. Total messages:', this.messages.length);
        
        return messageId;
    }

    formatMessage(content) {
        // Clean up content - remove duplicate headers and sections
        content = this.cleanDuplicateHeaders(content);
        
        // Split content into lines for better processing
        let lines = content.split('\n');
        let formatted = '';
        let inTable = false;
        let tableRows = [];
        let tableHeaders = [];
        let seenHeaders = new Set(); // Track seen headers to avoid duplicates
        
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            
            // Check if this is a table row (contains |)
            if (line.includes('|') && line.split('|').filter(c => c.trim()).length > 1) {
                const cells = line.split('|').map(c => c.trim()).filter(c => c);
                
                // Special handling for "Column | Value" format - format as key-value pairs
                const isColumnValueHeader = cells.length === 2 && 
                    (cells[0].toLowerCase() === 'column' || cells[0].toLowerCase().includes('column')) && 
                    (cells[1].toLowerCase() === 'value' || cells[1].toLowerCase().includes('value'));
                
                if (isColumnValueHeader) {
                    // Process any pending table first
                    if (inTable) {
                        formatted += this.formatTable(tableHeaders, tableRows);
                        inTable = false;
                        tableRows = [];
                        tableHeaders = [];
                    }
                    
                    // Start collecting key-value pairs
                    const kvPairs = [];
                    // Look ahead for key-value pairs
                    for (let j = i + 1; j < lines.length; j++) {
                        const nextLine = lines[j].trim();
                        // Stop if we hit a section header or empty line followed by non-table content
                        if (nextLine && !nextLine.includes('|') && 
                            (nextLine.toLowerCase().includes('first') || 
                             nextLine.toLowerCase().includes('complete') ||
                             nextLine.toLowerCase().includes('table view') ||
                             nextLine.toLowerCase().includes('rows'))) {
                            break;
                        }
                        if (nextLine.includes('|') && nextLine.split('|').filter(c => c.trim()).length === 2) {
                            const kvCells = nextLine.split('|').map(c => c.trim()).filter(c => c);
                            if (kvCells.length === 2 && 
                                !kvCells[0].toLowerCase().includes('column') && 
                                !kvCells[1].toLowerCase().includes('value')) {
                                kvPairs.push({ key: kvCells[0], value: kvCells[1] });
                            } else {
                                break;
                            }
                        } else if (nextLine && !nextLine.includes('|')) {
                            break;
                        }
                    }
                    
                    if (kvPairs.length > 0) {
                        formatted += this.formatKeyValuePairs(kvPairs);
                        // Skip the processed lines
                        i += kvPairs.length;
                        continue;
                    }
                }
                
                // Check if this is a header row (next line might be separator, or it's the first table row)
                if (!inTable) {
                    inTable = true;
                    tableRows = [];
                    // Check if next line is a separator (contains --- or ===)
                    if (i + 1 < lines.length && (lines[i + 1].includes('---') || lines[i + 1].includes('==='))) {
                        tableHeaders = cells;
                        i++; // Skip separator line
                        continue;
                    } else {
                        // First row might be headers
                        tableHeaders = cells;
                    }
                } else {
                    tableRows.push(cells);
                }
            } else {
                // Not a table row - process any pending table first
                if (inTable) {
                    formatted += this.formatTable(tableHeaders, tableRows);
                    inTable = false;
                    tableRows = [];
                    tableHeaders = [];
                }
                
                // Process regular content
                if (line) {
                    let processedLine = line
                        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                        .replace(/\*(.*?)\*/g, '<em>$1</em>')
                        .replace(/`(.*?)`/g, '<code>$1</code>');
                    formatted += processedLine + '<br>';
                } else {
                    formatted += '<br>';
                }
            }
        }
        
        // Handle table at end of content
        if (inTable) {
            formatted += this.formatTable(tableHeaders, tableRows);
        }
        
        return `<div class="chatbot-markdown">${formatted}</div>`;
    }
    
    cleanDuplicateHeaders(content) {
        // Remove duplicate "Column Information" and "Description" headers
        const lines = content.split('\n');
        const cleaned = [];
        let lastHeader = '';
        let headerCount = 0;
        
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            const lowerLine = line.toLowerCase();
            
            // Check if this is a header we've seen
            if (lowerLine.includes('column information') || 
                (lowerLine.includes('description') && line.length < 50 && !line.includes('|'))) {
                if (lastHeader === line) {
                    headerCount++;
                    // Skip duplicate headers
                    if (headerCount > 1) {
                        continue;
                    }
                } else {
                    headerCount = 1;
                    lastHeader = line;
                }
            } else {
                headerCount = 0;
                lastHeader = '';
            }
            
            // Remove empty lines that are just separators
            if (line === '' && i > 0 && i < lines.length - 1 && 
                lines[i-1].trim() === '' && lines[i+1].trim() === '') {
                continue;
            }
            
            cleaned.push(lines[i]);
        }
        
        // Remove repeated "Description" fields in key-value pairs
        const finalCleaned = [];
        let lastDescKey = '';
        for (let i = 0; i < cleaned.length; i++) {
            const line = cleaned[i].trim();
            if (line.includes('|')) {
                const parts = line.split('|').map(p => p.trim());
                if (parts.length === 2 && parts[0].toLowerCase().includes('description')) {
                    if (lastDescKey === parts[0]) {
                        continue; // Skip duplicate description
                    }
                    lastDescKey = parts[0];
                } else {
                    lastDescKey = '';
                }
            } else {
                lastDescKey = '';
            }
            finalCleaned.push(cleaned[i]);
        }
        
        return finalCleaned.join('\n');
    }
    
    formatTable(headers, rows) {
        if (!headers || headers.length === 0) return '';
        
        let tableHtml = '<div class="chatbot-table-container"><table class="chatbot-table">';
        
        // Add header row
        if (headers.length > 0) {
            tableHtml += '<thead><tr>';
            headers.forEach(header => {
                tableHtml += `<th>${this.escapeHtml(header)}</th>`;
            });
            tableHtml += '</tr></thead>';
        }
        
        // Add body rows
        if (rows.length > 0) {
            tableHtml += '<tbody>';
            rows.forEach(row => {
                tableHtml += '<tr>';
                // Match cells to headers, or use row cells as-is
                const maxCells = Math.max(headers.length, row.length);
                for (let i = 0; i < maxCells; i++) {
                    const cell = row[i] || '';
                    tableHtml += `<td>${this.escapeHtml(cell)}</td>`;
                }
                tableHtml += '</tr>';
            });
            tableHtml += '</tbody>';
        }
        
        tableHtml += '</table></div>';
        return tableHtml;
    }
    
    formatKeyValuePairs(pairs) {
        // Format as vertical list
        let html = '<div class="chatbot-key-value-list">';
        pairs.forEach(pair => {
            html += `<div class="chatbot-key-value-item">`;
            html += `<div class="chatbot-key">${this.escapeHtml(pair.key)}</div>`;
            html += `<div class="chatbot-value">${this.escapeHtml(pair.value)}</div>`;
            html += `</div>`;
        });
        html += '</div>';
        return html;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    addLoadingMessage() {
        const messagesEl = document.getElementById('chatbot-messages');
        const loadingId = `loading-${Date.now()}`;
        
        const messageEl = document.createElement('div');
        messageEl.className = 'chatbot-message assistant';
        messageEl.id = loadingId;
        
        const bubble = document.createElement('div');
        bubble.className = 'chatbot-message-bubble';
        
        const loading = document.createElement('div');
        loading.className = 'chatbot-loading';
        loading.innerHTML = `
            <div class="chatbot-loading-dot"></div>
            <div class="chatbot-loading-dot"></div>
            <div class="chatbot-loading-dot"></div>
        `;
        
        bubble.appendChild(loading);
        messageEl.appendChild(bubble);
        messagesEl.appendChild(messageEl);
        messagesEl.scrollTop = messagesEl.scrollHeight;
        
        return loadingId;
    }

    removeMessage(messageId) {
        const messageEl = document.getElementById(messageId);
        if (messageEl) {
            messageEl.remove();
        }
    }

    showSuggestions(suggestions, title = null) {
        // CRITICAL: Hide autocomplete immediately when suggestions appear
        this.hideAutocomplete();
        
        // Clear any pending autocomplete timeout
        if (this.autocompleteTimeout) {
            clearTimeout(this.autocompleteTimeout);
            this.autocompleteTimeout = null;
        }
        
        // Reset prevent suggestions flag
        this.preventSuggestions = false;
        
        // Double-check: ensure autocomplete is actually hidden
        const autocompleteEl = document.getElementById('chatbot-autocomplete');
        if (autocompleteEl) {
            autocompleteEl.style.display = 'none';
            autocompleteEl.classList.remove('show');
        }
        
        // CRITICAL: Remove ALL suggestion chips from entire document first
        const allChips = document.querySelectorAll('.chatbot-suggestion-chip');
        allChips.forEach(chip => chip.remove());
        
        // Hide ALL suggestion containers from entire document (including duplicates)
        const allSuggestionContainers = document.querySelectorAll('#chatbot-suggestions');
        allSuggestionContainers.forEach(el => {
            el.style.display = 'none';
            el.classList.remove('collapsed');
            const chipsContainer = el.querySelector('#chatbot-suggestion-chips');
            if (chipsContainer) {
                chipsContainer.innerHTML = '';
            }
        });
        
        // If suggestions are already shown and we're trying to show the same ones, skip
        if (this.suggestionsShown && suggestions && suggestions.length > 0) {
            const currentChips = document.querySelectorAll('.chatbot-suggestion-chip');
            if (currentChips.length > 0) {
                console.log('⚠️ Suggestions already shown, skipping duplicate display');
                return;
            }
        }
        
        // Now get the correct suggestions element (from our container only)
        const suggestionsEl = this.container ? 
            this.container.querySelector('#chatbot-suggestions') : 
            document.getElementById('chatbot-suggestions');
        const chipsEl = suggestionsEl ? 
            suggestionsEl.querySelector('#chatbot-suggestion-chips') : 
            document.getElementById('chatbot-suggestion-chips');
        
        if (!suggestionsEl || !chipsEl) {
            console.error('Suggestions elements not found');
            return;
        }
        
        // Remove collapsed class when showing suggestions
        suggestionsEl.classList.remove('collapsed');
        
        if (title) {
            const titleEl = suggestionsEl.querySelector('.chatbot-suggestions-title');
            if (titleEl) titleEl.textContent = title;
        }
        
        // CRITICAL: Clear all existing chips completely
        chipsEl.innerHTML = '';
        
        if (!suggestions || suggestions.length === 0) {
            suggestionsEl.style.display = 'none';
            this.suggestionsShown = false;
            return;
        }
        
        // Remove duplicates and filter out used suggestions
        const uniqueSuggestions = [...new Set(suggestions)];
        const unusedSuggestions = uniqueSuggestions.filter(s => !this.usedSuggestions.includes(s));
        
        // Limit to exactly 3 suggestions (prefer unused ones)
        let finalSuggestions = unusedSuggestions.slice(0, 3);
        
        // If we don't have enough unused suggestions, fill with used ones if needed
        if (finalSuggestions.length < 3 && uniqueSuggestions.length > unusedSuggestions.length) {
            const usedButAvailable = uniqueSuggestions.filter(s => this.usedSuggestions.includes(s));
            const needed = 3 - finalSuggestions.length;
            finalSuggestions = [...finalSuggestions, ...usedButAvailable.slice(0, needed)];
        }
        
        console.log(`Filtered suggestions: ${unusedSuggestions.length} unused out of ${uniqueSuggestions.length} total, showing ${finalSuggestions.length}`);
        
        finalSuggestions.forEach(suggestion => {
            const chip = document.createElement('div');
            chip.className = 'chatbot-suggestion-chip';
            chip.textContent = suggestion;
            chip.style.cursor = 'pointer';
            chip.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                // Mark this suggestion as used
                if (!this.usedSuggestions.includes(suggestion)) {
                    this.usedSuggestions.push(suggestion);
                    console.log('Marked suggestion as used:', suggestion);
                }
                
                const input = document.getElementById('chatbot-input');
                if (input) {
                    this.setInputValue(suggestion);
                    input.focus();
                    this.hideSuggestions();
                    // Auto-send if user wants (optional - remove if not needed)
                    // this.sendMessage();
                }
            });
            chipsEl.appendChild(chip);
        });
        
        suggestionsEl.style.display = 'block';
        this.suggestionsShown = true;
        
        console.log(`✅ Showing ${finalSuggestions.length} suggestions:`, finalSuggestions);
    }

    hideSuggestions() {
        // Clear any pending suggestions timeout
        if (this.suggestionsTimeout) {
            clearTimeout(this.suggestionsTimeout);
            this.suggestionsTimeout = null;
        }
        
        // Hide ALL suggestion containers (in case of duplicates)
        const allSuggestionContainers = document.querySelectorAll('#chatbot-suggestions');
        allSuggestionContainers.forEach(el => {
            el.style.display = 'none';
            el.classList.remove('collapsed');
            const chipsContainer = el.querySelector('#chatbot-suggestion-chips');
            if (chipsContainer) {
                chipsContainer.innerHTML = '';
            }
        });
        
        // Also remove all chips from entire document
        const allChips = document.querySelectorAll('.chatbot-suggestion-chip');
        allChips.forEach(chip => chip.remove());
        
        this.suggestionsShown = false;
    }

    async downloadAnswerWithRename(answer, numericValue, query) {
        try {
            // Ask user for filename
            const defaultName = `answer_${new Date().toISOString().slice(0, 10).replace(/-/g, '')}_${Date.now()}`;
            const filename = prompt('Enter filename (without extension):', defaultName) || defaultName;
            
            if (!filename) {
                return; // User cancelled
            }
            
            const response = await fetch(`${this.apiUrl}/download`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    answer: answer,
                    query: query || 'Query',
                    numeric_value: numericValue,
                    filename: filename
                })
            });
            
            const data = await response.json();
            
            if (data.error) {
                alert(`Error: ${data.error}`);
            } else {
                this.showNotification(`✅ Downloaded: ${data.filename}`);
            }
        } catch (error) {
            alert(`Error downloading: ${error.message}`);
        }
    }
    
    async downloadAnswer(answer, numericValue) {
        await this.downloadAnswerWithRename(answer, numericValue, this.messages[this.messages.length - 2]?.content || 'Query');
    }

    openSettings() {
        console.log('Opening settings...');
        const modal = document.getElementById('chatbot-settings-modal');
        if (!modal) {
            console.error('Settings modal not found - creating it...');
            // Modal should be created in createWidget, but recreate if missing
            this.createSettingsModal();
            // Setup tabs again
            setTimeout(() => {
                this.setupSettingsTabs();
                this.openSettings();
            }, 100);
            return;
        }
        
        console.log('Modal found, showing...');
        
        // Load current settings first (await to ensure it completes)
        this.loadCurrentSettings().then(() => {
            // Then load files list with the correct path
            this.loadFilesList();
        });
        
        // Show modal
        modal.classList.add('show');
        console.log('Modal should be visible now');
    }

    closeSettings() {
        const modal = document.getElementById('chatbot-settings-modal');
        if (modal) {
            modal.classList.remove('show');
        }
    }
    
    async loadCurrentSettings() {
        try {
            console.log('Loading settings from:', `${this.apiUrl}/settings`);
            
            // Create abort controller for timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
            
            const response = await fetch(`${this.apiUrl}/settings`, {
                method: 'GET',
                signal: controller.signal,
                headers: {
                    'Accept': 'application/json'
                }
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('Loaded settings from API:', data);
            
            if (data.download_path) {
                const downloadInput = document.getElementById('settings-download-path');
                if (downloadInput) {
                    downloadInput.value = data.download_path;
                    console.log('Set download path:', data.download_path);
                }
                this.settings.downloadPath = data.download_path;
            }
            
            if (data.files_folder_path) {
                const filesInput = document.getElementById('settings-files-folder-path');
                if (filesInput) {
                    filesInput.value = data.files_folder_path;
                    console.log('Set files folder path:', data.files_folder_path);
                }
                this.settings.filesFolderPath = data.files_folder_path;
            } else {
                console.warn('No files_folder_path in settings response');
            }
        } catch (error) {
            console.error('Error loading settings:', error);
            // Check if it's a blocked request error
            if (error.message.includes('Failed to fetch') || error.name === 'TypeError' || error.message.includes('ERR_BLOCKED') || error.name === 'AbortError') {
                console.warn('⚠️ Settings request may be blocked by browser extension or network issue.');
                console.warn('   API URL:', this.apiUrl);
                console.warn('   Try:');
                console.warn('   1. Disable ad blockers or browser extensions');
                console.warn('   2. Check if the server is running and accessible');
                console.warn('   3. Verify CORS configuration');
                // Don't throw - allow the app to continue with default settings
            }
        }
    }

    async saveSettings() {
        const downloadPath = (document.getElementById('settings-download-path')?.value || '').trim();
        const filesFolderPath = (document.getElementById('settings-files-folder-path')?.value || '').trim();
        
        // Validate paths
        if (filesFolderPath && !filesFolderPath.match(/^([A-Za-z]:|\\\\|\/)/)) {
            alert('Invalid files folder path format. Please provide full path (e.g., E:/Bluemingo Project/SLM Excel Files Path)');
            return;
        }
        
        if (downloadPath && !downloadPath.match(/^([A-Za-z]:|\\\\|\/)/)) {
            alert('Invalid download path format. Please provide full path (e.g., C:/Users/YourName/Downloads)');
            return;
        }
        
        try {
            const response = await fetch(`${this.apiUrl}/settings`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    download_path: downloadPath,
                    files_folder_path: filesFolderPath
                })
            });
            
            const data = await response.json();
            
            if (data.error) {
                alert(`Error: ${data.error}`);
            } else {
                this.settings.downloadPath = downloadPath;
                this.settings.filesFolderPath = filesFolderPath;
                console.log('✅ Settings saved successfully. Files folder path:', filesFolderPath);
                console.log('✅ Settings object updated:', this.settings);
                // Don't close modal, just show success
                this.showNotification('✅ Settings saved successfully!');
            }
        } catch (error) {
            alert(`Error saving settings: ${error.message}`);
        }
    }
    
    // Browse functions removed - using text input only
    
    async uploadFiles() {
        const fileInput = document.getElementById('file-upload-input');
        if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
            alert('Please select file(s) to upload');
            return;
        }
        
        const processAfterUpload = document.getElementById('process-after-upload')?.checked ?? true;
        
        const formData = new FormData();
        for (let i = 0; i < fileInput.files.length; i++) {
            formData.append('file', fileInput.files[i]);
        }
        formData.append('process', processAfterUpload ? 'true' : 'false');
        
        try {
            if (processAfterUpload) {
                this.showNotification('Uploading and processing files... This may take a while.');
            } else {
                this.showNotification('Uploading files...');
            }
            
            const response = await fetch(`${this.apiUrl}/upload`, {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.error) {
                alert(`Error: ${data.error}`);
                this.showNotification(`❌ Upload failed: ${data.error}`, 'error');
            } else {
                if (processAfterUpload) {
                    this.showNotification(`✅ File(s) uploaded and processed successfully!`);
                } else {
                    this.showNotification(`✅ File(s) uploaded successfully! Use "Process Uploaded Files" to process them.`);
                }
                // Refresh file list
                this.loadFilesList();
                // Clear file input
                fileInput.value = '';
            }
        } catch (error) {
            alert(`Error uploading files: ${error.message}`);
            this.showNotification(`❌ Error: ${error.message}`, 'error');
        }
    }
    
    async processUploadedFiles() {
        try {
            this.showNotification('Checking for uploaded files...');
            
            // Get list of uploaded files from uploads folder
            const response = await fetch(`${this.apiUrl}/uploaded-files`);
            const data = await response.json();
            
            if (data.error) {
                alert(`Error: ${data.error}`);
                this.showNotification(`❌ Error: ${data.error}`, 'error');
                return;
            }
            
            const uploadedFiles = data.files || [];
            if (uploadedFiles.length === 0) {
                alert('No uploaded files found. Please upload files first.');
                this.showNotification('No uploaded files to process', 'info');
                return;
            }
            
            // Ask user to confirm
            const fileList = uploadedFiles.map(f => `• ${f.filename}`).join('\n');
            const confirmed = confirm(
                `Found ${uploadedFiles.length} uploaded file(s):\n\n${fileList}\n\nProcess these files now?`
            );
            
            if (!confirmed) {
                return;
            }
            
            // Process all uploaded files
            this.showNotification('Processing uploaded files... This may take a while.');
            
            const filePaths = uploadedFiles.map(f => f.path);
            const processResponse = await fetch(`${this.apiUrl}/files/process`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    file_paths: filePaths,
                    process_all_sheets: true
                })
            });
            
            const processData = await processResponse.json();
            
            if (processData.error) {
                alert(`Error: ${processData.error}`);
                this.showNotification(`❌ Processing failed: ${processData.error}`, 'error');
            } else {
                const totalProcessed = processData.total_processed || 0;
                if (totalProcessed > 0) {
                    this.showNotification(`✅ Processed ${totalProcessed}/${uploadedFiles.length} file(s) successfully!`);
                    // Refresh file list
                    this.loadFilesList();
                } else {
                    const errors = processData.results?.filter(r => r.status === 'error') || [];
                    if (errors.length > 0) {
                        const errorMsg = errors.map(e => `${e.file}: ${e.message}`).join('\n');
                        alert(`Processing failed:\n${errorMsg}`);
                        this.showNotification(`❌ Processing failed. Check console for details.`, 'error');
                    } else {
                        alert('No files were processed. Please check server logs.');
                        this.showNotification('No files processed', 'error');
                    }
                }
            }
        } catch (error) {
            console.error('[Process Uploaded] Error:', error);
            alert(`Error processing uploaded files: ${error.message}`);
            this.showNotification(`❌ Error: ${error.message}`, 'error');
        }
    }
    
    async clearDatabase() {
        const confirmed = confirm(
            '⚠️ WARNING: This will delete ALL data from the database!\n\n' +
            'All processed files will need to be re-processed.\n\n' +
            'Are you sure you want to clear the database?'
        );
        
        if (!confirmed) {
            return;
        }
        
        try {
            this.showNotification('Clearing database...');
            const response = await fetch(`${this.apiUrl}/clear-database`, {
                method: 'POST'
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.error) {
                alert(`Error: ${data.error}`);
                this.showNotification(`❌ Error: ${data.error}`, 'error');
            } else {
                alert('✅ Database cleared successfully!\n\nYou can now process files again.');
                this.showNotification('✅ Database cleared successfully', 'success');
                // Refresh file list to update status
                setTimeout(() => this.loadFilesList(), 500);
            }
        } catch (error) {
            console.error('[Clear Database] Error:', error);
            alert(`Error clearing database: ${error.message}`);
            this.showNotification(`❌ Error: ${error.message}`, 'error');
        }
    }
    
    async checkDatabaseStatus() {
        try {
            this.showNotification('Checking database status...');
            const response = await fetch(`${this.apiUrl}/database-stats`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            const stats = data.stats || {};
            const totalChunks = stats.total_chunks || 0;
            const loadedFilesCount = data.loaded_files_count || 0;
            
            let message = `📊 Database Status:\n\n`;
            message += `Total Chunks: ${totalChunks}\n`;
            message += `Loaded Files: ${loadedFilesCount}\n\n`;
            
            if (totalChunks === 0) {
                message += `⚠️ Database is empty!\n\nPlease:\n1. Select files from the list\n2. Click "Process Selected Files"\n3. Wait for processing to complete`;
            } else if (totalChunks < 10) {
                message += `⚠️ Database has very few chunks (${totalChunks}).\n\nThis might indicate incomplete processing.\n\nTry:\n1. Clear database (🗑️ Clear Database button)\n2. Re-process your files\n3. Check server console for chunk creation logs`;
            } else {
                message += `✅ Database is ready for queries!`;
            }
            
            alert(message);
            this.showNotification(`Database has ${totalChunks} chunks`, totalChunks > 0 ? 'success' : 'info');
            
        } catch (error) {
            console.error('[Check DB Status] Error:', error);
            alert(`Error checking database status: ${error.message}`);
            this.showNotification(`❌ Error: ${error.message}`, 'error');
        }
    }
    
    async loadFilesList() {
        const container = document.getElementById('file-list-container');
        if (!container) {
            console.warn('File list container not found');
            return;
        }
        
        container.innerHTML = '<div class="chatbot-loading-text">Loading files...</div>';
        
        // Declare filesFolderPath outside try block so it's accessible in catch
        let filesFolderPath = '';
        
        try {
            // Get path from input field first (most current), then from settings, then from API
            filesFolderPath = document.getElementById('settings-files-folder-path')?.value?.trim() || '';
            
            console.log('loadFilesList - Path from input field:', filesFolderPath);
            
            if (!filesFolderPath) {
                filesFolderPath = this.settings.filesFolderPath;
                console.log('loadFilesList - Path from settings object:', filesFolderPath);
            }
            
            // If still no path, try to load from API settings
            if (!filesFolderPath) {
                try {
                    console.log('loadFilesList - Loading path from API...');
                    console.log('loadFilesList - API URL:', `${this.apiUrl}/settings`);
                    
                    // Create abort controller for timeout
                    const controller = new AbortController();
                    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
                    
                    const settingsResponse = await fetch(`${this.apiUrl}/settings`, {
                        method: 'GET',
                        signal: controller.signal,
                        headers: {
                            'Accept': 'application/json'
                        }
                    });
                    
                    clearTimeout(timeoutId);
                    
                    if (!settingsResponse.ok) {
                        throw new Error(`HTTP ${settingsResponse.status}: ${settingsResponse.statusText}`);
                    }
                    
                    const settingsData = await settingsResponse.json();
                    console.log('loadFilesList - API settings:', settingsData);
                    if (settingsData.files_folder_path) {
                        filesFolderPath = settingsData.files_folder_path;
                        // Update the input field
                        const filesInput = document.getElementById('settings-files-folder-path');
                        if (filesInput) {
                            filesInput.value = filesFolderPath;
                        }
                        this.settings.filesFolderPath = filesFolderPath;
                        console.log('loadFilesList - Path from API:', filesFolderPath);
                    }
                } catch (e) {
                    console.error('Error loading settings:', e);
                    // Check if it's a blocked request error
                    if (e.message.includes('Failed to fetch') || e.name === 'TypeError' || e.message.includes('ERR_BLOCKED')) {
                        console.warn('⚠️ Request may be blocked by browser extension or CORS. API URL:', this.apiUrl);
                        console.warn('   Try disabling ad blockers or check CORS configuration.');
                    }
                }
            }
            
            if (!filesFolderPath || filesFolderPath.trim() === '') {
                container.innerHTML = '<div class="chatbot-loading-text">Please set files folder path first</div>';
                console.warn('No files folder path available');
                return;
            }
            
            // Normalize path - ensure it's a full path, not just a folder name
            filesFolderPath = filesFolderPath.trim();
            
            // If path doesn't look like a full path (no drive letter or leading slash), show error
            if (!filesFolderPath.match(/^([A-Za-z]:|\\\\|\/)/)) {
                container.innerHTML = `<div class="chatbot-error-text">Invalid path format. Please provide full path (e.g., E:/Bluemingo Project/SLM Excel Files Path)<br/><small>Current path: ${filesFolderPath}</small></div>`;
                console.error('Invalid path format:', filesFolderPath);
                return;
            }
            
            console.log('Loading files from path:', filesFolderPath);
            console.log('API URL:', `${this.apiUrl}/files/list`);
            
            // Create abort controller for timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout for file listing
            
            const response = await fetch(`${this.apiUrl}/files/list`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    folder_path: filesFolderPath
                }),
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('Files list response:', data);
            
            if (data.error) {
                container.innerHTML = `<div class="chatbot-error-text">${data.error}<br/><small>Current path: ${filesFolderPath}</small></div>`;
                console.error('Error loading files:', data.error, 'Path:', filesFolderPath);
                return;
            }
            
            if (!data.files || data.files.length === 0) {
                container.innerHTML = `<div class="chatbot-loading-text">No Excel/CSV files found in this folder<br/><small>Path: ${filesFolderPath}</small></div>`;
                console.warn('No files found in folder:', filesFolderPath);
                return;
            }
            
            console.log(`✅ Found ${data.files.length} files in folder:`, filesFolderPath);
            console.log('Files:', data.files.map(f => f.filename));
            
            // Check database stats to show overall status
            let dbStats = null;
            try {
                const statsResponse = await fetch(`${this.apiUrl}/database-stats`);
                if (statsResponse.ok) {
                    dbStats = await statsResponse.json();
                    console.log('[File List] Database stats:', dbStats);
                }
            } catch (e) {
                console.warn('[File List] Could not fetch database stats:', e);
            }
            
            const totalChunks = dbStats?.stats?.total_chunks || 0;
            const processedCount = data.files.filter(f => f.loaded).length;
            
            let html = '';
            
            // Show simple status message (no chunks info)
            if (data.files.length > 0 && processedCount === 0) {
                html += `<div style="padding: 10px; background: #fef3c7; border-radius: 6px; margin-bottom: 10px; font-size: 13px;">
                    <strong>⚠️ No files processed yet.</strong> Select files and click "Process Selected Files" to add them to the database.
                </div>`;
            }
            
            // Pre-select all files by default
            data.files.forEach(file => {
                const fileSize = (file.size / 1024).toFixed(2) + ' KB';
                html += `
                    <div class="chatbot-file-item">
                        <input type="checkbox" class="chatbot-file-checkbox" 
                               data-filename="${file.filename}" 
                               data-path="${file.path}"
                               checked />
                        <div class="chatbot-file-name">${file.filename}</div>
                        <div class="chatbot-file-status ${file.loaded ? 'loaded' : 'pending'}">
                            ${file.loaded ? '✓ Processed' : 'Not Processed'}
                        </div>
                        <div style="font-size: 11px; color: #6b7280; margin-left: 10px;">${fileSize}</div>
                    </div>
                `;
            });
            
            container.innerHTML = html;
            
        } catch (error) {
            console.error('Error loading files list:', error);
            
            // Get filesFolderPath from input or settings if not already set
            if (!filesFolderPath) {
                filesFolderPath = document.getElementById('settings-files-folder-path')?.value?.trim() || 
                                 this.settings.filesFolderPath || 
                                 'Not set';
            }
            
            // Check if it's a blocked request error
            if (error.message.includes('Failed to fetch') || error.name === 'TypeError' || error.message.includes('ERR_BLOCKED') || error.name === 'AbortError') {
                container.innerHTML = `<div class="chatbot-error-text">
                    Unable to load files. Request may be blocked by browser extension or network issue.<br/>
                    <small style="color: #6b7280; display: block; margin-top: 8px;">
                        API URL: ${this.apiUrl}/files/list<br/>
                        Current Page: ${window.location.href}<br/>
                        Path: ${filesFolderPath}<br/><br/>
                        <strong>Try:</strong><br/>
                        1. Disable ad blockers or browser extensions<br/>
                        2. Check if the server is running and accessible<br/>
                        3. Verify CORS configuration<br/>
                        4. Check browser console for more details
                    </small>
                </div>`;
                console.warn('⚠️ Files list request may be blocked by browser extension or network issue.');
                console.warn('   API URL:', this.apiUrl);
                console.warn('   Current page:', window.location.href);
                console.warn('   Expected API URL should match current page origin');
            } else {
                // Other errors
                container.innerHTML = `<div class="chatbot-error-text">Error loading files: ${error.message}<br/><small>Path: ${filesFolderPath}</small></div>`;
            }
        }
    }
    
    selectAllFiles() {
        const checkboxes = document.querySelectorAll('.chatbot-file-checkbox');
        checkboxes.forEach(cb => cb.checked = true);
    }
    
    selectUnprocessedFiles() {
        const checkboxes = document.querySelectorAll('.chatbot-file-checkbox');
        checkboxes.forEach(cb => {
            // Check if file is not processed (file status is 'pending')
            const fileItem = cb.closest('.chatbot-file-item');
            if (fileItem) {
                const statusEl = fileItem.querySelector('.chatbot-file-status');
                if (statusEl && statusEl.classList.contains('pending')) {
                    cb.checked = true;
                } else {
                    cb.checked = false;
                }
            }
        });
    }
    
    deselectAllFiles() {
        const checkboxes = document.querySelectorAll('.chatbot-file-checkbox');
        checkboxes.forEach(cb => cb.checked = false);
    }
    
    async processSelectedFiles() {
        const checkboxes = document.querySelectorAll('.chatbot-file-checkbox:checked');
        if (checkboxes.length === 0) {
            alert('Please select at least one file to process');
            return;
        }
        
        const filesToProcess = Array.from(checkboxes).map(cb => cb.dataset.path);
        const fileNames = Array.from(checkboxes).map(cb => cb.dataset.filename);
        
        // Show confirmation with file list
        const fileList = fileNames.map((name, idx) => `${idx + 1}. ${name}`).join('\n');
        const confirmed = confirm(
            `You are about to process ${filesToProcess.length} file(s):\n\n${fileList}\n\nThis may take a while. Continue?`
        );
        
        if (!confirmed) {
            return;
        }
        
        try {
            this.showNotification(`Processing ${filesToProcess.length} file(s)... This may take a while.`);
            console.log('[Processing] Starting to process files:', filesToProcess);
            console.log('[Processing] File names:', fileNames);
            
            const response = await fetch(`${this.apiUrl}/files/process`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    file_paths: filesToProcess,
                    process_all_sheets: true
                })
            });
            
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
            }
            
            const data = await response.json();
            console.log('[Processing] Response:', data);
            
            if (data.error) {
                alert(`Error: ${data.error}`);
                this.showNotification(`❌ Error: ${data.error}`, 'error');
            } else if (data.total_processed === 0) {
                // Check if there were errors
                const errors = (data.results || []).filter(r => r.status === 'error');
                if (errors.length > 0) {
                    const errorMsg = errors.map(e => `${e.file}: ${e.message}`).join('\n');
                    alert(`Processing failed:\n${errorMsg}`);
                    this.showNotification(`❌ Processing failed. Check console for details.`, 'error');
                    console.error('[Processing] Errors:', errors);
                } else {
                    alert('No files were processed. Please check server logs.');
                    this.showNotification('❌ No files processed', 'error');
                }
            } else {
                const successMsg = `✅ Successfully processed ${data.total_processed}/${filesToProcess.length} file(s)!`;
                this.showNotification(successMsg);
                
                // Show detailed results
                const results = data.results || [];
                const successFiles = results.filter(r => r.status === 'success').map(r => r.file);
                const errorFiles = results.filter(r => r.status === 'error');
                
                if (errorFiles.length > 0) {
                    console.warn('[Processing] Some files had errors:', errorFiles);
                    const errorMsg = errorFiles.map(e => `${e.file}: ${e.message}`).join('\n');
                    alert(`Processed ${data.total_processed} file(s), but ${errorFiles.length} had errors:\n\n${errorMsg}`);
                }
                
                // Refresh file list to update status
                setTimeout(() => {
                    this.loadFilesList();
                }, 1500);
                
                // Hide process button after successful processing
                const processBtn = document.getElementById('chatbot-process-btn');
                if (processBtn) {
                    processBtn.style.display = 'none';
                }
                
                // Reload greeting to show suggestions now that data is processed
                setTimeout(() => {
                    this.loadGreeting();
                }, 2000);
            }
            
        } catch (error) {
            console.error('[Processing] Exception:', error);
            const errorMsg = error.message || 'Unknown error occurred';
            alert(`Error processing files: ${errorMsg}\n\nPlease check:\n1. Server is running\n2. Files exist at the specified paths\n3. Browser console for details`);
            this.showNotification(`❌ Error: ${errorMsg}`, 'error');
        }
    }
    
    async loadFAQs() {
        const container = document.getElementById('faqs-container');
        if (!container) return;
        
        container.innerHTML = '<div class="chatbot-loading-text">Loading FAQs...</div>';
        
        try {
            const response = await fetch(`${this.apiUrl}/faqs`);
            const data = await response.json();
            
            if (data.error) {
                container.innerHTML = `<div class="chatbot-error-text">Error: ${data.error}</div>`;
                return;
            }
            
            let html = '';
            
            // Basic FAQs
            if (data.basic && data.basic.length > 0) {
                html += '<div class="chatbot-faq-section">';
                html += '<h4 class="chatbot-faq-section-title">🟢 Basic Level Questions</h4>';
                html += '<ul class="chatbot-faq-list">';
                data.basic.forEach((faq, index) => {
                    // Escape HTML in FAQ text
                    const escapedFaq = faq.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
                    html += `<li class="chatbot-faq-item" data-faq="${escapedFaq}">${index + 1}. ${faq}</li>`;
                });
                html += '</ul></div>';
            }
            
            // Intermediate FAQs
            if (data.intermediate && data.intermediate.length > 0) {
                html += '<div class="chatbot-faq-section">';
                html += '<h4 class="chatbot-faq-section-title">🟡 Intermediate Level Questions</h4>';
                html += '<ul class="chatbot-faq-list">';
                data.intermediate.forEach((faq, index) => {
                    const escapedFaq = faq.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
                    html += `<li class="chatbot-faq-item" data-faq="${escapedFaq}">${index + 1}. ${faq}</li>`;
                });
                html += '</ul></div>';
            }
            
            // Advanced FAQs
            if (data.advanced && data.advanced.length > 0) {
                html += '<div class="chatbot-faq-section">';
                html += '<h4 class="chatbot-faq-section-title">🔴 Advanced Level Questions</h4>';
                html += '<ul class="chatbot-faq-list">';
                data.advanced.forEach((faq, index) => {
                    const escapedFaq = faq.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
                    html += `<li class="chatbot-faq-item" data-faq="${escapedFaq}">${index + 1}. ${faq}</li>`;
                });
                html += '</ul></div>';
            }
            
            // Operational FAQs
            if (data.operational && data.operational.length > 0) {
                html += '<div class="chatbot-faq-section">';
                html += '<h4 class="chatbot-faq-section-title">⚙️ Operational Level Questions</h4>';
                html += '<ul class="chatbot-faq-list">';
                data.operational.forEach((faq, index) => {
                    const escapedFaq = faq.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
                    html += `<li class="chatbot-faq-item" data-faq="${escapedFaq}">${index + 1}. ${faq}</li>`;
                });
                html += '</ul></div>';
            }
            
            container.innerHTML = html;
            
            // Add click handlers - paste FAQ into input and close settings
            container.querySelectorAll('.chatbot-faq-item').forEach(item => {
                item.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    const faq = item.dataset.faq;
                    const input = document.getElementById('chatbot-input');
                    if (input) {
                        this.setInputValue(faq);
                        input.focus();
                        this.closeSettings();
                        // Optionally auto-send (commented out - user can press Enter)
                        // setTimeout(() => this.sendMessage(), 100);
                    }
                });
            });
            
        } catch (error) {
            console.error('Error loading FAQs:', error);
            container.innerHTML = `<div class="chatbot-error-text">Error loading FAQs: ${error.message}</div>`;
        }
    }
    
    async loadTrainingData() {
        const container = document.getElementById('training-list-container');
        if (!container) return;
        
        container.innerHTML = '<div class="chatbot-loading-text">Loading training data...</div>';
        
        try {
            const response = await fetch(`${this.apiUrl}/training`);
            const data = await response.json();
            
            if (data.error) {
                container.innerHTML = `<div class="chatbot-error-text">Error: ${data.error}</div>`;
                return;
            }
            
            // Only show user training data (FAQ training data is filtered out by backend)
            const userTrainingData = data.training_data || {};
            
            if (!userTrainingData || Object.keys(userTrainingData).length === 0) {
                container.innerHTML = '<div class="chatbot-loading-text">No custom training data yet. Add your first training entry above!<br><small style="color: #9ca3af;">Note: FAQ training data is managed automatically and not shown here.</small></div>';
                return;
            }
            
            // Show summary if there's FAQ training data
            let summaryHtml = '';
            if (data.faq_count && data.faq_count > 0) {
                summaryHtml = `<div style="padding: 8px; background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px; margin-bottom: 10px; font-size: 12px; color: #1e40af;">
                    ℹ️ ${data.faq_count} FAQ questions are automatically trained (not shown here)
                </div>`;
            }
            
            let html = summaryHtml + '<div style="display: flex; flex-direction: column; gap: 10px;">';
            Object.entries(userTrainingData).forEach(([question, answer]) => {
                const answerPreview = answer.length > 100 ? answer.substring(0, 100) + '...' : answer;
                html += `
                    <div class="chatbot-training-item" style="padding: 12px; border: 1px solid #e5e7eb; border-radius: 8px; background: white;">
                        <div style="font-weight: 600; margin-bottom: 5px; color: #374151;">Q: ${question}</div>
                        <div style="font-size: 12px; color: #6b7280; margin-bottom: 8px;">A: ${answerPreview}</div>
                        <button class="chatbot-btn-secondary delete-training-btn" data-question="${question.replace(/"/g, '&quot;')}" style="padding: 5px 10px; font-size: 12px;">🗑️ Delete</button>
                    </div>
                `;
            });
            html += '</div>';
            container.innerHTML = html;
            
            // Add delete handlers
            container.querySelectorAll('.delete-training-btn').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    const question = btn.dataset.question.replace(/&quot;/g, '"');
                    if (confirm(`Delete training data for: "${question}"?`)) {
                        await this.deleteTrainingData(question);
                    }
                });
            });
            
        } catch (error) {
            console.error('Error loading training data:', error);
            container.innerHTML = `<div class="chatbot-error-text">Error loading training data: ${error.message}</div>`;
        }
    }
    
    async saveTrainingData() {
        console.log('saveTrainingData called');
        const questionInput = document.getElementById('train-question-input');
        const answerTextInput = document.getElementById('train-answer-text-input');
        const answerFileInput = document.getElementById('train-answer-file-input');
        const answerTextContainer = document.getElementById('train-answer-text-container');
        const answerFileContainer = document.getElementById('train-answer-file-container');
        
        if (!questionInput) {
            alert('Question input not found');
            console.error('Question input element not found');
            return;
        }
        
        const question = questionInput.value.trim();
        let answer = '';
        
        if (!question) {
            alert('Please enter a question');
            return;
        }
        
        // Check if using text or file mode - check computed style, not inline style
        const textContainerStyle = window.getComputedStyle(answerTextContainer || {});
        const fileContainerStyle = window.getComputedStyle(answerFileContainer || {});
        const isTextMode = answerTextContainer && 
                          (answerTextContainer.style.display !== 'none' && 
                           textContainerStyle.display !== 'none');
        const isFileMode = answerFileContainer && 
                          (answerFileContainer.style.display !== 'none' && 
                           fileContainerStyle.display !== 'none');
        
        // Fallback: check if file input has a file selected
        if (!isTextMode && !isFileMode) {
            // Default to text mode if neither is explicitly shown
            if (answerTextInput && answerTextInput.value.trim()) {
                // Text mode
                answer = answerTextInput.value.trim();
                if (!answer) {
                    alert('Please enter an answer');
                    return;
                }
                
                console.log('Saving text training data (fallback):', {question, answerLength: answer.length});
                
                try {
                    const response = await fetch(`${this.apiUrl}/training`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({question, answer})
                    });
                    
                    const data = await response.json();
                    console.log('Training save response:', data);
                    
                    if (data.error) {
                        alert(`Error: ${data.error}`);
                        return;
                    }
                    
                    this.showNotification('✅ Training data saved successfully!');
                    questionInput.value = '';
                    answerTextInput.value = '';
                    await this.loadTrainingData();
                    return;
                } catch (error) {
                    console.error('Error saving training data:', error);
                    alert(`Error saving training data: ${error.message}`);
                    return;
                }
            } else {
                alert('Please select either Text or Excel File mode and provide an answer');
                return;
            }
        }
        
        if (isTextMode) {
            if (!answerTextInput) {
                alert('Answer text input not found');
                return;
            }
            answer = answerTextInput.value.trim();
            if (!answer) {
                alert('Please enter an answer');
                return;
            }
            
            console.log('Saving text training data:', {question, answerLength: answer.length});
            
            // Save via API
            try {
                const response = await fetch(`${this.apiUrl}/training`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({question, answer})
                });
                
                const data = await response.json();
                console.log('Training save response:', data);
                
                if (data.error) {
                    alert(`Error: ${data.error}`);
                    return;
                }
                
                this.showNotification('✅ Training data saved successfully!');
                
                // Clear inputs
                questionInput.value = '';
                answerTextInput.value = '';
                
                // Reload training list
                await this.loadTrainingData();
                
            } catch (error) {
                console.error('Error saving training data:', error);
                alert(`Error saving training data: ${error.message}`);
            }
        } else if (isFileMode) {
            // File mode
            if (!answerFileInput) {
                alert('File input not found');
                return;
            }
            
            const file = answerFileInput.files[0];
            if (!file) {
                alert('Please select a file');
                return;
            }
            
            console.log('Uploading file training data:', {question, fileName: file.name});
            
            const formData = new FormData();
            formData.append('file', file);
            formData.append('question', question);
            
            try {
                const response = await fetch(`${this.apiUrl}/training/upload`, {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                console.log('Training upload response:', data);
                
                if (data.error) {
                    alert(`Error: ${data.error}`);
                    return;
                }
                
                this.showNotification('✅ Training data uploaded and saved successfully!');
                
                // Clear inputs
                questionInput.value = '';
                answerFileInput.value = '';
                
                // Reload training list
                await this.loadTrainingData();
                
            } catch (error) {
                console.error('Error uploading training data:', error);
                alert(`Error uploading training data: ${error.message}`);
            }
        }
    }
    
    async deleteTrainingData(question) {
        try {
            const response = await fetch(`${this.apiUrl}/training`, {
                method: 'DELETE',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({question})
            });
            
            const data = await response.json();
            if (data.error) {
                alert(`Error: ${data.error}`);
                return;
            }
            
            this.showNotification('✅ Training data deleted successfully!');
            await this.loadTrainingData();
            
        } catch (error) {
            alert(`Error deleting training data: ${error.message}`);
        }
    }
    
    openEditAnswerModal(query, answer, messageElement) {
        // Create edit modal
        const modal = document.createElement('div');
        modal.className = 'chatbot-modal';
        modal.id = 'chatbot-edit-modal';
        modal.innerHTML = `
            <div class="chatbot-modal-content" style="max-width: 800px; max-height: 90vh;">
                <div class="chatbot-modal-header">
                    <h3>✏️ Edit Answer</h3>
                    <button class="chatbot-modal-close" id="chatbot-edit-modal-close">×</button>
                </div>
                <div class="chatbot-modal-body" style="overflow-y: auto; max-height: calc(90vh - 150px);">
                    <div class="chatbot-form-group">
                        <label><strong>Question:</strong></label>
                        <div style="padding: 10px; background: #f3f4f6; border-radius: 6px; margin-bottom: 15px;">
                            ${query.replace(/</g, '&lt;').replace(/>/g, '&gt;')}
                        </div>
                    </div>
                    <div class="chatbot-form-group">
                        <label><strong>Answer:</strong></label>
                        <textarea id="edit-answer-textarea" style="width: 100%; min-height: 400px; padding: 12px; border: 1px solid #e5e7eb; border-radius: 8px; font-size: 14px; font-family: 'Courier New', monospace; resize: vertical; white-space: pre-wrap;">${answer.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</textarea>
                    </div>
                    <div class="chatbot-form-group" style="display: flex; gap: 10px; margin-top: 20px;">
                        <button class="chatbot-btn-secondary" id="edit-cancel-btn">Cancel</button>
                        <button class="chatbot-btn-secondary" id="edit-save-download-btn" style="background: #10b981; color: white;">💾 Save & Download</button>
                        <button class="chatbot-btn-primary" id="edit-save-permanent-btn">🔒 Permanent Save</button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        // Show modal
        setTimeout(() => {
            modal.style.display = 'flex';
        }, 10);
        
        // Focus textarea
        const textarea = document.getElementById('edit-answer-textarea');
        if (textarea) {
            textarea.focus();
            textarea.setSelectionRange(textarea.value.length, textarea.value.length);
        }
        
        // Close button
        const closeBtn = document.getElementById('chatbot-edit-modal-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                modal.remove();
            });
        }
        
        // Cancel button
        const cancelBtn = document.getElementById('edit-cancel-btn');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => {
                modal.remove();
            });
        }
        
        // Close on outside click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
        
        // Save & Download button
        const saveDownloadBtn = document.getElementById('edit-save-download-btn');
        if (saveDownloadBtn) {
            saveDownloadBtn.addEventListener('click', async () => {
                const editedAnswer = textarea.value.trim();
                if (!editedAnswer) {
                    alert('Answer cannot be empty');
                    return;
                }
                
                // Download the edited answer
                await this.downloadAnswerWithRename(editedAnswer, null, query);
                
                // Update the message in the chat
                const messageContent = messageElement.querySelector('.chatbot-message-content');
                if (messageContent) {
                    messageContent.innerHTML = this.formatMessage(editedAnswer);
                }
                
                this.showNotification('✅ Answer downloaded successfully!');
                modal.remove();
            });
        }
        
        // Permanent Save button
        const savePermanentBtn = document.getElementById('edit-save-permanent-btn');
        if (savePermanentBtn) {
            savePermanentBtn.addEventListener('click', async () => {
                const editedAnswer = textarea.value.trim();
                if (!editedAnswer) {
                    alert('Answer cannot be empty');
                    return;
                }
                
                // Save permanently via API
                try {
                    const response = await fetch(`${this.apiUrl}/edited-answers`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({question: query, answer: editedAnswer})
                    });
                    
                    const data = await response.json();
                    if (data.error) {
                        alert(`Error: ${data.error}`);
                        return;
                    }
                    
                    // Update the message in the chat
                    const messageContent = messageElement.querySelector('.chatbot-message-content');
                    if (messageContent) {
                        messageContent.innerHTML = this.formatMessage(editedAnswer);
                    }
                    
                    this.showNotification('✅ Answer saved permanently! This answer will be used for future queries.');
                    modal.remove();
                } catch (error) {
                    console.error('Error saving edited answer:', error);
                    alert(`Error saving edited answer: ${error.message}`);
                }
            });
        }
    }
    
    showNotification(message) {
        // Simple notification - you can enhance this
        const notification = document.createElement('div');
        notification.className = 'chatbot-notification';
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #10b981;
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 10002;
            animation: slideIn 0.3s ease;
        `;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
}

// Auto-initialize if script is loaded
if (typeof window !== 'undefined') {
    window.ChatbotWidget = ChatbotWidget;
    
    // Add fix function to window
    window.fixChatbot = function() {
        console.log('=== CHATBOT FIX SCRIPT ===');
        
        // 1. Check input element
        const input = document.getElementById('chatbot-input');
        console.log('1. Input element:', input);
        if (input) {
            console.log('   - Value:', input.value);
            console.log('   - Disabled:', input.disabled);
            console.log('   - ReadOnly:', input.readOnly);
            
            // Fix input - CRITICAL: Set -webkit-text-fill-color for text visibility
            input.disabled = false;
            input.readOnly = false;
            input.removeAttribute('disabled');
            input.removeAttribute('readonly');
            input.style.setProperty('pointer-events', 'auto', 'important');
            input.style.setProperty('opacity', '1', 'important');
            input.style.setProperty('visibility', 'visible', 'important');
            input.style.setProperty('display', 'block', 'important');
            input.style.setProperty('color', '#1f2937', 'important');
            input.style.setProperty('-webkit-text-fill-color', '#1f2937', 'important');
            input.style.setProperty('text-fill-color', '#1f2937', 'important');
            input.style.setProperty('font-size', '14px', 'important');
            console.log('   ✅ Input fixed with text-fill-color');
        } else {
            console.error('   ❌ Input not found!');
        }
        
        // 2. Check messages container
        const messagesEl = document.getElementById('chatbot-messages');
        console.log('2. Messages container:', messagesEl);
        if (messagesEl) {
            console.log('   - Children count:', messagesEl.children.length);
            
            // Fix messages container
            messagesEl.style.display = 'flex';
            messagesEl.style.visibility = 'visible';
            messagesEl.style.opacity = '1';
            messagesEl.style.height = 'auto';
            messagesEl.style.minHeight = '100px';
            console.log('   ✅ Messages container fixed');
            
            // Removed test message - no longer needed
        } else {
            console.error('   ❌ Messages container not found!');
        }
        
        // 3. Check chatbot container
        const container = document.getElementById('chatbot-widget');
        console.log('3. Chatbot container:', container);
        if (container) {
            container.style.display = 'flex';
            container.style.visibility = 'visible';
            container.style.opacity = '1';
            console.log('   ✅ Container fixed');
        }
        
        console.log('=== FIX COMPLETE ===');
        console.log('Try typing in the input now.');
    };
    
    // Auto-initialize if data attribute is present AND chatbot doesn't already exist
    const script = document.currentScript;
    if (script && script.dataset.autoInit !== 'false') {
        // Check if chatbot already exists (prevent duplicate initialization)
        if (!window.chatbot && !document.getElementById('chatbot-widget') && !document.getElementById('chatbot-container')) {
            // Auto-detect API URL from current page if not explicitly provided
            let apiUrl = script.dataset.apiUrl;
            if (!apiUrl && typeof window !== 'undefined' && window.location) {
                const host = window.location.hostname;
                let port = window.location.port;
                if (!port || port === '') {
                    const urlMatch = window.location.href.match(/:(\d+)/);
                    if (urlMatch) {
                        port = urlMatch[1];
                    } else {
                        port = window.location.protocol === 'https:' ? '443' : '5000';
                    }
                }
                apiUrl = `${window.location.protocol}//${host}:${port}/api`;
                console.log('🔍 Auto-detected API URL for initialization:', apiUrl);
            }
            // Only pass apiUrl if it was explicitly set or auto-detected
            const config = apiUrl ? { apiUrl } : {};
            window.chatbot = new ChatbotWidget(config);
            
            // Run fix after initialization
            setTimeout(() => {
                if (window.fixChatbot) {
                    console.log('Running auto-fix...');
                    window.fixChatbot();
                }
            }, 2000);
        } else {
            console.log('ℹ️ Chatbot already initialized, skipping auto-initialization');
        }
    }
    
    // Also make fixChatbot available immediately (even before chatbot loads)
    // This allows manual fixing
    if (!window.fixChatbot) {
        window.fixChatbot = function() {
            console.log('fixChatbot called - but chatbot.js may not be fully loaded yet');
            console.log('Please refresh the page and try again, or wait for chatbot to initialize');
        };
    }
}

