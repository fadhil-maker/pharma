#!/bin/bash
echo "Setting up Pharma VPS Services..."

cat << 'EOF' > /etc/systemd/system/gunicorn-pharma.socket
[Unit]
Description=gunicorn-pharma socket

[Socket]
ListenStream=/run/gunicorn-pharma.sock

[Install]
WantedBy=sockets.target
EOF

cat << 'EOF' > /etc/systemd/system/gunicorn-pharma.service
[Unit]
Description=gunicorn daemon for pharma
Requires=gunicorn-pharma.socket
After=network.target

[Service]
User=root
Group=www-data
Environment="DEBUG=True"
WorkingDirectory=/var/www/pharma
ExecStart=/var/www/pharma/backend/venv/bin/gunicorn --access-logfile - --workers 3 --timeout 120 --bind unix:/run/gunicorn-pharma.sock backend.wsgi:application

[Install]
WantedBy=multi-user.target
EOF

cat << 'EOF' > /etc/nginx/sites-available/pharma
server {
    listen 80;
    server_name pharma.shanudigicore.com;

    root /var/www/pharma/frontend;
    index index.html;

    location = /favicon.ico { access_log off; log_not_found off; }

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://unix:/run/gunicorn-pharma.sock;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /admin/ {
        proxy_pass http://unix:/run/gunicorn-pharma.sock;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

ln -sf /etc/nginx/sites-available/pharma /etc/nginx/sites-enabled/
systemctl daemon-reload
systemctl enable --now gunicorn-pharma.socket
systemctl restart gunicorn-pharma.service
systemctl restart nginx

echo "All done! Configuration has been safely applied."
