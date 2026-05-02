# Memorial Fountain Controller

A Raspberry Pi system that plays music and drives a water pump in sync with audio dynamics —
using RMS volume and bass FFT to modulate pump speed in real time.

---

## Project status

**Currently in prototype stage.** The Pi controls an L298N H-bridge driving a small
aquarium pump. The production version will use a VFD (Variable Frequency Drive) and
3-phase pump motor. The code supports both via a swappable driver layer.

---

## Quick start

### On the Raspberry Pi (prototype — L298N)

> **Prerequisite:** I2C must be enabled on the Pi or the MCP4725 DAC will fail.
> Run `sudo raspi-config` → Interface Options → I2C → Enable, then reboot.

```bash
# fountain_config.json defaults to: "driver": "l298n", "auto_start": true
python3 fountain_controller.py
```

### On Windows / Mac (no hardware — simulation only)

```bash
python test_fountain.py test_music/beethoven01.mp3
# or test all files
python test_fountain.py --all
```

---

## Repo layout

```text
fountain_controller.py    Main Pi script (works with both hardware targets)
fountain_config.json      Active configuration — edit this to change behavior
drivers/
  l298n_driver.py         Prototype: L298N H-bridge + aquarium pump
  vfd_driver.py           Production: MCP4725 DAC → VFD → 3-phase motor
test_fountain.py          PC simulation — no hardware required
test_music/               Sample audio files for testing
archive/
  fountain_rms_bass.py    Original single-file VFD script (reference only)
web/                      Web interface experiment (parked for later)
CLAUDE.md                 Instructions for AI agents working in this repo
```

---

## Hardware

### Prototype test rig (current)

| Component | Details |
| --- | --- |
| Pi | Raspberry Pi (any model with I2C + GPIO) |
| Motor driver | L298N H-bridge |
| Pump | DIANN AD20P-1230A, 12V DC brushless aquarium pump |
| DAC | MCP4725 (used to latch L298N ENA permanently HIGH) |

**Wire colors:**

| Color | From | To | Purpose |
| --- | --- | --- | --- |
| Gray | Pi pin 1 (3.3V) | MCP4725 VCC | DAC power |
| White | Pi pin 3 (SDA) | MCP4725 SDA | I2C data |
| Black | Pi pin 5 (SCL) | MCP4725 SCL | I2C clock |
| Purple | Pi pin 6 (GND) | MCP4725 GND | Ground |
| Blue | MCP4725 OUT | L298N ENA | Latched HIGH (enables L298N) |
| Red | Pi pin 12 (GPIO 18) | L298N IN1 | PWM speed control |
| Brown | Pi pin 14 (GND) | L298N IN2 | Fixed LOW (one direction) |
| — | L298N OUT1 | Pump Red (+) | Motor positive |
| — | L298N OUT2 | Pump Black (−) | Motor negative |

### Production (future)

| Component | Details |
| --- | --- |
| Pi | Raspberry Pi |
| DAC | MCP4725 → 0–10V analog input on VFD |
| VFD | 1 HP, 0–10V input (Hitachi WJ200, ABB ACS355, or similar) |
| Motor | 1 HP 3-phase synchronous motor + pump |

> VFD installation requires a licensed electrician.

---

## Configuration (fountain_config.json)

| Key | Default | Description |
| --- | --- | --- |
| `driver` | `"l298n"` | `"l298n"` for prototype, `"vfd"` for production |
| `auto_start` | `true` | `true` = run immediately; `false` = wait for GPIO trigger |
| `music_dir` | `"/home/bvalachovic/music"` | Music folder on the Pi |
| `fountain_pin` | `17` | GPIO pin for external fountain-on trigger (auto_start=false only) |
| `min_frequency_percent` | `30` | Minimum pump speed (% — maps to min PWM or DAC) |
| `max_frequency_percent` | `100` | Maximum pump speed |
| `rms_weight` | `0.6` | Volume contribution to intensity (0–1) |
| `bass_weight` | `0.4` | Bass beat contribution to intensity (0–1) |
| `smoothing_factor` | `0.2` | Speed transition smoothing (0.1=slow, 0.5=reactive) |

---

## How it works

```text
Audio file
  → ffmpeg decode to raw PCM
  → RMS (overall loudness)  ×  rms_weight
  → Bass FFT (20–250 Hz)    ×  bass_weight
  → Combined intensity (0–100%)
  → Motor driver (L298N PWM or VFD DAC)
  → Pump speed
```

Quiet strings → gentle trickle. Timpani hit → sudden surge.

---

## Dependencies

```bash
pip install RPi.GPIO adafruit-circuitpython-mcp4725 numpy
sudo apt install ffmpeg vlc
```

Enable I2C on the Pi: `sudo raspi-config` → Interface Options → I2C → Enable.

---

## Music recommendations

Works best with music that has strong dynamics and bass content:

- Beethoven, Tchaikovsky, Stravinsky symphonies
- Film scores (Hans Zimmer, John Williams)
- Jazz with upright bass
