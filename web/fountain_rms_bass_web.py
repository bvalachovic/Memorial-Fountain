#!/usr/bin/env python3
"""
VFD Musical Fountain Controller with RMS + Bass Analysis
Web-enabled version that loads settings from fountain_config.json

- RMS for overall volume/intensity
- FFT bass energy for beat emphasis
- Settings controllable via web interface
"""

import RPi.GPIO as GPIO
import subprocess
import time
import os
import logging
import threading
import numpy as np
import board
import busio
import adafruit_mcp4725
from pathlib import Path
import json

# Configuration file path
CONFIG_FILE = Path(__file__).parent / 'fountain_config.json'

# Default Configuration
DEFAULT_CONFIG = {
    'fountain_pin': 17,
    'music_dir': "/home/pi/music",
    'debounce_time': 2,
    'min_frequency_percent': 30,
    'max_frequency_percent': 100,
    'smoothing_factor': 0.2,
    'sample_rate': 22050,
    'chunk_size': 2048,
    'update_rate': 0.05,
    'bass_low_freq': 20,
    'bass_high_freq': 250,
    'rms_weight': 0.6,
    'bass_weight': 0.4,
}

def load_config():
    """Load configuration from file or return defaults"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception as e:
            logging.warning(f"Error loading config, using defaults: {e}")
    return DEFAULT_CONFIG.copy()

# Load config at module level
config = load_config()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/fountain_vfd.log'),
        logging.StreamHandler()
    ]
)

class VFDController:
    """Manages DAC output to control VFD"""

    def __init__(self):
        self.reload_config()
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            self.dac = adafruit_mcp4725.MCP4725(i2c)
            self.current_output = 0
            self.target_output = 0
            logging.info("VFD Controller initialized (MCP4725 DAC)")
        except Exception as e:
            logging.error(f"Failed to initialize DAC: {e}")
            self.dac = None

    def reload_config(self):
        """Reload configuration from file"""
        global config
        config = load_config()
        self.min_freq = config['min_frequency_percent']
        self.max_freq = config['max_frequency_percent']
        self.smoothing = config['smoothing_factor']

    def set_intensity(self, percent):
        """
        Set VFD output intensity
        percent: 0-100, where 0 = MIN_FREQUENCY, 100 = MAX_FREQUENCY
        """
        if self.dac is None:
            return

        # Map percent to actual frequency range
        freq_range = self.max_freq - self.min_freq
        actual_percent = self.min_freq + (percent / 100.0 * freq_range)

        # Clamp to valid range
        actual_percent = max(self.min_freq, min(self.max_freq, actual_percent))

        # Convert to DAC value (0-4095 for 12-bit DAC)
        self.target_output = int((actual_percent / 100.0) * 4095)

    def update_smooth(self):
        """Smooth transitions to prevent jerky pump movement"""
        if self.dac is None:
            return

        if self.current_output != self.target_output:
            # Exponential smoothing
            diff = self.target_output - self.current_output
            self.current_output += diff * self.smoothing

            # Close enough? Snap to target
            if abs(self.target_output - self.current_output) < 5:
                self.current_output = self.target_output

            self.dac.raw_value = int(self.current_output)

    def ramp_to_zero(self):
        """Safely ramp down to zero"""
        logging.info("Ramping VFD to zero...")
        for i in range(100, -1, -5):
            freq_range = self.max_freq - self.min_freq
            actual_percent = self.min_freq + (i / 100.0 * freq_range)
            value = int((actual_percent / 100.0) * 4095)

            if self.dac:
                self.dac.raw_value = value
            time.sleep(0.1)

        self.current_output = 0
        self.target_output = 0
        logging.info("VFD at zero")


class AudioAnalyzer:
    """
    Real-time audio analysis using RMS and FFT bass energy
    Decodes audio to PCM and analyzes in separate thread
    """

    def __init__(self, vfd_controller, status_callback=None):
        self.vfd = vfd_controller
        self.is_analyzing = False
        self.analysis_thread = None
        self.playback_process = None
        self.status_callback = status_callback

        # Status values for web interface
        self.current_rms = 0
        self.current_bass = 0
        self.current_intensity = 0

        self.reload_config()

    def reload_config(self):
        """Reload configuration from file"""
        global config
        config = load_config()
        self.sample_rate = config['sample_rate']
        self.chunk_size = config['chunk_size']
        self.update_rate = config['update_rate']
        self.bass_low_freq = config['bass_low_freq']
        self.bass_high_freq = config['bass_high_freq']
        self.rms_weight = config['rms_weight']
        self.bass_weight = config['bass_weight']

        # Calculate FFT bin indices for bass range
        self.bass_low_bin = int(self.bass_low_freq * self.chunk_size / self.sample_rate)
        self.bass_high_bin = int(self.bass_high_freq * self.chunk_size / self.sample_rate)

        logging.info(f"Bass analysis: {self.bass_low_freq}-{self.bass_high_freq} Hz (bins {self.bass_low_bin}-{self.bass_high_bin})")

    def start_analysis(self, audio_file):
        """Start analyzing audio file and controlling VFD"""
        self.is_analyzing = True
        self.reload_config()
        self.vfd.reload_config()

        # Start audio playback to Bluetooth speakers
        self.playback_process = subprocess.Popen(
            ['cvlc', '--play-and-exit', '--no-video', '--intf', 'dummy',
             '--quiet', audio_file],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        logging.info(f"Started playback: {os.path.basename(audio_file)}")

        # Start parallel analysis thread
        self.analysis_thread = threading.Thread(
            target=self._analyze_audio,
            args=(audio_file,),
            daemon=True
        )
        self.analysis_thread.start()

    def _decode_audio_to_pcm(self, audio_file):
        """
        Decode audio file to raw PCM using ffmpeg
        Returns file path to decoded PCM data
        """
        import tempfile

        # Create temp file for PCM output
        pcm_file = tempfile.NamedTemporaryFile(suffix='.pcm', delete=False)
        pcm_path = pcm_file.name
        pcm_file.close()

        # Use ffmpeg to decode to mono PCM at our sample rate
        cmd = [
            'ffmpeg', '-y',
            '-i', audio_file,
            '-f', 's16le',  # 16-bit signed PCM
            '-acodec', 'pcm_s16le',
            '-ar', str(self.sample_rate),  # Resample to our rate
            '-ac', '1',  # Mono
            pcm_path
        ]

        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return pcm_path
        except Exception as e:
            logging.error(f"Failed to decode audio: {e}")
            return None

    def _analyze_audio(self, audio_file):
        """
        Main analysis loop - reads PCM data and calculates RMS + bass energy
        """
        try:
            # Decode audio to PCM
            pcm_path = self._decode_audio_to_pcm(audio_file)
            if not pcm_path:
                return

            logging.info("Starting audio analysis (RMS + Bass FFT)")

            # Open PCM file
            with open(pcm_path, 'rb') as pcm_file:
                bytes_per_sample = 2  # 16-bit = 2 bytes
                chunk_bytes = self.chunk_size * bytes_per_sample

                chunk_count = 0

                while self.is_analyzing:
                    # Read chunk of audio data
                    data = pcm_file.read(chunk_bytes)

                    if len(data) < chunk_bytes:
                        # End of file
                        break

                    # Convert bytes to numpy array of int16
                    audio_data = np.frombuffer(data, dtype=np.int16)

                    # Normalize to -1.0 to 1.0
                    audio_normalized = audio_data.astype(np.float32) / 32768.0

                    # Calculate RMS (Root Mean Square) - overall volume
                    rms = np.sqrt(np.mean(audio_normalized ** 2))

                    # Calculate FFT for bass energy
                    fft = np.fft.rfft(audio_normalized)
                    fft_magnitude = np.abs(fft)

                    # Extract bass frequencies
                    bass_energy = np.sum(fft_magnitude[self.bass_low_bin:self.bass_high_bin])

                    # Normalize bass energy (typical range is 0-200 for this chunk size)
                    bass_normalized = min(1.0, bass_energy / 200.0)

                    # Calculate combined intensity
                    # RMS gives smooth volume following
                    # Bass gives punchy beat emphasis
                    rms_component = rms * self.rms_weight
                    bass_component = bass_normalized * self.bass_weight

                    combined_intensity = (rms_component + bass_component) * 100

                    # Clamp to 0-100
                    combined_intensity = max(0, min(100, combined_intensity))

                    # Update status values for web interface
                    self.current_rms = rms
                    self.current_bass = bass_normalized
                    self.current_intensity = combined_intensity

                    # Set VFD intensity
                    self.vfd.set_intensity(combined_intensity)

                    # Log periodically (every 2 seconds)
                    chunk_count += 1
                    if chunk_count % 40 == 0:  # 20Hz * 2 = 40 chunks
                        logging.info(f"RMS: {rms:.3f} | Bass: {bass_normalized:.3f} | Intensity: {combined_intensity:.1f}%")

                    # Control analysis rate
                    time.sleep(self.update_rate)

            # Clean up temp file
            os.unlink(pcm_path)

            logging.info("Audio analysis completed")

        except Exception as e:
            logging.error(f"Analysis error: {e}")
            import traceback
            logging.error(traceback.format_exc())
        finally:
            # Reset status values
            self.current_rms = 0
            self.current_bass = 0
            self.current_intensity = 0
            # Ramp down at end
            self.vfd.ramp_to_zero()

    def stop_analysis(self):
        """Stop analysis and playback"""
        self.is_analyzing = False

        if self.playback_process:
            self.playback_process.terminate()
            try:
                self.playback_process.wait(timeout=2)
            except:
                self.playback_process.kill()

        if self.analysis_thread:
            self.analysis_thread.join(timeout=3)

        # Kill any remaining VLC processes
        subprocess.run(['pkill', '-9', 'vlc'],
                      stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL)


class MusicalFountainController:
    """Main controller with RMS + Bass analysis"""

    def __init__(self):
        self.is_playing = False
        self.vfd = VFDController()
        self.analyzer = AudioAnalyzer(self.vfd)

        # Reload config
        global config
        config = load_config()

        # Setup GPIO for fountain detection
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(config['fountain_pin'], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

        logging.info("Musical Fountain Controller started (RMS + Bass FFT)")
        logging.info(f"RMS Weight: {config['rms_weight']*100}% | Bass Weight: {config['bass_weight']*100}%")
        logging.info(f"Monitoring GPIO pin {config['fountain_pin']}")
        logging.info(f"Music directory: {config.get('music_dir', '/home/pi/music')}")

    def get_status(self):
        """Get current status for web interface"""
        return {
            'is_playing': self.is_playing,
            'current_intensity': self.analyzer.current_intensity,
            'current_rms': self.analyzer.current_rms,
            'current_bass': self.analyzer.current_bass
        }

    def get_music_files(self):
        """Get list of audio files"""
        music_dir = config.get('music_dir', '/home/pi/music')
        music_path = Path(music_dir)
        if not music_path.exists():
            logging.error(f"Music directory not found: {music_dir}")
            return []

        # Supported formats
        extensions = ['*.mp3', '*.m4a', '*.flac', '*.wav', '*.ogg']
        files = []

        for ext in extensions:
            files.extend(music_path.glob(ext))

        files = sorted([str(f) for f in files])

        logging.info(f"Found {len(files)} music files")
        return files

    def start_music(self):
        """Play random music and control fountain"""
        if self.is_playing:
            logging.info("Music already playing")
            return

        files = self.get_music_files()

        if not files:
            logging.error("No music files found")
            return

        # Pick random file
        import random
        selected = random.choice(files)

        logging.info(f"Selected: {os.path.basename(selected)}")

        self.is_playing = True

        # Start analysis and playback
        self.analyzer.start_analysis(selected)

    def stop_music(self):
        """Stop music and ramp down fountain"""
        if not self.is_playing:
            return

        logging.info("Stopping playback...")

        self.analyzer.stop_analysis()
        self.vfd.ramp_to_zero()

        self.is_playing = False
        logging.info("Playback stopped")

    def check_fountain_state(self):
        """Check if fountain is on"""
        return GPIO.input(config['fountain_pin']) == GPIO.HIGH

    def run(self):
        """Main monitoring loop"""
        last_state = False
        state_change_time = None
        debounce_time = config['debounce_time']
        update_rate = config['update_rate']

        try:
            while True:
                current_state = self.check_fountain_state()

                # Detect state change
                if current_state != last_state:
                    if state_change_time is None:
                        state_change_time = time.time()

                    # Debounce
                    elif time.time() - state_change_time >= debounce_time:
                        if current_state:
                            logging.info("Fountain turned ON")
                            self.start_music()
                        else:
                            logging.info("Fountain turned OFF")
                            self.stop_music()

                        last_state = current_state
                        state_change_time = None
                else:
                    state_change_time = None

                # Update VFD smoothing
                self.vfd.update_smooth()

                time.sleep(update_rate)

        except KeyboardInterrupt:
            logging.info("Shutting down...")
            self.stop_music()
            GPIO.cleanup()
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            self.stop_music()
            GPIO.cleanup()
            raise


# Global controller instance for web interface access
fountain_controller = None

def get_controller():
    """Get or create the fountain controller instance"""
    global fountain_controller
    if fountain_controller is None:
        fountain_controller = MusicalFountainController()
    return fountain_controller


if __name__ == "__main__":
    controller = get_controller()
    controller.run()
