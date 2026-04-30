#!/bin/bash
# ============================================================
# Server Setup Script — GCP e2-micro VM (Ubuntu)
# Run this ONCE after creating the VM:
#   chmod +x setup_server.sh && ./setup_server.sh
# ============================================================

set -e

echo "============================================"
echo "  Social Media Agency — Server Setup"
echo "============================================"

# 1. System updates
echo "[1/6] Updating system..."
sudo apt update -y && sudo apt upgrade -y

# 2. Install Python 3.12+
echo "[2/6] Installing Python..."
sudo apt install -y python3 python3-pip python3-venv git

# 3. Clone the private repo
echo "[3/6] Cloning repository..."
if [ ! -d "$HOME/agency" ]; then
    git clone https://github.com/amajumdar2249/SYRA-Automation-Private.git $HOME/agency
fi
cd $HOME/agency

# 4. Create virtual environment
echo "[4/6] Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 5. Create .env file (user must fill API keys)
echo "[5/6] Creating .env template..."
if [ ! -f .env ]; then
    cat > .env << 'EOF'
# Fill in your API keys below
GEMINI_API_KEY=
GEMINI_API_KEY_2=
GEMINI_API_KEY_3=
OPENROUTER_API_KEY=
DEEPSEEK_API_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
PIPELINE_INTERVAL_HOURS=4
APPROVAL_TIMEOUT_MIN=60
EOF
    echo "  >> IMPORTANT: Edit .env with your API keys: nano .env"
else
    echo "  >> .env already exists, skipping."
fi

# 6. Create systemd service for auto-start
echo "[6/6] Creating systemd service..."
sudo tee /etc/systemd/system/agency.service > /dev/null << EOF
[Unit]
Description=Social Media Agency — Autonomous Pipeline
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME/agency
ExecStart=$HOME/agency/venv/bin/python scheduler.py
Restart=always
RestartSec=30
Environment=PYTHONUNBUFFERED=1
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo ""
echo "============================================"
echo "  Setup Complete!"
echo "============================================"
echo ""
echo "  NEXT STEPS:"
echo "  1. Edit .env:           nano ~/agency/.env"
echo "  2. Start the agency:    sudo systemctl start agency"
echo "  3. Enable auto-start:   sudo systemctl enable agency"
echo "  4. View logs:           sudo journalctl -u agency -f"
echo "  5. Check status:        sudo systemctl status agency"
echo ""
echo "  The agency will run every 4 hours automatically."
echo "  It survives reboots thanks to systemd."
echo ""
