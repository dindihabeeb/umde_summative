// ============================================
// CONFIGURATION - UPDATE THIS WITH YOUR BACKEND URL
// ============================================
const API_BASE_URL = 'http://localhost:5000/api'; // Change this to your backend URL

// ============================================
// GLOBAL VARIABLES
// ============================================
let charts = {};
const chartColors = {
    primary: 'rgba(102, 126, 234, 0.8)',
    secondary: 'rgba(118, 75, 162, 0.8)',
    success: 'rgba(74, 222, 128, 0.8)',
    warning: 'rgba(251, 191, 36, 0.8)',
    danger: 'rgba(248, 113, 113, 0.8)',
    info: 'rgba(96, 165, 250, 0.8)'
};

// ============================================
// API HELPER FUNCTIONS
// ============================================

async function fetchAPI(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        if (!response.ok) {
            throw new Error(`API Error: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();
        updateConnectionStatus(true);
        return data;
    } catch (error) {
        console.error('Fetch error:', error);
        updateConnectionStatus(false);
        showError(`Failed to fetch data: ${error.message}`);
        throw error;
    }
}

function getFilters() {
    return {
        startDate: document.getElementById('startDate').value,
        endDate: document.getElementById('endDate').value,
        timeOfDay: {
            morning: document.getElementById('timeMorning').checked,
            afternoon: document.getElementById('timeAfternoon').checked,
            evening: document.getElementById('timeEvening').checked,
            night: document.getElementById('timeNight').checked
        },
        fareMax: parseInt(document.getElementById('fareRange').value),
        distanceMax: parseInt(document.getElementById('distanceRange').value),
        passengerCount: document.getElementById('passengerFilter').value,
        borough: document.getElementById('boroughFilter').value
    };
}

function buildQueryString(filters) {
    const params = new URLSearchParams();
    
    if (filters.startDate) params.append('start_date', filters.startDate);
    if (filters.endDate) params.append('end_date', filters.endDate);
    if (filters.fareMax) params.append('fare_max', filters.fareMax);
    if (filters.distanceMax) params.append('distance_max', filters.distanceMax);
    if (filters.passengerCount !== 'all') params.append('passenger_count', filters.passengerCount);
    if (filters.borough !== 'all') params.append('borough', filters.borough);
    
    const timeFilters = [];
    if (filters.timeOfDay.morning) timeFilters.push('morning');
    if (filters.timeOfDay.afternoon) timeFilters.push('afternoon');
    if (filters.timeOfDay.evening) timeFilters.push('evening');
    if (filters.timeOfDay.night) timeFilters.push('night');
    if (timeFilters.length > 0 && timeFilters.length < 4) {
        params.append('time_of_day', timeFilters.join(','));
    }
    
    return params.toString();
}

// ============================================
// API ENDPOINT FUNCTIONS
// ============================================

async function fetchSummary(filters) {
    const query = buildQueryString(filters);
    return await fetchAPI(`/summary?${query}`);
}

async function fetchHourlyTrips(filters) {
    const query = buildQueryString(filters);
    return await fetchAPI(`/trips/hourly?${query}`);
}

async function fetchSpeedByTime(filters) {
    const query = buildQueryString(filters);
    return await fetchAPI(`/speed/by-time?${query}`);
}

async function fetchPassengerDistribution(filters) {
    const query = buildQueryString(filters);
    return await fetchAPI(`/passengers/distribution?${query}`);
}

async function fetchDurationDistribution(filters) {
    const query = buildQueryString(filters);
    return await fetchAPI(`/duration/distribution?${query}`);
}

async function fetchScatterData(filters) {
    const query = buildQueryString(filters);
    return await fetchAPI(`/trips/scatter?${query}&limit=200`);
}

async function fetchInsights(filters) {
    const query = buildQueryString(filters);
    return await fetchAPI(`/insights?${query}`);
}

// ============================================
// UI UPDATE FUNCTIONS
// ============================================

function updateKPIs(data) {
    document.getElementById('kpiTotalTrips').textContent = formatNumber(data.total_trips);
    document.getElementById('kpiAvgDuration').textContent = `${data.avg_duration}m`;
    document.getElementById('kpiTotalDistance').textContent = `${formatNumber(data.total_distance)} mi`;
    document.getElementById('kpiAvgFare').textContent = `$${data.avg_fare.toFixed(2)}`;
    
    if (data.changes) {
        updateChangeIndicator('kpiTotalTripsChange', data.changes.trips);
        updateChangeIndicator('kpiAvgDurationChange', data.changes.duration);
        updateChangeIndicator('kpiTotalDistanceChange', data.changes.distance);
        updateChangeIndicator('kpiAvgFareChange', data.changes.fare);
    }
}

function updateChangeIndicator(elementId, change) {
    const element = document.getElementById(elementId);
    if (change !== undefined && change !== null) {
        const arrow = change >= 0 ? '↑' : '↓';
        const color = change >= 0 ? '#4ade80' : '#f87171';
        element.textContent = `${arrow} ${Math.abs(change).toFixed(1)}% vs last month`;
        element.style.color = color;
    } else {
        element.textContent = 'No comparison data';
        element.style.color = '#a0a0a0';
    }
}

function updateInsights(insights) {
    const container = document.getElementById('insightsContainer');
    
    if (!insights || insights.length === 0) {
        container.innerHTML = '<div class="insight-item"><h4>No insights available</h4><p>Try adjusting your filters.</p></div>';
        return;
    }
    
    container.innerHTML = insights.map(insight => `
        <div class="insight-item">
            <h4>${insight.title}</h4>
            <p>${insight.description}</p>
        </div>
    `).join('');
}

function showError(message) {
    const errorElement = document.getElementById('errorMessage');
    errorElement.textContent = message;
    errorElement.classList.add('show');
    setTimeout(() => errorElement.classList.remove('show'), 5000);
}

function updateConnectionStatus(connected) {
    const indicator = document.getElementById('statusIndicator');
    indicator.className = `status-indicator ${connected ? 'connected' : 'disconnected'}`;
}

function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}

// ============================================
// CHART FUNCTIONS
// ============================================

function initializeCharts() {
    charts.timeSeries = new Chart(document.getElementById('timeSeriesChart').getContext('2d'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Trips per Hour',
                data: [],
                borderColor: chartColors.primary,
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                tension: 0.4,
                fill: true,
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: getChartOptions('linear')
    });

    charts.speed = new Chart(document.getElementById('speedChart').getContext('2d'), {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Avg Speed (mph)',
                data: [],
                backgroundColor: [chartColors.warning, chartColors.success, chartColors.danger, chartColors.info]
            }]
        },
        options: getChartOptions('bar')
    });

    charts.passenger = new Chart(document.getElementById('passengerChart').getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: [chartColors.primary, chartColors.secondary, chartColors.success, chartColors.warning]
            }]
        },
        options: getDoughnutOptions()
    });

    charts.duration = new Chart(document.getElementById('durationChart').getContext('2d'), {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Number of Trips',
                data: [],
                backgroundColor: chartColors.primary
            }]
        },
        options: getChartOptions('bar')
    });

    charts.scatter = new Chart(document.getElementById('scatterChart').getContext('2d'), {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Trips',
                data: [],
                backgroundColor: chartColors.info,
                pointRadius: 3
            }]
        },
        options: getScatterOptions()
    });
}

function getChartOptions(type) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: { color: '#e0e0e0' }
            }
        },
        scales: {
            y: {
                beginAtZero: true,
                ticks: { color: '#a0a0a0' },
                grid: { color: 'rgba(255, 255, 255, 0.1)' }
            },
            x: {
                ticks: { color: '#a0a0a0' },
                grid: { color: 'rgba(255, 255, 255, 0.1)' }
            }
        }
    };
}

function getDoughnutOptions() {
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'bottom',
                labels: { color: '#e0e0e0', padding: 15 }
            }
        }
    };
}

function getScatterOptions() {
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: { color: '#e0e0e0' }
            }
        },
        scales: {
            y: {
                title: { display: true, text: 'Duration (min)', color: '#a0a0a0' },
                ticks: { color: '#a0a0a0' },
                grid: { color: 'rgba(255, 255, 255, 0.1)' }
            },
            x: {
                title: { display: true, text: 'Distance (miles)', color: '#a0a0a0' },
                ticks: { color: '#a0a0a0' },
                grid: { color: 'rgba(255, 255, 255, 0.1)' }
            }
        }
    };
}

function updateChart(chartName, labels, data) {
    if (!charts[chartName]) return;
    
    charts[chartName].data.labels = labels;
    
    if (Array.isArray(data)) {
        charts[chartName].data.datasets[0].data = data;
    } else {
        charts[chartName].data.datasets[0].data = data;
    }
    
    charts[chartName].update();
}

function updateScatterChart(data) {
    if (!charts.scatter) return;
    charts.scatter.data.datasets[0].data = data;
    charts.scatter.update();
}

// ============================================
// MAIN DATA LOADING FUNCTION
// ============================================

async function loadDashboardData() {
    const filters = getFilters();
    
    document.getElementById('applyFiltersBtn').disabled = true;
    document.getElementById('applyDateBtn').disabled = true;
    
    try {
        const [
            summaryData,
            hourlyData,
            speedData,
            passengerData,
            durationData,
            scatterData,
            insightsData
        ] = await Promise.all([
            fetchSummary(filters),
            fetchHourlyTrips(filters),
            fetchSpeedByTime(filters),
            fetchPassengerDistribution(filters),
            fetchDurationDistribution(filters),
            fetchScatterData(filters),
            fetchInsights(filters)
        ]);
        
        updateKPIs(summaryData);
        updateChart('timeSeries', hourlyData.hours, hourlyData.counts);
        updateChart('speed', speedData.labels, speedData.speeds);
        updateChart('passenger', passengerData.labels, passengerData.counts);
        updateChart('duration', durationData.ranges, durationData.counts);
        updateScatterChart(scatterData.data);
        updateInsights(insightsData.insights);
        
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        loadMockData();
    } finally {
        document.getElementById('applyFiltersBtn').disabled = false;
        document.getElementById('applyDateBtn').disabled = false;
    }
}

// ============================================
// MOCK DATA (FOR TESTING WITHOUT BACKEND)
// ============================================

function loadMockData() {
    console.warn('Loading mock data - backend connection failed');
    
    updateKPIs({
        total_trips: 1200000,
        avg_duration: 18.4,
        total_distance: 8300000,
        avg_fare: 16.82,
        changes: {
            trips: 12.5,
            duration: -3.2,
            distance: 8.7,
            fare: 5.1
        }
    });
    
    updateChart('timeSeries', 
        ['12AM', '2AM', '4AM', '6AM', '8AM', '10AM', '12PM', '2PM', '4PM', '6PM', '8PM', '10PM'],
        [3200, 1800, 1200, 2500, 8900, 7200, 6500, 6800, 7500, 9800, 8200, 5400]
    );
    
    updateChart('speed',
        ['Morning', 'Afternoon', 'Evening', 'Night'],
        [12.5, 14.2, 9.8, 18.5]
    );
    
    updateChart('passenger',
        ['1 Passenger', '2 Passengers', '3 Passengers', '4+ Passengers'],
        [72, 18, 7, 3]
    );
    
    updateChart('duration',
        ['0-10m', '10-20m', '20-30m', '30-40m', '40-50m', '50m+'],
        [285000, 420000, 315000, 125000, 45000, 15000]
    );
    
    const mockScatter = [];
    for (let i = 0; i < 200; i++) {
        mockScatter.push({
            x: Math.random() * 30,
            y: Math.random() * 60 + (Math.random() * 30)
        });
    }
    updateScatterChart(mockScatter);
    
    updateInsights([
        {
            title: '🕐 Peak Rush Hour Pattern',
            description: 'Trip volume peaks at 8-9 AM and 5-7 PM on weekdays, with 45% higher demand during evening rush hours. Average trip duration increases by 28% during these periods due to traffic congestion.'
        },
        {
            title: '💰 Fare Efficiency Analysis',
            description: 'Trips under 5 miles show the highest fare-per-mile ratio ($4.20/mi), while longer trips (15+ miles) average $2.10/mi. Night trips (12AM-6AM) command 15% higher fares on average.'
        },
        {
            title: '🚦 Speed Anomaly Detection',
            description: 'Average speed drops to 8.2 mph during weekday rush hours in Manhattan, compared to 18.5 mph during off-peak hours. Weekend speeds are 32% faster on average.'
        }
    ]);
    
    showError('Using mock data - backend connection unavailable. Please check API_BASE_URL in app.js');
}

// ============================================
// EVENT LISTENERS
// ============================================

function initializeEventListeners() {
    document.getElementById('fareRange').addEventListener('input', function(e) {
        document.getElementById('fareValue').textContent = e.target.value;
    });

    document.getElementById('distanceRange').addEventListener('input', function(e) {
        document.getElementById('distanceValue').textContent = e.target.value;
    });
    
    document.getElementById('applyFiltersBtn').addEventListener('click', function() {
        loadDashboardData();
    });
    
    document.getElementById('applyDateBtn').addEventListener('click', function() {
        loadDashboardData();
    });
    
    document.getElementById('startDate').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') loadDashboardData();
    });
    
    document.getElementById('endDate').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') loadDashboardData();
    });
}

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing NYC Taxi Analytics Dashboard...');
    console.log('API Base URL:', API_BASE_URL);
    
    initializeCharts();
    initializeEventListeners();
    loadDashboardData();
    
    console.log('Dashboard initialized successfully!');
});

// ============================================
// UTILITY FUNCTIONS FOR BACKEND DEVELOPERS
// ============================================

window.testAPIConnection = async function() {
    console.log('Testing API connection to:', API_BASE_URL);
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (response.ok) {
            console.log('Backend connection successful!');
            const data = await response.json();
            console.log('Response:', data);
            return true;
        } else {
            console.error('Backend returned error:', response.status);
            return false;
        }
    } catch (error) {
        console.error('Cannot connect to backend:', error.message);
        console.log('Make sure your backend is running on:', API_BASE_URL);
        return false;
    }
};

window.refreshDashboard = function() {
    console.log('Refreshing dashboard...');
    loadDashboardData();
};

window.getCurrentFilters = function() {
    const filters = getFilters();
    console.log('Current Filters:', filters);
    return filters;
};
