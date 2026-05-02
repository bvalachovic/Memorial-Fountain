# Testing & Deployment Instructions

Three scenarios are covered here. Read the one that matches your situation.

---

## Scenario 1: Prototype testing on the Pi (L298N + pump)

This is the current active setup. Use this when you want to test real hardware.

**You do NOT need to run the install script. You do NOT need to reboot.**

### Steps

```bash
# 1. On the Pi — pull the latest code
cd ~/Memorial-Fountain
git pull

# 2. Install Python dependencies (first time only)
pip3 install --break-system-packages adafruit-circuitpython-mcp4725 numpy

# 3. Make sure ffmpeg and VLC are installed (first time only)
sudo apt install ffmpeg vlc -y

# 4. Confirm I2C is enabled (first time only — required for MCP4725)
sudo raspi-config
# → Interface Options → I2C → Enable → reboot once, then come back

# 5. Add music files to the music directory
ls /home/bvalachovic/music
# Must have at least one .mp3 / .flac / .wav / .m4a / .ogg file

# 6. Run the controller
python3 fountain_controller.py
```

The pump should start within a few seconds. Log output goes to the console
and to `/var/log/fountain.log`.

To stop: **Ctrl+C**

### What the config should look like for prototype testing

`fountain_config.json` (these are already the defaults — do not change):

```json
{
  "driver": "l298n",
  "auto_start": true,
  ...
}
```

- `driver: "l298n"` — uses the L298N H-bridge driver (`drivers/l298n_driver.py`)
- `auto_start: true` — music starts immediately when the script runs, no GPIO trigger needed

### Prototype wiring reference (wire colors)

| Color  | From              | To             | Purpose                   |
| ------ | ----------------- | -------------- | ------------------------- |
| Gray   | Pi pin 1 (3.3V)   | MCP4725 VCC    | DAC power                 |
| White  | Pi pin 3 (SDA)    | MCP4725 SDA    | I2C data                  |
| Black  | Pi pin 5 (SCL)    | MCP4725 SCL    | I2C clock                 |
| Purple | Pi pin 6 (GND)    | MCP4725 GND    | Ground                    |
| Blue   | MCP4725 OUT       | L298N ENA      | Latched HIGH (always on)  |
| Red    | Pi pin 12 GPIO 18 | L298N IN1      | PWM speed control         |
| Brown  | Pi pin 14 (GND)   | L298N IN2      | Fixed LOW (one direction) |
| —      | L298N OUT1        | Pump Red (+)   | Motor positive            |
| —      | L298N OUT2        | Pump Black (−) | Motor negative            |

### Troubleshooting prototype

**ERRNO 5 / I2C error on startup**
I2C is not enabled. Run `sudo raspi-config` → Interface Options → I2C → Enable, reboot.

**"No music files found"**
Check `/home/bvalachovic/music` exists and has audio files.
Update `music_dir` in `fountain_config.json` if the path differs.

**Pump does not spin**

- Confirm I2C is enabled and the MCP4725 is wired correctly (Gray/White/Black/Purple)
- Check the log for DAC errors: `cat /var/log/fountain.log`
- Confirm IN1 (Red wire) is on Pi physical pin 12

**L298N gets hot**
This happens if the Blue wire (MCP4725 OUT → ENA) is at an intermediate voltage
instead of fully HIGH. The code sets the DAC to maximum on startup to prevent this.
If it still happens, check the Blue wire connection.

---

## Scenario 2: PC simulation (Windows / Mac — no hardware needed)

Use this to preview audio analysis and tune parameters without needing the Pi.
No hardware, no Pi libraries required. Runs on Windows or Mac.

```bash
# Single file
python test_fountain.py test_music/beethoven01.mp3

# All files in the test_music folder
python test_fountain.py --all

# Custom music directory
python test_fountain.py --dir C:\Users\you\Music --all
```

You will see a live bar chart of RMS, bass, and intensity values in the terminal.
Use this to tune `rms_weight` and `bass_weight` in `fountain_config.json` before
deploying to the Pi.

### Dependencies (Windows)

```bash
pip install numpy
# Also need ffmpeg on PATH — download from ffmpeg.org
```

---

## Scenario 3: Production deployment (automatic start at Pi boot)

Use this when the fountain is permanently installed and should run hands-free.
The script starts automatically when the Pi boots and waits for the fountain
power switch (GPIO pin 17) to go HIGH before playing music.

### Production setup steps

```bash
# 1. Clone the repo to the Pi (one time)
cd ~
git clone https://github.com/bvalachovic/Memorial-Fountain.git
cd Memorial-Fountain

# 2. Set config to production mode
nano fountain_config.json
# Change: "driver": "vfd"       (when VFD hardware is installed)
# Change: "auto_start": false   (wait for GPIO trigger)

# 3. Run the install script (installs dependencies + systemd service)
sudo ./install_rms_bass.sh

# 4. Start the service (or reboot)
sudo systemctl start fountain-vfd
sudo systemctl status fountain-vfd

# Check logs
sudo journalctl -u fountain-vfd -f
```

### How production auto-start works

```
Pi boots
  → systemd starts fountain_controller.py automatically
  → script monitors GPIO pin 17 (fountain_pin in config)
  → someone switches on the fountain power → GPIO 17 goes HIGH
  → music starts + pump speed controlled by audio
  → fountain switches off → GPIO 17 goes LOW → music stops
```

### Switching back to prototype mode after production install

```bash
# Edit config
nano fountain_config.json
# Set: "driver": "l298n"
# Set: "auto_start": true

# Stop the service so it doesn't conflict with manual runs
sudo systemctl stop fountain-vfd

# Run manually
python3 fountain_controller.py
```

---

## Config reference

All settings live in `fountain_config.json` at the repo root.

| Key | Prototype default | Production | Description |
| --- | --- | --- | --- |
| `driver` | `"l298n"` | `"vfd"` | Which motor driver to use |
| `auto_start` | `true` | `false` | Start immediately vs wait for GPIO |
| `music_dir` | `"/home/bvalachovic/music"` | same | Where music files live on the Pi |
| `fountain_pin` | `17` | `17` | GPIO pin for fountain-on trigger |
| `min_frequency_percent` | `30` | `30` | Minimum pump speed |
| `max_frequency_percent` | `100` | `100` | Maximum pump speed |
| `rms_weight` | `0.6` | `0.6` | Volume contribution to intensity |
| `bass_weight` | `0.4` | `0.4` | Bass beat contribution to intensity |
