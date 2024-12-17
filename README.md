# YASA Flaskified

## Overview
YASA Flaskified is a web application designed to streamline EEG data processing and sleep analysis. Built on Flask, Redis, Gunicorn, and Nginx, it integrates the **YASA** Python library for automated sleep staging and hypnogram generation. This platform allows users to upload EEG files, process them asynchronously, and visualize the results in an easy-to-use interface.

YASA Flaskified is built upon the **YASA** library developed by Raphaël Vallat. YASA is a powerful tool for sleep analysis using machine learning techniques, enabling precise and efficient sleep staging and event detection. Special thanks to the original author for his contributions to the scientific community.

- Learn more about the YASA library on [Raphaël Vallat’s website](https://raphaelvallat.com/yasa/)
- Explore the related article published in **eLife**: [Automated sleep staging with YASA](https://elifesciences.org/articles/70092)

The deployment is simplified with an automated script (`deploy.sh`) to set up the application on a fresh Ubuntu 24.04 server.

You can find the full project on GitHub at: [YASA Flaskified Repository](https://github.com/bartromb/YASAFlaskified)

---

## Deployment Guide (Using `deploy.sh`)

The **`deploy.sh`** script automates the installation and configuration process, ensuring all dependencies and services are set up. Follow these steps to deploy YASA Flaskified:

### Steps to Deploy

1. **Download the Deployment Script**
   Start by downloading the script:
   ```bash
   wget https://raw.githubusercontent.com/bartromb/YASAFlaskified/main/deploy.sh
   chmod +x deploy.sh
   ```

2. **Run the Deployment Script**
   Execute the script with `sudo` privileges to install required dependencies and configure services:
   ```bash
   sudo ./deploy.sh
   ```

3. **Follow the Prompts**
   - Choose between a **local** deployment (default IP: `0.0.0.0`) or a **domain-based** deployment.
   - If deploying to a domain, provide the domain name when prompted.

4. **What the Script Does**:
   - Installs essential packages: Python, Redis, Nginx, SQLite, and Certbot.
   - Sets up the virtual environment and installs project dependencies.
   - Initializes the database and creates an `admin` user with the default password `admin`.
   - Configures Gunicorn to serve the Flask app.
   - Sets up Nginx as a reverse proxy.
   - Starts and enables Redis, RQ Worker, Gunicorn, and Nginx as system services.

5. **Access the Application**
   - For local deployments: Visit `http://<server-ip>`
   - For domain-based deployments: Visit `http://<your-domain>`

6. **Post-Deployment Checklist**
   - **Change the Default Admin Password**:
     Log in with `admin` (username) and `admin` (password), then change the password.
   - **Verify Running Services**:
     ```bash
     sudo systemctl status redis-server
     sudo systemctl status rq-worker
     sudo systemctl status YASAFlaskified
     sudo systemctl status nginx
     ```
   - **Monitor Application Logs**:
     ```bash
     tail -f /var/www/YASAFlaskified/logs/app.log
     ```

---

## Manual Installation Guide
For users who prefer manual installation, follow these detailed steps:

### Prerequisites
- Ubuntu 24.04 server
- Python 3.8+
- Redis server
- Nginx
- Basic terminal knowledge

### Step-by-Step Instructions

1. **Install Dependencies**
   Update and install required system packages:
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install -y python3 python3-venv python3-pip nginx redis-server git sqlite3 certbot python3-certbot-nginx
   ```

2. **Clone the Repository**
   ```bash
   git clone https://github.com/bartromb/YASAFlaskified.git /var/www/YASAFlaskified
   cd /var/www/YASAFlaskified
   ```

3. **Set Up Python Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Initialize the Database**
   ```bash
   mkdir -p instance logs uploads processed
   python3 -c "
   from app import app, db
   with app.app_context():
       db.create_all()
   print('Database initialized.')"
   chown -R www-data:www-data instance
   chmod 664 instance/users.db
   ```

5. **Configure Gunicorn and Nginx**
   - Create a systemd service for Gunicorn:
     ```bash
     sudo nano /etc/systemd/system/YASAFlaskified.service
     ```
     Add the following:
     ```ini
     [Unit]
     Description=Gunicorn service for YASA Flaskified
     After=network.target

     [Service]
     User=www-data
     Group=www-data
     WorkingDirectory=/var/www/YASAFlaskified
     Environment="PATH=/var/www/YASAFlaskified/venv/bin"
     ExecStart=/var/www/YASAFlaskified/venv/bin/gunicorn --workers 3 --timeout 6000 --bind unix:/var/www/YASAFlaskified/run/gunicorn.sock app:app

     [Install]
     WantedBy=multi-user.target
     ```
   - Enable and start the service:
     ```bash
     sudo systemctl daemon-reload
     sudo systemctl start YASAFlaskified
     sudo systemctl enable YASAFlaskified
     ```

   - Configure Nginx as a reverse proxy:
     ```bash
     sudo nano /etc/nginx/sites-available/YASAFlaskified
     ```
     Add the following:
     ```nginx
     server {
         listen 80;
         server_name <your-domain>;

         location / {
             proxy_pass http://unix:/var/www/YASAFlaskified/run/gunicorn.sock;
             proxy_set_header Host $host;
             proxy_set_header X-Real-IP $remote_addr;
             proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
         }

         location /static/ {
             alias /var/www/YASAFlaskified/static/;
         }
     }
     ```
     Enable the site and restart Nginx:
     ```bash
     sudo ln -s /etc/nginx/sites-available/YASAFlaskified /etc/nginx/sites-enabled
     sudo nginx -t
     sudo systemctl restart nginx
     ```

6. **Set Up RQ Worker**
   - Create a systemd service for RQ Worker:
     ```bash
     sudo nano /etc/systemd/system/rq-worker.service
     ```
     Add the following:
     ```ini
     [Unit]
     Description=RQ Worker for YASA Flaskified
     After=network.target

     [Service]
     User=www-data
     Group=www-data
     WorkingDirectory=/var/www/YASAFlaskified
     Environment="PATH=/var/www/YASAFlaskified/venv/bin"
     ExecStart=/var/www/YASAFlaskified/venv/bin/rq worker

     [Install]
     WantedBy=multi-user.target
     ```
     Enable and start the worker:
     ```bash
     sudo systemctl daemon-reload
     sudo systemctl start rq-worker
     sudo systemctl enable rq-worker
     ```

---

## Detailed Description of app.py
The `app.py` file is the core of YASA Flaskified. It includes:

1. **Flask Routes**:
   - `/` : File upload page (requires login).
   - `/results` : Processed results download.
   - `/login` and `/logout` : User authentication.

2. **File Upload**:
   - EDF files are uploaded and saved in a specified directory.

3. **Processing**:
   - Files are processed using the YASA library.
   - Sleep staging generates hypnograms and CSV outputs.

4. **Asynchronous Task Queue**:
   - RQ and Redis handle background processing.

5. **Logging**:
   - Logs detailed events for debugging.

6. **Authentication**:
   - Uses Flask-Login for secure user sessions.

---

## Administrator Commands
- Restart services:
   ```bash
   sudo systemctl restart redis-server rq-worker YASAFlaskified nginx
   ```
- View logs:
   ```bash
   tail -f logs/app.log
   ```

---

## License
This project is licensed under the BSD 3-Clause License. See the LICENSE file for details.
