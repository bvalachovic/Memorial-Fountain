#!/bin/bash
# GitHub Deployment Setup for VFD Musical Fountain
# Sets up automatic updates from GitHub repository

set -e

echo "=================================================="
echo "GitHub Deployment Setup"
echo "=================================================="
echo ""

# Configuration
REPO_URL=""  # Will be set during installation
INSTALL_DIR="/opt/fountain"
SERVICE_USER="pi"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Get GitHub repository URL
echo "Enter your GitHub repository URL:"
echo "Example: https://github.com/yourusername/vfd-fountain.git"
read -p "Repository URL: " REPO_URL

if [ -z "$REPO_URL" ]; then
    echo "Error: Repository URL required"
    exit 1
fi

# Install git if not present
echo ""
echo "Installing git..."
apt-get update
apt-get install -y git

# Create installation directory
echo ""
echo "Creating installation directory: $INSTALL_DIR"
mkdir -p $INSTALL_DIR
cd $INSTALL_DIR

# Clone or update repository
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "Repository already exists, updating..."
    git pull origin main || git pull origin master
else
    echo "Cloning repository..."
    git clone $REPO_URL .
fi

# Make scripts executable
chmod +x *.sh 2>/dev/null || true
chmod +x *.py 2>/dev/null || true

# Create update script
cat > /usr/local/bin/fountain-update << 'UPDATESCRIPT'
#!/bin/bash
# Update fountain code from GitHub

INSTALL_DIR="/opt/fountain"
LOG_FILE="/var/log/fountain_update.log"

echo "$(date): Starting fountain update" >> $LOG_FILE

cd $INSTALL_DIR

# Save current version
CURRENT_VERSION=$(git rev-parse HEAD)

# Fetch updates
git fetch origin

# Check if updates available
LATEST_VERSION=$(git rev-parse origin/main 2>/dev/null || git rev-parse origin/master 2>/dev/null)

if [ "$CURRENT_VERSION" = "$LATEST_VERSION" ]; then
    echo "$(date): Already up to date ($CURRENT_VERSION)" >> $LOG_FILE
    exit 0
fi

echo "$(date): Update available: $CURRENT_VERSION -> $LATEST_VERSION" >> $LOG_FILE

# Backup current code
cp fountain_rms_bass.py fountain_rms_bass.py.backup 2>/dev/null || true

# Pull updates
if git pull origin main 2>/dev/null || git pull origin master 2>/dev/null; then
    echo "$(date): Code updated successfully" >> $LOG_FILE
    
    # Make scripts executable
    chmod +x *.sh 2>/dev/null || true
    chmod +x *.py 2>/dev/null || true
    
    # Restart service
    systemctl restart fountain-vfd
    echo "$(date): Service restarted" >> $LOG_FILE
else
    echo "$(date): Update failed, restoring backup" >> $LOG_FILE
    cp fountain_rms_bass.py.backup fountain_rms_bass.py 2>/dev/null || true
    exit 1
fi
UPDATESCRIPT

chmod +x /usr/local/bin/fountain-update

# Create auto-update service (checks for updates on boot)
cat > /etc/systemd/system/fountain-autoupdate.service << 'AUTOSERVICE'
[Unit]
Description=Fountain Auto-Update from GitHub
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/fountain-update
User=root

[Install]
WantedBy=multi-user.target
AUTOSERVICE

# Create timer for periodic updates (optional - checks daily)
cat > /etc/systemd/system/fountain-autoupdate.timer << 'AUTOTIMER'
[Unit]
Description=Daily Fountain Update Check

[Timer]
OnBootSec=2min
OnUnitActiveSec=24h

[Install]
WantedBy=timers.target
AUTOTIMER

systemctl daemon-reload

# Ask if user wants auto-updates
echo ""
echo "Auto-update options:"
echo "1) Update only on boot (safer - you control when Pi reboots)"
echo "2) Update on boot + check daily (automatic updates)"
echo "3) Manual updates only (use 'sudo fountain-update')"
read -p "Choice [1-3]: " UPDATE_CHOICE

case $UPDATE_CHOICE in
    1)
        systemctl enable fountain-autoupdate.service
        echo "✓ Auto-update on boot enabled"
        ;;
    2)
        systemctl enable fountain-autoupdate.service
        systemctl enable fountain-autoupdate.timer
        systemctl start fountain-autoupdate.timer
        echo "✓ Auto-update on boot + daily check enabled"
        ;;
    3)
        echo "✓ Manual updates only"
        echo "  Run 'sudo fountain-update' to update"
        ;;
    *)
        echo "Invalid choice, defaulting to manual only"
        ;;
esac

# Create version check command
cat > /usr/local/bin/fountain-version << 'VERSIONSCRIPT'
#!/bin/bash
# Show current fountain version and check for updates

INSTALL_DIR="/opt/fountain"

cd $INSTALL_DIR

echo "Current Version:"
echo "  Commit: $(git rev-parse HEAD)"
echo "  Date: $(git log -1 --format=%cd)"
echo "  Message: $(git log -1 --format=%s)"
echo ""

git fetch origin -q

LATEST=$(git rev-parse origin/main 2>/dev/null || git rev-parse origin/master 2>/dev/null)
CURRENT=$(git rev-parse HEAD)

if [ "$CURRENT" = "$LATEST" ]; then
    echo "Status: ✓ Up to date"
else
    echo "Status: ⚠ Update available"
    echo ""
    echo "Latest Version:"
    git log HEAD..origin/main --oneline 2>/dev/null || git log HEAD..origin/master --oneline 2>/dev/null
    echo ""
    echo "Run 'sudo fountain-update' to update"
fi
VERSIONSCRIPT

chmod +x /usr/local/bin/fountain-version

# Create rollback script
cat > /usr/local/bin/fountain-rollback << 'ROLLBACKSCRIPT'
#!/bin/bash
# Rollback to previous version

INSTALL_DIR="/opt/fountain"

if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

cd $INSTALL_DIR

echo "Current version:"
git log -1 --oneline

echo ""
echo "Recent versions:"
git log --oneline -10

echo ""
read -p "Enter commit hash to rollback to: " COMMIT

if [ -z "$COMMIT" ]; then
    echo "Cancelled"
    exit 1
fi

echo "Rolling back to $COMMIT..."
git reset --hard $COMMIT

systemctl restart fountain-vfd

echo "✓ Rollback complete and service restarted"
ROLLBACKSCRIPT

chmod +x /usr/local/bin/fountain-rollback

# Save repository URL for reference
echo $REPO_URL > $INSTALL_DIR/.repo_url

echo ""
echo "=================================================="
echo "GitHub Deployment Setup Complete!"
echo "=================================================="
echo ""
echo "Repository: $REPO_URL"
echo "Install Location: $INSTALL_DIR"
echo ""
echo "Available Commands:"
echo "  sudo fountain-update      - Pull latest code from GitHub"
echo "  sudo fountain-version     - Check current version and updates"
echo "  sudo fountain-rollback    - Rollback to previous version"
echo ""
echo "Update Log: /var/log/fountain_update.log"
echo ""
echo "Auto-update configuration:"
case $UPDATE_CHOICE in
    1) echo "  ✓ Updates on boot only" ;;
    2) echo "  ✓ Updates on boot + daily checks" ;;
    3) echo "  Manual updates only" ;;
esac
echo ""
echo "IMPORTANT NEXT STEPS:"
echo ""
echo "1. Initialize your GitHub repository:"
echo "   - Create a new repo on GitHub"
echo "   - Push fountain code:"
echo ""
echo "     cd $INSTALL_DIR"
echo "     git init"
echo "     git add ."
echo "     git commit -m 'Initial fountain code'"
echo "     git branch -M main"
echo "     git remote add origin $REPO_URL"
echo "     git push -u origin main"
echo ""
echo "2. To push updates from your computer:"
echo "   - Make changes to code"
echo "   - Commit and push:"
echo "     git commit -am 'Fix: your change description'"
echo "     git push"
echo ""
echo "3. Updates will deploy to Pi:"
if [ "$UPDATE_CHOICE" = "1" ]; then
    echo "   - Next time Pi reboots"
elif [ "$UPDATE_CHOICE" = "2" ]; then
    echo "   - Next time Pi reboots OR within 24 hours"
else
    echo "   - When you run 'sudo fountain-update'"
fi
echo ""
