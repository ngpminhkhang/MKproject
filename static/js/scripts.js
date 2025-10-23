var gk_isXlsx = false;
var gk_xlsxFileLookup = {};
var gk_fileData = {};

function filledCell(cell) {
    return cell !== '' && cell != null;
}

function loadFileData(filename) {
    if (gk_isXlsx && gk_xlsxFileLookup[filename]) {
        try {
            var workbook = XLSX.read(gk_fileData[filename], { type: 'base64' });
            var firstSheetName = workbook.SheetNames[0];
            var worksheet = workbook.Sheets[firstSheetName];
            var jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1, blankrows: false, defval: '' });
            var filteredData = jsonData.filter(row => row.some(filledCell));
            var headerRowIndex = filteredData.findIndex((row, index) =>
                row.filter(filledCell).length >= filteredData[index + 1]?.filter(filledCell).length
            );
            if (headerRowIndex === -1 || headerRowIndex > 25) {
                headerRowIndex = 0;
            }
            var csv = XLSX.utils.aoa_to_sheet(filteredData.slice(headerRowIndex));
            csv = XLSX.utils.sheet_to_csv(csv, { header: 1 });
            return csv;
        } catch (e) {
            console.error(e);
            return "";
        }
    }
    return gk_fileData[filename] || "";
}

// Function to handle insight filtering
function filterInsights(category) {
    const insights = document.querySelectorAll('.insight-card');
    insights.forEach(insight => {
        if (category === 'all' || insight.getAttribute('data-category') === category) {
            insight.style.display = 'block';
        } else {
            insight.style.display = 'none';
        }
    });
    
    // Update active filter button
    document.querySelectorAll('.filter-btn').forEach(btn => {
        if (btn.getAttribute('data-filter') === category) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

// Function to handle search
function searchInsights() {
    const searchTerm = document.getElementById('insightSearch').value.toLowerCase();
    const insights = document.querySelectorAll('.insight-card');
    
    insights.forEach(insight => {
        const title = insight.querySelector('.card-title').textContent.toLowerCase();
        const content = insight.querySelector('.insight-summary').textContent.toLowerCase();
        
        if (title.includes(searchTerm) || content.includes(searchTerm)) {
            insight.style.display = 'block';
        } else {
            insight.style.display = 'none';
        }
    });
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('MK Project loaded');
    
    // Initialize filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const filter = this.getAttribute('data-filter');
            filterInsights(filter);
        });
    });
    
    // Initialize search functionality
    const searchInput = document.getElementById('insightSearch');
    if (searchInput) {
        searchInput.addEventListener('keyup', searchInsights);
    }
    
    // Setup full width layout for insights page
    setupFullWidthLayout();
});

// Setup full width layout
function setupFullWidthLayout() {
    const insightsPage = document.querySelector('.insights-full-width');
    
    if (insightsPage) {
        // Remove container padding for full width
        const container = document.querySelector('.insights-full-width .container');
        if (container) {
            container.classList.remove('container');
            container.classList.add('container-fluid');
        }
        
        // Add custom padding for very large screens
        if (window.innerWidth > 1600) {
            insightsPage.style.paddingLeft = '5%';
            insightsPage.style.paddingRight = '5%';
        }
    }
}

// Adjust layout on window resize
window.addEventListener('resize', setupFullWidthLayout);