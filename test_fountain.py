#!/usr/bin/env python3
"""
VFD Musical Fountain - TEST MODE
Tests RMS + Bass analysis WITHOUT hardware
- No GPIO needed (simulates fountain always ON)
- No DAC needed (prints voltage values instead)
- Just audio analysis and visualization
"""

import subprocess
import time
import os
import logging
import threading
import numpy as np
from pathlib import Path
import sys

# Configuration
MUSIC_DIR = "./test_music"  # Test music directory (current folder)

# VFD Control Parameters (for calculation only)
MIN_FREQUENCY_PERCENT = 30  
MAX_FREQUENCY_PERCENT = 100  
SMOOTHING_FACTOR = 0.2

# Audio Analysis Parameters
SAMPLE_RATE = 22050
CHUNK_SIZE = 2048
UPDATE_RATE = 0.05

# Bass frequency range
BASS_LOW_FREQ = 20
BASS_HIGH_FREQ = 250

# Mixing weights
RMS_WEIGHT = 0.6
BASS_WEIGHT = 0.4

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

class SimulatedVFD:
    """Simulates VFD - just prints values instead of controlling hardware"""
    
    def __init__(self):
        self.current_output = 0
        self.target_output = 0
        self.current_percent = 0
        logging.info("✓ VFD Controller initialized (SIMULATION MODE)")
    
    def set_intensity(self, percent):
        """Calculate what voltage we WOULD send to VFD"""
        # Map percent to frequency range
        freq_range = MAX_FREQUENCY_PERCENT - MIN_FREQUENCY_PERCENT
        actual_percent = MIN_FREQUENCY_PERCENT + (percent / 100.0 * freq_range)
        actual_percent = max(MIN_FREQUENCY_PERCENT, min(MAX_FREQUENCY_PERCENT, actual_percent))
        
        # Convert to DAC value (0-4095)
        self.target_output = int((actual_percent / 100.0) * 4095)
        self.current_percent = percent
    
    def update_smooth(self):
        """Smooth transitions"""
        if self.current_output != self.target_output:
            diff = self.target_output - self.current_output
            self.current_output += diff * SMOOTHING_FACTOR
            
            if abs(self.target_output - self.current_output) < 5:
                self.current_output = self.target_output
    
    def get_voltage(self):
        """Return simulated voltage (0-5V)"""
        return (self.current_output / 4095.0) * 5.0
    
    def ramp_to_zero(self):
        """Simulate ramp down"""
        logging.info("→ Ramping VFD to zero...")
        for i in range(100, -1, -5):
            freq_range = MAX_FREQUENCY_PERCENT - MIN_FREQUENCY_PERCENT
            actual_percent = MIN_FREQUENCY_PERCENT + (i / 100.0 * freq_range)
            value = int((actual_percent / 100.0) * 4095)
            self.current_output = value
            time.sleep(0.05)
        
        self.current_output = 0
        self.target_output = 0
        logging.info("✓ VFD at zero")

class AudioAnalyzer:
    """Real audio analysis - same as production version"""
    
    def __init__(self, vfd_controller):
        self.vfd = vfd_controller
        self.is_analyzing = False
        self.analysis_thread = None
        self.playback_process = None
        
        # Calculate FFT bin indices for bass range
        self.bass_low_bin = int(BASS_LOW_FREQ * CHUNK_SIZE / SAMPLE_RATE)
        self.bass_high_bin = int(BASS_HIGH_FREQ * CHUNK_SIZE / SAMPLE_RATE)
        
        logging.info(f"✓ Bass analysis: {BASS_LOW_FREQ}-{BASS_HIGH_FREQ} Hz (bins {self.bass_low_bin}-{self.bass_high_bin})")
    
    def start_analysis(self, audio_file):
        """Start analyzing audio file"""
        self.is_analyzing = True
        
        # Start audio playback (to speakers if available, muted if not)
        self.playback_process = subprocess.Popen(
            ['cvlc', '--play-and-exit', '--no-video', '--intf', 'dummy', 
             '--quiet', audio_file],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        logging.info(f"♪ Playing: {os.path.basename(audio_file)}")
        
        # Start analysis thread
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
            'ffmpeg', '-y',
            '-i', audio_file,
            '-f', 's16le',
            '-acodec', 'pcm_s16le',
            '-ar', str(SAMPLE_RATE),
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
            
            logging.info("✓ Starting audio analysis (RMS + Bass FFT)")
            logging.info("")
            logging.info("=" * 80)
            logging.info("LIVE ANALYSIS - Watch the pump intensity change!")
            logging.info("=" * 80)
            logging.info(f"{'Time':>6} │ {'RMS':>6} │ {'Bass':>6} │ {'Intensity':>9} │ {'Voltage':>7} │ Bar Chart")
            logging.info("─" * 80)
            
            with open(pcm_path, 'rb') as pcm_file:
                bytes_per_sample = 2
                chunk_bytes = CHUNK_SIZE * bytes_per_sample
                
                chunk_count = 0
                start_time = time.time()
                
                while self.is_analyzing:
                    data = pcm_file.read(chunk_bytes)
                    
                    if len(data) < chunk_bytes:
                        break
                    
                    # Convert to numpy array
                    audio_data = np.frombuffer(data, dtype=np.int16)
                    audio_normalized = audio_data.astype(np.float32) / 32768.0
                    
                    # Calculate RMS
                    rms = np.sqrt(np.mean(audio_normalized ** 2))
                    
                    # Calculate FFT for bass
                    fft = np.fft.rfft(audio_normalized)
                    fft_magnitude = np.abs(fft)
                    
                    # Bass energy
                    bass_energy = np.sum(fft_magnitude[self.bass_low_bin:self.bass_high_bin])
                    bass_normalized = min(1.0, bass_energy / 200.0)
                    
                    # Combined intensity
                    rms_component = rms * RMS_WEIGHT
                    bass_component = bass_normalized * BASS_WEIGHT
                    combined_intensity = (rms_component + bass_component) * 100
                    combined_intensity = max(0, min(100, combined_intensity))
                    
                    # Set VFD
                    self.vfd.set_intensity(combined_intensity)
                    
                    # Visual output every chunk
                    chunk_count += 1
                    elapsed = time.time() - start_time
                    
                    # Create bar chart visualization
                    bar_length = int(combined_intensity / 2)  # 50 chars = 100%
                    bar = "█" * bar_length
                    
                    # Get voltage
                    voltage = self.vfd.get_voltage()
                    
                    # Print live update
                    print(f"\r{elapsed:6.1f}s │ {rms:5.3f} │ {bass_normalized:5.3f} │ {combined_intensity:6.1f}%  │ {voltage:5.2f}V │ {bar}", 
                          end='', flush=True)
                    
                    # Every 2 seconds, print newline and summary
                    if chunk_count % 40 == 0:
                        print()  # New line
                    
                    time.sleep(UPDATE_RATE)
            
            print()  # Final newline
            logging.info("─" * 80)
            os.unlink(pcm_path)
            
            logging.info("✓ Audio analysis completed")
            
        except Exception as e:
            logging.error(f"✗ Analysis error: {e}")
            import traceback
            logging.error(traceback.format_exc())
        finally:
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
        
        subprocess.run(['pkill', '-9', 'vlc'], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL)

class TestController:
    """Test controller - no GPIO, just analysis"""
    
    def __init__(self):
        self.vfd = SimulatedVFD()
        self.analyzer = AudioAnalyzer(self.vfd)
        
        logging.info("")
        logging.info("╔═══════════════════════════════════════════════════════════╗")
        logging.info("║     VFD MUSICAL FOUNTAIN - TEST MODE                      ║")
        logging.info("╚═══════════════════════════════════════════════════════════╝")
        logging.info("")
        logging.info("This is a SIMULATION - no hardware needed!")
        logging.info(f"  • No GPIO (fountain detection simulated)")
        logging.info(f"  • No DAC (voltage values printed)")
        logging.info(f"  • Real audio analysis (RMS + Bass FFT)")
        logging.info("")
        logging.info(f"Configuration:")
        logging.info(f"  • RMS Weight: {RMS_WEIGHT*100}%")
        logging.info(f"  • Bass Weight: {BASS_WEIGHT*100}%")
        logging.info(f"  • Bass Range: {BASS_LOW_FREQ}-{BASS_HIGH_FREQ} Hz")
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
        
        files = sorted([str(f) for f in files])
        
        return files
    
    def test_file(self, filepath):
        """Test a specific file"""
        if not os.path.exists(filepath):
            logging.error(f"✗ File not found: {filepath}")
            return
        
        logging.info(f"Testing: {os.path.basename(filepath)}")
        logging.info("")
        
        self.analyzer.start_analysis(filepath)
        
        # Wait for analysis to complete
        while self.analyzer.is_analyzing:
            self.vfd.update_smooth()
            time.sleep(0.1)
    
    def test_all(self):
        """Test all files in music directory"""
        files = self.get_music_files()
        
        if not files:
            logging.error("✗ No music files found!")
            logging.info("")
            logging.info(f"Add MP3/FLAC files to: {MUSIC_DIR}")
            logging.info("Then run the test again.")
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
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test VFD Fountain Controller (No Hardware)')
    parser.add_argument('file', nargs='?', help='Audio file to test (optional)')
    parser.add_argument('--all', action='store_true', help='Test all files in music directory')
    parser.add_argument('--dir', default='./test_music', help='Music directory (default: ./test_music)')
    
    args = parser.parse_args()
    
    # Update music directory if specified
    global MUSIC_DIR
    MUSIC_DIR = args.dir
    
    controller = TestController()
    
    try:
        if args.file:
            # Test specific file
            controller.test_file(args.file)
        elif args.all:
            # Test all files
            controller.test_all()
        else:
            # Interactive mode
            files = controller.get_music_files()
            
            if not files:
                logging.info("No files found. Usage:")
                logging.info("  python3 test_fountain.py <audio_file.mp3>")
                logging.info("  python3 test_fountain.py --all")
                logging.info(f"  python3 test_fountain.py --dir /path/to/music --all")
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
