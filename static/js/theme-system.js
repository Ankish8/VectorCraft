/**
 * Advanced Theme System for VectorCraft Admin Dashboard
 * Supports dark/light themes with persistence and smooth transitions
 */

class ThemeSystem {
    constructor() {
        this.themes = {
            light: {
                name: 'Light',
                icon: 'bi-sun',
                colors: {
                    primary: '#667eea',
                    secondary: '#764ba2',
                    background: '#ffffff',
                    surface: '#f8fafc',
                    text: '#1f2937',
                    textSecondary: '#6b7280',
                    border: '#e5e7eb',
                    shadow: 'rgba(0, 0, 0, 0.1)',
                    success: '#10b981',
                    warning: '#f59e0b',
                    error: '#ef4444',
                    info: '#3b82f6'
                }
            },
            dark: {
                name: 'Dark',
                icon: 'bi-moon',
                colors: {
                    primary: '#818cf8',
                    secondary: '#a78bfa',
                    background: '#0f172a',
                    surface: '#1e293b',
                    text: '#f1f5f9',
                    textSecondary: '#94a3b8',
                    border: '#334155',
                    shadow: 'rgba(0, 0, 0, 0.3)',
                    success: '#22c55e',
                    warning: '#eab308',
                    error: '#f87171',
                    info: '#60a5fa'
                }
            }
        };

        this.currentTheme = this.getStoredTheme() || 'light';
        this.init();
    }

    /**
     * Initialize theme system
     */
    init() {
        this.createThemeToggle();
        this.applyTheme(this.currentTheme);
        this.bindEvents();
        this.watchSystemTheme();
    }

    /**
     * Create theme toggle button
     */
    createThemeToggle() {
        const navbar = document.querySelector('.navbar, .sidebar');
        if (!navbar) return;

        const themeToggle = document.createElement('div');
        themeToggle.className = 'theme-toggle-container';
        themeToggle.innerHTML = `
            <button class="theme-toggle-btn" id="themeToggle" title="Toggle theme">
                <i class="bi ${this.themes[this.currentTheme].icon}"></i>
            </button>
        `;

        // Add to navbar/sidebar
        const targetContainer = navbar.querySelector('.d-flex, .nav') || navbar;
        targetContainer.appendChild(themeToggle);

        // Add styles
        this.addThemeToggleStyles();
    }

    /**
     * Add theme toggle styles
     */
    addThemeToggleStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .theme-toggle-container {
                position: relative;
                margin-left: auto;
            }

            .theme-toggle-btn {
                background: none;
                border: 2px solid var(--border-color);
                color: var(--text-color);
                padding: 0.5rem;
                border-radius: 50%;
                cursor: pointer;
                transition: all 0.3s ease;
                width: 40px;
                height: 40px;
                display: flex;
                align-items: center;
                justify-content: center;
                position: relative;
                overflow: hidden;
            }

            .theme-toggle-btn::before {
                content: '';
                position: absolute;
                top: 50%;
                left: 50%;
                width: 0;
                height: 0;
                background: var(--primary-color);
                border-radius: 50%;
                transition: all 0.3s ease;
                transform: translate(-50%, -50%);
                z-index: -1;
            }

            .theme-toggle-btn:hover::before {
                width: 100%;
                height: 100%;
            }

            .theme-toggle-btn:hover {
                color: white;
                border-color: var(--primary-color);
                transform: scale(1.1);
            }

            .theme-toggle-btn i {
                font-size: 1.1rem;
                transition: transform 0.3s ease;
            }

            .theme-toggle-btn:hover i {
                transform: rotate(15deg);
            }

            @media (max-width: 768px) {
                .theme-toggle-container {
                    position: fixed;
                    bottom: 20px;
                    right: 20px;
                    z-index: 1000;
                }

                .theme-toggle-btn {
                    width: 50px;
                    height: 50px;
                    box-shadow: 0 4px 12px var(--shadow-color);
                }
            }
        `;
        document.head.appendChild(style);
    }

    /**
     * Apply theme to the page
     */
    applyTheme(themeName) {
        if (!this.themes[themeName]) return;

        const theme = this.themes[themeName];
        const root = document.documentElement;

        // Set CSS custom properties
        Object.entries(theme.colors).forEach(([key, value]) => {
            root.style.setProperty(`--${key.replace(/([A-Z])/g, '-$1').toLowerCase()}-color`, value);
        });

        // Update body class
        document.body.className = document.body.className.replace(/theme-\w+/g, '');
        document.body.classList.add(`theme-${themeName}`);

        // Update theme toggle icon
        const toggleBtn = document.getElementById('themeToggle');
        if (toggleBtn) {
            const icon = toggleBtn.querySelector('i');
            if (icon) {
                icon.className = `bi ${theme.icon}`;
            }
        }

        // Store theme preference
        localStorage.setItem('vectorcraft-theme', themeName);
        this.currentTheme = themeName;

        // Dispatch theme change event
        window.dispatchEvent(new CustomEvent('themeChanged', {
            detail: { theme: themeName, colors: theme.colors }
        }));

        // Update charts and visualizations
        this.updateVisualizations(theme);
    }

    /**
     * Toggle between light and dark themes
     */
    toggleTheme() {
        const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        this.applyTheme(newTheme);
    }

    /**
     * Get stored theme preference
     */
    getStoredTheme() {
        return localStorage.getItem('vectorcraft-theme');
    }

    /**
     * Bind theme-related events
     */
    bindEvents() {
        // Theme toggle button
        document.addEventListener('click', (e) => {
            if (e.target.id === 'themeToggle' || e.target.closest('#themeToggle')) {
                this.toggleTheme();
            }
        });

        // Keyboard shortcut (Ctrl/Cmd + Shift + T)
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'T') {
                e.preventDefault();
                this.toggleTheme();
            }
        });
    }

    /**
     * Watch for system theme changes
     */
    watchSystemTheme() {
        if (window.matchMedia) {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            
            mediaQuery.addEventListener('change', (e) => {
                if (!this.getStoredTheme()) {
                    this.applyTheme(e.matches ? 'dark' : 'light');
                }
            });

            // Apply system theme if no preference stored
            if (!this.getStoredTheme()) {
                this.applyTheme(mediaQuery.matches ? 'dark' : 'light');
            }
        }
    }

    /**
     * Update visualizations when theme changes
     */
    updateVisualizations(theme) {
        // Update Chart.js charts
        if (window.Chart) {
            Chart.defaults.color = theme.colors.text;
            Chart.defaults.borderColor = theme.colors.border;
            Chart.defaults.backgroundColor = theme.colors.surface;

            // Update all chart instances
            Object.values(Chart.instances).forEach(chart => {
                chart.options.plugins.legend.labels.color = theme.colors.text;
                chart.options.scales.x.grid.color = theme.colors.border;
                chart.options.scales.y.grid.color = theme.colors.border;
                chart.options.scales.x.ticks.color = theme.colors.textSecondary;
                chart.options.scales.y.ticks.color = theme.colors.textSecondary;
                chart.update();
            });
        }

        // Update health indicators
        this.updateHealthIndicators(theme);

        // Update metric cards
        this.updateMetricCards(theme);
    }

    /**
     * Update health indicators with theme colors
     */
    updateHealthIndicators(theme) {
        const indicators = document.querySelectorAll('.health-indicator');
        indicators.forEach(indicator => {
            const status = indicator.classList.contains('health-healthy') ? 'healthy' :
                         indicator.classList.contains('health-warning') ? 'warning' :
                         indicator.classList.contains('health-critical') ? 'critical' : 'unknown';
            
            const colors = {
                healthy: theme.colors.success,
                warning: theme.colors.warning,
                critical: theme.colors.error,
                unknown: theme.colors.textSecondary
            };
            
            indicator.style.backgroundColor = colors[status];
        });
    }

    /**
     * Update metric cards with theme colors
     */
    updateMetricCards(theme) {
        const cards = document.querySelectorAll('.metric-card, .card');
        cards.forEach(card => {
            card.style.backgroundColor = theme.colors.surface;
            card.style.borderColor = theme.colors.border;
            card.style.color = theme.colors.text;
        });
    }

    /**
     * Get current theme colors
     */
    getCurrentTheme() {
        return this.themes[this.currentTheme];
    }

    /**
     * Add custom theme
     */
    addCustomTheme(name, colors) {
        this.themes[name] = {
            name: name,
            icon: 'bi-palette',
            colors: colors
        };
    }

    /**
     * Create theme color palette
     */
    createColorPalette() {
        const palette = document.createElement('div');
        palette.className = 'theme-color-palette';
        palette.innerHTML = `
            <div class="palette-header">
                <h6>Theme Colors</h6>
                <button class="btn btn-sm btn-outline-secondary" onclick="themeSystem.togglePalette()">
                    <i class="bi bi-palette"></i>
                </button>
            </div>
            <div class="palette-colors">
                ${Object.entries(this.getCurrentTheme().colors).map(([key, color]) => `
                    <div class="color-item" title="${key}">
                        <div class="color-swatch" style="background-color: ${color}"></div>
                        <span class="color-label">${key}</span>
                    </div>
                `).join('')}
            </div>
        `;

        // Add palette styles
        const style = document.createElement('style');
        style.textContent = `
            .theme-color-palette {
                position: fixed;
                top: 20px;
                right: 20px;
                background: var(--surface-color);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 1rem;
                max-width: 200px;
                z-index: 1000;
                box-shadow: 0 4px 12px var(--shadow-color);
                display: none;
            }

            .palette-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 0.5rem;
            }

            .palette-colors {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 0.5rem;
            }

            .color-item {
                display: flex;
                align-items: center;
                gap: 0.25rem;
                font-size: 0.75rem;
            }

            .color-swatch {
                width: 16px;
                height: 16px;
                border-radius: 50%;
                border: 1px solid var(--border-color);
            }

            .color-label {
                color: var(--text-secondary-color);
                text-transform: capitalize;
            }
        `;
        document.head.appendChild(style);

        return palette;
    }

    /**
     * Toggle color palette visibility
     */
    togglePalette() {
        let palette = document.querySelector('.theme-color-palette');
        if (!palette) {
            palette = this.createColorPalette();
            document.body.appendChild(palette);
        }
        
        palette.style.display = palette.style.display === 'none' ? 'block' : 'none';
    }
}

// Initialize theme system
const themeSystem = new ThemeSystem();

// Make it globally available
window.themeSystem = themeSystem;

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ThemeSystem;
}