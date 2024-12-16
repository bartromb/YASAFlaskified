#!/bin/bash

# Ensure root privileges
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

# Prompt for deployment type
read -p "Do you want to deploy locally (localhost) or on a domain? Enter 'local' or 'domain': " DEPLOY_OPTION
if [[ $DEPLOY_OPTION == "local" ]]; then
    DOMAIN="0.0.0.0"
    echo "Deploying locally. Accessible via the server's IP on port 80."
elif [[ $DEPLOY_OPTION == "domain" ]]; then
    read -p "Enter the domain name for your website (e.g., example.com): " DOMAIN
    echo "Deploying on the domain: $DOMAIN"
else
    echo "Invalid option. Please run the script again and choose 'local' or 'domain'."
    exit 1
fi

# Install system packages
apt update && apt upgrade -y
apt install -y python3 python3-venv python3-pip nginx redis-server git certbot python3-certbot-nginx sqlite3 supervisor

# Clone the repository
if [[ -d "$PROJECT_DIR" ]]; then
    read -p "$PROJECT_DIR exists. Overwrite? (y/N) " overwrite
    [[ "$overwrite" != "y" ]] && exit 1
    rm -rf "$PROJECT_DIR"
fi
git clone "$REPO_URL" "$PROJECT_DIR" || { echo "Failed to clone repository"; exit 1; }

# Ensure correct project structure
if [[ -d "$PROJECT_DIR/myproject" ]]; then
    mv "$PROJECT_DIR/myproject"/* "$PROJECT_DIR/" || { echo "Failed to restructure project files"; exit 1; }
    rm -rf "$PROJECT_DIR/myproject"
fi

# Verify the presence of app.py
if [[ ! -f "$PROJECT_DIR/app.py" ]]; then
    echo "app.py not found in $PROJECT_DIR. Please check your repository structure."
    exit 1
fi

# Set up virtual environment and install requirements
python3 -m venv "$VENV_DIR" || { echo "Failed to create virtual environment"; exit 1; }
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r "$PROJECT_DIR/requirements.txt" || { echo "Failed to install requirements"; exit 1; }
deactivate

# Configure directories
mkdir -p "$RUN_DIR" "$LOGS_DIR" "$UPLOAD_FOLDER" "$PROCESSED_FOLDER" "$INSTANCE_FOLDER" "$MPLCONFIGDIR"
chown -R www-data:www-data "$PROJECT_DIR"
chmod -R 755 "$PROJECT_DIR"

# Create application config
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

# Set PYTHONPATH to the project directory for module resolution
export PYTHONPATH="$PROJECT_DIR"

# Initialize the database and create admin user
source "$VENV_DIR/bin/activate"
cd "$PROJECT_DIR"  # Change working directory to the project directory
python3 -c "
import os, json
from app import app, db, User
from werkzeug.security import generate_password_hash

with open('config.json') as f: # Now uses relative path since working directory is set
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

# Gunicorn configuration (using Supervisor)
cat > /etc/supervisor/conf.d/$PROJECT_NAME.conf <<EOL
[program:$PROJECT_NAME]
command=$VENV_DIR/bin/gunicorn --worker-class gevent -w 3 --timeout 6000 --bind unix:$RUN_DIR/gunicorn.sock app:app
directory=$PROJECT_DIR
user=www-data
autostart=true
autorestart=true
stdout_logfile=$LOGS_DIR/gunicorn_stdout.log
stderr_logfile=$LOGS_DIR/gunicorn_stderr.log
environment=MPLCONFIGDIR="$MPLCONFIGDIR"
EOL

# Reload Supervisor configuration and start Gunicorn process
supervisorctl reread
supervisorctl update
supervisorctl restart $PROJECT_NAME

# Configure Nginx
cat > /etc/nginx/sites-available/$PROJECT_NAME <<EOL
server {
    listen 80;
    server_name $DOMAIN;

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
nginx -t && systemctl restart nginx || { echo "Failed to start Nginx"; exit 1; }

# Redis configuration and RQ worker setup
systemctl enable redis-server
systemctl start redis-server

cat > /etc/supervisor/conf.d/rq-worker.conf <<EOL
[program:rq-worker]
command=$VENV_DIR/bin/rq worker
directory=$PROJECT_DIR
user=www-data
autostart=true
autorestart=true
stdout_logfile=$LOGS_DIR/rq_worker_stdout.log
stderr_logfile=$LOGS_DIR/rq_worker_stderr.log
EOL

supervisorctl reread
supervisorctl update
supervisorctl restart rq-worker

# Set up Let's Encrypt if deploying on a domain
if [[ $DEPLOY_OPTION == "domain" ]]; then
    certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN || { echo "Let's Encrypt setup failed"; exit 1; }
fi

# Final message
echo "Deployment completed successfully. If deploying locally, access the application at http://<server-ip>."
