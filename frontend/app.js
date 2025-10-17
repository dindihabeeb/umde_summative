const API_BASE_URL = 'http://localhost:5000/api'; 

let charts = {};
const chartColors = {
    primary: 'rgba(102, 126, 234, 0.8)',
    secondary: 'rgba(118, 75, 162, 0.8)',
    success: 'rgba(74, 222, 128, 0.8)',
    warning: 'rgba(251, 191, 36, 0.8)',
    danger: 'rgba(248, 113, 113, 0.8)',
    info: 'rgba(96, 165, 250, 0.8)'
};

// API HELPER FUNCTIONS

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
        fareMax: (document.getElementById('fareRange') ? parseInt(document.getElementById('fareRange').value) : null),
        distanceMax: (document.getElementById('distanceRange') ? parseInt(document.getElementById('distanceRange').value) : null),
        passengerCount: document.getElementById('passengerFilter').value,
        vendorId: document.getElementById('vendorFilter') ? document.getElementById('vendorFilter').value : 'all',
        durationMin: document.getElementById('durationMin') ? document.getElementById('durationMin').value : '',
        durationMax: document.getElementById('durationMax') ? document.getElementById('durationMax').value : '',
    };
}

function buildQueryString(filters) {
    const params = new URLSearchParams();
    
    if (filters.startDate) params.append('start_date', filters.startDate);
    if (filters.endDate) params.append('end_date', filters.endDate);
    if (filters.passengerCount !== 'all') params.append('passenger_count', filters.passengerCount);
    if (filters.vendorId && filters.vendorId !== 'all') params.append('vendor_id', filters.vendorId);
    if (filters.durationMin) params.append('min_duration', filters.durationMin);
    if (filters.durationMax) params.append('max_duration', filters.durationMax);

    const timeFilters = [];
    if (filters.timeOfDay.morning) timeFilters.push('morning');
    if (filters.timeOfDay.afternoon) timeFilters.push('afternoon');
    if (filters.timeOfDay.evening) timeFilters.push('evening');
    if (filters.timeOfDay.night) timeFilters.push('night');
    if (timeFilters.length > 0 && timeFilters.length < 4) {
    }
    
    return params.toString();
}

// API ENDPOINT FUNCTIONS

async function fetchSummary(filters) {
    const query = buildQueryString(filters);
    const resp = await fetchAPI(`/statistics/overview?${query}`);
    const stats = resp && resp.statistics ? resp.statistics : {};
    // Normalize for UI expectations
    if (typeof stats.avg_duration === 'number') {
        stats.avg_duration = (stats.avg_duration / 60).toFixed(1); // seconds -> minutes
    }
    // Approximate total distance (miles) from first 1000 trips if backend does not provide it
    if (stats.total_distance === undefined || stats.total_distance === null) {
        try {
            const tripsResp = await fetchAPI(`/trips?${query}&limit=1000&page=1`);
            const trips = tripsResp.trips || [];
            let totalMiles = 0;
            for (const t of trips) {
                const miles = haversineMiles(
                    Number(t.pickup_latitude), Number(t.pickup_longitude),
                    Number(t.dropoff_latitude), Number(t.dropoff_longitude)
                );
                if (!Number.isNaN(miles) && Number.isFinite(miles)) totalMiles += miles;
            }
            stats.total_distance = Math.round(totalMiles);
        } catch (e) {
            stats.total_distance = null;
        }
    }
    if (stats.avg_fare === undefined) stats.avg_fare = null; // not provided by backend
    return stats;
}

async function fetchHourlyTrips(filters) {
    const query = buildQueryString(filters);
    const resp = await fetchAPI(`/statistics/by-hour?${query}`);
    const rows = resp && resp.statistics ? resp.statistics : [];
    const hours = rows.map(r => r.hour);
    const counts = rows.map(r => r.trip_count);
    return { hours, counts };
}

async function fetchSpeedByTime(filters) {
    // Approximate "speed" panel with average duration by time-of-day buckets
    const query = buildQueryString(filters);
    const resp = await fetchAPI(`/statistics/by-hour?${query}`);
    const rows = resp && resp.statistics ? resp.statistics : [];
    const buckets = { morning: [], afternoon: [], evening: [], night: [] };
    rows.forEach(r => {
        const h = Number(r.hour);
        const avgMin = Number(r.avg_duration) / 60;
        if (h >= 6 && h < 12) buckets.morning.push(avgMin);
        else if (h >= 12 && h < 18) buckets.afternoon.push(avgMin);
        else if (h >= 18 && h < 22) buckets.evening.push(avgMin);
        else buckets.night.push(avgMin);
    });
    const avg = arr => (arr.length ? (arr.reduce((a, b) => a + b, 0) / arr.length) : 0).toFixed(1);
    return {
        labels: ['Morning', 'Afternoon', 'Evening', 'Night'],
        speeds: [avg(buckets.morning), avg(buckets.afternoon), avg(buckets.evening), avg(buckets.night)]
    };
}

async function fetchPassengerDistribution(filters) {
    const query = buildQueryString(filters);
    const data = await fetchAPI(`/trips?${query}&limit=1000&page=1`);
    const trips = data.trips || [];
    const bins = { '1': 0, '2': 0, '3': 0, '4+': 0 };
    trips.forEach(t => {
        const pc = Number(t.passenger_count || 0);
        if (pc <= 1) bins['1']++;
        else if (pc === 2) bins['2']++;
        else if (pc === 3) bins['3']++;
        else bins['4+']++;
    });
    return {
        labels: ['1 Passenger', '2 Passengers', '3 Passengers', '4+ Passengers'],
        counts: [bins['1'], bins['2'], bins['3'], bins['4+']]
    };
}

async function fetchDurationDistribution(filters) {
    const query = buildQueryString(filters);
    const data = await fetchAPI(`/trips?${query}&limit=1000&page=1`);
    const trips = data.trips || [];
    const buckets = [0, 0, 0, 0, 0, 0];
    trips.forEach(t => {
        const minutes = Number(t.trip_duration || 0) / 60;
        if (minutes < 10) buckets[0]++;
        else if (minutes < 20) buckets[1]++;
        else if (minutes < 30) buckets[2]++;
        else if (minutes < 40) buckets[3]++;
        else if (minutes < 50) buckets[4]++;
        else buckets[5]++;
    });
    return {
        ranges: ['0-10m', '10-20m', '20-30m', '30-40m', '40-50m', '50m+'],
        counts: buckets
    };
}

async function fetchScatterData(filters) {
    const query = buildQueryString(filters);
    const data = await fetchAPI(`/trips?${query}&limit=200&page=1`);
    const trips = data.trips || [];
    const points = trips.map(t => {
        const d = haversineMiles(
            Number(t.pickup_latitude), Number(t.pickup_longitude),
            Number(t.dropoff_latitude), Number(t.dropoff_longitude)
        );
        const minutes = Number(t.trip_duration || 0) / 60;
        return { x: Number(d.toFixed(2)), y: Number(minutes.toFixed(1)) };
    });
    return { data: points };
}

async function fetchInsights(filters) {
    const query = buildQueryString(filters);
    const resp = await fetchAPI(`/statistics/by-hour?${query}`);
    const rows = resp && resp.statistics ? resp.statistics : [];
    if (!rows || !rows.length) return { insights: [] };
    const maxRow = rows.reduce((a, b) => (a.trip_count > b.trip_count ? a : b));
    const minRow = rows.reduce((a, b) => (a.trip_count < b.trip_count ? a : b));
    const slowRow = rows.reduce((a, b) => (a.avg_duration > b.avg_duration ? a : b));
    const slowMin = (Number(slowRow.avg_duration) / 60).toFixed(1);
    return {
        insights: [
            {
                title: 'Peak Hour',
                description: `Highest trip volume at ${maxRow.hour}:00 with ${maxRow.trip_count} trips.`
            },
            {
                title: 'Quietest Hour',
                description: `Lowest trip volume at ${minRow.hour}:00 with ${minRow.trip_count} trips.`
            },
            {
                title: 'Longest Avg Duration',
                description: `Trips around ${slowRow.hour}:00 take the longest on average (${slowMin} min).`
            }
        ]
    };
}

// UI UPDATE FUNCTIONS
function updateKPIs(data) {
    const setText = (id, value) => { const el = document.getElementById(id); if (el) el.textContent = value; };
    setText('kpiTotalTrips', data.total_trips !== undefined ? formatNumber(data.total_trips) : '—');
    setText('kpiAvgDuration', data.avg_duration !== undefined ? `${data.avg_duration}m` : '—');
    setText('kpiTotalDistance', (data.total_distance !== null && data.total_distance !== undefined) ? `${formatNumber(data.total_distance)} mi` : '—');
    setText('kpiAvgFare', (data.avg_fare !== null && data.avg_fare !== undefined) ? `$${Number(data.avg_fare).toFixed(2)}` : '—');
    // Reset change indicators if no comparison data
    const resetChange = (id) => {
        const el = document.getElementById(id);
        if (el) {
            el.textContent = '—';
            el.style.color = '#a0a0a0';
        }
    };
    resetChange('kpiTotalTripsChange');
    resetChange('kpiAvgDurationChange');
    resetChange('kpiTotalDistanceChange');
    resetChange('kpiAvgFareChange');

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

// CHART FUNCTIONS

function initializeCharts() {
    const getCtx = (id) => {
        const el = document.getElementById(id);
        return el ? el.getContext('2d') : null;
    };

    const tsCtx = getCtx('timeSeriesChart');
    if (tsCtx) charts.timeSeries = new Chart(tsCtx, {
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

    const spCtx = getCtx('speedChart');
    if (spCtx) charts.speed = new Chart(spCtx, {
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

    const psCtx = getCtx('passengerChart');
    if (psCtx) charts.passenger = new Chart(psCtx, {
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

    const duCtx = getCtx('durationChart');
    if (duCtx) charts.duration = new Chart(duCtx, {
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

    const scCtx = getCtx('scatterChart');
    if (scCtx) charts.scatter = new Chart(scCtx, {
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
                title: { display: true, text: 'Distance (miles, haversine)', color: '#a0a0a0' },
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

// Haversine distance in miles from lat/lon pairs
function haversineMiles(lat1, lon1, lat2, lon2) {
    const toRad = d => d * Math.PI / 180;
    const R = 3958.7613; // Earth radius in miles
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
              Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
              Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
}

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
        // Stay on UI and show error; avoid undefined mock fallback
        showError('Backend request failed. Check API_BASE_URL and server status.');
    } finally {
        document.getElementById('applyFiltersBtn').disabled = false;
        document.getElementById('applyDateBtn').disabled = false;
    }
}

// EVENT LISTENERS
function initializeEventListeners() {
    const fareRange = document.getElementById('fareRange');
    if (fareRange) {
        fareRange.addEventListener('input', function(e) {
            const fareValue = document.getElementById('fareValue');
            if (fareValue) fareValue.textContent = e.target.value;
        });
    }

    const distanceRange = document.getElementById('distanceRange');
    if (distanceRange) {
        distanceRange.addEventListener('input', function(e) {
            const distanceValue = document.getElementById('distanceValue');
            if (distanceValue) distanceValue.textContent = e.target.value;
        });
    }
    
    const applyFiltersBtn = document.getElementById('applyFiltersBtn');
    if (applyFiltersBtn) applyFiltersBtn.addEventListener('click', function() {
        loadDashboardData();
    });
    
    const applyDateBtn = document.getElementById('applyDateBtn');
    if (applyDateBtn) applyDateBtn.addEventListener('click', function() {
        loadDashboardData();
    });
    
    const startDateInput = document.getElementById('startDate');
    if (startDateInput) startDateInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') loadDashboardData();
    });
    
    const endDateInput = document.getElementById('endDate');
    if (endDateInput) endDateInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') loadDashboardData();
    });
}

// INITIALIZATION

document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing NYC Taxi Analytics Dashboard...');
    console.log('API Base URL:', API_BASE_URL);
    
    initializeCharts();
    initializeEventListeners();
    loadDashboardData();
    
    console.log('Dashboard initialized successfully!');
});

// UTILITY FUNCTIONS FOR BACKEND DEVELOPERS
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
