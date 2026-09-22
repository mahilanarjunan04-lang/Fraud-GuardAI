/**
 * FraudGuard AI - Chart.js Visualizations & Network Graph Canvas
 * Strictly rectangular styling, high contrast, clean security-themed colors.
 */

document.addEventListener('DOMContentLoaded', () => {
    initDashboardCharts();
    initAnalyticsCharts();
    initNetworkCanvas();
});

// Common Chart.js styling defaults
Chart.defaults.font.family = "'Inter', -apple-system, sans-serif";
Chart.defaults.color = '#94A3B8';
Chart.defaults.borderColor = '#1E3360';

// =========================================================================
// 1. DASHBOARD CHARTS
// =========================================================================

function initDashboardCharts() {
    // A. Current Risk Landscape Doughnut Chart
    const doughnutCanvas = document.getElementById('riskLandscapeChart');
    if (doughnutCanvas) {
        fetch('/api/analytics')
            .then(res => res.json())
            .then(data => {
                if (!data.success) return;
                const rd = data.risk_distribution;

                new Chart(doughnutCanvas, {
                    type: 'doughnut',
                    data: {
                        labels: ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'],
                        datasets: [{
                            data: [rd.critical, rd.high, rd.medium, rd.low],
                            backgroundColor: ['#DC2626', '#EA580C', '#D97706', '#059669'],
                            borderColor: '#0E1833',
                            borderWidth: 3,
                            hoverOffset: 6
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        cutout: '72%',
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                backgroundColor: '#0B132B',
                                titleColor: '#FFFFFF',
                                bodyColor: '#CBD5E1',
                                borderColor: '#1E3360',
                                borderWidth: 1,
                                cornerRadius: 4,
                                padding: 10
                            }
                        }
                    }
                });
            })
            .catch(err => console.error('Error loading risk distribution chart:', err));
    }

    // B. Weekly Transaction Activity Line Chart
    const activityCanvas = document.getElementById('transactionActivityChart');
    if (activityCanvas) {
        new Chart(activityCanvas, {
            type: 'line',
            data: {
                labels: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
                datasets: [
                    {
                        label: 'Normal Volume',
                        data: [1420, 1680, 1850, 1920, 2100, 1750, 1400],
                        borderColor: '#3B82F6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.3,
                        pointRadius: 4,
                        pointBackgroundColor: '#3B82F6'
                    },
                    {
                        label: 'Suspicious Flagged',
                        data: [38, 45, 52, 68, 92, 74, 51],
                        borderColor: '#DC2626',
                        backgroundColor: 'rgba(220, 38, 38, 0.15)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.3,
                        pointRadius: 5,
                        pointBackgroundColor: '#DC2626'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        grid: { color: '#17264A' },
                        ticks: { color: '#94A3B8' }
                    },
                    y: {
                        grid: { color: '#17264A' },
                        ticks: { color: '#94A3B8' }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: { boxWidth: 12, boxHeight: 12, borderRadius: 2, color: '#CBD5E1' }
                    },
                    tooltip: {
                        backgroundColor: '#0B132B',
                        borderColor: '#1E3360',
                        borderWidth: 1,
                        cornerRadius: 4
                    }
                }
            }
        });
    }
}

// =========================================================================
// 2. ANALYTICS PAGE MULTI-CHARTS
// =========================================================================

function initAnalyticsCharts() {
    // 1. Fraud Trend Chart
    const trendCanvas = document.getElementById('fraudTrendChart');
    if (trendCanvas) {
        new Chart(trendCanvas, {
            type: 'line',
            data: {
                labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5', 'Week 6', 'Week 7', 'Week 8'],
                datasets: [{
                    label: 'Fraud Attacks Prevented',
                    data: [18, 26, 34, 42, 68, 55, 84, 98],
                    borderColor: '#EA580C',
                    backgroundColor: 'rgba(234, 88, 12, 0.15)',
                    fill: true,
                    tension: 0.35,
                    borderWidth: 3,
                    pointRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { grid: { color: '#17264A' } },
                    y: { grid: { color: '#17264A' } }
                },
                plugins: {
                    legend: { labels: { color: '#CBD5E1' } }
                }
            }
        });
    }

    // 2. Fraud by Location
    const locCanvas = document.getElementById('locationFraudChart');
    if (locCanvas) {
        fetch('/api/analytics')
            .then(r => r.json())
            .then(data => {
                if (!data.success) return;
                const locs = data.location_analysis;
                new Chart(locCanvas, {
                    type: 'bar',
                    data: {
                        labels: locs.map(l => l.location),
                        datasets: [
                            {
                                label: 'Total Transactions',
                                data: locs.map(l => l.total_tx),
                                backgroundColor: '#3B82F6',
                                borderRadius: 2
                            },
                            {
                                label: 'Suspicious Count',
                                data: locs.map(l => l.suspicious_tx),
                                backgroundColor: '#DC2626',
                                borderRadius: 2
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        indexAxis: 'y',
                        scales: {
                            x: { grid: { color: '#17264A' } },
                            y: { grid: { color: '#17264A' } }
                        },
                        plugins: {
                            legend: { labels: { color: '#CBD5E1' } }
                        }
                    }
                });
            });
    }

    // 3. Fraud by Hour (Bar)
    const hourCanvas = document.getElementById('hourlyFraudChart');
    if (hourCanvas) {
        fetch('/api/analytics')
            .then(r => r.json())
            .then(data => {
                if (!data.success) return;
                const hours = data.hourly_anomalies;
                new Chart(hourCanvas, {
                    type: 'bar',
                    data: {
                        labels: hours.map(h => h.hour),
                        datasets: [{
                            label: 'Anomalies Detected',
                            data: hours.map(h => h.count),
                            backgroundColor: hours.map((h, i) => i < 2 || i > 6 ? '#DC2626' : '#6D28D9'),
                            borderRadius: 2
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            x: { grid: { color: '#17264A' } },
                            y: { grid: { color: '#17264A' } }
                        },
                        plugins: {
                            legend: { labels: { color: '#CBD5E1' } }
                        }
                    }
                });
            });
    }

    // 4. Amount Distribution
    const amountCanvas = document.getElementById('amountDistChart');
    if (amountCanvas) {
        new Chart(amountCanvas, {
            type: 'bar',
            data: {
                labels: ['< ₹5K', '₹5K-15K', '₹15K-35K', '₹35K-75K', '> ₹75K'],
                datasets: [{
                    label: 'Flagged Transactions',
                    data: [12, 18, 24, 38, 48],
                    backgroundColor: '#0D9488',
                    borderRadius: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { grid: { color: '#17264A' } },
                    y: { grid: { color: '#17264A' } }
                }
            }
        });
    }
}

// =========================================================================
// 3. FRAUD NETWORK CANVAS (Connected Coordinated Accounts Visualization)
// =========================================================================

function initNetworkCanvas() {
    const canvas = document.getElementById('networkCanvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let width = canvas.parentElement.clientWidth;
    let height = canvas.parentElement.clientHeight || 440;
    canvas.width = width;
    canvas.height = height;

    fetch('/api/network')
        .then(res => res.json())
        .then(data => {
            if (!data.success) return;
            drawNetworkGraph(canvas, ctx, data.nodes, data.edges);
        })
        .catch(err => console.error('Error initializing network canvas:', err));
}

function drawNetworkGraph(canvas, ctx, nodesData, edgesData) {
    const width = canvas.width;
    const height = canvas.height;

    // Node layout positions mapped in circular/force structure
    const nodePositions = {
        'ACC101': { x: width * 0.20, y: height * 0.35 },
        'ACC102': { x: width * 0.45, y: height * 0.40 },
        'ACC105': { x: width * 0.68, y: height * 0.28 },
        'ACC108': { x: width * 0.35, y: height * 0.75 },
        'ACC109': { x: width * 0.82, y: height * 0.65 },
        'ACC112': { x: width * 0.15, y: height * 0.70 },
        'ACC115': { x: width * 0.85, y: height * 0.25 },
        'ACC121': { x: width * 0.55, y: height * 0.80 },
        'ACC124': { x: width * 0.30, y: height * 0.18 },
        'ACC130': { x: width * 0.65, y: height * 0.60 }
    };

    let hoveredNode = null;

    function render() {
        ctx.clearRect(0, 0, width, height);

        // Draw background grid lines
        ctx.strokeStyle = 'rgba(30, 51, 96, 0.4)';
        ctx.lineWidth = 1;
        for (let x = 0; x < width; x += 40) {
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, height);
            ctx.stroke();
        }
        for (let y = 0; y < height; y += 40) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(width, y);
            ctx.stroke();
        }

        // Draw Edges (Transaction flows)
        edgesData.forEach(edge => {
            const src = nodePositions[edge.from] || { x: width * 0.5, y: height * 0.5 };
            const tgt = nodePositions[edge.to] || { x: width * 0.5, y: height * 0.5 };

            ctx.beginPath();
            ctx.moveTo(src.x, src.y);
            ctx.lineTo(tgt.x, tgt.y);

            const isHigh = edge.risk_level === 'CRITICAL' || edge.risk_level === 'HIGH';
            ctx.strokeStyle = isHigh ? 'rgba(220, 38, 38, 0.85)' : 'rgba(59, 130, 246, 0.45)';
            ctx.lineWidth = isHigh ? 2.5 : 1.5;
            if (isHigh) {
                ctx.setLineDash([6, 3]);
            } else {
                ctx.setLineDash([]);
            }
            ctx.stroke();
            ctx.setLineDash([]);

            // Draw directional transfer indicator
            const midX = (src.x + tgt.x) / 2;
            const midY = (src.y + tgt.y) / 2;
            ctx.fillStyle = isHigh ? '#F87171' : '#60A5FA';
            ctx.beginPath();
            ctx.arc(midX, midY, isHigh ? 4 : 3, 0, Math.PI * 2);
            ctx.fill();
        });

        // Draw Nodes
        nodesData.forEach(node => {
            const pos = nodePositions[node.id] || { x: width * 0.5, y: height * 0.5 };
            const isHigh = node.risk_score >= 61;
            const radius = 22;

            // Outer node box (Rectangular with slight rounded corners)
            ctx.fillStyle = isHigh ? '#1F121C' : '#0E1833';
            ctx.strokeStyle = isHigh ? '#DC2626' : '#3B82F6';
            ctx.lineWidth = isHigh ? 3 : 2;

            // Draw rectangular node with 4px radius
            const rw = 72;
            const rh = 34;
            const rx = pos.x - rw / 2;
            const ry = pos.y - rh / 2;

            ctx.beginPath();
            ctx.roundRect(rx, ry, rw, rh, 4);
            ctx.fill();
            ctx.stroke();

            // Label text
            ctx.fillStyle = '#FFFFFF';
            ctx.font = '600 12px "JetBrains Mono", monospace';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(node.label, pos.x, pos.y - 2);

            // Risk indicator badge on corner
            ctx.fillStyle = isHigh ? '#DC2626' : '#059669';
            ctx.beginPath();
            ctx.rect(pos.x + rw/2 - 8, pos.y - rh/2, 8, rh);
            ctx.fill();
        });
    }

    render();

    // Canvas click event to navigate to account
    canvas.addEventListener('click', (e) => {
        const rect = canvas.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        for (const node of nodesData) {
            const pos = nodePositions[node.id];
            if (pos && Math.abs(mouseX - pos.x) < 36 && Math.abs(mouseY - pos.y) < 18) {
                window.location.href = `/accounts/${node.id}`;
                break;
            }
        }
    });
}
