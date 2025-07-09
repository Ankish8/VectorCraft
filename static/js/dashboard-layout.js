/**
 * Customizable Dashboard Layout System
 * Drag-and-drop dashboard widgets with persistent layouts
 */

class DashboardLayout {
    constructor() {
        this.widgets = new Map();
        this.layouts = {
            default: {
                name: 'Default Layout',
                widgets: [
                    { id: 'metrics', col: 0, row: 0, width: 12, height: 1 },
                    { id: 'health', col: 0, row: 1, width: 6, height: 2 },
                    { id: 'transactions', col: 6, row: 1, width: 6, height: 2 },
                    { id: 'charts', col: 0, row: 3, width: 12, height: 2 }
                ]
            },
            analytics: {
                name: 'Analytics Focus',
                widgets: [
                    { id: 'charts', col: 0, row: 0, width: 12, height: 3 },
                    { id: 'metrics', col: 0, row: 3, width: 8, height: 1 },
                    { id: 'health', col: 8, row: 3, width: 4, height: 2 }
                ]
            },
            monitoring: {
                name: 'System Monitoring',
                widgets: [
                    { id: 'health', col: 0, row: 0, width: 12, height: 2 },
                    { id: 'metrics', col: 0, row: 2, width: 6, height: 1 },
                    { id: 'transactions', col: 6, row: 2, width: 6, height: 1 }
                ]
            }
        };
        
        this.currentLayout = this.getStoredLayout() || 'default';
        this.editMode = false;
        this.init();
    }

    /**
     * Initialize dashboard layout system
     */
    init() {
        this.createLayoutControls();
        this.createGridSystem();
        this.registerWidgets();
        this.applyLayout(this.currentLayout);
        this.bindEvents();
    }

    /**
     * Create layout controls
     */
    createLayoutControls() {
        const controlsContainer = document.createElement('div');
        controlsContainer.className = 'dashboard-controls';
        controlsContainer.innerHTML = `
            <div class="controls-header">
                <h6>Dashboard Layout</h6>
                <div class="controls-actions">
                    <button class="btn btn-sm btn-outline-primary" id="editLayoutBtn">
                        <i class="bi bi-pencil"></i> Edit Layout
                    </button>
                    <div class="dropdown">
                        <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" id="layoutDropdown" data-bs-toggle="dropdown">
                            <i class="bi bi-layout-wtf"></i> Layout
                        </button>
                        <ul class="dropdown-menu" aria-labelledby="layoutDropdown">
                            ${Object.entries(this.layouts).map(([key, layout]) => `
                                <li><a class="dropdown-item layout-option" href="#" data-layout="${key}">${layout.name}</a></li>
                            `).join('')}
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item" href="#" id="saveLayoutBtn"><i class="bi bi-save"></i> Save Layout</a></li>
                            <li><a class="dropdown-item" href="#" id="resetLayoutBtn"><i class="bi bi-arrow-clockwise"></i> Reset to Default</a></li>
                        </ul>
                    </div>
                </div>
            </div>
            <div class="layout-info" id="layoutInfo">
                <span>Current: ${this.layouts[this.currentLayout].name}</span>
                <span class="edit-hint" style="display: none;">Drag widgets to rearrange</span>
            </div>
        `;

        // Insert at the top of the dashboard
        const dashboard = document.querySelector('.container-fluid');
        if (dashboard) {
            dashboard.insertBefore(controlsContainer, dashboard.firstChild);
        }

        this.addLayoutControlsStyles();
    }

    /**
     * Add styles for layout controls
     */
    addLayoutControlsStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .dashboard-controls {
                background: var(--surface-color);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 1rem;
                margin-bottom: 1.5rem;
            }

            .controls-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 0.5rem;
            }

            .controls-header h6 {
                margin: 0;
                color: var(--text-color);
            }

            .controls-actions {
                display: flex;
                gap: 0.5rem;
            }

            .layout-info {
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-size: 0.875rem;
                color: var(--text-secondary-color);
            }

            .edit-hint {
                color: var(--warning-color);
                font-weight: 500;
            }

            .dashboard-grid {
                display: grid;
                grid-template-columns: repeat(12, 1fr);
                grid-auto-rows: 200px;
                gap: 1rem;
                margin-bottom: 2rem;
            }

            .dashboard-widget {
                background: var(--surface-color);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 1rem;
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }

            .dashboard-widget:hover {
                box-shadow: 0 4px 12px var(--shadow-color);
            }

            .dashboard-widget.draggable {
                cursor: move;
            }

            .dashboard-widget.dragging {
                opacity: 0.5;
                transform: scale(0.95);
                z-index: 1000;
            }

            .dashboard-widget.drag-over {
                border-color: var(--primary-color);
                background: var(--primary-color)10;
            }

            .widget-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 1rem;
                padding-bottom: 0.5rem;
                border-bottom: 1px solid var(--border-color);
            }

            .widget-title {
                font-size: 1rem;
                font-weight: 600;
                color: var(--text-color);
                margin: 0;
            }

            .widget-actions {
                display: flex;
                gap: 0.25rem;
            }

            .widget-btn {
                background: none;
                border: none;
                color: var(--text-secondary-color);
                cursor: pointer;
                padding: 0.25rem;
                border-radius: 4px;
                transition: all 0.2s ease;
            }

            .widget-btn:hover {
                background: var(--border-color);
                color: var(--text-color);
            }

            .widget-content {
                height: calc(100% - 3rem);
                overflow: auto;
            }

            .widget-placeholder {
                border: 2px dashed var(--border-color);
                background: var(--surface-color);
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: var(--text-secondary-color);
                font-size: 0.875rem;
                min-height: 100px;
            }

            .resize-handle {
                position: absolute;
                bottom: 0;
                right: 0;
                width: 16px;
                height: 16px;
                background: var(--primary-color);
                cursor: nw-resize;
                opacity: 0;
                transition: opacity 0.2s ease;
            }

            .resize-handle::after {
                content: '';
                position: absolute;
                bottom: 2px;
                right: 2px;
                width: 0;
                height: 0;
                border-left: 6px solid transparent;
                border-bottom: 6px solid white;
            }

            .dashboard-widget:hover .resize-handle {
                opacity: 1;
            }

            .edit-mode .dashboard-widget {
                border: 2px dashed var(--primary-color);
            }

            .edit-mode .widget-header {
                background: var(--primary-color)20;
                margin: -1rem -1rem 1rem -1rem;
                padding: 0.5rem 1rem;
            }

            @media (max-width: 768px) {
                .dashboard-grid {
                    grid-template-columns: 1fr;
                    grid-auto-rows: auto;
                }

                .controls-header {
                    flex-direction: column;
                    gap: 0.5rem;
                }

                .controls-actions {
                    width: 100%;
                    justify-content: space-between;
                }

                .layout-info {
                    flex-direction: column;
                    align-items: flex-start;
                    gap: 0.25rem;
                }
            }
        `;
        document.head.appendChild(style);
    }

    /**
     * Create grid system
     */
    createGridSystem() {
        const existingGrid = document.querySelector('.dashboard-grid');
        if (existingGrid) {
            existingGrid.remove();
        }

        const gridContainer = document.createElement('div');
        gridContainer.className = 'dashboard-grid';
        gridContainer.id = 'dashboardGrid';

        // Insert after controls
        const controls = document.querySelector('.dashboard-controls');
        if (controls) {
            controls.insertAdjacentElement('afterend', gridContainer);
        }
    }

    /**
     * Register available widgets
     */
    registerWidgets() {
        const widgetDefinitions = [
            {
                id: 'metrics',
                title: 'System Metrics',
                icon: 'bi-speedometer2',
                content: this.createMetricsWidget(),
                minWidth: 6,
                minHeight: 1
            },
            {
                id: 'health',
                title: 'System Health',
                icon: 'bi-heart-pulse',
                content: this.createHealthWidget(),
                minWidth: 4,
                minHeight: 2
            },
            {
                id: 'transactions',
                title: 'Recent Transactions',
                icon: 'bi-credit-card',
                content: this.createTransactionsWidget(),
                minWidth: 4,
                minHeight: 2
            },
            {
                id: 'charts',
                title: 'Analytics Charts',
                icon: 'bi-bar-chart',
                content: this.createChartsWidget(),
                minWidth: 6,
                minHeight: 2
            },
            {
                id: 'logs',
                title: 'System Logs',
                icon: 'bi-journal-text',
                content: this.createLogsWidget(),
                minWidth: 6,
                minHeight: 2
            },
            {
                id: 'alerts',
                title: 'Active Alerts',
                icon: 'bi-bell',
                content: this.createAlertsWidget(),
                minWidth: 4,
                minHeight: 1
            }
        ];

        widgetDefinitions.forEach(widget => {
            this.widgets.set(widget.id, widget);
        });
    }

    /**
     * Create metrics widget content
     */
    createMetricsWidget() {
        return `
            <div id="realtime-metrics">
                <div class="metric-widget" data-metric="cpu">
                    <div class="metric-header">
                        <span class="metric-label">CPU Usage</span>
                        <span class="metric-value" id="cpu-value">0%</span>
                    </div>
                    <div class="metric-progress">
                        <div class="progress-bar">
                            <div class="progress-fill" id="cpu-progress"></div>
                        </div>
                    </div>
                </div>
                <div class="metric-widget" data-metric="memory">
                    <div class="metric-header">
                        <span class="metric-label">Memory</span>
                        <span class="metric-value" id="memory-value">0%</span>
                    </div>
                    <div class="metric-progress">
                        <div class="progress-bar">
                            <div class="progress-fill" id="memory-progress"></div>
                        </div>
                    </div>
                </div>
                <div class="metric-widget" data-metric="disk">
                    <div class="metric-header">
                        <span class="metric-label">Disk Usage</span>
                        <span class="metric-value" id="disk-value">0%</span>
                    </div>
                    <div class="metric-progress">
                        <div class="progress-bar">
                            <div class="progress-fill" id="disk-progress"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Create health widget content
     */
    createHealthWidget() {
        return `
            <div id="health-status">
                <div class="health-overview">
                    <div class="health-indicator health-healthy"></div>
                    <span>All Systems Operational</span>
                </div>
                <div class="health-components">
                    <div class="health-component">
                        <span class="health-indicator health-healthy"></span>
                        <span>Database</span>
                    </div>
                    <div class="health-component">
                        <span class="health-indicator health-healthy"></span>
                        <span>PayPal API</span>
                    </div>
                    <div class="health-component">
                        <span class="health-indicator health-healthy"></span>
                        <span>Email Service</span>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Create transactions widget content
     */
    createTransactionsWidget() {
        return `
            <div class="transactions-list">
                <div class="transaction-item">
                    <div class="transaction-details">
                        <strong>user@example.com</strong>
                        <span class="transaction-amount">$19.99</span>
                    </div>
                    <div class="transaction-meta">
                        <span class="badge badge-success">Completed</span>
                        <span class="transaction-time">2 min ago</span>
                    </div>
                </div>
                <div class="transaction-item">
                    <div class="transaction-details">
                        <strong>test@domain.com</strong>
                        <span class="transaction-amount">$19.99</span>
                    </div>
                    <div class="transaction-meta">
                        <span class="badge badge-warning">Pending</span>
                        <span class="transaction-time">5 min ago</span>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Create charts widget content
     */
    createChartsWidget() {
        return `
            <div class="charts-container">
                <div class="chart-wrapper">
                    <canvas id="transaction-volume-chart" width="400" height="200"></canvas>
                </div>
                <div class="chart-wrapper">
                    <canvas id="revenue-chart" width="400" height="200"></canvas>
                </div>
            </div>
        `;
    }

    /**
     * Create logs widget content
     */
    createLogsWidget() {
        return `
            <div class="logs-container">
                <div class="log-entry">
                    <span class="log-level log-info">INFO</span>
                    <span class="log-message">User login successful</span>
                    <span class="log-time">10:30 AM</span>
                </div>
                <div class="log-entry">
                    <span class="log-level log-warning">WARN</span>
                    <span class="log-message">High CPU usage detected</span>
                    <span class="log-time">10:25 AM</span>
                </div>
                <div class="log-entry">
                    <span class="log-level log-error">ERROR</span>
                    <span class="log-message">Payment processing failed</span>
                    <span class="log-time">10:20 AM</span>
                </div>
            </div>
        `;
    }

    /**
     * Create alerts widget content
     */
    createAlertsWidget() {
        return `
            <div class="alerts-container">
                <div class="alert-item">
                    <i class="bi bi-exclamation-triangle text-warning"></i>
                    <span>High memory usage</span>
                    <button class="btn btn-sm btn-outline-secondary">Dismiss</button>
                </div>
                <div class="alert-item">
                    <i class="bi bi-info-circle text-info"></i>
                    <span>System update available</span>
                    <button class="btn btn-sm btn-outline-secondary">Dismiss</button>
                </div>
            </div>
        `;
    }

    /**
     * Apply layout to dashboard
     */
    applyLayout(layoutName) {
        const layout = this.layouts[layoutName];
        if (!layout) return;

        const grid = document.getElementById('dashboardGrid');
        if (!grid) return;

        // Clear existing widgets
        grid.innerHTML = '';

        // Add widgets according to layout
        layout.widgets.forEach(widgetConfig => {
            const widget = this.widgets.get(widgetConfig.id);
            if (!widget) return;

            const widgetElement = this.createWidgetElement(widget, widgetConfig);
            grid.appendChild(widgetElement);
        });

        // Update layout info
        const layoutInfo = document.getElementById('layoutInfo');
        if (layoutInfo) {
            layoutInfo.querySelector('span').textContent = `Current: ${layout.name}`;
        }

        this.currentLayout = layoutName;
        this.saveLayout();
    }

    /**
     * Create widget element
     */
    createWidgetElement(widget, config) {
        const element = document.createElement('div');
        element.className = 'dashboard-widget';
        element.dataset.widgetId = widget.id;
        element.style.gridColumn = `${config.col + 1} / span ${config.width}`;
        element.style.gridRow = `${config.row + 1} / span ${config.height}`;

        element.innerHTML = `
            <div class="widget-header">
                <h6 class="widget-title">
                    <i class="${widget.icon}"></i>
                    ${widget.title}
                </h6>
                <div class="widget-actions">
                    <button class="widget-btn" onclick="dashboardLayout.refreshWidget('${widget.id}')" title="Refresh">
                        <i class="bi bi-arrow-clockwise"></i>
                    </button>
                    <button class="widget-btn" onclick="dashboardLayout.toggleWidget('${widget.id}')" title="Minimize">
                        <i class="bi bi-dash"></i>
                    </button>
                </div>
            </div>
            <div class="widget-content">
                ${widget.content}
            </div>
            <div class="resize-handle"></div>
        `;

        // Make draggable in edit mode
        if (this.editMode) {
            element.classList.add('draggable');
            element.draggable = true;
        }

        return element;
    }

    /**
     * Toggle edit mode
     */
    toggleEditMode() {
        this.editMode = !this.editMode;
        const grid = document.getElementById('dashboardGrid');
        const editBtn = document.getElementById('editLayoutBtn');
        const editHint = document.querySelector('.edit-hint');

        if (this.editMode) {
            grid.classList.add('edit-mode');
            editBtn.innerHTML = '<i class="bi bi-check"></i> Done';
            editBtn.classList.remove('btn-outline-primary');
            editBtn.classList.add('btn-success');
            editHint.style.display = 'block';
            
            // Make widgets draggable
            grid.querySelectorAll('.dashboard-widget').forEach(widget => {
                widget.classList.add('draggable');
                widget.draggable = true;
            });
        } else {
            grid.classList.remove('edit-mode');
            editBtn.innerHTML = '<i class="bi bi-pencil"></i> Edit Layout';
            editBtn.classList.remove('btn-success');
            editBtn.classList.add('btn-outline-primary');
            editHint.style.display = 'none';
            
            // Remove draggable
            grid.querySelectorAll('.dashboard-widget').forEach(widget => {
                widget.classList.remove('draggable');
                widget.draggable = false;
            });
        }
    }

    /**
     * Save current layout
     */
    saveCurrentLayout() {
        const grid = document.getElementById('dashboardGrid');
        const widgets = Array.from(grid.querySelectorAll('.dashboard-widget'));
        
        const layoutWidgets = widgets.map(widget => {
            const id = widget.dataset.widgetId;
            const style = window.getComputedStyle(widget);
            const gridColumn = style.gridColumn;
            const gridRow = style.gridRow;
            
            // Parse grid position
            const colMatch = gridColumn.match(/(\d+) \/ span (\d+)/);
            const rowMatch = gridRow.match(/(\d+) \/ span (\d+)/);
            
            return {
                id: id,
                col: colMatch ? parseInt(colMatch[1]) - 1 : 0,
                row: rowMatch ? parseInt(rowMatch[1]) - 1 : 0,
                width: colMatch ? parseInt(colMatch[2]) : 6,
                height: rowMatch ? parseInt(rowMatch[2]) : 2
            };
        });

        const customLayout = {
            name: 'Custom Layout',
            widgets: layoutWidgets
        };

        this.layouts.custom = customLayout;
        this.currentLayout = 'custom';
        this.saveLayout();
    }

    /**
     * Reset to default layout
     */
    resetLayout() {
        this.applyLayout('default');
    }

    /**
     * Refresh widget
     */
    refreshWidget(widgetId) {
        const widget = document.querySelector(`[data-widget-id="${widgetId}"]`);
        if (!widget) return;

        const content = widget.querySelector('.widget-content');
        content.innerHTML = '<div class="text-center py-3"><div class="spinner-border"></div></div>';

        // Simulate refresh
        setTimeout(() => {
            const widgetDef = this.widgets.get(widgetId);
            if (widgetDef) {
                content.innerHTML = widgetDef.content;
            }
        }, 1000);
    }

    /**
     * Toggle widget visibility
     */
    toggleWidget(widgetId) {
        const widget = document.querySelector(`[data-widget-id="${widgetId}"]`);
        if (!widget) return;

        const content = widget.querySelector('.widget-content');
        const toggleBtn = widget.querySelector('.widget-actions .widget-btn:last-child i');

        if (content.style.display === 'none') {
            content.style.display = 'block';
            toggleBtn.className = 'bi bi-dash';
        } else {
            content.style.display = 'none';
            toggleBtn.className = 'bi bi-plus';
        }
    }

    /**
     * Bind events
     */
    bindEvents() {
        // Edit mode toggle
        document.addEventListener('click', (e) => {
            if (e.target.id === 'editLayoutBtn' || e.target.closest('#editLayoutBtn')) {
                this.toggleEditMode();
            }
        });

        // Layout selection
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('layout-option')) {
                e.preventDefault();
                const layoutName = e.target.dataset.layout;
                this.applyLayout(layoutName);
            }
        });

        // Save layout
        document.addEventListener('click', (e) => {
            if (e.target.id === 'saveLayoutBtn' || e.target.closest('#saveLayoutBtn')) {
                e.preventDefault();
                this.saveCurrentLayout();
            }
        });

        // Reset layout
        document.addEventListener('click', (e) => {
            if (e.target.id === 'resetLayoutBtn' || e.target.closest('#resetLayoutBtn')) {
                e.preventDefault();
                this.resetLayout();
            }
        });

        // Drag and drop
        document.addEventListener('dragstart', (e) => {
            if (e.target.classList.contains('dashboard-widget')) {
                e.target.classList.add('dragging');
                e.dataTransfer.setData('text/plain', e.target.dataset.widgetId);
            }
        });

        document.addEventListener('dragend', (e) => {
            if (e.target.classList.contains('dashboard-widget')) {
                e.target.classList.remove('dragging');
            }
        });

        document.addEventListener('dragover', (e) => {
            e.preventDefault();
        });

        document.addEventListener('drop', (e) => {
            e.preventDefault();
            // Handle widget reordering
            this.handleWidgetDrop(e);
        });
    }

    /**
     * Handle widget drop
     */
    handleWidgetDrop(e) {
        const widgetId = e.dataTransfer.getData('text/plain');
        const draggedWidget = document.querySelector(`[data-widget-id="${widgetId}"]`);
        const target = e.target.closest('.dashboard-widget');

        if (draggedWidget && target && draggedWidget !== target) {
            // Swap positions
            const grid = document.getElementById('dashboardGrid');
            const draggedIndex = Array.from(grid.children).indexOf(draggedWidget);
            const targetIndex = Array.from(grid.children).indexOf(target);

            if (draggedIndex < targetIndex) {
                target.insertAdjacentElement('afterend', draggedWidget);
            } else {
                target.insertAdjacentElement('beforebegin', draggedWidget);
            }
        }
    }

    /**
     * Get stored layout
     */
    getStoredLayout() {
        return localStorage.getItem('vectorcraft-dashboard-layout');
    }

    /**
     * Save layout to storage
     */
    saveLayout() {
        localStorage.setItem('vectorcraft-dashboard-layout', this.currentLayout);
    }
}

// Initialize dashboard layout
const dashboardLayout = new DashboardLayout();

// Make it globally available
window.dashboardLayout = dashboardLayout;

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DashboardLayout;
}