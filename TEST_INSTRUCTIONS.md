# Testing VFD Fountain Without Hardware

## Quick Start - Test on Your Computer

You can test the audio analysis **right now** on any computer (Mac, Linux, Windows with WSL) - **no Raspberry Pi needed, no hardware needed!**

### Requirements

Just these common tools:
```bash
# Check if you have them:
python3 --version    # Need Python 3.7+
ffmpeg -version      # For audio decoding
cvlc --version       # VLC for playback

# Install if needed:
# Mac:
brew install python3 ffmpeg vlc

# Ubuntu/Debian:
sudo apt-get install python3 python3-pip ffmpeg vlc

# Install numpy:
pip3 install numpy
```

### 1. Create Test Music Folder

```bash
# Create folder and add some music
mkdir test_music
cp ~/Music/beethoven.mp3 test_music/
cp ~/Music/vivaldi.mp3 test_music/
```

### 2. Run the Test

```bash
# Test a specific file:
python3 test_fountain.py test_music/beethoven.mp3

# Or test all files in folder:
python3 test_fountain.py --all

# Or interactive mode:
python3 test_fountain.py
```

### What You'll See

```
╔═══════════════════════════════════════════════════════════╗
║     VFD MUSICAL FOUNTAIN - TEST MODE                      ║
╚═══════════════════════════════════════════════════════════╝

This is a SIMULATION - no hardware needed!
  • No GPIO (fountain detection simulated)
  • No DAC (voltage values printed)
  • Real audio analysis (RMS + Bass FFT)

Configuration:
  • RMS Weight: 60.0%
  • Bass Weight: 40.0%
  • Bass Range: 20-250 Hz

✓ Bass analysis: 20-250 Hz (bins 1-23)
✓ VFD Controller initialized (SIMULATION MODE)
♪ Playing: beethoven_symphony_5.mp3
✓ Starting audio analysis (RMS + Bass FFT)

================================================================================
LIVE ANALYSIS - Watch the pump intensity change!
================================================================================
  Time │    RMS │   Bass │ Intensity │ Voltage │ Bar Chart
────────────────────────────────────────────────────────────────────────────────
   0.0s │ 0.234 │ 0.156 │   20.3%  │  2.15V │ ██████████
   2.1s │ 0.445 │ 0.523 │   47.6%  │  3.28V │ ███████████████████████
   4.2s │ 0.678 │ 0.892 │   76.4%  │  4.52V │ ██████████████████████████████████████
   6.3s │ 0.523 │ 0.234 │   40.7%  │  2.98V │ ████████████████████
```

You can **watch the intensity change in real-time** as the music plays!

---

## What Each Column Means

| Column | Range | Meaning |
|--------|-------|---------|
| **Time** | 0-∞ | Seconds into the song |
| **RMS** | 0.000-1.000 | Overall volume (Root Mean Square) |
| **Bass** | 0.000-1.000 | Bass energy from FFT (20-250 Hz) |
| **Intensity** | 0-100% | Combined pump intensity |
| **Voltage** | 1.5-5.0V | What would be sent to VFD (0-5V) |
| **Bar Chart** | Visual | Graphical representation |

---

## Example Output Explained

```
   4.2s │ 0.678 │ 0.892 │   76.4%  │  4.52V │ ████████████████████████████████████
```

**Translation:**
- At 4.2 seconds into the song
- RMS = 0.678 (music is fairly loud, 67.8%)
- Bass = 0.892 (STRONG bass energy, 89.2% - probably timpani or kick drum!)
- Combined = 76.4% intensity (the magic formula!)
- Would send 4.52 volts to VFD (high voltage = fast pump)
- Bar chart shows ~38 blocks = 76% of 50 max blocks

**In the fountain:** This would be a powerful surge of water!

---

## Testing Different Configurations

Edit `test_fountain.py` to experiment:

```python
# Line 24-25: Change the mixing weights
RMS_WEIGHT = 0.6   # Try 0.8 for smoother response
BASS_WEIGHT = 0.4  # Try 0.6 for more punch

# Line 21-22: Change bass frequency range
BASS_LOW_FREQ = 20    # Try 40 for less rumble
BASS_HIGH_FREQ = 250  # Try 150 for tighter bass

# Line 14: Change response speed
SMOOTHING_FACTOR = 0.2  # Try 0.1 (smoother) or 0.4 (reactive)
```

After editing, just run the test again to see the difference!

---

## Testing Tips

### Best Test Music

**Good for testing:**
- Beethoven symphonies (dramatic dynamics + strong bass)
- Film scores (Hans Zimmer - lots of action)
- Jazz with upright bass
- Classical with timpani

**Bad for testing:**
- Modern pop (compressed, constant volume)
- Ambient/drone music (no dynamics)
- Podcasts/spoken word

### What to Look For

**Good Response:**
- Intensity varies from 10-90%
- Bass spikes during drum hits
- RMS follows overall volume
- Bar chart is lively and changing

**Poor Response (needs tuning):**
- Stuck at one intensity
- No bass variation (weights wrong?)
- Too jumpy/jerky (smoothing too high)
- Too sluggish (smoothing too low)

---

## Interpreting Results

### Example Patterns

**Quiet passage:**
```
  12.3s │ 0.123 │ 0.045 │   10.2%  │  1.81V │ █████
```
→ Gentle trickle, minimal water flow

**Building crescendo:**
```
  45.1s │ 0.234 │ 0.123 │   18.7%  │  2.12V │ █████████
  47.2s │ 0.456 │ 0.287 │   35.9%  │  2.79V │ █████████████████
  49.3s │ 0.678 │ 0.523 │   61.1%  │  3.98V │ ██████████████████████████████
```
→ Gradually increasing flow

**Timpani strike!**
```
  62.1s │ 0.445 │ 0.234 │   35.7%  │ 2.78V │ █████████████████
  62.2s │ 0.523 │ 0.923 │   68.3%  │ 4.26V │ ██████████████████████████████████  ← BOOM!
  62.3s │ 0.389 │ 0.156 │   29.6%  │ 2.53V │ ██████████████
```
→ Sudden spike from bass hit!

---

## Troubleshooting Test

### "Module not found: numpy"
```bash
pip3 install numpy
```

### "ffmpeg not found"
```bash
# Mac: brew install ffmpeg
# Ubuntu: sudo apt-get install ffmpeg
```

### "cvlc not found"
```bash
# Mac: brew install vlc
# Ubuntu: sudo apt-get install vlc
```

### No audio playback?
That's fine! The analysis still works. VLC might be muted or no speakers.

### Analysis shows all zeros?
- Check audio file is valid (play it in another app)
- Make sure ffmpeg can decode it
- Try different audio file

---

## Advanced Testing

### Test with Custom Directory

```bash
python3 test_fountain.py --dir ~/Music/Classical --all
```

### Compare Different Files

```bash
# Test multiple files and compare results
python3 test_fountain.py quiet_piece.mp3 > quiet.log
python3 test_fountain.py loud_piece.mp3 > loud.log

# Compare:
diff quiet.log loud.log
```

### Record Output for Analysis

```bash
python3 test_fountain.py beethoven.mp3 2>&1 | tee test_output.txt
```

---

## What This Proves

✅ **Audio analysis works** - RMS + Bass FFT calculations are correct  
✅ **Intensity formula works** - Combining weights properly  
✅ **Smoothing works** - Values transition naturally  
✅ **Voltage calculation works** - Correct 0-5V mapping  

**Once this test looks good, you know the code is solid!**

The only difference on the real Raspberry Pi is:
- GPIO reads fountain state (instead of always ON)
- DAC outputs actual voltage (instead of printing)
- Everything else is **exactly the same**

---

## Next Steps

1. **Test on your computer** - Make sure analysis looks good
2. **Tune the parameters** - Adjust weights until you like the response
3. **Copy to Raspberry Pi** - Transfer the working config
4. **Install on Pi** - Run `install_rms_bass.sh`
5. **Connect hardware** - DAC, relay, VFD (electrician does VFD)
6. **Real test!** - Turn on fountain and watch it work

---

## Example Test Session

```bash
$ mkdir test_music
$ cp ~/Music/beethoven_symphony_5.mp3 test_music/
$ python3 test_fountain.py --all

╔═══════════════════════════════════════════════════════════╗
║     VFD MUSICAL FOUNTAIN - TEST MODE                      ║
╚═══════════════════════════════════════════════════════════╝

[Analysis runs, shows live data]

✓ Audio analysis completed
✓ Test complete!

$ # Looks good! Now tune it...
$ nano test_fountain.py  # Change RMS_WEIGHT to 0.7
$ python3 test_fountain.py beethoven_symphony_5.mp3

[Test again with new weights]

$ # Perfect! Now deploy to Pi...
```

---

**Start testing now - no hardware needed!** 🎵📊
