document.addEventListener('DOMContentLoaded', () => {
    loadOpportunities();
});

async function loadOpportunities() {
    const tableBody = document.getElementById('opportunities-table-body');
    const loadingMessage = document.getElementById('loading-message');

    try {
        // We fetch our 'database' file. Add a cache-buster to get the latest version.
        const response = await fetch(`opportunities.json?v=${new Date().getTime()}`);

        if (!response.ok) {
            throw new Error('Could not find opportunities data. The script may not have run yet.');
        }

        const data = await response.json();

        if (data.length === 0) {
            loadingMessage.innerText = 'No opportunities found matching your criteria. Check back later!';
            return;
        }

        // Clear the table and loading message
        tableBody.innerHTML = '';
        loadingMessage.style.display = 'none';

        // Loop through each opportunity and create a table row
        data.forEach(op => {
            const row = `
                <tr>
                    <td>${op.event}</td>
                    <td>${op.market}</td>
                    <td>$${op.kalshi_price.toFixed(2)}</td>
                    <td>+${op.moneyline}</td>
                    <td><a href="${op.kalshi_url}" target="_blank">View Market</a></td>
                </tr>
            `;
            tableBody.innerHTML += row;
        });

    } catch (error) {
        console.error('Error fetching opportunities:', error);
        loadingMessage.innerText = `Error: ${error.message}`;
    }
}
