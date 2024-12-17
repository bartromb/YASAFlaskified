#!/bin/bash

# Ensure the script is run as root
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root."
    exit 1
fi

PROJECT_NAME="YASAFlaskified"
PROJECT_DIR="/var/www/$PROJECT_NAME"
VENV_DIR="$PROJECT_DIR/venv"
RUN_DIR="$PROJECT_DIR/run"
LOGS_DIR="$PROJECT_DIR/logs"
UPLOAD_FOLDER="$PROJECT_DIR/uploads"
PROCESSED_FOLDER="$PROJECT_DIR/processed"
INSTANCE_FOLDER="$PROJECT_DIR/instance"
MPLCONFIGDIR="$PROJECT_DIR/.config/matplotlib"
CONFIG_FILE="$PROJECT_DIR/config.json"
REPO_URL="https://github.com/bartromb/YASAFlaskified.git"

# Deployment type prompt
read -p "Deploy locally (localhost) or on a domain? Enter 'local' or 'domain': " DEPLOY_OPTION
if [[ $DEPLOY_OPTION == "local" ]]; then
    DOMAIN="0.0.0.0"
    echo "Deploying locally. Accessible via the server's IP address on port 80."
elif [[ $DEPLOY_OPTION == "domain" ]]; then
    read -p "Enter the domain name for your website (e.g., example.com): " DOMAIN
    echo "Deploying on the domain: $DOMAIN"
else
    echo "Invalid option. Re-run the script and choose 'local' or 'domain'."
    exit 1
fi

# Clean up previous installations
echo "Cleaning up previous installations..."

systemctl stop $PROJECT_NAME.service nginx redis-server
for i in {1..4}; do
    systemctl stop rq-worker@$i
done

# Stop and disable services
systemctl stop $PROJECT_NAME.service
systemctl disable $PROJECT_NAME.service
systemctl stop nginx.service
systemctl stop redis-server.service

# Remove systemd service files
rm -f /etc/systemd/system/$PROJECT_NAME.service

# Remove Nginx configuration
rm -f /etc/nginx/sites-available/$PROJECT_NAME
rm -f /etc/nginx/sites-enabled/$PROJECT_NAME
rm -f /etc/nginx/sites-enabled/default

# Remove project directory
if [[ -d "$PROJECT_DIR" ]]; then
    rm -rf "$PROJECT_DIR"
fi

echo "Previous installations cleaned."

# Install system packages
apt update && apt upgrade -y
apt install -y python3 python3-venv python3-pip nginx redis-server git certbot python3-certbot-nginx sqlite3

# Clone the repository
git clone "$REPO_URL" "$PROJECT_DIR" || { echo "Cloning repository failed"; exit 1; }

# Ensure correct project structure
if [[ -d "$PROJECT_DIR/myproject" ]]; then
    mv "$PROJECT_DIR/myproject"/* "$PROJECT_DIR/" || { echo "Reorganizing project files failed"; exit 1; }
    rm -rf "$PROJECT_DIR/myproject"
fi

# Check for app.py
if [[ ! -f "$PROJECT_DIR/app.py" ]]; then
    echo "app.py not found in $PROJECT_DIR. Check your repository structure."
    exit 1
fi

# Set up virtual environment and install requirements
python3 -m venv "$VENV_DIR" || { echo "Creating virtual environment failed"; exit 1; }
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r "$PROJECT_DIR/requirements.txt" || { echo "Installing requirements failed"; exit 1; }
deactivate

# Configure directories
mkdir -p "$RUN_DIR" "$LOGS_DIR" "$UPLOAD_FOLDER" "$PROCESSED_FOLDER" "$INSTANCE_FOLDER" "$MPLCONFIGDIR"
chown -R www-data:www-data "$PROJECT_DIR"
chmod -R 755 "$PROJECT_DIR"
chmod -R 777 "$MPLCONFIGDIR"

# Create application configuration
cat > "$CONFIG_FILE" <<EOL
{
    "UPLOAD_FOLDER": "$UPLOAD_FOLDER",
    "PROCESSED_FOLDER": "$PROCESSED_FOLDER",
    "SQLALCHEMY_DATABASE_URI": "sqlite:///$INSTANCE_FOLDER/users.db",
    "SQLALCHEMY_TRACK_MODIFICATIONS": false,
    "LOG_FILE": "$LOGS_DIR/app.log",
    "JOB_TIMEOUT": 6000
}
EOL

# Initialize database and create admin user
source "$VENV_DIR/bin/activate"
cd "$PROJECT_DIR"
python3 -c "
import os, json
from app import app, db, User
from werkzeug.security import generate_password_hash

with open('config.json') as f:
    config = json.load(f)
app.config.from_mapping(config)
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin_password = generate_password_hash('admin', method='pbkdf2:sha256', salt_length=8)
        admin = User(username='admin', password=admin_password)
        db.session.add(admin)
        db.session.commit()
        print('Admin user created with password: admin')
" || { echo "Database initialization failed"; exit 1; }
deactivate

# Ensure users.db is writable
chown www-data:www-data "$INSTANCE_FOLDER/users.db"
chmod 664 "$INSTANCE_FOLDER/users.db"

# Create systemd service for Gunicorn
cat > /etc/systemd/system/$PROJECT_NAME.service <<EOL
[Unit]
Description=Gunicorn instance to serve $PROJECT_NAME
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$VENV_DIR/bin"
Environment="MPLCONFIGDIR=$MPLCONFIGDIR"
ExecStart=$VENV_DIR/bin/gunicorn --worker-class gevent -w 3 --timeout 6000 --bind unix:$RUN_DIR/gunicorn.sock app:app

[Install]
WantedBy=multi-user.target
EOL

# Create systemd template for RQ Workers
cat > /etc/systemd/system/rq-worker@.service <<EOL
[Unit]
Description=RQ Worker instance %i for $PROJECT_NAME
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$VENV_DIR/bin"
ExecStart=$VENV_DIR/bin/rq worker
Restart=always

[Install]
WantedBy=multi-user.target
EOL

# Start 4 RQ Workers
for i in {1..4}; do
    systemctl enable rq-worker@$i
    systemctl start rq-worker@$i
done

# Create Nginx configuration
cat > /etc/nginx/sites-available/$PROJECT_NAME <<EOL
server {
    listen 80;
    server_name $DOMAIN;

    client_max_body_size 2000M;

    location / {
        proxy_pass http://unix:$RUN_DIR/gunicorn.sock;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }

    location /static {
        alias $PROJECT_DIR/static;
    }
}
EOL

ln -sf /etc/nginx/sites-available/$PROJECT_NAME /etc/nginx/sites-enabled/

# Enable and start services
systemctl daemon-reload
systemctl enable $PROJECT_NAME.service
systemctl start $PROJECT_NAME.service
systemctl enable nginx.service
systemctl restart nginx.service
systemctl enable redis-server.service
systemctl start redis-server.service

# Set up Let's Encrypt for domain-based deployments
if [[ $DEPLOY_OPTION == "domain" ]]; then
    certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN || { echo "Let's Encrypt setup failed"; exit 1; }
fi

# Final message
echo "Deployment completed successfully. Access your application at http://$DOMAIN."
