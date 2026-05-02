/**
 * Fountain Controller Web Interface
 * Main application logic
 */

class FountainController {
    constructor() {
        this.knobs = {};
        this.config = {};
        this.statusInterval = null;

        this.init();
    }

    async init() {
        // Load initial configuration
        await this.loadConfig();

        // Initialize all knobs
        this.initKnobs();

        // Setup button handlers
        this.setupButtons();

        // Start status polling
        this.startStatusPolling();

        // Show ready toast
        this.showToast('Controller ready');
    }

    async loadConfig() {
        try {
            const response = await fetch('/api/config');
            if (response.ok) {
                this.config = await response.json();
                this.updateStatus(true);
            } else {
                throw new Error('Failed to load config');
            }
        } catch (error) {
            console.error('Error loading config:', error);
            this.showToast('Failed to connect to server', true);
            this.updateStatus(false);
        }
    }

    initKnobs() {
        const knobElements = document.querySelectorAll('.knob');

        knobElements.forEach(element => {
            const param = element.dataset.param;

            const knob = new AudioKnob(element, {
                onChange: (param, value) => this.onKnobChange(param, value)
            });

            // Set initial value from config
            if (this.config[param] !== undefined) {
                knob.setValue(this.config[param]);
            }

            this.knobs[param] = knob;
        });
    }

    onKnobChange(param, value) {
        this.config[param] = value;

        // Visual feedback - briefly highlight the knob
        const knobElement = document.querySelector(`.knob[data-param="${param}"]`);
        if (knobElement) {
            knobElement.style.boxShadow = '0 5px 30px rgba(0, 212, 255, 0.6)';
            setTimeout(() => {
                knobElement.style.boxShadow = '';
            }, 200);
        }
    }

    setupButtons() {
        // Save button
        const saveBtn = document.getElementById('btn-save');
        saveBtn.addEventListener('click', () => this.saveConfig());

        // Reset button
        const resetBtn = document.getElementById('btn-reset');
        resetBtn.addEventListener('click', () => this.resetConfig());
    }

    async saveConfig() {
        try {
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(this.config)
            });

            const result = await response.json();

            if (result.status === 'success') {
                this.showToast('Settings saved successfully');
            } else {
                throw new Error(result.message || 'Save failed');
            }
        } catch (error) {
            console.error('Error saving config:', error);
            this.showToast('Failed to save settings', true);
        }
    }

    async resetConfig() {
        if (!confirm('Reset all settings to defaults?')) {
            return;
        }

        try {
            const response = await fetch('/api/config/reset', {
                method: 'POST'
            });

            const result = await response.json();

            if (result.status === 'success') {
                this.config = result.config;

                // Update all knobs
                Object.keys(this.knobs).forEach(param => {
                    if (this.config[param] !== undefined) {
                        this.knobs[param].setValue(this.config[param]);
                    }
                });

                this.showToast('Settings reset to defaults');
            } else {
                throw new Error(result.message || 'Reset failed');
            }
        } catch (error) {
            console.error('Error resetting config:', error);
            this.showToast('Failed to reset settings', true);
        }
    }

    startStatusPolling() {
        // Poll status every 500ms when playing
        this.statusInterval = setInterval(() => this.pollStatus(), 500);
    }

    async pollStatus() {
        try {
            const response = await fetch('/api/status');
            if (response.ok) {
                const status = await response.json();
                this.updateStatusDisplay(status);
                this.updateStatus(true);
            }
        } catch (error) {
            // Silently ignore polling errors
        }
    }

    updateStatusDisplay(status) {
        // Update intensity display
        const intensityEl = document.getElementById('current-intensity');
        if (intensityEl) {
            intensityEl.textContent = `${Math.round(status.current_intensity)}%`;
        }

        // Update RMS display
        const rmsEl = document.getElementById('current-rms');
        if (rmsEl) {
            rmsEl.textContent = status.current_rms.toFixed(2);
        }

        // Update Bass display
        const bassEl = document.getElementById('current-bass');
        if (bassEl) {
            bassEl.textContent = status.current_bass.toFixed(2);
        }

        // Update status indicator
        const indicator = document.getElementById('status-indicator');
        const statusText = indicator.querySelector('.text');

        if (status.is_playing) {
            indicator.classList.add('online');
            statusText.textContent = 'Playing';
        } else {
            indicator.classList.remove('online');
            statusText.textContent = 'Standby';
        }
    }

    updateStatus(connected) {
        const indicator = document.getElementById('status-indicator');
        const statusText = indicator.querySelector('.text');

        if (connected) {
            if (!statusText.textContent.includes('Playing')) {
                statusText.textContent = 'Connected';
            }
        } else {
            indicator.classList.remove('online');
            statusText.textContent = 'Offline';
        }
    }

    showToast(message, isError = false) {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.classList.remove('error');

        if (isError) {
            toast.classList.add('error');
        }

        toast.classList.add('show');

        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.fountainController = new FountainController();
});
