/**
 * Interactive Data Visualization Components
 * Advanced charts and visualizations for VectorCraft Admin Dashboard
 */

class InteractiveVisualizations {
    constructor() {
        this.charts = {};
        this.colors = this.getThemeColors();
        this.init();
    }

    /**
     * Initialize all visualizations
     */
    init() {
        this.initRealtimeMetrics();
        this.initTransactionCharts();
        this.initSystemHealthCharts();
        this.initAnalyticsDashboard();
        this.bindEvents();
    }

    /**
     * Get theme colors for charts
     */
    getThemeColors() {
        const isDark = document.body.classList.contains('theme-dark');
        return {
            primary: isDark ? '#818cf8' : '#667eea',
            secondary: isDark ? '#a78bfa' : '#764ba2',
            success: isDark ? '#22c55e' : '#10b981',
            warning: isDark ? '#eab308' : '#f59e0b',
            error: isDark ? '#f87171' : '#ef4444',
            info: isDark ? '#60a5fa' : '#3b82f6',
            text: isDark ? '#f1f5f9' : '#1f2937',
            textSecondary: isDark ? '#94a3b8' : '#6b7280',
            background: isDark ? '#0f172a' : '#ffffff',
            surface: isDark ? '#1e293b' : '#f8fafc',
            border: isDark ? '#334155' : '#e5e7eb'
        };
    }

    /**
     * Initialize realtime metrics display
     */
    initRealtimeMetrics() {
        const metricsContainer = document.getElementById('realtime-metrics');
        if (!metricsContainer) return;

        const metrics = [
            { id: 'cpu', label: 'CPU Usage', value: 0, unit: '%', color: this.colors.info },
            { id: 'memory', label: 'Memory', value: 0, unit: '%', color: this.colors.warning },
            { id: 'disk', label: 'Disk Usage', value: 0, unit: '%', color: this.colors.error },
            { id: 'network', label: 'Network', value: 0, unit: 'MB/s', color: this.colors.success }
        ];

        metricsContainer.innerHTML = metrics.map(metric => `
            <div class="metric-widget" data-metric="${metric.id}">
                <div class="metric-header">
                    <span class="metric-label">${metric.label}</span>
                    <span class="metric-value" id="${metric.id}-value">0${metric.unit}</span>
                </div>
                <div class="metric-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" id="${metric.id}-progress" style="background-color: ${metric.color}"></div>
                    </div>
                </div>
                <canvas class="metric-sparkline" id="${metric.id}-sparkline" width="100" height="30"></canvas>
            </div>
        `).join('');

        this.addMetricStyles();
        this.initSparklines();
    }

    /**
     * Add styles for metric widgets
     */
    addMetricStyles() {
        const style = document.createElement('style');
        style.textContent = `
            #realtime-metrics {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 1rem;
                margin-bottom: 2rem;
            }

            .metric-widget {
                background: var(--surface-color);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 1rem;
                transition: all 0.3s ease;
            }

            .metric-widget:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px var(--shadow-color);
            }

            .metric-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 0.5rem;
            }

            .metric-label {
                font-size: 0.875rem;
                color: var(--text-secondary-color);
                font-weight: 500;
            }

            .metric-value {
                font-size: 1.25rem;
                font-weight: 600;
                color: var(--text-color);
            }

            .metric-progress {
                margin-bottom: 0.5rem;
            }

            .progress-bar {
                width: 100%;
                height: 4px;
                background: var(--border-color);
                border-radius: 2px;
                overflow: hidden;
            }

            .progress-fill {
                height: 100%;
                transition: width 0.3s ease;
                border-radius: 2px;
            }

            .metric-sparkline {
                width: 100%;
                height: 30px;
                opacity: 0.7;
            }

            @media (max-width: 768px) {
                #realtime-metrics {
                    grid-template-columns: 1fr 1fr;
                }
            }

            @media (max-width: 480px) {
                #realtime-metrics {
                    grid-template-columns: 1fr;
                }
            }
        `;
        document.head.appendChild(style);
    }

    /**
     * Initialize sparkline charts
     */
    initSparklines() {
        const metrics = ['cpu', 'memory', 'disk', 'network'];
        
        metrics.forEach(metric => {
            const canvas = document.getElementById(`${metric}-sparkline`);
            if (canvas) {
                const ctx = canvas.getContext('2d');
                this.charts[`${metric}-sparkline`] = {
                    canvas: canvas,
                    ctx: ctx,
                    data: Array(20).fill(0),
                    color: this.getMetricColor(metric)
                };
            }
        });
    }

    /**
     * Get metric color
     */
    getMetricColor(metric) {
        const colors = {
            cpu: this.colors.info,
            memory: this.colors.warning,
            disk: this.colors.error,
            network: this.colors.success
        };
        return colors[metric] || this.colors.primary;
    }

    /**
     * Update sparkline chart
     */
    updateSparkline(metric, value) {
        const chart = this.charts[`${metric}-sparkline`];
        if (!chart) return;

        chart.data.push(value);
        chart.data.shift();

        const { ctx, canvas, data, color } = chart;
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        const max = Math.max(...data, 1);
        const stepX = canvas.width / (data.length - 1);
        const stepY = canvas.height / max;

        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.beginPath();

        data.forEach((point, index) => {
            const x = index * stepX;
            const y = canvas.height - (point * stepY);
            
            if (index === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });

        ctx.stroke();

        // Add gradient fill
        ctx.fillStyle = color + '20';
        ctx.lineTo(canvas.width, canvas.height);
        ctx.lineTo(0, canvas.height);
        ctx.closePath();
        ctx.fill();
    }

    /**
     * Initialize transaction charts
     */
    initTransactionCharts() {
        this.initTransactionVolumeChart();
        this.initTransactionStatusChart();
        this.initRevenueChart();
    }

    /**
     * Initialize transaction volume chart
     */
    initTransactionVolumeChart() {
        const canvas = document.getElementById('transaction-volume-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        this.charts.transactionVolume = new Chart(ctx, {
            type: 'line',
            data: {
                labels: this.getLast24Hours(),
                datasets: [{
                    label: 'Transactions',
                    data: Array(24).fill(0),
                    borderColor: this.colors.primary,
                    backgroundColor: this.colors.primary + '20',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: this.colors.border
                        },
                        ticks: {
                            color: this.colors.textSecondary
                        }
                    },
                    y: {
                        grid: {
                            color: this.colors.border
                        },
                        ticks: {
                            color: this.colors.textSecondary
                        }
                    }
                }
            }
        });
    }

    /**
     * Initialize transaction status chart
     */
    initTransactionStatusChart() {
        const canvas = document.getElementById('transaction-status-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        this.charts.transactionStatus = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Completed', 'Pending', 'Failed'],
                datasets: [{
                    data: [0, 0, 0],
                    backgroundColor: [
                        this.colors.success,
                        this.colors.warning,
                        this.colors.error
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: this.colors.text,
                            padding: 20
                        }
                    }
                }
            }
        });
    }

    /**
     * Initialize revenue chart
     */
    initRevenueChart() {
        const canvas = document.getElementById('revenue-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        this.charts.revenue = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: this.getLast7Days(),
                datasets: [{
                    label: 'Revenue',
                    data: Array(7).fill(0),
                    backgroundColor: this.colors.success,
                    borderColor: this.colors.success,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: this.colors.border
                        },
                        ticks: {
                            color: this.colors.textSecondary
                        }
                    },
                    y: {
                        grid: {
                            color: this.colors.border
                        },
                        ticks: {
                            color: this.colors.textSecondary,
                            callback: function(value) {
                                return '$' + value.toFixed(2);
                            }
                        }
                    }
                }
            }
        });
    }

    /**
     * Initialize system health charts
     */
    initSystemHealthCharts() {
        this.initSystemStatusChart();
        this.initResponseTimeChart();
    }

    /**
     * Initialize system status chart
     */
    initSystemStatusChart() {
        const canvas = document.getElementById('system-status-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        this.charts.systemStatus = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: ['Database', 'PayPal API', 'Email Service', 'Storage', 'CPU', 'Memory'],
                datasets: [{
                    label: 'Health Score',
                    data: [100, 100, 100, 100, 100, 100],
                    borderColor: this.colors.success,
                    backgroundColor: this.colors.success + '20',
                    pointBackgroundColor: this.colors.success,
                    pointBorderColor: this.colors.success,
                    pointHoverBackgroundColor: this.colors.success,
                    pointHoverBorderColor: this.colors.success
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100,
                        grid: {
                            color: this.colors.border
                        },
                        ticks: {
                            color: this.colors.textSecondary
                        }
                    }
                }
            }
        });
    }

    /**
     * Initialize response time chart
     */
    initResponseTimeChart() {
        const canvas = document.getElementById('response-time-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        this.charts.responseTime = new Chart(ctx, {
            type: 'line',
            data: {
                labels: this.getLast30Minutes(),
                datasets: [{
                    label: 'Response Time (ms)',
                    data: Array(30).fill(0),
                    borderColor: this.colors.info,
                    backgroundColor: this.colors.info + '20',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: this.colors.border
                        },
                        ticks: {
                            color: this.colors.textSecondary
                        }
                    },
                    y: {
                        grid: {
                            color: this.colors.border
                        },
                        ticks: {
                            color: this.colors.textSecondary,
                            callback: function(value) {
                                return value + 'ms';
                            }
                        }
                    }
                }
            }
        });
    }

    /**
     * Initialize analytics dashboard
     */
    initAnalyticsDashboard() {
        this.initUserActivityChart();
        this.initConversionFunnelChart();
        this.initGeographicChart();
    }

    /**
     * Initialize user activity chart
     */
    initUserActivityChart() {
        const canvas = document.getElementById('user-activity-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        this.charts.userActivity = new Chart(ctx, {
            type: 'area',
            data: {
                labels: this.getLast30Days(),
                datasets: [{
                    label: 'Active Users',
                    data: Array(30).fill(0),
                    borderColor: this.colors.primary,
                    backgroundColor: this.colors.primary + '20',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: this.colors.border
                        },
                        ticks: {
                            color: this.colors.textSecondary
                        }
                    },
                    y: {
                        grid: {
                            color: this.colors.border
                        },
                        ticks: {
                            color: this.colors.textSecondary
                        }
                    }
                }
            }
        });
    }

    /**
     * Initialize conversion funnel chart
     */
    initConversionFunnelChart() {
        const canvas = document.getElementById('conversion-funnel-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        this.charts.conversionFunnel = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Visitors', 'Signups', 'Purchases', 'Conversions'],
                datasets: [{
                    label: 'Funnel',
                    data: [1000, 500, 200, 100],
                    backgroundColor: [
                        this.colors.info,
                        this.colors.warning,
                        this.colors.success,
                        this.colors.primary
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: this.colors.border
                        },
                        ticks: {
                            color: this.colors.textSecondary
                        }
                    },
                    y: {
                        grid: {
                            color: this.colors.border
                        },
                        ticks: {
                            color: this.colors.textSecondary
                        }
                    }
                }
            }
        });
    }

    /**
     * Initialize geographic chart
     */
    initGeographicChart() {
        const canvas = document.getElementById('geographic-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        this.charts.geographic = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: ['United States', 'India', 'United Kingdom', 'Germany', 'Canada', 'Others'],
                datasets: [{
                    data: [35, 25, 15, 10, 8, 7],
                    backgroundColor: [
                        this.colors.primary,
                        this.colors.secondary,
                        this.colors.success,
                        this.colors.warning,
                        this.colors.info,
                        this.colors.error
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: this.colors.text,
                            padding: 20
                        }
                    }
                }
            }
        });
    }

    /**
     * Update all charts with new data
     */
    updateCharts(data) {
        if (data.metrics) {
            this.updateMetrics(data.metrics);
        }
        
        if (data.transactions) {
            this.updateTransactionCharts(data.transactions);
        }
        
        if (data.system) {
            this.updateSystemCharts(data.system);
        }
        
        if (data.analytics) {
            this.updateAnalyticsCharts(data.analytics);
        }
    }

    /**
     * Update metrics
     */
    updateMetrics(metrics) {
        Object.entries(metrics).forEach(([key, value]) => {
            const valueElement = document.getElementById(`${key}-value`);
            const progressElement = document.getElementById(`${key}-progress`);
            
            if (valueElement) {
                valueElement.textContent = value + (key === 'network' ? 'MB/s' : '%');
            }
            
            if (progressElement) {
                progressElement.style.width = Math.min(value, 100) + '%';
            }
            
            this.updateSparkline(key, value);
        });
    }

    /**
     * Update transaction charts
     */
    updateTransactionCharts(data) {
        if (this.charts.transactionVolume && data.volume) {
            this.charts.transactionVolume.data.datasets[0].data = data.volume;
            this.charts.transactionVolume.update();
        }
        
        if (this.charts.transactionStatus && data.status) {
            this.charts.transactionStatus.data.datasets[0].data = data.status;
            this.charts.transactionStatus.update();
        }
        
        if (this.charts.revenue && data.revenue) {
            this.charts.revenue.data.datasets[0].data = data.revenue;
            this.charts.revenue.update();
        }
    }

    /**
     * Update system charts
     */
    updateSystemCharts(data) {
        if (this.charts.systemStatus && data.health) {
            this.charts.systemStatus.data.datasets[0].data = data.health;
            this.charts.systemStatus.update();
        }
        
        if (this.charts.responseTime && data.responseTime) {
            this.charts.responseTime.data.datasets[0].data = data.responseTime;
            this.charts.responseTime.update();
        }
    }

    /**
     * Update analytics charts
     */
    updateAnalyticsCharts(data) {
        if (this.charts.userActivity && data.userActivity) {
            this.charts.userActivity.data.datasets[0].data = data.userActivity;
            this.charts.userActivity.update();
        }
        
        if (this.charts.conversionFunnel && data.funnel) {
            this.charts.conversionFunnel.data.datasets[0].data = data.funnel;
            this.charts.conversionFunnel.update();
        }
        
        if (this.charts.geographic && data.geographic) {
            this.charts.geographic.data.datasets[0].data = data.geographic;
            this.charts.geographic.update();
        }
    }

    /**
     * Bind events
     */
    bindEvents() {
        // Listen for theme changes
        window.addEventListener('themeChanged', (e) => {
            this.colors = this.getThemeColors();
            this.updateChartColors();
        });

        // Listen for resize events
        window.addEventListener('resize', () => {
            Object.values(this.charts).forEach(chart => {
                if (chart.resize) {
                    chart.resize();
                }
            });
        });
    }

    /**
     * Update chart colors when theme changes
     */
    updateChartColors() {
        Object.values(this.charts).forEach(chart => {
            if (chart.options) {
                chart.options.scales.x.grid.color = this.colors.border;
                chart.options.scales.y.grid.color = this.colors.border;
                chart.options.scales.x.ticks.color = this.colors.textSecondary;
                chart.options.scales.y.ticks.color = this.colors.textSecondary;
                chart.update();
            }
        });
    }

    /**
     * Helper methods for date ranges
     */
    getLast24Hours() {
        const hours = [];
        for (let i = 23; i >= 0; i--) {
            const hour = new Date();
            hour.setHours(hour.getHours() - i);
            hours.push(hour.getHours() + ':00');
        }
        return hours;
    }

    getLast7Days() {
        const days = [];
        for (let i = 6; i >= 0; i--) {
            const day = new Date();
            day.setDate(day.getDate() - i);
            days.push(day.toLocaleDateString('en-US', { weekday: 'short' }));
        }
        return days;
    }

    getLast30Minutes() {
        const minutes = [];
        for (let i = 29; i >= 0; i--) {
            const minute = new Date();
            minute.setMinutes(minute.getMinutes() - i);
            minutes.push(minute.getMinutes().toString().padStart(2, '0'));
        }
        return minutes;
    }

    getLast30Days() {
        const days = [];
        for (let i = 29; i >= 0; i--) {
            const day = new Date();
            day.setDate(day.getDate() - i);
            days.push(day.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
        }
        return days;
    }
}

// Initialize visualizations
const interactiveViz = new InteractiveVisualizations();

// Make it globally available
window.interactiveViz = interactiveViz;

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = InteractiveVisualizations;
}