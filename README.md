Here are the three commands needed. All assume you're in the project directory.

Install dependencies first (one time):


python -m pip install flask flask-cors numpy
Web Interface — config panel at http://localhost:5000


python web_interface.py
Test Mode — simulated VFD, no hardware needed, runs on Windows


python test_fountain.py test_music/beethoven01.mp3
Production — real hardware on the Raspberry Pi only


python fountain_rms_bass.py
Or with the web-configurable version:


python fountain_rms_bass_web.py
The production scripts (fountain_rms_bass.py / fountain_rms_bass_web.py) will fail on Windows because they import RPi.GPIO, board, and adafruit_mcp4725 — those only exist on the Pi. On Windows, stick with test_fountain.py for analysis testing and web_interface.py for tuning parameters.


This setup is well-suited for a 16–18" copper garden fountain is actually a modest demand for the hardware your project specifies.

Pump/VFD Sizing
Your README.md:180-188 specifies a 1 HP VFD and motor — that's significantly oversized for an 18" fountain basin, which works in your favor:

A fountain that size typically needs only 1/4 to 1/2 HP to push water 2–4 feet high
1 HP would give you a very tall, dramatic water column if you wanted it
The VFD lets you dial it back via MIN_FREQUENCY_PERCENT / MAX_FREQUENCY_PERCENT in your config
For an 18" copper fountain, a 1/2 HP submersible or inline pump with a matching VFD is the sweet spot. 1 HP would work too but you'd be running it at the low end of its range most of the time.

Key Considerations for a Real Garden Install
Pump type:

Submersible pump is simplest — sits in the basin, no plumbing runs
Must be rated for continuous duty since the VFD will modulate speed constantly
Needs to be a 3-phase motor (the VFD converts single-phase household power to 3-phase)
Standard fountain pumps (like those from Aquascape or similar) are typically single-phase AC and won't work with a VFD — you need an industrial-type pump
Water volume:

16–18" deep basin with ~18" diameter holds roughly 15–20 gallons
A 1/2 HP pump can easily circulate that volume
Your MIN_FREQUENCY_PERCENT = 30 in fountain_rms_bass.py:29 prevents the pump from stalling at low speeds — important for keeping water moving
Outdoor/garden concerns:

The Raspberry Pi, DAC, and relay need to be in a weatherproof enclosure (IP65 junction box, ~$15)
The VFD also needs a weatherproof enclosure or to be mounted indoors/in a shed with conduit run to the pump
Run the Bluetooth speaker wirelessly from the Pi — that part already works without extra wiring
Use outdoor-rated cable for the pump motor wiring and the low-voltage DAC signal to the VFD



Electrical:

A 1/2 HP VFD on a standard 120V/15A household circuit is fine
1 HP may need a 240V circuit depending on the VFD — check the specs
As noted in DEPLOYMENT_GUIDE.md:143, have an electrician handle the VFD-to-motor wiring
Software Adjustments You'd Likely Tweak
For a smaller decorative fountain vs. a large memorial fountain, you'd probably want to tune these values in the web interface or fountain_rms_bass.py:

Parameter	Current Default	Garden Fountain Suggestion
MIN_FREQUENCY_PERCENT	30%	25–35% (keep a gentle trickle during quiet parts)
MAX_FREQUENCY_PERCENT	100%	60–80% (100% on 1/2 HP might splash out of an 18" basin)
SMOOTHING_FACTOR	0.2	0.15–0.2 (smoother transitions look better on a small fountain)
BASS_WEIGHT	0.4	0.3–0.4 (less bass emphasis avoids sudden surges that splash)
Bottom Line
A 16–18" copper garden fountain is a great fit. Go with a 1/2 HP 3-phase submersible pump and a matching single-phase-input VFD with 0–10V analog input, put the electronics in a weatherproof box, and the software will work as-is — just tune down MAX_FREQUENCY_PERCENT so you don't splash water out of the basin during loud passages.





# VFD Musical Fountain - Complete Project Files

## 🎵 Three Versions Available - Choose Your Approach

This package contains **three different implementations** of varying complexity. Pick the one that fits your needs!

---

## ⭐ RECOMMENDED: RMS + Bass FFT Analysis

**Files:**
- `fountain_rms_bass.py` - Main script
- `install_rms_bass.sh` - Installation

**How it works:**
```
Audio → Real-time Analysis → Two Parameters:
  1. RMS (60%) = Overall volume/intensity
  2. Bass FFT (40%) = Beat emphasis (20-250 Hz)
→ Combined Intensity → VFD → Pump Speed
```

**Best of both worlds:**
- ✅ Smooth volume following (RMS)
- ✅ Punchy beat response (Bass)
- ✅ No MIDI files needed
- ✅ Works with any MP3/FLAC
- ✅ Sophisticated but not complex

**Perfect for:** Classical music, film scores, jazz - anything with dynamics AND rhythm

**Example:** 
- Quiet string passage → RMS low, Bass low → Gentle flow
- Timpani hits → RMS medium, Bass HIGH → Sudden powerful surge!
- Full orchestra crescendo → RMS high, Bass medium → Strong sustained flow

---

## 📊 Version Comparison

| Feature | Simple RMS | **RMS + Bass** ⭐ | MIDI |
|---------|-----------|----------------|------|
| **Complexity** | Low | Medium | High |
| **Setup Time** | 30 min | 45 min | 2-3 hours |
| **Music Prep** | Just MP3s | Just MP3s | MP3 + MIDI pairs |
| **Analysis Type** | Volume only | Volume + Beat | Full musical structure |
| **CPU Usage** | Very Low | Low | Medium |
| **Beat Response** | None | Excellent | Excellent |
| **Dynamic Range** | Good | Excellent | Excellent |
| **Code Lines** | ~200 | ~330 | ~450 |

---

## 📁 All Files Explained

### RMS + Bass Version (RECOMMENDED) ⭐
- `fountain_rms_bass.py` - Dual-parameter analysis
- `install_rms_bass.sh` - Installation script
- **Uses:** ffmpeg for decoding, numpy for FFT

### Simple RMS Version
- `fountain_simple_vfd.py` - Volume-only analysis  
- `install_simple.sh` - Installation script
- `README_SIMPLE.md` - Documentation
- **Uses:** sox for RMS calculation

### Full MIDI Version
- `fountain_vfd_controller.py` - MIDI parsing + audio
- `install_vfd.sh` - Installation script
- `VFD_SETUP_GUIDE.md` - Complete guide
- **Uses:** mido for MIDI, synchronized playback

### Documentation & Support
- `README.md` - Main project overview
- `VFD_SETUP_GUIDE.md` - Complete installation guide (23 pages)
- `VFD_WIRING_DIAGRAM.txt` - Detailed wiring
- `SHOPPING_LIST.md` - Parts with prices and links

---

## 🎯 Which Version Should You Use?

### Use **RMS + Bass** if: ⭐
- Want smooth volume tracking + beat emphasis
- Have classical music, jazz, or film scores
- Don't want to deal with MIDI files
- Want professional results with reasonable complexity

### Use **Simple RMS** if:
- Want absolute simplest approach
- Only care about volume, not beat
- Have very limited CPU/resources
- Music has no strong rhythmic elements

### Use **Full MIDI** if:
- Need bass vs treble distinction
- Want note velocity and orchestration awareness
- Willing to create/find MIDI files
- Want perfect pre-choreographed control

---

## 🚀 Quick Start (RMS + Bass - Recommended)

```bash
# 1. Upload files to Raspberry Pi
scp fountain_rms_bass.py install_rms_bass.sh pi@[PI_IP]:~

# 2. Run installation
ssh pi@[PI_IP]
chmod +x install_rms_bass.sh
sudo ./install_rms_bass.sh

# 3. Follow prompts for Bluetooth, Samba, etc.

# 4. Add music via network
# Windows: \\[PI_IP]\FountainMusic
# Mac: smb://[PI_IP]/FountainMusic

# 5. Turn fountain on and watch it dance!
```

---

## 🎛️ Configuration (RMS + Bass)

Edit `/home/pi/fountain_rms_bass.py`:

```python
# Line 14: Pump speed range
MIN_FREQUENCY_PERCENT = 30   # Min speed (30% of max)
MAX_FREQUENCY_PERCENT = 100  # Max speed (full power)
SMOOTHING_FACTOR = 0.2       # Response speed (0.1-0.5)

# Line 21-22: Bass frequency range
BASS_LOW_FREQ = 20    # Lower bound (Hz)
BASS_HIGH_FREQ = 250  # Upper bound (Hz)

# Line 24-25: Intensity mixing
RMS_WEIGHT = 0.6   # 60% from overall volume
BASS_WEIGHT = 0.4  # 40% from bass energy
```

**After editing:** `sudo systemctl restart fountain-vfd`

---

## 📊 Understanding the Parameters

### RMS (Root Mean Square)
- Measures average audio amplitude
- Represents overall "loudness"
- Smooth, follows dynamics naturally
- Good for: String swells, vocal dynamics, crescendos

### Bass FFT (20-250 Hz)
- Fast Fourier Transform on low frequencies
- Detects kick drums, bass notes, timpani
- Punchy, emphasizes rhythm
- Good for: Percussion hits, dramatic moments

### Combined:
```
Intensity = (RMS × 60%) + (Bass × 40%)
```

**Example Scenario:**
1. **Quiet violins** → RMS: 20%, Bass: 5% → Total: 14% → Gentle trickle
2. **Timpani hit!** → RMS: 40%, Bass: 95% → Total: 62% → SURGE!
3. **Full orchestra** → RMS: 85%, Bass: 60% → Total: 75% → Strong flow
4. **Fade to silence** → RMS: 5%, Bass: 2% → Total: 4% → Minimal flow

---

## 💻 Hardware Requirements

Same for all versions:

**Essential (~$230-400):**
- VFD (1 HP, 0-10V input): $180-300
  - Hitachi WJ200, ABB ACS355, or Delta VFD007E21A
- MCP4725 DAC module: $8-12
- 5V relay module: $5-8
- Jumper wires + cable: $15-30

**Client Should Have:**
- Raspberry Pi 3
- 1 HP Synchronous Motor with pump
- Bluetooth speakers
- Fountain with power switch

See `SHOPPING_LIST.md` for detailed specs and links.

---

## ⚡ Safety Reminders

### Electrician Required:
- VFD installation and wiring
- Motor connections
- AC power work
- All electrical code compliance

### You Can Do:
- Raspberry Pi setup
- Low-voltage Pi wiring
- Software installation
- Music management

**NEVER work on high voltage unless you're a licensed electrician.**

---

## 📝 Example Log Output (RMS + Bass)

```
2024-12-14 02:00:00 - INFO - Fountain turned ON
2024-12-14 02:00:00 - INFO - Found 12 music files
2024-12-14 02:00:00 - INFO - Selected: beethoven_symphony_5.mp3
2024-12-14 02:00:00 - INFO - Starting audio analysis (RMS + Bass FFT)
2024-12-14 02:00:02 - INFO - RMS: 0.234 | Bass: 0.156 | Intensity: 20.3%
2024-12-14 02:00:04 - INFO - RMS: 0.445 | Bass: 0.523 | Intensity: 47.6%
2024-12-14 02:00:06 - INFO - RMS: 0.678 | Bass: 0.892 | Intensity: 76.4%
2024-12-14 02:00:08 - INFO - RMS: 0.523 | Bass: 0.234 | Intensity: 40.7%
```

You can **see** how both parameters contribute to the total intensity!

---

## 🔧 Troubleshooting

### FFT Analysis Errors
```bash
# Check ffmpeg installed
ffmpeg -version

# Check numpy installed
python3 -c "import numpy; print(numpy.__version__)"

# Test audio decoding manually
ffmpeg -i your_song.mp3 -f s16le -ar 22050 -ac 1 test.pcm
```

### No Bass Response
- Increase `BASS_WEIGHT` (try 0.6)
- Lower `BASS_HIGH_FREQ` to 200 Hz
- Check music has bass content (some classical pieces are treble-heavy)

### Too Jerky/Reactive
- Decrease `SMOOTHING_FACTOR` to 0.1
- Increase `RMS_WEIGHT` to 0.8
- Decrease `BASS_WEIGHT` to 0.2

### Too Sluggish
- Increase `SMOOTHING_FACTOR` to 0.4
- Increase `BASS_WEIGHT` to 0.6

---

## 🎼 Music Recommendations

**Best Performance:**
- Beethoven symphonies (great dynamics + strong bass)
- Tchaikovsky (dramatic, rhythmic)
- Stravinsky (punchy, percussive)
- Film scores (Hans Zimmer, John Williams)
- Jazz with upright bass

**Good:**
- Mozart, Haydn (lighter textures)
- Chamber music with contrast
- Baroque with harpsichord/organ

**Less Ideal:**
- Renaissance vocal music (limited dynamics)
- Heavily compressed pop/rock
- Ambient/minimalist

---

## 🌟 Why RMS + Bass is the Sweet Spot

**Too Simple:** RMS-only misses rhythmic emphasis  
**Too Complex:** MIDI requires file preparation  
**Just Right:** RMS + Bass captures both smooth dynamics and punchy beats

It's like having a smart audio engineer adjusting the fountain in real-time:
- "Overall volume controls the baseline"
- "But give extra oomph when the drums hit!"

**Result:** Natural, musical response that works with any audio file.

---

## 📞 Getting Help

**Software/Analysis Issues:**
- Check logs: `sudo journalctl -u fountain-vfd -f`
- Test FFT: `python3 -c "import numpy; numpy.fft.rfft([1,2,3,4])"`
- Raspberry Pi forums

**Electrical/VFD Issues:**
- Licensed electrician
- VFD manufacturer support

**Music/Tuning:**
- Adjust weights in config file
- Test with different musical styles
- Share logs to see RMS vs Bass values

---

## 🏆 Final Recommendation

Start with **RMS + Bass version** (`fountain_rms_bass.py`).

It gives you:
✅ Professional results  
✅ No MIDI headaches  
✅ Tunable parameters  
✅ Beat-responsive water  
✅ Natural musical flow  

If it's not responsive enough, tweak the weights. If it's too complex, fall back to simple RMS. If you want more sophistication, move to MIDI.

But for 90% of installations, **RMS + Bass is perfect**.

---

**Ready to build? Run `install_rms_bass.sh` and make some waves!** 🎵💧
