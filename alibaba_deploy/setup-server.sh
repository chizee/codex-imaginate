#!/bin/bash
# Imaginate — Alibaba Cloud ECS Server Setup
# Run: bash setup-server.sh

set -e

echo "=== Installing system packages ==="
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y python3.12 python3.12-venv python3-pip nginx ffmpeg certbot python3-certbot-nginx

echo "=== Creating app user ==="
sudo useradd -m -s /bin/bash imaginate 2>/dev/null || true
sudo usermod -aG sudo imaginate

echo "=== Setting up app ==="
cd /home/imaginate
git clone https://github.com/chizee/imaginate-ai.git app 2>/dev/null || (cd app && git pull)
sudo chown -R imaginate:imaginate app/

echo "=== Python venv ==="
cd app
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt fastapi uvicorn slowapi

echo "=== Systemd service ==="
sudo tee /etc/systemd/system/imaginate.service > /dev/null << 'SVC'
[Unit]
Description=Imaginate
After=network.target

[Service]
User=imaginate
WorkingDirectory=/home/imaginate/app
Environment="DASHSCOPE_API_KEY=CHANGE_ME"
Environment="QWEN_API_BASE=https://ws-s8blchl8lx57ttc9.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"
Environment="QWEN_DASHSCOPE_BASE=https://ws-s8blchl8lx57ttc9.ap-southeast-1.maas.aliyuncs.com/api/v1"
ExecStart=/home/imaginate/app/venv/bin/uvicorn web_ui.backend.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always

[Install]
WantedBy=multi-user.target
SVC

echo "=== Nginx ==="
sudo tee /etc/nginx/sites-available/imaginate > /dev/null << 'NGX'
server {
    listen 80;
    server_name imaginate.ai www.imaginate.ai;
    client_max_body_size 100m;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGX

sudo ln -sf /etc/nginx/sites-available/imaginate /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx

echo "=== Starting service ==="
sudo systemctl daemon-reload
sudo systemctl enable imaginate
sudo systemctl start imaginate

echo "=== Done! ==="
echo "Check: sudo systemctl status imaginate"
echo "Logs: sudo journalctl -u imaginate -f"
echo ""
echo "After pointing your domain DNS to this server's IP, run:"
echo "  sudo certbot --nginx -d imaginate.ai -d www.imaginate.ai"