#!/bin/bash
# VFD Musical Fountain with RMS + Bass FFT Analysis
# Installation Script

set -e

echo "===================================================="
echo "VFD Musical Fountain - RMS + Bass Analysis"
echo "===================================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Update system
echo "Step 1: Updating system packages..."
apt-get update

# Install required packages
echo ""
echo "Step 2: Installing required packages..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-rpi.gpio \
    python3-numpy \
    vlc \
    ffmpeg \
    pulseaudio \
    pulseaudio-module-bluetooth \
    bluez \
    bluez-tools \
    samba \
    samba-common-bin \
    i2c-tools \
    python3-smbus \
    portaudio19-dev \
    python3-pyaudio

# Enable I2C for DAC communication
echo ""
echo "Step 3: Enabling I2C interface..."
raspi-config nonint do_i2c 0

# Install Python libraries
echo ""
echo "Step 4: Installing Python libraries..."
pip3 install --break-system-packages adafruit-circuitpython-mcp4725 pyaudio

# Enable Bluetooth
echo ""
echo "Step 5: Enabling Bluetooth services..."
systemctl enable bluetooth
systemctl start bluetooth

# Setup music directory
echo ""
echo "Step 6: Creating music directory..."
mkdir -p /home/pi/music
chown pi:pi /home/pi/music

# Create README
cat > /home/pi/music/README.txt << 'EOF'
MUSIC FOLDER - RMS + BASS ANALYSIS
===================================

Drop your music files here!

Supported formats:
- MP3 (.mp3)
- M4A (.m4a)
- FLAC (.flac)
- WAV (.wav)
- OGG (.ogg)

The system analyzes TWO parameters:

1. RMS (Root Mean Square) - Overall volume/intensity
   - Smooth, follows dynamics
   - Quiet passages = gentle flow
   - Loud passages = strong flow

2. Bass Energy (FFT 20-250 Hz) - Beat emphasis
   - Punchy, follows rhythm
   - Strong bass = extra boost
   - Kick drums and bass notes emphasized

Combined: RMS (60%) + Bass (40%) = Total Pump Intensity

Works best with:
- Classical music with dynamics
- Film scores
- Jazz
- Music with strong bass/rhythm

To adjust weighting, edit:
/home/pi/fountain_rms_bass.py
Lines 24-25: RMS_WEIGHT and BASS_WEIGHT
EOF

chown pi:pi /home/pi/music/README.txt

# Copy Python script
echo ""
echo "Step 7: Installing Python script..."
cp fountain_rms_bass.py /home/pi/fountain_rms_bass.py
chmod +x /home/pi/fountain_rms_bass.py
chown pi:pi /home/pi/fountain_rms_bass.py

# Install systemd service
echo ""
echo "Step 8: Installing systemd service..."
cat > /etc/systemd/system/fountain-vfd.service << 'EOF'
[Unit]
Description=VFD Musical Fountain Controller (RMS + Bass)
After=network.target sound.target bluetooth.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi
ExecStart=/usr/bin/python3 /home/pi/fountain_rms_bass.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable fountain-vfd.service

# Setup Samba for network file sharing
echo ""
echo "Step 9: Configuring Samba file sharing..."

# Backup original smb.conf
if [ -f /etc/samba/smb.conf ]; then
    cp /etc/samba/smb.conf /etc/samba/smb.conf.backup
fi

# Add music share
cat >> /etc/samba/smb.conf << 'EOF'

[FountainMusic]
   comment = Fountain Music Files
   path = /home/pi/music
   browseable = yes
   read only = no
   create mask = 0775
   directory mask = 0775
   valid users = pi
EOF

systemctl restart smbd

echo ""
echo "===================================================="
echo "Installation Complete!"
echo "===================================================="
echo ""
echo "SYSTEM FEATURES:"
echo "  ✓ RMS analysis for overall volume (60%)"
echo "  ✓ Bass FFT (20-250 Hz) for beat emphasis (40%)"
echo "  ✓ Combined intensity control"
echo ""
echo "NEXT STEPS:"
echo ""
echo "1. Set Samba password:"
echo "   sudo smbpasswd -a pi"
echo ""
echo "2. Pair Bluetooth speakers:"
echo "   bluetoothctl"
echo "   (power on, scan on, pair, trust, connect)"
echo ""
echo "3. Set Bluetooth as default audio:"
echo "   pactl set-default-sink [BLUETOOTH_SINK_NAME]"
echo ""
echo "4. Wire hardware:"
echo "   - Relay: VCC→Pin2, GND→Pin6, SIG→Pin11"
echo "   - DAC: VCC→Pin1, GND→Pin9, SDA→Pin3, SCL→Pin5"
echo "   - DAC OUT → VFD Analog Input"
echo ""
echo "5. Add music files:"
echo "   Access: \\\\[PI_IP]\\FountainMusic"
echo "   Drop MP3/FLAC files"
echo ""
echo "6. Start service:"
echo "   sudo systemctl start fountain-vfd"
echo ""
echo "7. Check logs (you'll see RMS + Bass values):"
echo "   sudo journalctl -u fountain-vfd -f"
echo ""
echo "TUNING:"
echo "  Edit /home/pi/fountain_rms_bass.py to adjust:"
echo "  - RMS_WEIGHT (line 24): Currently 60%"
echo "  - BASS_WEIGHT (line 25): Currently 40%"
echo "  - BASS_LOW_FREQ/BASS_HIGH_FREQ (lines 21-22)"
echo "  - SMOOTHING_FACTOR (line 14)"
echo ""
echo "  Then: sudo systemctl restart fountain-vfd"
echo ""
