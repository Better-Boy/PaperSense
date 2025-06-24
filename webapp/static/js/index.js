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

    card.innerHTML = `
        <div class="similarity-score">${paper.relevance}</div>
        <div class="paper-title"><a href="/api/chat-ui?query=${paper.article_id}" style="text-decoration:none; color: #1a202c" target="_blank">${paper.title ? paper.title: ""}</a></div>
        <div class="paper-authors">${paper.authors}</div>
        <div class="paper-meta">
            <span>📄 ${paper.article_id ? `arXiv:${paper.article_id}` : ''}</span>
            <span>📅 ${paper.published_year}</span>
        </div>
        <div class="paper-abstract">
            ${paper.summary}
        </div>
        <div class="paper-tags">
            ${paper.categories.split(",").map(tag => `<span class="tag">${tag.trim()}</span>`).join('')}
        </div>
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