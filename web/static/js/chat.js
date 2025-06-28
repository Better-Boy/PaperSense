// PDF.js setup
pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

let pdfDoc = null;
let pageNum = 1;
let pageRendering = false;
let pageNumPending = null;
let scale = 1.5;
const canvas = document.createElement('canvas');
canvas.className = 'pdf-canvas';

// Chat data
let messages = [];

// Navigation function
function goToHome() {
    
    // You could also redirect to an actual home page if needed
    window.location.href = '/';
}

function getArxivId(url){
    const array = url.trim().split("=");
    return array[array.length - 1];
}

function loadPdfFromUrl() {
    const arxivId = getArxivId(window.location.href);
    const url = `https://arxiv.org/pdf/${arxivId}`;

    // Show loading state
    const viewer = document.getElementById('pdf-viewer');
    viewer.innerHTML = '<div class="pdf-placeholder"><div style="text-align: center;"><div style="margin-bottom: 20px;">📄</div><h3>Loading PDF...</h3><p>Please wait while we fetch the document</p></div></div>';

    // Use a CORS proxy for external PDFs
    const proxyUrl = url;
    
    pdfjsLib.getDocument(proxyUrl).promise.then(function(pdf) {
        pdfDoc = pdf;
        pageNum = 1;
        document.getElementById('pdf-controls').style.display = 'flex';
        renderPage(pageNum);
        updatePageInfo();
        
        // Add welcome message for PDF
        addMessage("assistant", "📄 PDF loaded successfully! I can now help you analyze and answer questions about this document. What would you like to know?");
    }).catch(function(error) {
        console.error('Error loading PDF:', error);
        viewer.innerHTML = '<div class="pdf-placeholder"><div style="text-align: center; color: #ef4444;"><div style="margin-bottom: 20px;">❌</div><h3>Error loading PDF</h3><p>Please check the URL and try again.<br>Note: Some PDFs may not load due to CORS restrictions.</p></div></div>';
    });
}

// Load default PDF on page load
window.addEventListener('load', function() {
    loadPdfFromUrl();
});

// Render a page
function renderPage(num) {
    pageRendering = true;
    pdfDoc.getPage(num).then(function(page) {
        const viewport = page.getViewport({scale: scale});
        canvas.height = viewport.height;
        canvas.width = viewport.width;

        const renderContext = {
            canvasContext: canvas.getContext('2d'),
            viewport: viewport
        };

        const renderTask = page.render(renderContext);
        renderTask.promise.then(function() {
            pageRendering = false;
            if (pageNumPending !== null) {
                renderPage(pageNumPending);
                pageNumPending = null;
            }
        });

        // Replace placeholder with canvas
        const viewer = document.getElementById('pdf-viewer');
        viewer.innerHTML = '';
        viewer.appendChild(canvas);
    });
}

// Queue rendering
function queueRenderPage(num) {
    if (pageRendering) {
        pageNumPending = num;
    } else {
        renderPage(num);
    }
}

// Navigation functions
function previousPage() {
    if (pageNum <= 1) return;
    pageNum--;
    queueRenderPage(pageNum);
    updatePageInfo();
}

function nextPage() {
    if (pageNum >= pdfDoc.numPages) return;
    pageNum++;
    queueRenderPage(pageNum);
    updatePageInfo();
}

function zoomIn() {
    scale += 0.25;
    queueRenderPage(pageNum);
}

function zoomOut() {
    if (scale <= 0.5) return;
    scale -= 0.25;
    queueRenderPage(pageNum);
}

function updatePageInfo() {
    document.getElementById('page-info').textContent = `Page ${pageNum} of ${pdfDoc ? pdfDoc.numPages : 1}`;
}

// Chat functions
function addMessage(sender, text, isLoading = false) {
    const messagesContainer = document.getElementById('chat-messages');
    
    if (firstMessage && sender === 'user') {
        const welcomeMsg = messagesContainer.querySelector('.welcome-message');
        if (welcomeMsg) welcomeMsg.remove();
        firstMessage = false;
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    
    const now = new Date();
    const time = now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    
    if (isLoading) {
        messageDiv.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px;">
                <div class="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
                <span>thinking...</span>
            </div>
            <div class="message-time">${time}</div>
        `;
    } else {
        messageDiv.innerHTML = `
            <div>${text}</div>
            <div class="message-time">${time}</div>
        `;
    }
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    messages.push({sender, text, time});
    return messageDiv;
}

async function handleUserMessage(text) {
    if (!text.trim()) return;
    
    addMessage('user', text);
    
    // Add loading message
    const loadingMessage = addMessage('assistant', '', true);
    const arxivId = getArxivId(window.location.href);
    try {
        
        // Make API call
        const response = await fetch('/api/chat', {
            method: 'POST',
            body: JSON.stringify({
                arxiv_id: arxivId,
                query: text
            })
        });

        // Remove loading message
        loadingMessage.remove();

        if (!response.ok) {
            throw new Error(`API request failed: ${response.status}`);
        }

        const data = await response.json();
        const aiResponse = data.response;
        const parsed_response = marked.parse(aiResponse);
        addMessage('assistant', parsed_response);
        
    } catch (error) {
        console.error('API Error:', error);
        
        // Remove loading message
        loadingMessage.remove();
        
        // Show error message with fallback
        const errorMessage = "⚠️ Sorry, I couldn't connect to the AI service right now. Please try again later.";
        
        addMessage('assistant', errorMessage);
    }
}

function handleEnter(event) {
    if (event.key === 'Enter') {
        const input = document.getElementById('chat-input');
        const text = input.value;
        input.value = '';
        handleUserMessage(text);
    }
}

// Remove welcome message when first user message is sent
let firstMessage = true;