#!/bin/bash

# Ensure the script is run with sudo
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root or with sudo privileges." 
   exit 1
fi

# Variables
PROJECT_NAME="YASAFlaskified"
PROJECT_DIR="/var/www/$PROJECT_NAME"
VENV_DIR="$PROJECT_DIR/venv"

# Prompt for deployment type
read -p "Do you want to deploy locally (localhost) or on a domain? Enter 'local' or 'domain': " DEPLOY_OPTION
if [[ $DEPLOY_OPTION == "local" ]]; then
    DOMAIN="localhost"
    echo "You have chosen to deploy locally. The application will run on http://localhost."
elif [[ $DEPLOY_OPTION == "domain" ]]; then
    read -p "Enter the domain name for your website (e.g., example.com): " DOMAIN
    echo "You have chosen to deploy on the domain: $DOMAIN"
else
    echo "Invalid option. Please run the script again and enter 'local' or 'domain'."
    exit 1
fi

# Update and install required packages
apt update && apt upgrade -y
apt install -y python3 python3-venv python3-pip nginx redis git certbot python3-certbot-nginx

# Clone the repository
if [[ -d $PROJECT_DIR ]]; then
    echo "$PROJECT_DIR already exists. Please remove it first if you want a fresh installation."
    exit 1
fi

# Create project directory
mkdir -p $PROJECT_DIR

# Clone the repository and move files
git clone https://github.com/bartromb/YASAFlaskified.git /tmp/YASAFlaskified
if [[ -d /tmp/YASAFlaskified/myproject ]]; then
    mv /tmp/YASAFlaskified/myproject/* $PROJECT_DIR/
    rm -rf /tmp/YASAFlaskified
else
    echo "Error: Cloned repository does not contain the expected 'myproject' folder."
    exit 1
fi

# Navigate to the project directory
cd $PROJECT_DIR || { echo "Error: Failed to navigate to $PROJECT_DIR."; exit 1; }

# Validate required files
if [[ ! -f requirements.txt ]]; then
    echo "Error: requirements.txt not found in the repository. Please ensure the file exists."
    exit 1
fi
if [[ ! -f app.py ]]; then
    echo "Error: app.py not found in the repository. Please ensure the file exists."
    exit 1
fi

# Set up the Python virtual environment
python3 -m venv $VENV_DIR
source $VENV_DIR/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Configure the application
CONFIG_FILE="$PROJECT_DIR/config.json"
cat > $CONFIG_FILE <<EOL
{
    "UPLOAD_FOLDER": "$PROJECT_DIR/uploads",
    "PROCESSED_FOLDER": "$PROJECT_DIR/processed",
    "SECRET_KEY": "supersecretkey",
    "SQLALCHEMY_DATABASE_URI": "sqlite:///$PROJECT_DIR/instance/users.db",
    "SQLALCHEMY_TRACK_MODIFICATIONS": false,
    "LOG_FILE": "$PROJECT_DIR/logs/app.log",
    "ADMIN_PASSWORD": "admin",
    "JOB_TIMEOUT": 6000
}
EOL
mkdir -p "$PROJECT_DIR/uploads" "$PROJECT_DIR/processed" "$PROJECT_DIR/instance" "$PROJECT_DIR/logs"

# Initialize the database
python3 app.py &
sleep 5
kill $!
echo "Flask server initialized and stopped."
deactivate

# Set up Gunicorn
GUNICORN_SERVICE="/etc/systemd/system/$PROJECT_NAME.service"
cat > $GUNICORN_SERVICE <<EOL
[Unit]
Description=Gunicorn instance to serve $PROJECT_NAME
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$VENV_DIR/bin"
ExecStart=$VENV_DIR/bin/gunicorn -w 4 -b 127.0.0.1:8000 app:app

[Install]
WantedBy=multi-user.target
EOL

# Enable and start Gunicorn
systemctl daemon-reload
systemctl start $PROJECT_NAME
if ! systemctl is-active --quiet $PROJECT_NAME; then
    echo "Error: Gunicorn failed to start. Check Gunicorn logs for details."
    exit 1
fi
systemctl enable $PROJECT_NAME

# Configure Nginx
NGINX_CONFIG="/etc/nginx/sites-available/$PROJECT_NAME"
cat > $NGINX_CONFIG <<EOL
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static/ {
        alias $PROJECT_DIR/static/;
    }
}
EOL
if [[ ! -L /etc/nginx/sites-enabled/$PROJECT_NAME ]]; then
    ln -s /etc/nginx/sites-available/$PROJECT_NAME /etc/nginx/sites-enabled/
else
    echo "Nginx site configuration already linked."
fi
nginx -t && systemctl restart nginx

# Configure HTTPS with Let's Encrypt
if [[ $DEPLOY_OPTION == "domain" ]]; then
    certbot --nginx -d $DOMAIN
else
    echo "Skipping HTTPS setup for localhost deployment."
fi

# Start Redis
systemctl daemon-reload
systemctl start redis-server
systemctl enable redis-server

# Set up RQ workers
RQ_WORKER_SERVICE="/etc/systemd/system/rq-worker@.service"
cat > $RQ_WORKER_SERVICE <<EOL
[Unit]
Description=RQ Worker %i
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$VENV_DIR/bin"
ExecStart=$VENV_DIR/bin/rq worker

[Install]
WantedBy=multi-user.target
EOL

# Enable and start RQ workers
systemctl daemon-reload
for i in {1..4}; do
    systemctl start rq-worker@$i
    systemctl enable rq-worker@$i
done

# Finalize
chown -R www-data:www-data $PROJECT_DIR
chmod -R 755 $PROJECT_DIR

echo "Deployment complete! Visit http://$DOMAIN or https://$DOMAIN to access your application."