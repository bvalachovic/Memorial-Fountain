#!/usr/bin/env python3
"""
Web Interface for VFD Musical Fountain Controller
Provides a web-based control panel with audio knob-style dials
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import json
import os
from pathlib import Path

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# Default configuration (matches fountain_rms_bass.py)
CONFIG_FILE = Path(__file__).parent / 'fountain_config.json'

DEFAULT_CONFIG = {
    # VFD Control Parameters
    'min_frequency_percent': 30,
    'max_frequency_percent': 100,
    'smoothing_factor': 0.2,

    # Audio Analysis Parameters
    'sample_rate': 22050,
    'chunk_size': 2048,
    'update_rate': 0.05,

    # Bass frequency range
    'bass_low_freq': 20,
    'bass_high_freq': 250,

    # Mixing weights
    'rms_weight': 0.6,
    'bass_weight': 0.4,

    # GPIO
    'fountain_pin': 17,
    'debounce_time': 2,
}

def load_config():
    """Load configuration from file or return defaults"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception as e:
            print(f"Error loading config: {e}")
    return DEFAULT_CONFIG.copy()

def save_config(config):
    """Save configuration to file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

@app.route('/')
def index():
    """Serve the main control panel"""
    return render_template('index.html')

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    return jsonify(load_config())

@app.route('/api/config', methods=['POST'])
def update_config():
    """Update configuration"""
    try:
        new_config = request.json
        current_config = load_config()
        current_config.update(new_config)

        if save_config(current_config):
            return jsonify({'status': 'success', 'config': current_config})
        else:
            return jsonify({'status': 'error', 'message': 'Failed to save config'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/config/reset', methods=['POST'])
def reset_config():
    """Reset configuration to defaults"""
    if save_config(DEFAULT_CONFIG):
        return jsonify({'status': 'success', 'config': DEFAULT_CONFIG})
    return jsonify({'status': 'error', 'message': 'Failed to reset config'}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current fountain status"""
    try:
        # Try to import the fountain controller for real status
        from fountain_rms_bass_web import get_controller
        controller = get_controller()
        return jsonify(controller.get_status())
    except ImportError:
        # Running without hardware - return placeholder
        return jsonify({
            'is_playing': False,
            'current_intensity': 0,
            'current_rms': 0,
            'current_bass': 0
        })

if __name__ == '__main__':
    # Create templates and static directories if they don't exist
    (Path(__file__).parent / 'templates').mkdir(exist_ok=True)
    (Path(__file__).parent / 'static').mkdir(exist_ok=True)

    print("Starting Fountain Control Web Interface...")
    print("Open http://localhost:5000 in your browser")
    app.run(host='0.0.0.0', port=5000, debug=True)
