#!/usr/bin/env python3
"""
Memorial Fountain Controller
Runs on Raspberry Pi. Selects motor driver from fountain_config.json.

  driver = "l298n"  →  prototype test rig (L298N + aquarium pump)
  driver = "vfd"    →  production (MCP4725 DAC → VFD → 3-phase pump motor)

Set auto_start = true to run immediately without a GPIO fountain trigger.
Set auto_start = false to wait for fountain_pin to go HIGH (production mode).
"""

import os
import time
import random
import logging
import threading
import subprocess
import json
import numpy as np
import RPi.GPIO as GPIO
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / 'fountain_config.json'

DEFAULT_CONFIG = {
    'driver': 'l298n',
    'auto_start': True,
    'music_dir': '/home/bvalachovic/music',
    'fountain_pin': 17,
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

LOG_FILE = Path(__file__).parent / 'fountain.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)


def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception as e:
            logging.warning(f"Config load failed, using defaults: {e}")
    return DEFAULT_CONFIG.copy()


def load_driver(config):
    """Import and return the configured motor driver instance."""
    driver_name = config.get('driver', 'l298n')
    min_s = config['min_frequency_percent']
    max_s = config['max_frequency_percent']
    smooth = config['smoothing_factor']

    if driver_name == 'vfd':
        from drivers.vfd_driver import VFDDriver
        logging.info("Loading VFD driver (production hardware)")
        return VFDDriver(min_speed=min_s, max_speed=max_s, smoothing=smooth)
    else:
        from drivers.l298n_driver import L298NDriver
        logging.info("Loading L298N driver (prototype test rig)")
        return L298NDriver(min_speed=min_s, max_speed=max_s, smoothing=smooth)


class AudioAnalyzer:
    """
    Decodes audio to PCM via ffmpeg, then drives the motor driver
    using RMS (volume) + bass FFT (beat) in a background thread.
    """

    def __init__(self, driver, config):
        self.driver = driver
        self.config = config
        self.is_analyzing = False
        self.analysis_thread = None
        self.playback_process = None
        self._update_bins()

    def _update_bins(self):
        c = self.config
        self.bass_low_bin = int(c['bass_low_freq'] * c['chunk_size'] / c['sample_rate'])
        self.bass_high_bin = int(c['bass_high_freq'] * c['chunk_size'] / c['sample_rate'])

    def start(self, audio_file):
        self.is_analyzing = True

        self.playback_process = subprocess.Popen(
            ['cvlc', '--play-and-exit', '--no-video', '--intf', 'dummy',
             '--quiet', audio_file],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        logging.info(f"Playback started: {os.path.basename(audio_file)}")

        self.analysis_thread = threading.Thread(
            target=self._analyze, args=(audio_file,), daemon=True
        )
        self.analysis_thread.start()

    def _decode_to_pcm(self, audio_file):
        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix='.pcm', delete=False)
        pcm_path = tmp.name
        tmp.close()

        cmd = [
            'ffmpeg', '-y', '-i', audio_file,
            '-f', 's16le', '-acodec', 'pcm_s16le',
            '-ar', str(self.config['sample_rate']),
            '-ac', '1', pcm_path
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return pcm_path
        except Exception as e:
            logging.error(f"ffmpeg decode failed: {e}")
            return None

    def _analyze(self, audio_file):
        try:
            pcm_path = self._decode_to_pcm(audio_file)
            if not pcm_path:
                return

            c = self.config
            chunk_bytes = c['chunk_size'] * 2  # 16-bit = 2 bytes/sample
            chunk_count = 0

            logging.info("Audio analysis started (RMS + Bass FFT)")

            with open(pcm_path, 'rb') as f:
                while self.is_analyzing:
                    data = f.read(chunk_bytes)
                    if len(data) < chunk_bytes:
                        break

                    audio = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0

                    rms = np.sqrt(np.mean(audio ** 2))

                    fft_mag = np.abs(np.fft.rfft(audio))
                    bass_energy = np.sum(fft_mag[self.bass_low_bin:self.bass_high_bin])
                    bass = min(1.0, bass_energy / 200.0)

                    intensity = (rms * c['rms_weight'] + bass * c['bass_weight']) * 100
                    intensity = max(0, min(100, intensity))

                    self.driver.set_intensity(intensity)

                    chunk_count += 1
                    if chunk_count % 40 == 0:
                        logging.info(f"RMS: {rms:.3f} | Bass: {bass:.3f} | Intensity: {intensity:.1f}%")

                    time.sleep(c['update_rate'])

            os.unlink(pcm_path)
            logging.info("Audio analysis complete")

        except Exception as e:
            logging.error(f"Analysis error: {e}")
            import traceback
            logging.error(traceback.format_exc())
        finally:
            self.driver.ramp_to_zero()

    def stop(self):
        self.is_analyzing = False
        if self.playback_process:
            self.playback_process.terminate()
            try:
                self.playback_process.wait(timeout=2)
            except Exception:
                self.playback_process.kill()
        if self.analysis_thread:
            self.analysis_thread.join(timeout=3)
        subprocess.run(['pkill', '-9', 'vlc'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class FountainController:

    def __init__(self):
        self.config = load_config()
        self.driver = load_driver(self.config)
        self.analyzer = AudioAnalyzer(self.driver, self.config)
        self.is_playing = False

        auto_start = self.config.get('auto_start', False)
        if not auto_start:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.config['fountain_pin'], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

        logging.info(f"Fountain controller ready | driver={self.config['driver']} | auto_start={auto_start}")

    def _get_music_files(self):
        music_path = Path(self.config['music_dir'])
        if not music_path.exists():
            logging.error(f"Music directory not found: {music_path}")
            return []
        files = []
        for ext in ['*.mp3', '*.m4a', '*.flac', '*.wav', '*.ogg']:
            files.extend(music_path.glob(ext))
        files = sorted([str(f) for f in files])
        logging.info(f"Found {len(files)} music files")
        return files

    def start_music(self):
        if self.is_playing:
            return
        files = self._get_music_files()
        if not files:
            logging.error("No music files found — check music_dir in fountain_config.json")
            return
        selected = random.choice(files)
        self.is_playing = True
        self.analyzer.start(selected)

    def stop_music(self):
        if not self.is_playing:
            return
        logging.info("Stopping playback...")
        self.analyzer.stop()
        self.driver.ramp_to_zero()
        self.is_playing = False

    def run(self):
        c = self.config
        auto_start = c.get('auto_start', False)
        update_rate = c['update_rate']

        try:
            if auto_start:
                logging.info("Auto-start: beginning playback immediately")
                self.start_music()
                while True:
                    self.driver.update_smooth()
                    time.sleep(update_rate)
            else:
                last_state = False
                state_change_time = None
                debounce = c['debounce_time']

                while True:
                    current_state = GPIO.input(c['fountain_pin']) == GPIO.HIGH

                    if current_state != last_state:
                        if state_change_time is None:
                            state_change_time = time.time()
                        elif time.time() - state_change_time >= debounce:
                            if current_state:
                                logging.info("Fountain ON")
                                self.start_music()
                            else:
                                logging.info("Fountain OFF")
                                self.stop_music()
                            last_state = current_state
                            state_change_time = None
                    else:
                        state_change_time = None

                    self.driver.update_smooth()
                    time.sleep(update_rate)

        except KeyboardInterrupt:
            logging.info("Shutting down...")
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            raise
        finally:
            self.stop_music()
            self.driver.cleanup()


if __name__ == "__main__":
    FountainController().run()
