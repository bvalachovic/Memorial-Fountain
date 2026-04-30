#!/usr/bin/env python3
"""
VFD Musical Fountain - TEST MODE (Web-Configurable)
Same as test_fountain.py but loads settings from fountain_config.json
so the web interface (web_interface.py) can control parameters in real time.

Usage:
  1. Start the web interface:  python web_interface.py
  2. Run this test:            python test_fountain_web.py test_music/beethoven01.mp3
  3. Adjust knobs at http://localhost:5000 — changes apply on next song
"""

import subprocess
import time
import os
import logging
import threading
import numpy as np
from pathlib import Path
import sys
import shutil
import glob
import json

# Config file shared with web_interface.py
CONFIG_FILE = Path(__file__).parent / 'fountain_config.json'
# Status file read by web_interface.py for live display
STATUS_FILE = Path(__file__).parent / 'fountain_status.json'

DEFAULT_CONFIG = {
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
    """Load configuration from fountain_config.json, falling back to defaults"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception as e:
            logging.warning(f"Could not load config: {e}, using defaults")
    return DEFAULT_CONFIG.copy()


def _write_status(is_playing, intensity=0, rms=0, bass=0):
    """Write current status to file for the web interface to read (atomic write)"""
    try:
        status = {
            'is_playing': is_playing,
            'current_intensity': round(intensity, 1),
            'current_rms': round(rms, 3),
            'current_bass': round(bass, 3),
        }
        tmp = STATUS_FILE.with_suffix('.tmp')
        with open(tmp, 'w') as f:
            json.dump(status, f)
        tmp.replace(STATUS_FILE)
    except Exception:
        pass


def _clear_status():
    """Reset status to idle"""
    _write_status(False)


def _find_ffmpeg():
    """Find ffmpeg executable, checking PATH and common Windows install locations"""
    found = shutil.which('ffmpeg')
    if found:
        return found
    if sys.platform == 'win32':
        patterns = [
            os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\WinGet\Packages\*\ffmpeg*\bin\ffmpeg.exe'),
            r'C:\ffmpeg\bin\ffmpeg.exe',
            r'C:\ProgramData\chocolatey\bin\ffmpeg.exe',
        ]
        for pattern in patterns:
            matches = glob.glob(pattern)
            if matches:
                return matches[0]
    return 'ffmpeg'


FFMPEG_PATH = _find_ffmpeg()

# Music directory
MUSIC_DIR = "./test_music"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[logging.StreamHandler()]
)


class SimulatedVFD:
    """Simulates VFD - just prints values instead of controlling hardware"""

    def __init__(self, config):
        self.config = config
        self.current_output = 0
        self.target_output = 0
        self.current_percent = 0
        logging.info("✓ VFD Controller initialized (SIMULATION MODE)")

    def reload_config(self, config):
        self.config = config

    def set_intensity(self, percent):
        """Calculate what voltage we WOULD send to VFD"""
        min_freq = self.config['min_frequency_percent']
        max_freq = self.config['max_frequency_percent']
        freq_range = max_freq - min_freq
        actual_percent = min_freq + (percent / 100.0 * freq_range)
        actual_percent = max(min_freq, min(max_freq, actual_percent))

        self.target_output = int((actual_percent / 100.0) * 4095)
        self.current_percent = percent

    def update_smooth(self):
        """Smooth transitions"""
        if self.current_output != self.target_output:
            diff = self.target_output - self.current_output
            self.current_output += diff * self.config['smoothing_factor']

            if abs(self.target_output - self.current_output) < 5:
                self.current_output = self.target_output

    def get_voltage(self):
        """Return simulated voltage (0-5V)"""
        return (self.current_output / 4095.0) * 5.0

    def ramp_to_zero(self):
        """Simulate ramp down"""
        min_freq = self.config['min_frequency_percent']
        logging.info("→ Ramping VFD to zero...")
        for i in range(100, -1, -5):
            freq_range = self.config['max_frequency_percent'] - min_freq
            actual_percent = min_freq + (i / 100.0 * freq_range)
            value = int((actual_percent / 100.0) * 4095)
            self.current_output = value
            time.sleep(0.05)

        self.current_output = 0
        self.target_output = 0
        logging.info("✓ VFD at zero")


class AudioAnalyzer:
    """Real audio analysis - reads config from fountain_config.json"""

    def __init__(self, vfd_controller, config):
        self.vfd = vfd_controller
        self.config = config
        self.is_analyzing = False
        self.analysis_thread = None
        self.playback_process = None
        self._update_bins()

    def _update_bins(self):
        self.bass_low_bin = int(self.config['bass_low_freq'] * self.config['chunk_size'] / self.config['sample_rate'])
        self.bass_high_bin = int(self.config['bass_high_freq'] * self.config['chunk_size'] / self.config['sample_rate'])
        logging.info(f"✓ Bass analysis: {self.config['bass_low_freq']}-{self.config['bass_high_freq']} Hz (bins {self.bass_low_bin}-{self.bass_high_bin})")

    def reload_config(self, config):
        self.config = config
        self._update_bins()

    def start_analysis(self, audio_file):
        """Start analyzing audio file"""
        # Reload config from file at the start of each song
        self.config = load_config()
        self.vfd.reload_config(self.config)
        self._update_bins()

        self.is_analyzing = True

        # Start audio playback
        try:
            if sys.platform == 'win32':
                vlc_paths = [
                    r'C:\Program Files\VideoLAN\VLC\vlc.exe',
                    r'C:\Program Files (x86)\VideoLAN\VLC\vlc.exe',
                ]
                vlc_cmd = next((p for p in vlc_paths if os.path.exists(p)), None)
                if vlc_cmd:
                    self.playback_process = subprocess.Popen(
                        [vlc_cmd, '--play-and-exit', '--no-video', '--intf', 'dummy',
                         '--quiet', audio_file],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                else:
                    logging.warning("VLC not found - analysis only, no audio playback")
            else:
                self.playback_process = subprocess.Popen(
                    ['cvlc', '--play-and-exit', '--no-video', '--intf', 'dummy',
                     '--quiet', audio_file],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
        except FileNotFoundError:
            logging.warning("VLC not found - analysis only, no audio playback")

        logging.info(f"♪ Playing: {os.path.basename(audio_file)}")

        self.analysis_thread = threading.Thread(
            target=self._analyze_audio,
            args=(audio_file,),
            daemon=True
        )
        self.analysis_thread.start()

    def _decode_audio_to_pcm(self, audio_file):
        """Decode audio file to raw PCM using ffmpeg"""
        import tempfile

        pcm_file = tempfile.NamedTemporaryFile(suffix='.pcm', delete=False)
        pcm_path = pcm_file.name
        pcm_file.close()

        cmd = [
            FFMPEG_PATH, '-y',
            '-i', audio_file,
            '-f', 's16le',
            '-acodec', 'pcm_s16le',
            '-ar', str(self.config['sample_rate']),
            '-ac', '1',
            pcm_path
        ]

        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return pcm_path
        except Exception as e:
            logging.error(f"✗ Failed to decode audio: {e}")
            return None

    def _analyze_audio(self, audio_file):
        """Main analysis loop with live visualization"""
        try:
            pcm_path = self._decode_audio_to_pcm(audio_file)
            if not pcm_path:
                return

            cfg = self.config
            logging.info("✓ Starting audio analysis (RMS + Bass FFT)")
            logging.info(f"  Config: RMS {cfg['rms_weight']*100:.0f}% + Bass {cfg['bass_weight']*100:.0f}% | "
                         f"Freq {cfg['min_frequency_percent']}-{cfg['max_frequency_percent']}% | "
                         f"Smoothing {cfg['smoothing_factor']}")
            logging.info("")
            logging.info("=" * 80)
            logging.info("LIVE ANALYSIS - Watch the pump intensity change!")
            logging.info("=" * 80)
            logging.info(f"{'Time':>6} │ {'RMS':>6} │ {'Bass':>6} │ {'Intensity':>9} │ {'Voltage':>7} │ Bar Chart")
            logging.info("─" * 80)

            chunk_size = cfg['chunk_size']

            with open(pcm_path, 'rb') as pcm_file:
                bytes_per_sample = 2
                chunk_bytes = chunk_size * bytes_per_sample

                chunk_count = 0
                start_time = time.time()

                while self.is_analyzing:
                    data = pcm_file.read(chunk_bytes)

                    if len(data) < chunk_bytes:
                        break

                    audio_data = np.frombuffer(data, dtype=np.int16)
                    audio_normalized = audio_data.astype(np.float32) / 32768.0

                    # RMS
                    rms = np.sqrt(np.mean(audio_normalized ** 2))

                    # FFT for bass
                    fft = np.fft.rfft(audio_normalized)
                    fft_magnitude = np.abs(fft)

                    bass_energy = np.sum(fft_magnitude[self.bass_low_bin:self.bass_high_bin])
                    bass_normalized = min(1.0, bass_energy / 200.0)

                    # Combined intensity
                    rms_component = rms * cfg['rms_weight']
                    bass_component = bass_normalized * cfg['bass_weight']
                    combined_intensity = (rms_component + bass_component) * 100
                    combined_intensity = max(0, min(100, combined_intensity))

                    self.vfd.set_intensity(combined_intensity)

                    chunk_count += 1
                    elapsed = time.time() - start_time

                    bar_length = int(combined_intensity / 2)
                    bar = "█" * bar_length

                    voltage = self.vfd.get_voltage()

                    print(f"\r{elapsed:6.1f}s │ {rms:5.3f} │ {bass_normalized:5.3f} │ {combined_intensity:6.1f}%  │ {voltage:5.2f}V │ {bar}",
                          end='', flush=True)

                    # Write status for web interface
                    _write_status(True, combined_intensity, rms, bass_normalized)

                    if chunk_count % 40 == 0:
                        print()

                    time.sleep(cfg['update_rate'])

            print()
            logging.info("─" * 80)
            os.unlink(pcm_path)

            logging.info("✓ Audio analysis completed")

        except Exception as e:
            logging.error(f"✗ Analysis error: {e}")
            import traceback
            logging.error(traceback.format_exc())
        finally:
            _clear_status()
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

        if sys.platform == 'win32':
            subprocess.run(['cmd', '/c', 'taskkill', '/IM', 'vlc.exe', '/F'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.run(['pkill', '-9', 'vlc'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class TestController:
    """Test controller - no GPIO, loads config from fountain_config.json"""

    def __init__(self):
        self.config = load_config()
        self.vfd = SimulatedVFD(self.config)
        self.analyzer = AudioAnalyzer(self.vfd, self.config)

        logging.info("")
        logging.info("╔═══════════════════════════════════════════════════════════╗")
        logging.info("║   VFD MUSICAL FOUNTAIN - TEST MODE (Web-Configurable)     ║")
        logging.info("╚═══════════════════════════════════════════════════════════╝")
        logging.info("")
        logging.info("This is a SIMULATION - no hardware needed!")
        logging.info("  • No GPIO (fountain detection simulated)")
        logging.info("  • No DAC (voltage values printed)")
        logging.info("  • Real audio analysis (RMS + Bass FFT)")
        logging.info(f"  • Config loaded from: {CONFIG_FILE}")
        logging.info("")
        logging.info(f"Configuration:")
        logging.info(f"  • RMS Weight: {self.config['rms_weight']*100:.0f}%")
        logging.info(f"  • Bass Weight: {self.config['bass_weight']*100:.0f}%")
        logging.info(f"  • Bass Range: {self.config['bass_low_freq']}-{self.config['bass_high_freq']} Hz")
        logging.info(f"  • Pump Speed: {self.config['min_frequency_percent']}-{self.config['max_frequency_percent']}%")
        logging.info(f"  • Smoothing: {self.config['smoothing_factor']}")
        logging.info(f"  • Music Directory: {MUSIC_DIR}")
        logging.info("")

    def get_music_files(self):
        """Get list of audio files"""
        music_path = Path(MUSIC_DIR)

        if not music_path.exists():
            logging.warning(f"⚠ Music directory not found: {MUSIC_DIR}")
            logging.info(f"  Creating directory: {MUSIC_DIR}")
            music_path.mkdir(parents=True, exist_ok=True)
            logging.info(f"  → Please add MP3/FLAC files to: {MUSIC_DIR}")
            return []

        extensions = ['*.mp3', '*.m4a', '*.flac', '*.wav', '*.ogg']
        files = []
        for ext in extensions:
            files.extend(music_path.glob(ext))

        return sorted([str(f) for f in files])

    def test_file(self, filepath):
        """Test a specific file"""
        if not os.path.exists(filepath):
            logging.error(f"✗ File not found: {filepath}")
            return

        logging.info(f"Testing: {os.path.basename(filepath)}")
        logging.info("")

        self.analyzer.start_analysis(filepath)

        while self.analyzer.is_analyzing:
            self.vfd.update_smooth()
            time.sleep(0.1)

    def test_all(self):
        """Test all files in music directory"""
        files = self.get_music_files()

        if not files:
            logging.error("✗ No music files found!")
            logging.info(f"Add MP3/FLAC files to: {MUSIC_DIR}")
            return

        logging.info(f"✓ Found {len(files)} music files")
        logging.info("")

        for i, filepath in enumerate(files, 1):
            logging.info(f"[{i}/{len(files)}] Testing: {os.path.basename(filepath)}")
            self.test_file(filepath)
            logging.info("")

            if i < len(files):
                logging.info("Press Ctrl+C to stop, or wait 3 seconds for next file...")
                try:
                    time.sleep(3)
                except KeyboardInterrupt:
                    logging.info("")
                    logging.info("Stopped by user")
                    break


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Test VFD Fountain (Web-Configurable, No Hardware)')
    parser.add_argument('file', nargs='?', help='Audio file to test (optional)')
    parser.add_argument('--all', action='store_true', help='Test all files in music directory')
    parser.add_argument('--dir', default='./test_music', help='Music directory (default: ./test_music)')

    args = parser.parse_args()

    global MUSIC_DIR
    MUSIC_DIR = args.dir

    controller = TestController()

    try:
        if args.file:
            controller.test_file(args.file)
        elif args.all:
            controller.test_all()
        else:
            files = controller.get_music_files()

            if not files:
                logging.info("No files found. Usage:")
                logging.info("  python test_fountain_web.py <audio_file.mp3>")
                logging.info("  python test_fountain_web.py --all")
                logging.info(f"  python test_fountain_web.py --dir /path/to/music --all")
                return

            logging.info("Select a file to test:")
            for i, f in enumerate(files, 1):
                logging.info(f"  {i}. {os.path.basename(f)}")

            logging.info("")
            choice = input("Enter number (or 'all' for all files): ").strip()

            if choice.lower() == 'all':
                controller.test_all()
            else:
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(files):
                        controller.test_file(files[idx])
                    else:
                        logging.error("Invalid selection")
                except ValueError:
                    logging.error("Invalid input")

    except KeyboardInterrupt:
        logging.info("")
        logging.info("✓ Test stopped by user")

    logging.info("")
    logging.info("Test complete!")


if __name__ == "__main__":
    main()
