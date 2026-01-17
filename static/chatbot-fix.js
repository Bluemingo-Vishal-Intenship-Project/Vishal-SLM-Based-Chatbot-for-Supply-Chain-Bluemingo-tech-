/**
 * Emergency fix script - run this in browser console if chatbot isn't working
 */

function fixChatbot() {
    console.log('=== CHATBOT FIX SCRIPT ===');
    
    // 1. Check input element
    const input = document.getElementById('chatbot-input');
    console.log('1. Input element:', input);
    if (input) {
        console.log('   - Value:', input.value);
        console.log('   - Disabled:', input.disabled);
        console.log('   - ReadOnly:', input.readOnly);
        console.log('   - Style display:', window.getComputedStyle(input).display);
        console.log('   - Style visibility:', window.getComputedStyle(input).visibility);
        console.log('   - Style opacity:', window.getComputedStyle(input).opacity);
        
        // Fix input
        input.disabled = false;
        input.readOnly = false;
        input.style.pointerEvents = 'auto';
        input.style.opacity = '1';
        input.style.visibility = 'visible';
        input.style.display = 'block';
        console.log('   ✅ Input fixed');
    } else {
        console.error('   ❌ Input not found!');
    }
    
    // 2. Check messages container
    const messagesEl = document.getElementById('chatbot-messages');
    console.log('2. Messages container:', messagesEl);
    if (messagesEl) {
        console.log('   - Children count:', messagesEl.children.length);
        console.log('   - Style display:', window.getComputedStyle(messagesEl).display);
        console.log('   - Style visibility:', window.getComputedStyle(messagesEl).visibility);
        console.log('   - Style opacity:', window.getComputedStyle(messagesEl).opacity);
        console.log('   - Style height:', window.getComputedStyle(messagesEl).height);
        
        // Fix messages container
        messagesEl.style.display = 'flex';
        messagesEl.style.visibility = 'visible';
        messagesEl.style.opacity = '1';
        messagesEl.style.height = 'auto';
        messagesEl.style.minHeight = '100px';
        console.log('   ✅ Messages container fixed');
    } else {
        console.error('   ❌ Messages container not found!');
    }
    
    // 3. Check chatbot container
    const container = document.getElementById('chatbot-widget');
    console.log('3. Chatbot container:', container);
    if (container) {
        console.log('   - Style display:', window.getComputedStyle(container).display);
        console.log('   - Style visibility:', window.getComputedStyle(container).visibility);
        console.log('   - Style z-index:', window.getComputedStyle(container).zIndex);
    }
    
    // 4. Test input
    if (input) {
        console.log('4. Testing input...');
        input.value = 'test';
        console.log('   - Set value to "test", current value:', input.value);
        
        // Test typing
        const event = new Event('input', { bubbles: true });
        input.dispatchEvent(event);
        console.log('   - Dispatched input event');
    }
    
    // 5. Test message removed - no longer needed
    // Removed test message to prevent clutter
    
    console.log('=== FIX COMPLETE ===');
    console.log('Try typing in the input now. If it still doesn\'t work, check the console for errors.');
}

// Auto-run if chatbot exists
if (window.chatbot) {
    console.log('Chatbot found, running fix...');
    fixChatbot();
} else {
    console.log('Chatbot not found. Run fixChatbot() manually after chatbot loads.');
    window.fixChatbot = fixChatbot;
}




