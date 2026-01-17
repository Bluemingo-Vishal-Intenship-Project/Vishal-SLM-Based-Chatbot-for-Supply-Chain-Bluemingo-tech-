/**
 * Input Test Script
 * Run this in console to test and fix input
 */

function testAndFixInput() {
    console.log('=== INPUT TEST & FIX ===');
    
    const input = document.getElementById('chatbot-input');
    if (!input) {
        console.error('Input not found!');
        return;
    }
    
    console.log('1. Current input state:');
    console.log('   - Type:', input.type);
    console.log('   - Value:', input.value);
    console.log('   - Disabled:', input.disabled);
    console.log('   - ReadOnly:', input.readOnly);
    console.log('   - TabIndex:', input.tabIndex);
    
    // Check what's overlaying
    const rect = input.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    const elements = document.elementsFromPoint(centerX, centerY);
    console.log('2. Elements at input position:', elements.map(el => ({
        tag: el.tagName,
        id: el.id,
        class: el.className,
        zIndex: window.getComputedStyle(el).zIndex
    })));
    
    // Check for contenteditable
    const contenteditables = document.querySelectorAll('[contenteditable="true"]');
    console.log('3. Contenteditable elements:', Array.from(contenteditables));
    
    // Try to set value
    console.log('4. Testing value setting...');
    input.value = 'test123';
    console.log('   Set to "test123", current:', input.value);
    
    // Remove ALL event listeners by cloning
    console.log('5. Replacing input with clean clone...');
    const newInput = input.cloneNode(true);
    newInput.value = '';
    newInput.disabled = false;
    newInput.readOnly = false;
    newInput.removeAttribute('disabled');
    newInput.removeAttribute('readonly');
    newInput.style.cssText = `
        pointer-events: auto !important;
        opacity: 1 !important;
        visibility: visible !important;
        display: block !important;
        color: #1f2937 !important;
        background: transparent !important;
        cursor: text !important;
        z-index: 99999 !important;
        position: relative !important;
        -webkit-user-select: text !important;
        user-select: text !important;
        flex: 1;
        border: none;
        outline: none;
        font-size: 14px;
        padding: 8px 0;
        font-family: inherit;
    `;
    
    // Replace
    input.parentNode.replaceChild(newInput, input);
    newInput.id = 'chatbot-input';
    newInput.focus();
    
    console.log('✅ Input replaced. Try typing now!');
    console.log('   If it works, the issue was event listeners.');
    console.log('   If it still doesn\'t work, there\'s a deeper issue.');
    
    // Test typing
    setTimeout(() => {
        newInput.value = 'test';
        console.log('Test value set:', newInput.value);
    }, 100);
    
    return newInput;
}

// Make it available
window.testAndFixInput = testAndFixInput;







