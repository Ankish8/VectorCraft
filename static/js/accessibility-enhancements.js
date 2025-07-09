/**
 * Accessibility Enhancements for VectorCraft Admin Dashboard
 * WCAG 2.1 AA compliance features and usability improvements
 */

class AccessibilityEnhancements {
    constructor() {
        this.settings = {
            highContrast: false,
            largeText: false,
            reducedMotion: false,
            screenReader: false,
            keyboardNavigation: true,
            focusIndicators: true,
            announcements: true
        };
        
        this.init();
    }

    /**
     * Initialize accessibility features
     */
    init() {
        this.loadSettings();
        this.createAccessibilityMenu();
        this.setupKeyboardNavigation();
        this.setupFocusManagement();
        this.setupScreenReaderSupport();
        this.setupLiveRegions();
        this.setupMotionControls();
        this.bindEvents();
    }

    /**
     * Create accessibility menu
     */
    createAccessibilityMenu() {
        const menu = document.createElement('div');
        menu.className = 'accessibility-menu';
        menu.innerHTML = `
            <button class="accessibility-toggle" 
                    id="accessibilityToggle" 
                    aria-label="Open accessibility menu"
                    aria-expanded="false">
                <i class="bi bi-universal-access"></i>
            </button>
            <div class="accessibility-panel" id="accessibilityPanel" aria-hidden="true">
                <div class="panel-header">
                    <h3>Accessibility Settings</h3>
                    <button class="panel-close" aria-label="Close accessibility menu">
                        <i class="bi bi-x"></i>
                    </button>
                </div>
                <div class="panel-content">
                    <div class="setting-group">
                        <h4>Visual Settings</h4>
                        <label class="toggle-setting">
                            <input type="checkbox" id="highContrast" ${this.settings.highContrast ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <span class="setting-label">High Contrast</span>
                        </label>
                        <label class="toggle-setting">
                            <input type="checkbox" id="largeText" ${this.settings.largeText ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <span class="setting-label">Large Text</span>
                        </label>
                        <label class="toggle-setting">
                            <input type="checkbox" id="reducedMotion" ${this.settings.reducedMotion ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <span class="setting-label">Reduce Motion</span>
                        </label>
                    </div>
                    <div class="setting-group">
                        <h4>Navigation Settings</h4>
                        <label class="toggle-setting">
                            <input type="checkbox" id="keyboardNavigation" ${this.settings.keyboardNavigation ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <span class="setting-label">Keyboard Navigation</span>
                        </label>
                        <label class="toggle-setting">
                            <input type="checkbox" id="focusIndicators" ${this.settings.focusIndicators ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <span class="setting-label">Focus Indicators</span>
                        </label>
                        <label class="toggle-setting">
                            <input type="checkbox" id="announcements" ${this.settings.announcements ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <span class="setting-label">Screen Reader Announcements</span>
                        </label>
                    </div>
                    <div class="setting-group">
                        <h4>Quick Actions</h4>
                        <button class="btn btn-sm btn-outline-primary" onclick="accessibilityEnhancements.skipToContent()">
                            Skip to Main Content
                        </button>
                        <button class="btn btn-sm btn-outline-primary" onclick="accessibilityEnhancements.resetSettings()">
                            Reset to Default
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(menu);
        this.addAccessibilityStyles();
    }

    /**
     * Add accessibility styles
     */
    addAccessibilityStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .accessibility-menu {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
            }

            .accessibility-toggle {
                width: 50px;
                height: 50px;
                border-radius: 50%;
                background: var(--primary-color);
                color: white;
                border: none;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.25rem;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
                transition: all 0.3s ease;
                position: relative;
            }

            .accessibility-toggle:hover {
                background: var(--secondary-color);
                transform: scale(1.1);
            }

            .accessibility-toggle:focus {
                outline: 3px solid var(--warning-color);
                outline-offset: 2px;
            }

            .accessibility-panel {
                position: absolute;
                top: 100%;
                right: 0;
                width: 320px;
                background: var(--surface-color);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
                margin-top: 10px;
                opacity: 0;
                visibility: hidden;
                transform: translateY(-10px);
                transition: all 0.3s ease;
            }

            .accessibility-panel.active {
                opacity: 1;
                visibility: visible;
                transform: translateY(0);
            }

            .panel-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 1rem;
                border-bottom: 1px solid var(--border-color);
            }

            .panel-header h3 {
                margin: 0;
                font-size: 1.125rem;
                color: var(--text-color);
            }

            .panel-close {
                background: none;
                border: none;
                color: var(--text-secondary-color);
                cursor: pointer;
                padding: 0.25rem;
                border-radius: 4px;
                transition: all 0.2s ease;
            }

            .panel-close:hover {
                background: var(--border-color);
                color: var(--text-color);
            }

            .panel-content {
                padding: 1rem;
                max-height: 400px;
                overflow-y: auto;
            }

            .setting-group {
                margin-bottom: 1.5rem;
            }

            .setting-group h4 {
                margin: 0 0 0.75rem 0;
                font-size: 1rem;
                color: var(--text-color);
                font-weight: 600;
            }

            .toggle-setting {
                display: flex;
                align-items: center;
                margin-bottom: 0.75rem;
                cursor: pointer;
                gap: 0.75rem;
            }

            .toggle-setting input[type="checkbox"] {
                opacity: 0;
                width: 0;
                height: 0;
                position: absolute;
            }

            .toggle-slider {
                position: relative;
                width: 40px;
                height: 20px;
                background: var(--border-color);
                border-radius: 10px;
                transition: background 0.3s ease;
            }

            .toggle-slider::before {
                content: '';
                position: absolute;
                width: 16px;
                height: 16px;
                background: white;
                border-radius: 50%;
                top: 2px;
                left: 2px;
                transition: transform 0.3s ease;
            }

            .toggle-setting input:checked + .toggle-slider {
                background: var(--primary-color);
            }

            .toggle-setting input:checked + .toggle-slider::before {
                transform: translateX(20px);
            }

            .toggle-setting input:focus + .toggle-slider {
                outline: 2px solid var(--warning-color);
                outline-offset: 2px;
            }

            .setting-label {
                color: var(--text-color);
                font-size: 0.875rem;
                flex: 1;
            }

            .btn {
                margin-right: 0.5rem;
                margin-bottom: 0.5rem;
            }

            /* High Contrast Mode */
            .high-contrast {
                filter: contrast(150%);
            }

            .high-contrast .card,
            .high-contrast .btn,
            .high-contrast .form-input {
                border-width: 2px;
            }

            .high-contrast .text-secondary {
                color: var(--text-color) !important;
            }

            /* Large Text Mode */
            .large-text {
                font-size: 1.125rem;
            }

            .large-text .card-title {
                font-size: 1.5rem;
            }

            .large-text .btn {
                font-size: 1rem;
                padding: 0.875rem 1.75rem;
            }

            .large-text .form-input,
            .large-text .form-select {
                font-size: 1.125rem;
                padding: 0.875rem;
            }

            /* Reduced Motion Mode */
            .reduced-motion * {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
            }

            /* Focus Indicators */
            .focus-indicators *:focus {
                outline: 3px solid var(--warning-color);
                outline-offset: 2px;
            }

            .focus-indicators .btn:focus {
                outline: 3px solid var(--warning-color);
                outline-offset: 2px;
            }

            /* Skip Link */
            .skip-link {
                position: fixed;
                top: -40px;
                left: 20px;
                background: var(--primary-color);
                color: white;
                padding: 0.5rem 1rem;
                border-radius: 4px;
                text-decoration: none;
                z-index: 10001;
                transition: top 0.3s ease;
            }

            .skip-link:focus {
                top: 20px;
            }

            /* Live Region */
            .live-region {
                position: absolute;
                left: -10000px;
                width: 1px;
                height: 1px;
                overflow: hidden;
            }

            /* Keyboard Navigation Helpers */
            .keyboard-nav-active {
                outline: 2px solid var(--primary-color);
                outline-offset: 2px;
                border-radius: 4px;
            }

            /* Mobile Adjustments */
            @media (max-width: 768px) {
                .accessibility-menu {
                    top: 10px;
                    right: 10px;
                }

                .accessibility-toggle {
                    width: 44px;
                    height: 44px;
                }

                .accessibility-panel {
                    width: 280px;
                    right: -20px;
                }
            }

            @media (max-width: 480px) {
                .accessibility-panel {
                    width: 260px;
                    right: -40px;
                }
            }
        `;
        document.head.appendChild(style);
    }

    /**
     * Setup keyboard navigation
     */
    setupKeyboardNavigation() {
        // Add skip link
        const skipLink = document.createElement('a');
        skipLink.href = '#main-content';
        skipLink.className = 'skip-link';
        skipLink.textContent = 'Skip to main content';
        document.body.insertBefore(skipLink, document.body.firstChild);

        // Add main content landmark
        const mainContent = document.querySelector('.container-fluid');
        if (mainContent) {
            mainContent.id = 'main-content';
            mainContent.setAttribute('role', 'main');
        }

        // Tab navigation
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                document.body.classList.add('keyboard-nav-active');
            }
        });

        document.addEventListener('mousedown', () => {
            document.body.classList.remove('keyboard-nav-active');
        });

        // Arrow key navigation for cards
        this.setupArrowNavigation();
    }

    /**
     * Setup arrow key navigation
     */
    setupArrowNavigation() {
        const cards = document.querySelectorAll('.card, .metric-card');
        
        cards.forEach((card, index) => {
            card.setAttribute('tabindex', '0');
            card.setAttribute('role', 'button');
            
            card.addEventListener('keydown', (e) => {
                let targetIndex = index;
                
                switch(e.key) {
                    case 'ArrowRight':
                        targetIndex = (index + 1) % cards.length;
                        break;
                    case 'ArrowLeft':
                        targetIndex = (index - 1 + cards.length) % cards.length;
                        break;
                    case 'ArrowDown':
                        targetIndex = Math.min(index + 3, cards.length - 1);
                        break;
                    case 'ArrowUp':
                        targetIndex = Math.max(index - 3, 0);
                        break;
                    case 'Enter':
                    case ' ':
                        card.click();
                        break;
                    default:
                        return;
                }
                
                if (targetIndex !== index) {
                    cards[targetIndex].focus();
                }
                
                e.preventDefault();
            });
        });
    }

    /**
     * Setup focus management
     */
    setupFocusManagement() {
        // Focus trap for modals
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const activeModal = document.querySelector('.modal.active');
                if (activeModal) {
                    this.closeModal(activeModal);
                }
                
                const activePanel = document.querySelector('.accessibility-panel.active');
                if (activePanel) {
                    this.closeAccessibilityPanel();
                }
            }
        });

        // Focus management for dynamic content
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList') {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            const focusable = node.querySelector('[autofocus]');
                            if (focusable) {
                                focusable.focus();
                            }
                        }
                    });
                }
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    /**
     * Setup screen reader support
     */
    setupScreenReaderSupport() {
        // Add ARIA labels to common elements
        const buttons = document.querySelectorAll('button:not([aria-label])');
        buttons.forEach(button => {
            if (button.textContent.trim()) {
                button.setAttribute('aria-label', button.textContent.trim());
            }
        });

        // Add ARIA landmarks
        const sidebar = document.querySelector('.sidebar');
        if (sidebar) {
            sidebar.setAttribute('role', 'navigation');
            sidebar.setAttribute('aria-label', 'Main navigation');
        }

        const header = document.querySelector('.dashboard-header');
        if (header) {
            header.setAttribute('role', 'banner');
        }

        // Add ARIA live regions for dynamic content
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(alert => {
            alert.setAttribute('role', 'alert');
            alert.setAttribute('aria-live', 'polite');
        });

        // Add table headers
        const tables = document.querySelectorAll('table');
        tables.forEach(table => {
            table.setAttribute('role', 'table');
            const headers = table.querySelectorAll('th');
            headers.forEach(header => {
                header.setAttribute('scope', 'col');
            });
        });
    }

    /**
     * Setup live regions for announcements
     */
    setupLiveRegions() {
        const liveRegion = document.createElement('div');
        liveRegion.className = 'live-region';
        liveRegion.setAttribute('aria-live', 'polite');
        liveRegion.setAttribute('aria-atomic', 'true');
        liveRegion.id = 'live-region';
        document.body.appendChild(liveRegion);

        // Announce page changes
        this.announcePageChange();

        // Announce form validation
        this.announceFormValidation();
    }

    /**
     * Setup motion controls
     */
    setupMotionControls() {
        // Respect user's motion preferences
        const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
        
        if (mediaQuery.matches) {
            this.settings.reducedMotion = true;
            this.applyReducedMotion();
        }

        mediaQuery.addEventListener('change', (e) => {
            if (e.matches) {
                this.settings.reducedMotion = true;
                this.applyReducedMotion();
            }
        });
    }

    /**
     * Apply reduced motion
     */
    applyReducedMotion() {
        document.body.classList.add('reduced-motion');
        
        // Disable auto-refresh if motion is reduced
        if (window.stopAutoRefresh) {
            window.stopAutoRefresh();
        }
    }

    /**
     * Announce page change
     */
    announcePageChange() {
        const title = document.title;
        this.announce(`Page loaded: ${title}`);
    }

    /**
     * Announce form validation
     */
    announceFormValidation() {
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            form.addEventListener('submit', (e) => {
                const errors = form.querySelectorAll('.error, .invalid');
                if (errors.length > 0) {
                    this.announce(`Form has ${errors.length} error${errors.length > 1 ? 's' : ''}`);
                }
            });
        });
    }

    /**
     * Make announcement to screen readers
     */
    announce(message) {
        if (!this.settings.announcements) return;

        const liveRegion = document.getElementById('live-region');
        if (liveRegion) {
            liveRegion.textContent = message;
            
            // Clear after announcement
            setTimeout(() => {
                liveRegion.textContent = '';
            }, 1000);
        }
    }

    /**
     * Toggle accessibility panel
     */
    toggleAccessibilityPanel() {
        const panel = document.getElementById('accessibilityPanel');
        const toggle = document.getElementById('accessibilityToggle');
        const isActive = panel.classList.contains('active');

        if (isActive) {
            this.closeAccessibilityPanel();
        } else {
            this.openAccessibilityPanel();
        }
    }

    /**
     * Open accessibility panel
     */
    openAccessibilityPanel() {
        const panel = document.getElementById('accessibilityPanel');
        const toggle = document.getElementById('accessibilityToggle');
        
        panel.classList.add('active');
        panel.setAttribute('aria-hidden', 'false');
        toggle.setAttribute('aria-expanded', 'true');
        
        // Focus first input
        const firstInput = panel.querySelector('input');
        if (firstInput) {
            firstInput.focus();
        }
    }

    /**
     * Close accessibility panel
     */
    closeAccessibilityPanel() {
        const panel = document.getElementById('accessibilityPanel');
        const toggle = document.getElementById('accessibilityToggle');
        
        panel.classList.remove('active');
        panel.setAttribute('aria-hidden', 'true');
        toggle.setAttribute('aria-expanded', 'false');
        toggle.focus();
    }

    /**
     * Apply setting
     */
    applySetting(setting, value) {
        this.settings[setting] = value;
        
        switch(setting) {
            case 'highContrast':
                document.body.classList.toggle('high-contrast', value);
                break;
            case 'largeText':
                document.body.classList.toggle('large-text', value);
                break;
            case 'reducedMotion':
                document.body.classList.toggle('reduced-motion', value);
                if (value) {
                    this.applyReducedMotion();
                }
                break;
            case 'focusIndicators':
                document.body.classList.toggle('focus-indicators', value);
                break;
        }
        
        this.saveSettings();
        this.announce(`${setting} ${value ? 'enabled' : 'disabled'}`);
    }

    /**
     * Skip to main content
     */
    skipToContent() {
        const mainContent = document.getElementById('main-content');
        if (mainContent) {
            mainContent.focus();
            mainContent.scrollIntoView();
        }
    }

    /**
     * Reset all settings
     */
    resetSettings() {
        Object.keys(this.settings).forEach(key => {
            this.settings[key] = key === 'keyboardNavigation' || key === 'focusIndicators' || key === 'announcements';
        });
        
        this.applyAllSettings();
        this.updateSettingsUI();
        this.saveSettings();
        this.announce('All settings reset to default');
    }

    /**
     * Apply all settings
     */
    applyAllSettings() {
        Object.entries(this.settings).forEach(([key, value]) => {
            this.applySetting(key, value);
        });
    }

    /**
     * Update settings UI
     */
    updateSettingsUI() {
        Object.entries(this.settings).forEach(([key, value]) => {
            const input = document.getElementById(key);
            if (input) {
                input.checked = value;
            }
        });
    }

    /**
     * Close modal
     */
    closeModal(modal) {
        modal.classList.remove('active');
        
        // Return focus to trigger
        const trigger = modal.getAttribute('data-trigger');
        if (trigger) {
            const triggerElement = document.getElementById(trigger);
            if (triggerElement) {
                triggerElement.focus();
            }
        }
    }

    /**
     * Load settings from localStorage
     */
    loadSettings() {
        const stored = localStorage.getItem('vectorcraft-accessibility');
        if (stored) {
            this.settings = { ...this.settings, ...JSON.parse(stored) };
        }
        
        this.applyAllSettings();
    }

    /**
     * Save settings to localStorage
     */
    saveSettings() {
        localStorage.setItem('vectorcraft-accessibility', JSON.stringify(this.settings));
    }

    /**
     * Bind events
     */
    bindEvents() {
        // Accessibility toggle
        document.addEventListener('click', (e) => {
            if (e.target.id === 'accessibilityToggle' || e.target.closest('#accessibilityToggle')) {
                this.toggleAccessibilityPanel();
            }
        });

        // Close panel
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('panel-close') || e.target.closest('.panel-close')) {
                this.closeAccessibilityPanel();
            }
        });

        // Setting toggles
        document.addEventListener('change', (e) => {
            if (e.target.matches('#accessibilityPanel input[type="checkbox"]')) {
                const setting = e.target.id;
                const value = e.target.checked;
                this.applySetting(setting, value);
            }
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Alt + A to open accessibility menu
            if (e.altKey && e.key === 'a') {
                e.preventDefault();
                this.toggleAccessibilityPanel();
            }
            
            // Alt + S to skip to content
            if (e.altKey && e.key === 's') {
                e.preventDefault();
                this.skipToContent();
            }
        });

        // Click outside to close
        document.addEventListener('click', (e) => {
            const panel = document.getElementById('accessibilityPanel');
            const toggle = document.getElementById('accessibilityToggle');
            
            if (panel && panel.classList.contains('active') && 
                !panel.contains(e.target) && !toggle.contains(e.target)) {
                this.closeAccessibilityPanel();
            }
        });
    }
}

// Initialize accessibility enhancements
const accessibilityEnhancements = new AccessibilityEnhancements();

// Make it globally available
window.accessibilityEnhancements = accessibilityEnhancements;

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AccessibilityEnhancements;
}