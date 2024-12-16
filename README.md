# YASA Flaskified

## Overview
This project is built on the YASA Python library, a powerful tool for sleep analysis using machine learning techniques to automate and enhance sleep staging and event detection. Developed by Raphaël Vallat, YASA provides precise and efficient analysis of sleep data. Learn more about YASA on [Raphaël Vallat's website](https://raphaelvallat.com/yasa/) and explore the related [eLife article](https://elifesciences.org/articles/70092).

YASA Flaskified is a web application leveraging Flask, Redis, Gunicorn, and Nginx to provide an accessible platform for EEG data processing, sleep analysis, and results visualization. It integrates YASA for advanced scientific analysis while offering a user-friendly interface for researchers and practitioners.

You can find the full project on GitHub at: [YASA Flaskified Repository](https://github.com/bartromb/YASAFlaskified)

---

## Features
- User authentication (login, logout, registration)
- File upload and processing
- Task queue using Redis
- Result visualization and download

---

## Screenshots

### Login Page
The login page allows users to securely access the application. Administrators can create new user accounts.

![Login Page](images/Screenshot_01.png)

---

### Upload Page
Users can upload EEG data files (e.g., EDF format). The application automatically identifies EEG channels and begins processing the files.

![Upload Page](images/Screenshot_02.png)

---

### Results Page
Once processing is complete, users can download the generated hypnogram as a PDF and the corresponding data in CSV format. The system also provides a visualization of the results.

![Results Page](images/Screenshot_04.png)

---

## Requirements
- Python 3.8+
- Redis
- Nginx
- Gunicorn

---

## Deployment Guide (Using `deploy.sh`)

The easiest way to deploy this application is by using the `deploy.sh` script provided at the root of this repository. The script automates the installation and configuration process, ensuring all dependencies and services are set up correctly. It is tested on a vanilla Ubuntu 24.04 server.

### Steps to Deploy

1. **Download the Deployment Script**
   ```bash
   wget https://raw.githubusercontent.com/bartromb/YASAFlaskified/main/deploy.sh
   chmod +x deploy.sh
   ```

2. **Run the Deployment Script**
   Run the script with sudo privileges:
   ```bash
   sudo ./deploy.sh
   ```

3. **Follow the Prompts**
   - Choose whether to deploy locally or on a domain.
   - If deploying on a domain, provide the domain name when prompted.

4. **Access the Application**
   - For local deployments: Visit `http://<server-ip>`.
   - For domain-based deployments: Visit `http://<your-domain>`.

5. **Post-Deployment**
   - Change the default admin password immediately after the first login.
   - Verify that all services (Redis, Gunicorn, Nginx) are running.

---

## Manual Installation Guide

If you prefer to manually set up the application, follow these steps:

### Prerequisites
Ensure you have the following:
- A server running Ubuntu 24.04 or later.
- Basic knowledge of terminal commands.
- A valid domain name (optional but recommended).

### Step-by-Step Instructions

1. **Download the Repository**
   ```bash
   wget https://github.com/bartromb/YASAFlaskified/archive/main.zip
   unzip main.zip
   cd YASAFlaskified-main
   ```

2. **Install System Dependencies**
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install -y python3 python3-venv python3-pip nginx redis-server certbot python3-certbot-nginx sqlite3
   ```

3. **Set Up Python Environment**
   - Create and activate a Python virtual environment:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```
   - Install dependencies:
     ```bash
     pip install --upgrade pip
     pip install -r requirements.txt
     ```

4. **Configure Directories**
   ```bash
   mkdir -p logs uploads processed instance .config/matplotlib
   chown -R www-data:www-data .
   chmod -R 755 .
   chmod -R 777 .config/matplotlib
   ```

5. **Create Configuration File**
   ```bash
   cat > config.json <<EOL
   {
       "UPLOAD_FOLDER": "uploads",
       "PROCESSED_FOLDER": "processed",
       "SQLALCHEMY_DATABASE_URI": "sqlite:///instance/users.db",
       "SQLALCHEMY_TRACK_MODIFICATIONS": false,
       "LOG_FILE": "logs/app.log",
       "JOB_TIMEOUT": 6000
   }
   EOL
   ```

6. **Initialize the Database**
   ```bash
   python3 -c "
   from app import app, db
   with app.app_context():
       db.create_all()
   "
   chown www-data:www-data instance/users.db
   chmod 664 instance/users.db
   ```

7. **Run the Application Locally**
   ```bash
   python app.py
   ```
   Visit `http://127.0.0.1:5000` in your browser.

8. **Set Up Gunicorn and Nginx**
   Follow the steps in the Administrator Setup section below.

---

## Administrator Setup Manual

### Nginx Configuration
1. **Create an Nginx Configuration File**
   ```bash
   sudo nano /etc/nginx/sites-available/YASAFlaskified
   ```
2. **Add Configuration**
   ```nginx
   server {
       listen 80;
       server_name your_domain_or_ip;

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
3. **Enable and Restart Nginx**
   ```bash
   sudo ln -s /etc/nginx/sites-available/YASAFlaskified /etc/nginx/sites-enabled
   sudo nginx -t
   sudo systemctl restart nginx
   ```

### Gunicorn Configuration
1. **Create a Gunicorn Service File**
   ```bash
   sudo nano /etc/systemd/system/YASAFlaskified.service
   ```
2. **Add Configuration**
   ```ini
   [Unit]
   Description=Gunicorn instance to serve YASA Flaskified
   After=network.target

   [Service]
   User=www-data
   Group=www-data
   WorkingDirectory=/var/www/YASAFlaskified
   Environment="PATH=/var/www/YASAFlaskified/venv/bin"
   ExecStart=/var/www/YASAFlaskified/venv/bin/gunicorn --worker-class gevent -w 3 --timeout 6000 --bind unix:/var/www/YASAFlaskified/run/gunicorn.sock app:app

   [Install]
   WantedBy=multi-user.target
   ```
3. **Start and Enable the Service**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable YASAFlaskified
   sudo systemctl start YASAFlaskified
   ```

---

## License

This project is licensed under the BSD 3-Clause License. See the LICENSE file for details.
