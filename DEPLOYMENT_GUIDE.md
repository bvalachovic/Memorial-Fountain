# Remote Deployment & Update Strategy

## Overview - Hand-Off Ready System

This guide sets up a **production-ready deployment** where:

1. ✅ **Initial Setup** - You configure everything, test it works
2. ✅ **Hand-Off** - Give Pi to fountain installer, they just plug it in
3. ✅ **Remote Updates** - You can push fixes from anywhere via GitHub
4. ✅ **Auto-Deploy** - Pi pulls updates automatically (configurable)
5. ✅ **Rollback** - Can revert to previous version if needed

---

## Deployment Architecture

```
Your Computer                    GitHub                     Raspberry Pi
─────────────                    ──────                     ────────────
                                                           
fountain_rms_bass.py  ──push──►  Repository  ──pull──►   /opt/fountain/
(local changes)                  (version control)        (running code)
                                                                │
                                                                ▼
                                                          Auto-update
                                                          on boot/daily
                                                                │
                                                                ▼
                                                          Service restarts
                                                          with new code
```

---

## Phase 1: Initial Setup (You Do This Once)

### 1. Create GitHub Repository

```bash
# On GitHub.com:
# 1. Create new repository: "vfd-fountain" (or any name)
# 2. Keep it private (recommended) or public
# 3. Don't initialize with README (we'll push code)
# 4. Note the repository URL: https://github.com/yourusername/vfd-fountain.git
```

### 2. Set Up Pi for GitHub Deployment

```bash
# SSH into your Pi
ssh pi@[PI_IP]

# Run GitHub setup script
chmod +x setup_github.sh
sudo ./setup_github.sh

# It will ask for:
# - GitHub repository URL
# - Auto-update preference (choose option 1 or 2)
```

**Choose auto-update option:**
- **Option 1 (RECOMMENDED):** Updates only when Pi reboots
  - You control when updates deploy
  - Installer reboots Pi, new code loads
  - Safer, more predictable

- **Option 2:** Updates on boot + checks daily
  - Automatic updates within 24 hours
  - Good for critical bug fixes
  - More aggressive

- **Option 3:** Manual only
  - Must SSH in and run `sudo fountain-update`
  - For testing/development

### 3. Push Code to GitHub

```bash
# On your Pi (or local computer):
cd /opt/fountain

# Initialize git (if not already done)
git init
git add .
git commit -m "Initial fountain controller code"

# Connect to GitHub
git remote add origin https://github.com/yourusername/vfd-fountain.git
git branch -M main

# Push code
git push -u origin main
```

**Note:** You'll need a GitHub personal access token for authentication:
- GitHub → Settings → Developer settings → Personal access tokens
- Generate token with "repo" permissions
- Use token as password when pushing

### 4. Test the Deployment

```bash
# Make a small test change
echo "# Test deployment" >> /opt/fountain/README.md
git add README.md
git commit -m "Test: verify deployment works"
git push

# On Pi, manually trigger update to test
sudo fountain-update

# Check it worked
sudo fountain-version
```

---

## Phase 2: Hand-Off to Installer

### What the Installer Gets

**Physical:**
- Raspberry Pi (fully configured)
- Power supply
- SD card (with all software installed)

**Digital (optional, via USB stick or email):**
- `INSTALLER_GUIDE.md` - Simple connection instructions
- Wiring diagrams
- Your contact info

### Installer Instructions (Simple!)

```
FOUNTAIN INSTALLER - QUICK START
═════════════════════════════════

1. Plug in Pi power supply
2. Wait 2 minutes for boot and update check
3. Connect DAC to Pi (pre-wired if possible)
4. Connect Relay to Pi (pre-wired if possible)
5. Tell electrician: "Connect DAC output to VFD analog input"
6. Turn fountain on - music should play!

LED Indicators:
- Pi red LED: Power (should be solid)
- Pi green LED: Activity (should blink during boot)

Troubleshooting:
- No power: Check power supply
- No music: Check Bluetooth speakers paired
- No water response: Check VFD analog input connection

Support: [Your phone/email]
```

### Pre-Installation Checklist

Before handing off Pi:

```bash
# Verify everything works
sudo systemctl status fountain-vfd    # Should be "active (running)"
sudo fountain-version                  # Shows current version
sudo journalctl -u fountain-vfd -n 50 # Check logs look good

# Test GPIO (with relay connected)
gpio -g read 17                        # Returns 0 or 1

# Test DAC
sudo i2cdetect -y 1                    # Shows device at 0x60 or 0x62

# Test Bluetooth
bluetoothctl devices                   # Shows paired speaker

# Test music directory
ls -l /home/pi/music/                  # Contains MP3 files

# Test network share
# From another computer: \\[PI_IP]\FountainMusic
```

All green? **Ready to hand off!**

---

## Phase 3: Remote Updates (After Hand-Off)

### Scenario: You Need to Fix Something

**Example:** Fountain installer calls: "The pump seems too aggressive in quiet parts"

**Your fix process:**

```bash
# On your computer (not the Pi):

# 1. Clone the repository (if you haven't already)
git clone https://github.com/yourusername/vfd-fountain.git
cd vfd-fountain

# 2. Make the fix
nano fountain_rms_bass.py
# Change: MIN_FREQUENCY_PERCENT = 30
# To:     MIN_FREQUENCY_PERCENT = 25

# 3. Commit the change
git add fountain_rms_bass.py
git commit -m "Fix: Lower minimum pump speed from 30% to 25%"

# 4. Push to GitHub
git push

# 5. Tell installer:
#    "Please reboot the Pi - the fix will deploy automatically"
```

**That's it!** Next time Pi boots, it pulls the update and restarts the service.

### Update Log

The Pi keeps a log of all updates:

```bash
# On Pi, check update history:
sudo tail -f /var/log/fountain_update.log

# Example output:
2024-12-14 10:00:00: Starting fountain update
2024-12-14 10:00:05: Update available: abc123 -> def456
2024-12-14 10:00:10: Code updated successfully
2024-12-14 10:00:15: Service restarted
```

---

## Available Commands (On the Pi)

### Check Version & Status

```bash
# See current version
sudo fountain-version

# Output:
# Current Version:
#   Commit: abc123def456...
#   Date: Fri Dec 13 15:30:00 2024
#   Message: Fix: Lower minimum pump speed
# 
# Status: ✓ Up to date
```

### Manual Update

```bash
# Force an update check right now
sudo fountain-update

# Returns immediately if up to date
# Or pulls new code and restarts service
```

### Rollback (Undo Update)

```bash
# If new version has problems
sudo fountain-rollback

# Shows recent versions:
# abc123 Fix: Lower minimum pump speed
# def456 Update: Adjust bass weights
# ...
#
# Enter commit hash to rollback to: def456

# Reverts to that version and restarts
```

### View Update Logs

```bash
# See what updates have happened
sudo cat /var/log/fountain_update.log

# Watch live
sudo tail -f /var/log/fountain_update.log
```

---

## Update Workflow Examples

### Example 1: Tune Audio Parameters

**Situation:** Bass response too strong

```bash
# On your computer:
cd vfd-fountain
nano fountain_rms_bass.py

# Change:
BASS_WEIGHT = 0.4  # to
BASS_WEIGHT = 0.3

git commit -am "Tune: Reduce bass weight to 30%"
git push

# Tell installer: "Reboot Pi for update"
```

### Example 2: Add Logging

**Situation:** Need more debug info

```bash
# On your computer:
cd vfd-fountain
nano fountain_rms_bass.py

# Add more logging statements
logging.info(f"VFD voltage: {vfd.get_voltage():.2f}V")

git commit -am "Debug: Add VFD voltage logging"
git push

# Auto-deploys on next Pi boot
```

### Example 3: Emergency Bug Fix

**Situation:** Critical bug, needs immediate fix

```bash
# On your computer:
cd vfd-fountain
nano fountain_rms_bass.py
# Fix the bug

git commit -am "Hotfix: Fix crash in bass analysis"
git push

# Call installer: "Critical update - please reboot Pi ASAP"
# Or if daily updates enabled: Deploys within 24 hours
```

---

## Best Practices

### Version Control Hygiene

**Good commit messages:**
```bash
git commit -m "Fix: Lower minimum speed to prevent stalling"
git commit -m "Tune: Increase smoothing factor for gentler response"
git commit -m "Feature: Add emergency stop on GPIO 18"
git commit -m "Debug: Add bass frequency logging"
```

**Bad commit messages:**
```bash
git commit -m "stuff"
git commit -m "more changes"
git commit -m "asdf"
```

### Testing Before Push

```bash
# Always test changes locally first!

# Option 1: Test on your computer
python3 test_fountain.py test_music/beethoven.mp3

# Option 2: Test on a spare Pi
# (if you have one)

# Option 3: Create a dev branch
git checkout -b dev
# Make changes, test
git checkout main
git merge dev  # Only if tests pass
git push
```

### Branch Strategy (Advanced)

```bash
# Main branch = production (what's on Pi)
git checkout main

# Create feature branch
git checkout -b feature/improve-bass-detection

# Make changes, test
git commit -am "Improve bass frequency detection"

# Merge when ready
git checkout main
git merge feature/improve-bass-detection
git push

# Pi pulls from main branch only
```

---

## Troubleshooting Deployment

### Update Not Deploying

```bash
# On Pi:
sudo fountain-version
# Check if it sees the update

# Manually trigger update
sudo fountain-update

# Check logs
sudo journalctl -u fountain-autoupdate -n 50
```

### Git Authentication Issues

```bash
# On Pi:
cd /opt/fountain

# Fix remote URL to use token
git remote set-url origin https://YOUR_TOKEN@github.com/yourusername/vfd-fountain.git

# Or use SSH keys (more secure)
# Generate key on Pi:
ssh-keygen -t ed25519
# Add public key to GitHub settings
```

### Service Not Restarting After Update

```bash
# Check service status
sudo systemctl status fountain-vfd

# Manually restart
sudo systemctl restart fountain-vfd

# Check for errors
sudo journalctl -u fountain-vfd -n 100
```

---

## Alternative: USB Update (No Internet)

If installer location has no internet:

```bash
# On your computer:
# 1. Make changes
# 2. Copy files to USB stick

# On Pi:
# 1. Insert USB stick
# 2. Copy files
sudo cp /media/pi/USB/fountain_rms_bass.py /opt/fountain/
sudo systemctl restart fountain-vfd

# Works but loses version control benefits
```

---

## Security Considerations

### Keep Repository Private

**Recommended:** Private GitHub repository
- Contains your client's custom code
- Installation details
- Configuration

**If public:** Remove any:
- IP addresses
- WiFi passwords
- Client-specific information

### Pi Security

```bash
# Change default password
passwd

# Disable SSH after deployment (optional)
sudo systemctl disable ssh

# Or restrict SSH to specific IPs
# Edit /etc/ssh/sshd_config
```

---

## Handoff Checklist

**Before giving Pi to installer:**

- [ ] Code pushed to GitHub
- [ ] Auto-update configured and tested
- [ ] All services enabled and running
- [ ] Bluetooth speakers paired
- [ ] Music files added
- [ ] Network share working
- [ ] Test fountain detection (with relay)
- [ ] Test DAC output (with multimeter)
- [ ] Update log clean, no errors
- [ ] Installer guide written
- [ ] Your contact info provided
- [ ] Backup SD card image created (optional but smart!)

**Backup SD Card:**
```bash
# On your computer (Mac/Linux):
sudo dd if=/dev/sdX of=fountain-backup.img bs=4M

# Later restore if needed:
sudo dd if=fountain-backup.img of=/dev/sdX bs=4M
```

---

## Summary: Why This Is Great

✅ **Installer-Friendly:** Just plug in and it works  
✅ **Maintainable:** You can fix issues remotely  
✅ **Safe:** Updates deploy on reboot (controlled timing)  
✅ **Reversible:** Easy rollback if needed  
✅ **Logged:** Full audit trail of changes  
✅ **Professional:** Proper version control  
✅ **Scalable:** Same process for multiple installations  

**Result:** You can support the installation remotely without site visits!

---

## Quick Command Reference

```bash
# On Pi - Check & Update
sudo fountain-version      # Check current version
sudo fountain-update       # Pull latest code
sudo fountain-rollback     # Revert to old version

# On Pi - Service Management
sudo systemctl status fountain-vfd
sudo systemctl restart fountain-vfd
sudo journalctl -u fountain-vfd -f

# On Your Computer - Push Updates
git commit -am "Your changes"
git push
# Done! Pi pulls on next boot
```

**That's it! Professional deployment with minimal installer involvement.** 🚀
