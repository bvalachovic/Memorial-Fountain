/**
 * Audio Knob Control Component
 * Creates rotary knob controls that mimic analog audio equipment
 */

class AudioKnob {
    constructor(element, options = {}) {
        this.element = element;
        this.inner = element.querySelector('.knob-inner');
        this.ledRing = element.querySelector('.knob-led-ring');

        // Get config from data attributes
        this.param = element.dataset.param;
        this.min = parseFloat(element.dataset.min) || 0;
        this.max = parseFloat(element.dataset.max) || 100;
        this.step = parseFloat(element.dataset.step) || 1;

        // Knob rotation range (degrees)
        this.minAngle = -135;
        this.maxAngle = 135;

        // Current value
        this.value = this.min;

        // Interaction state
        this.isDragging = false;
        this.startY = 0;
        this.startValue = 0;

        // Callbacks
        this.onChange = options.onChange || (() => {});

        this.init();
    }

    init() {
        // Mouse events
        this.element.addEventListener('mousedown', this.onMouseDown.bind(this));
        document.addEventListener('mousemove', this.onMouseMove.bind(this));
        document.addEventListener('mouseup', this.onMouseUp.bind(this));

        // Touch events
        this.element.addEventListener('touchstart', this.onTouchStart.bind(this), { passive: false });
        document.addEventListener('touchmove', this.onTouchMove.bind(this), { passive: false });
        document.addEventListener('touchend', this.onTouchEnd.bind(this));

        // Wheel event for fine control
        this.element.addEventListener('wheel', this.onWheel.bind(this), { passive: false });

        // Double-click to reset to center
        this.element.addEventListener('dblclick', this.onDoubleClick.bind(this));

        // Initial render
        this.render();
    }

    onMouseDown(e) {
        e.preventDefault();
        this.startDrag(e.clientY);
    }

    onMouseMove(e) {
        if (this.isDragging) {
            this.drag(e.clientY);
        }
    }

    onMouseUp() {
        this.endDrag();
    }

    onTouchStart(e) {
        e.preventDefault();
        const touch = e.touches[0];
        this.startDrag(touch.clientY);
    }

    onTouchMove(e) {
        if (this.isDragging) {
            e.preventDefault();
            const touch = e.touches[0];
            this.drag(touch.clientY);
        }
    }

    onTouchEnd() {
        this.endDrag();
    }

    onWheel(e) {
        e.preventDefault();
        const delta = e.deltaY > 0 ? -this.step : this.step;
        this.setValue(this.value + delta);
    }

    onDoubleClick() {
        // Reset to middle value
        const midValue = (this.min + this.max) / 2;
        this.setValue(midValue);
    }

    startDrag(y) {
        this.isDragging = true;
        this.startY = y;
        this.startValue = this.value;
        this.element.classList.add('active');
        document.body.style.cursor = 'ns-resize';
    }

    drag(y) {
        // Calculate value change based on vertical drag
        // Moving up increases, moving down decreases
        const deltaY = this.startY - y;
        const sensitivity = (this.max - this.min) / 200; // 200px for full range
        const deltaValue = deltaY * sensitivity;

        this.setValue(this.startValue + deltaValue);
    }

    endDrag() {
        if (this.isDragging) {
            this.isDragging = false;
            this.element.classList.remove('active');
            document.body.style.cursor = '';
        }
    }

    setValue(value) {
        // Clamp and snap to step
        value = Math.max(this.min, Math.min(this.max, value));
        value = Math.round(value / this.step) * this.step;

        // Fix floating point precision
        const decimals = this.step.toString().split('.')[1];
        const precision = decimals ? decimals.length : 0;
        value = parseFloat(value.toFixed(precision));

        if (value !== this.value) {
            this.value = value;
            this.render();
            this.onChange(this.param, this.value);
        }
    }

    getValue() {
        return this.value;
    }

    render() {
        // Calculate rotation angle
        const range = this.max - this.min;
        const normalized = (this.value - this.min) / range;
        const angle = this.minAngle + (normalized * (this.maxAngle - this.minAngle));

        // Apply rotation to inner knob
        this.inner.style.transform = `rotate(${angle}deg)`;

        // Update LED ring if present
        if (this.ledRing) {
            const ledAngle = normalized * 270; // 270 degrees total arc
            this.ledRing.style.setProperty('--led-angle', `${ledAngle}deg`);
        }

        // Update value display
        const valueDisplay = document.getElementById(`val-${this.param}`);
        if (valueDisplay) {
            // Format based on step size
            if (this.step < 1) {
                valueDisplay.textContent = this.value.toFixed(2);
            } else {
                valueDisplay.textContent = Math.round(this.value);
            }
        }
    }
}

// Export for use in app.js
window.AudioKnob = AudioKnob;
