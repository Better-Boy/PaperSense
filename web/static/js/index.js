// Get references to HTML elements
const searchBox = document.querySelector('.search-box');
const searchBtn = document.querySelector('.search-btn');
const field = document.getElementById("field");
const year = document.getElementById("year");
const loading = document.getElementById('loading');
const resultsContainer = document.getElementById('results');
const resultsHeader = resultsContainer.querySelector('.results-header');
const resultsCount = resultsHeader.querySelector('.results-count');
const paperCardsContainer = document.createElement('div'); // Create a container for paper cards
paperCardsContainer.classList.add('paper-cards-wrapper'); // Add a class for potential styling

// Append the new container to the results div, after the header
resultsContainer.appendChild(paperCardsContainer);

// Function to show the loading spinner
const showLoading = () => {
    loading.style.display = 'block'; // Use flex to center spinner and text
    resultsContainer.style.display = 'none';
};

// Function to hide the loading spinner
const hideLoading = () => {
    loading.style.display = 'none';
    resultsContainer.style.display = 'block'; // Or 'flex' depending on your layout
};

// Function to create a paper card HTML element
const createPaperCard = (paper) => {
    const card = document.createElement('div');
    card.classList.add('paper-card');
    card.setAttribute('data-paper-id', paper.article_id);

    card.innerHTML = `
        <div class="similarity-score">${paper.relevance}</div>
        <div class="paper-title"><a href="/api/chat-ui?query=${paper.article_id}" style="text-decoration:none; color: #1a202c" target="_blank">${paper.title ? paper.title: ""}</a></div>
        <div class="paper-authors">${paper.authors}</div>
        <div class="paper-meta">
            <span>📄 ${paper.article_id ? `arXiv:${paper.article_id}` : ''}</span>
            <span>📅 ${paper.published_year}</span>
        </div>
        <div class="paper-abstract">
            ${paper.abstract}
        </div>
        <div class="paper-tags">
            ${paper.categories.split(",").map(tag => `<span class="tag">${tag.trim()}</span>`).join('')}
        </div>
        <div class="api-actions">
            <button class="api-btn" data-action="summary">
                <i class="fas fa-file-text"></i> AI Summary
            </button>
            <button class="api-btn" data-action="ideas">
                <i class="fa-solid fa-wand-magic-sparkles" style="color: #FFD43B;"></i> Generate Ideas
            </button>
        </div>
        <div class="api-response"></div>
    `;
    return card;
};

// Function to fetch and display search results
const fetchAndDisplayResults = async (query) => {
    showLoading();
    // Clear previous results
    paperCardsContainer.innerHTML = '';
    resultsCount.textContent = 'Searching...'; // Update count while loading

    try {
        var url = `/api/search?query=${encodeURIComponent(query)}`;
        if(field.value) url += `&category=${field.value}`;
        if(year.value) url += `&year=${year.value}`;
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const res = await response.json(); // Assuming the API returns JSON
        const data = res.results;
        resultsCount.textContent = `Found ${data.length} papers for "${query}"`;

        if (data.length > 0) {
            data.forEach(paper => {
                const paperCard = createPaperCard(paper);
                paperCardsContainer.appendChild(paperCard);
            });
        } else {
            paperCardsContainer.innerHTML = '<p class="no-results">No papers found for your query.</p>';
        }

    } catch (error) {
        console.error('Error fetching papers:', error);
        resultsCount.textContent = `Error: Could not retrieve papers.`;
        paperCardsContainer.innerHTML = '<p class="error-message">An error occurred while fetching results. Please try again later.</p>';
    } finally {
        hideLoading();
    }
};

document.addEventListener('DOMContentLoaded', function() {
    // Add this to your existing DOMContentLoaded code
    
    // API button clicks
    document.addEventListener('click', handleApiButtonClick);
    
    // Your existing code continues here...
});

async function makeApiCall(action, paperId) {

    var url = `/api/ai-table?action=${action}&arxivId=${paperId}`;
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`No ${action} data available for this paper`);
    }

    const res = await response.json(); // Assuming the API returns JSON
    const parsed_response = marked.parse(res);
    return {
        success:true,
        data: parsed_response
    }
}

function handleApiButtonClick(event) {
    const button = event.target.closest('.api-btn');
    if (!button) return;

    const action = button.dataset.action;
    const paperCard = button.closest('.paper-card');
    const paperId = paperCard.dataset.paperId;
    const responseContainer = paperCard.querySelector('.api-response');

    // Prevent multiple simultaneous calls
    if (button.classList.contains('loading')) return;

    // Show loading state
    button.classList.add('loading');
    button.disabled = true;
    const originalHTML = button.innerHTML;
    button.innerHTML = `<span class="spinner-small"></span> Loading...`;

    // Make API call
    makeApiCall(action, paperId)
        .then(response => {
            // Show response
            displayApiResponse(responseContainer, action, response.data);
        })
        .catch(error => {
            // Show error
            displayApiResponse(responseContainer, action, error.message, true);
        })
        .finally(() => {
            // Reset button state
            button.classList.remove('loading');
            button.disabled = false;
            button.innerHTML = originalHTML;
        });
}

// Display API response
function displayApiResponse(container, action, content, isError = false) {
    const actionTitles = {
        summary: 'AI Summary',
        ideas: 'Generate Ideas'
    };

    container.innerHTML = `
        <div class="api-response-header">
            <span class="api-response-title">${actionTitles[action]}</span>
            <button class="api-response-close" onclick="this.closest('.api-response').classList.remove('show')">&times;</button>
        </div>
        <div class="api-response-content">${content}</div>
    `;

    container.className = `api-response ${isError ? 'api-error' : ''} show`;
}


const performSearch = () => {
    const query = searchBox.value.trim();
    if (query) {
        fetchAndDisplayResults(query);
    }
}

// Event listener for the search button click
searchBtn.addEventListener('click', () => {
    performSearch();
});

// Event listener for pressing Enter in the search box
searchBox.addEventListener('keypress', (event) => {
    if (event.key === 'Enter') {
        performSearch();
    }
});

// Filter dropdown change
year.addEventListener('change', () => {
    performSearch();
});

field.addEventListener('change', () => {
    performSearch();
});

// Add hover effects to paper cards
document.querySelectorAll('.paper-card').forEach(card => {
    card.addEventListener('mouseenter', () => {
        card.style.transform = 'translateY(-4px)';
        card.style.boxShadow = '0 12px 40px rgba(0, 0, 0, 0.15)';
    });
    
    card.addEventListener('mouseleave', () => {
        card.style.transform = 'translateY(0)';
        card.style.boxShadow = '0 8px 30px rgba(0, 0, 0, 0.1)';
    });
});

// Smooth scrolling for better UX (Note: Your HTML does not have any href="#id" links to make this functional)
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

document.getElementById('arxiv-btn').addEventListener('click', () => {
    const modal = document.getElementById('arxiv-modal');
    const input = document.getElementById('arxiv-input');
    const errorElement = document.getElementById('arxiv-error');
    
    modal.classList.add('show');
    input.value = '';
    errorElement.style.display = 'none';
    setTimeout(() => input.focus(), 100);
});

// Modal cancel button
document.getElementById('modal-cancel').addEventListener('click', () => {
    document.getElementById('arxiv-modal').classList.remove('show');
});

// Modal submit button
document.getElementById('modal-submit').addEventListener('click', () => {
    const arxivId = document.getElementById('arxiv-input').value;
    const errorElement = document.getElementById('arxiv-error');
    
    // Hide error message first
    errorElement.style.display = 'none';
    
    if (arxivId && arxivId.trim()) {
        // Clean the input - remove any spaces and common prefixes
        let cleanId = arxivId.trim().replace(/^(arxiv:|arXiv:)/i, '');
        
        // Validate basic format (numbers, dots, letters)
        if (/^[\d.]+[a-z]*$/i.test(cleanId)) {
            // Open arXiv link in new tab
            const chatUrl = `/api/chat-ui?query=${cleanId}`;
            window.open(chatUrl, '_blank', 'noopener,noreferrer');
            
            // Close modal
            document.getElementById('arxiv-modal').classList.remove('show');
        } else {
            errorElement.style.display = 'block';
        }
    }
});

// Close modal when clicking overlay
document.getElementById('arxiv-modal').addEventListener('click', (e) => {
    if (e.target.id === 'arxiv-modal') {
        document.getElementById('arxiv-modal').classList.remove('show');
    }
});

// Handle input changes to hide error message
document.getElementById('arxiv-input').addEventListener('input', () => {
    document.getElementById('arxiv-error').style.display = 'none';
});

// Handle Enter key in modal input
document.getElementById('arxiv-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        document.getElementById('modal-submit').click();
    }
});

// Handle Escape key to close modal
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        document.getElementById('arxiv-modal').classList.remove('show');
    }
});