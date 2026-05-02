# CLAUDE.md — Agent Instructions for Memorial Fountain

Read this before touching any file. The repo has two hardware targets and an archived
experiment. Working on the wrong file is wasted effort.

---

## Hardware stages

### Current: Prototype test rig (L298N + aquarium pump)
- Raspberry Pi controls an **L298N H-bridge** motor driver
- Pump: DIANN AD20P-1230A, 12V DC brushless aquarium pump (unidirectional)
- Speed control: software PWM on GPIO 18 via IN1
- The **MCP4725 DAC is present** but used only to latch L298N ENA permanently HIGH
- Wire colors (always use these in comments and instructions):
  - Gray  → MCP4725 VCC  (Pi pin 1, 3.3V)
  - White → MCP4725 SDA  (Pi pin 3, GPIO 2)
  - Black → MCP4725 SCL  (Pi pin 5, GPIO 3)
  - Purple→ MCP4725 GND  (Pi pin 6)
  - Blue  → MCP4725 OUT → L298N ENA (latched max)
  - Red   → L298N IN1   (Pi pin 12, GPIO 18, PWM speed)
  - Brown → L298N IN2   (Pi pin 14, GND, hardwired LOW = fixed direction)

### Future: Production fountain (VFD + 3-phase pump motor)
- MCP4725 DAC → 0–10V analog input on VFD
- VFD drives a 3-phase pump motor
- NOT wired yet — do not modify VFD code for current hardware tests

---

## File map — which file to edit for what

| Task | File |
|---|---|
| Run on Pi (both prototype and production) | `fountain_controller.py` |
| Prototype motor driver (L298N) | `drivers/l298n_driver.py` |
| Production motor driver (VFD/DAC) | `drivers/vfd_driver.py` |
| Switch between drivers | `fountain_config.json` → `"driver": "l298n"` or `"vfd"` |
| Run without hardware (Windows/Mac) | `test_fountain.py` |
| Hardware config (pins, speeds, audio weights) | `fountain_config.json` |
| Web interface experiment (parked) | `web/` folder — leave alone unless working on web UI |
| Old single-file VFD script (archived) | `archive/fountain_rms_bass.py` — do not edit |

---

## Common mistakes to avoid

1. **Do not edit `archive/fountain_rms_bass.py`** — it is the original production VFD
   script kept for reference. All active work goes through `fountain_controller.py`.

2. **Do not edit files in `web/`** unless the task is specifically about the web
   interface. Those files are parked for a future sprint.

3. **Do not try to use the MCP4725 for variable speed control on the L298N.**
   The L298N ENA pin is digital, not analog. Intermediate DAC voltages put its
   transistors in linear mode and cause excessive heat. Speed control is done
   via PWM on IN1 (Red wire, GPIO 18).

4. **`auto_start` in fountain_config.json** — set `true` for prototype testing
   (runs immediately, no GPIO trigger). Set `false` for production (waits for
   fountain_pin to go HIGH before starting music).

5. **I2C must be enabled on the Pi** — run `sudo raspi-config` → Interface Options
   → I2C → Enable. Required for MCP4725 communication.

---

## Running on the Pi

```bash
# Switch to L298N prototype mode (already default)
# fountain_config.json: "driver": "l298n", "auto_start": true

python3 fountain_controller.py

# Switch to production VFD mode when hardware is ready
# fountain_config.json: "driver": "vfd", "auto_start": false
```

## Running simulation on Windows/Mac (no hardware)

```bash
python test_fountain.py test_music/beethoven01.mp3
# or
python test_fountain.py --all
```

---

## Key config options (fountain_config.json)

| Key | Values | Purpose |
|---|---|---|
| `driver` | `"l298n"` / `"vfd"` | Which motor driver to load |
| `auto_start` | `true` / `false` | Start immediately vs wait for GPIO trigger |
| `music_dir` | path string | Where to find music files on the Pi |
| `min_frequency_percent` | 0–100 | Minimum pump speed (maps to min PWM duty or DAC) |
| `max_frequency_percent` | 0–100 | Maximum pump speed |
| `rms_weight` | 0.0–1.0 | How much overall volume drives intensity |
| `bass_weight` | 0.0–1.0 | How much bass beat drives intensity |
