/**
 * VectorCraft Frontend JavaScript
 * Professional vector conversion application
 */

class VectorCraft {
    constructor() {
        this.initEventListeners();
        this.setupCSRFToken();
        this.setupFormValidation();
    }

    /**
     * Initialize event listeners
     */
    initEventListeners() {
        // File upload handling
        const fileInput = document.getElementById('file-input');
        if (fileInput) {
            fileInput.addEventListener('change', this.handleFileSelect.bind(this));
        }

        // Form submission
        const vectorizeForm = document.getElementById('vectorize-form');
        if (vectorizeForm) {
            vectorizeForm.addEventListener('submit', this.handleVectorizeSubmit.bind(this));
        }

        // Strategy selection
        const strategySelect = document.getElementById('strategy-select');
        if (strategySelect) {
            strategySelect.addEventListener('change', this.handleStrategyChange.bind(this));
        }
    }

    /**
     * Setup CSRF token for AJAX requests
     */
    setupCSRFToken() {
        const csrfToken = document.querySelector('meta[name="csrf-token"]');
        if (csrfToken) {
            this.csrfToken = csrfToken.getAttribute('content');
        }
    }

    /**
     * Setup form validation
     */
    setupFormValidation() {
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            form.addEventListener('submit', this.validateForm.bind(this));
        });
    }

    /**
     * Handle file selection
     */
    handleFileSelect(event) {
        const file = event.target.files[0];
        if (!file) return;

        // Validate file type
        const allowedTypes = ['image/png', 'image/jpeg', 'image/gif', 'image/bmp', 'image/tiff'];
        if (!allowedTypes.includes(file.type)) {
            this.showAlert('Invalid file type. Please upload PNG, JPG, GIF, BMP, or TIFF files.', 'error');
            event.target.value = '';
            return;
        }

        // Validate file size (16MB limit)
        const maxSize = 16 * 1024 * 1024;
        if (file.size > maxSize) {
            this.showAlert('File too large. Maximum size is 16MB.', 'error');
            event.target.value = '';
            return;
        }

        // Show file preview
        this.showFilePreview(file);
    }

    /**
     * Show file preview
     */
    showFilePreview(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const previewContainer = document.getElementById('file-preview');
            if (previewContainer) {
                previewContainer.innerHTML = `
                    <img src="${e.target.result}" alt="Preview" class="max-w-xs max-h-32 object-contain">
                    <p class="text-sm text-gray-600 mt-2">${file.name} (${this.formatFileSize(file.size)})</p>
                `;
                previewContainer.classList.remove('hidden');
            }
        };
        reader.readAsDataURL(file);
    }

    /**
     * Format file size for display
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * Handle vectorize form submission
     */
    async handleVectorizeSubmit(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        const submitButton = event.target.querySelector('button[type="submit"]');
        
        // Disable submit button and show loading
        submitButton.disabled = true;
        submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';
        
        try {
            const response = await fetch('/api/vectorize', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.csrfToken
                }
            });

            const result = await response.json();
            
            if (response.ok) {
                this.handleVectorizeSuccess(result);
            } else {
                this.handleVectorizeError(result.error || 'Vectorization failed');
            }
        } catch (error) {
            this.handleVectorizeError('Network error occurred');
        } finally {
            // Re-enable submit button
            submitButton.disabled = false;
            submitButton.innerHTML = 'Vectorize';
        }
    }

    /**
     * Handle successful vectorization
     */
    handleVectorizeSuccess(result) {
        this.showAlert('Vectorization completed successfully!', 'success');
        
        // Show download link
        const downloadContainer = document.getElementById('download-container');
        if (downloadContainer) {
            downloadContainer.innerHTML = `
                <a href="${result.download_url}" 
                   class="inline-flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors">
                    <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                    </svg>
                    Download Vector
                </a>
            `;
            downloadContainer.classList.remove('hidden');
        }
        
        // Show SVG preview if available
        if (result.svg_preview) {
            this.showSVGPreview(result.svg_preview);
        }
    }

    /**
     * Handle vectorization error
     */
    handleVectorizeError(error) {
        this.showAlert(error, 'error');
    }

    /**
     * Show SVG preview
     */
    showSVGPreview(svgContent) {
        const previewContainer = document.getElementById('svg-preview');
        if (previewContainer) {
            previewContainer.innerHTML = svgContent;
            previewContainer.classList.remove('hidden');
        }
    }

    /**
     * Handle strategy selection change
     */
    handleStrategyChange(event) {
        const strategy = event.target.value;
        const advancedOptions = document.getElementById('advanced-options');
        
        if (strategy === 'experimental_v2') {
            advancedOptions?.classList.remove('hidden');
        } else {
            advancedOptions?.classList.add('hidden');
        }
    }

    /**
     * Validate form before submission
     */
    validateForm(event) {
        const form = event.target;
        const requiredFields = form.querySelectorAll('[required]');
        
        for (let field of requiredFields) {
            if (!field.value.trim()) {
                this.showAlert(`Please fill in the ${field.name} field.`, 'error');
                event.preventDefault();
                return false;
            }
        }
        
        return true;
    }

    /**
     * Show alert message
     */
    showAlert(message, type = 'info') {
        const alertContainer = document.getElementById('alert-container') || document.body;
        
        const alertColors = {
            success: 'bg-green-100 border-green-400 text-green-700',
            error: 'bg-red-100 border-red-400 text-red-700',
            warning: 'bg-yellow-100 border-yellow-400 text-yellow-700',
            info: 'bg-blue-100 border-blue-400 text-blue-700'
        };
        
        const alertDiv = document.createElement('div');
        alertDiv.className = `border-l-4 p-4 mb-4 ${alertColors[type] || alertColors.info}`;
        alertDiv.innerHTML = `
            <div class="flex justify-between items-center">
                <span>${message}</span>
                <button class="ml-4 text-lg leading-none" onclick="this.parentElement.parentElement.remove()">
                    &times;
                </button>
            </div>
        `;
        
        alertContainer.insertBefore(alertDiv, alertContainer.firstChild);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            alertDiv.remove();
        }, 5000);
    }

    /**
     * Utility function to debounce function calls
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// Initialize VectorCraft when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new VectorCraft();
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VectorCraft;
}