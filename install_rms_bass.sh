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
MUSIC_USER=${SUDO_USER:-pi}
MUSIC_DIR="/home/${MUSIC_USER}/music"
mkdir -p "$MUSIC_DIR"
chown "${MUSIC_USER}:${MUSIC_USER}" "$MUSIC_DIR"
echo "Music directory: $MUSIC_DIR"

# Copy scripts
echo ""
echo "Step 7: Installing scripts..."
INSTALL_DIR="/home/${MUSIC_USER}/Memorial-Fountain"
mkdir -p "${INSTALL_DIR}/drivers"
cp fountain_controller.py "${INSTALL_DIR}/fountain_controller.py"
cp drivers/l298n_driver.py "${INSTALL_DIR}/drivers/l298n_driver.py"
cp drivers/vfd_driver.py "${INSTALL_DIR}/drivers/vfd_driver.py"
cp drivers/__init__.py "${INSTALL_DIR}/drivers/__init__.py"
cp fountain_config.json "${INSTALL_DIR}/fountain_config.json"
chown -R "${MUSIC_USER}:${MUSIC_USER}" "$INSTALL_DIR"

# Install systemd service
echo ""
echo "Step 8: Installing systemd service..."
cat > /etc/systemd/system/fountain-vfd.service << EOF
[Unit]
Description=Memorial Fountain Controller
After=network.target sound.target bluetooth.target

[Service]
Type=simple
User=${MUSIC_USER}
WorkingDirectory=${INSTALL_DIR}
ExecStart=/usr/bin/python3 ${INSTALL_DIR}/fountain_controller.py
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
echo "4. Set config to production mode:"
echo "   nano ${INSTALL_DIR}/fountain_config.json"
echo "   Set: \"driver\": \"vfd\"       (when VFD is installed)"
echo "   Set: \"auto_start\": false    (wait for GPIO fountain trigger)"
echo ""
echo "5. Add music files:"
echo "   Access: \\\\[PI_IP]\\FountainMusic"
echo "   Drop MP3/FLAC/WAV files into the share"
echo ""
echo "6. Start service:"
echo "   sudo systemctl start fountain-vfd"
echo ""
echo "7. Check logs:"
echo "   sudo journalctl -u fountain-vfd -f"
echo ""
echo "TUNING:"
echo "  Edit ${INSTALL_DIR}/fountain_config.json to adjust:"
echo "  - rms_weight (default 0.6 = 60%)"
echo "  - bass_weight (default 0.4 = 40%)"
echo "  - min/max_frequency_percent"
echo "  - smoothing_factor"
echo ""
echo "  Then: sudo systemctl restart fountain-vfd"
echo ""
echo "See TEST_INSTRUCTIONS.md for prototype vs production details."
echo ""
