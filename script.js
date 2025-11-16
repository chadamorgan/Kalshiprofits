// This will store all the data we fetch, so we don't lose it when filtering
let allMarketData = [];

document.addEventListener('DOMContentLoaded', () => {
    // Connect our buttons to the functions
    document.getElementById('filter-button').addEventListener('click', applyFilters);
    document.getElementById('reset-button').addEventListener('click', resetFilters);
    
    // Load the initial data
    loadInitialData();
});

async function loadInitialData() {
    const loadingMessage = document.getElementById('loading-message');
    try {
        // Fetch the 'database' file. Add a cache-buster to get the latest version.
        const response = await fetch(`opportunities.json?v=${new Date().getTime()}`);
        
        if (!response.ok) {
            throw new Error('Could not find opportunities data. The script may not have run yet.');
        }
        
        allMarketData = await response.json();

        if (allMarketData.length === 0) {
            loadingMessage.innerText = 'No markets found matching your criteria. Check back later!';
            return;
        }
        
        loadingMessage.style.display = 'none';
        // Render the full table for the first time
        renderTable(allMarketData);

    } catch (error) {
        console.error('Error fetching opportunities:', error);
        loadingMessage.innerText = `Error: ${error.message}`;
    }
}

/**
 * Renders the table on the page with a given set of market data
 * @param {Array} marketsToDisplay - The array of market objects to show
 */
function renderTable(marketsToDisplay) {
    const tableBody = document.getElementById('opportunities-table-body');
    tableBody.innerHTML = ''; // Clear the table first

    if (marketsToDisplay.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="4">No markets match your filter.</td></tr>';
        return;
    }

    marketsToDisplay.forEach(market => {
        // Create the list of bookmaker odds
        const oddsListHtml = market.bookmakers
            .map(book => {
                const moneyline = book.moneyline > 0 ? `+${book.moneyline}` : book.moneyline;
                return `<li><strong>${book.name}:</strong> ${moneyline}</li>`;
            })
            .join(''); // Join all list items into one string

        const row = `
            <tr>
                <td>${market.event}</td>
                <td>
                    <strong>${market.team_on_kalshi}</strong><br>
                    <a href="${market.kalshi_url}" target="_blank">${market.kalshi_market}</a>
                </td>
                <td>$${market.kalshi_price.toFixed(2)}</td>
                <td class="odds-list"><ul>${oddsListHtml}</ul></td>
            </tr>
        `;
        tableBody.innerHTML += row;
    });
}

/**
 * Called when the "Filter" button is clicked
 */
function applyFilters() {
    const minOddsInput = document.getElementById('min-odds').value;
    const maxOddsInput = document.getElementById('max-odds').value;

    // Convert empty strings to null, otherwise convert to a number
    const minOdds = minOddsInput ? Number(minOddsInput) : null;
    const maxOdds = maxOddsInput ? Number(maxOddsInput) : null;

    // Use the .filter() array method to find matching markets
    const filteredData = allMarketData.filter(market => {
        // .some() checks if AT LEAST ONE bookmaker matches the criteria
        return market.bookmakers.some(book => {
            const moneyline = book.moneyline;
            
            // Check if it passes the min-odds filter (if one exists)
            const passesMin = (minOdds === null) || (moneyline >= minOdds);
            // Check if it passes the max-odds filter (if one exists)
            const passesMax = (maxOdds === null) || (moneyline <= maxOdds);
            
            return passesMin && passesMax;
        });
    });

    // Re-render the table with only the filtered data
    renderTable(filteredData);
}

/**
 * Called when the "Reset" button is clicked
 */
function resetFilters() {
    // Clear the input boxes
    document.getElementById('min-odds').value = '';
    document.getElementById('max-odds').value = '';
    
    // Re-render the table with the original, complete dataset
    renderTable(allMarketData);
}
