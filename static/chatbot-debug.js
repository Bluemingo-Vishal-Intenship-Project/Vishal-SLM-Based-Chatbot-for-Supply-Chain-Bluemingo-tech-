/**
 * Debug version - logs everything
 * Use this to troubleshoot issues
 */

// Override console methods to show in UI
const originalLog = console.log;
const originalError = console.error;

const debugDiv = document.createElement('div');
debugDiv.id = 'chatbot-debug';
debugDiv.style.cssText = `
    position: fixed;
    top: 10px;
    left: 10px;
    width: 400px;
    max-height: 300px;
    background: rgba(0,0,0,0.8);
    color: #0f0;
    padding: 10px;
    font-family: monospace;
    font-size: 11px;
    z-index: 99999;
    overflow-y: auto;
    border: 2px solid #0f0;
    display: none;
`;
document.body.appendChild(debugDiv);

const debugToggle = document.createElement('button');
debugToggle.textContent = '🐛 Debug';
debugToggle.style.cssText = `
    position: fixed;
    top: 10px;
    left: 10px;
    z-index: 99998;
    padding: 5px 10px;
    background: #333;
    color: white;
    border: none;
    cursor: pointer;
`;
debugToggle.addEventListener('click', () => {
    debugDiv.style.display = debugDiv.style.display === 'none' ? 'block' : 'none';
});
document.body.appendChild(debugToggle);

function addDebugLog(type, ...args) {
    const time = new Date().toLocaleTimeString();
    const message = args.map(arg => 
        typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg)
    ).join(' ');
    const logLine = document.createElement('div');
    logLine.style.color = type === 'error' ? '#f00' : '#0f0';
    logLine.textContent = `[${time}] ${type.toUpperCase()}: ${message}`;
    debugDiv.appendChild(logLine);
    debugDiv.scrollTop = debugDiv.scrollHeight;
    
    // Keep only last 50 lines
    while (debugDiv.children.length > 50) {
        debugDiv.removeChild(debugDiv.firstChild);
    }
}

console.log = function(...args) {
    originalLog.apply(console, args);
    addDebugLog('log', ...args);
};

console.error = function(...args) {
    originalError.apply(console, args);
    addDebugLog('error', ...args);
};

console.log('Debug mode enabled');







