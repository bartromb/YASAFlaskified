# YASA Flaskified

## Overview
This project is built on the YASA Python library, a powerful tool for sleep analysis using machine learning techniques to automate and enhance sleep staging and event detection. Developed by Raphaël Vallat, YASA provides precise and efficient analysis of sleep data. Learn more about YASA on [Raphaël Vallat's website](https://raphaelvallat.com/yasa/) and explore the related [eLife article](https://elifesciences.org/articles/70092).

YASA Flaskified is a web application leveraging Flask, Redis, Gunicorn, and Nginx to provide an accessible platform for EEG data processing, sleep analysis, and results visualization. It integrates YASA for advanced scientific analysis while offering a user-friendly interface for researchers and practitioners.

---

## Features
- User authentication (login, logout, registration)
- File upload and processing
- Task queue using Redis
- Result visualization and download

---

## Requirements
- Python 3.8+
- Redis
- Nginx
- Gunicorn

---

## End User Installation Guide

### Prerequisites
To use this application, ensure you have the following:
- A server running Ubuntu 20.04 or later.
- Basic knowledge of terminal commands.
- A valid domain name (optional but recommended).

### Step-by-Step Instructions

1. **Clone the Repository**
   ```bash
   git clone https://github.com/<your-username>/<repository-name>.git
   cd <repository-name>
   ```

2. **Set Up Python Environment**
   - Create and activate a Python virtual environment:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```
   - Install dependencies:
     ```bash
     pip install -r requirements.txt
     ```

3. **Initialize the Database**
   - Set up the user database by running the following command:
     ```bash
     python app.py
     ```
   - This will create the necessary tables and an initial admin user with the following credentials:
     - **Username**: `admin`
     - **Password**: `admin`
   - **Important:** Immediately change the admin password after logging in for the first time.

4. **Run the Application Locally**
   - Test the application locally using Flask's built-in server:
     ```bash
     python app.py
     ```
   - Visit `http://127.0.0.1:5000` in your browser.

5. **Deploy the Application on a Server**
   - Follow the administrator guide below to configure the required server tools and services.

---

## Administrator Setup Manual

### Nginx Configuration
1. **Create an Nginx Configuration File**
   ```bash
   sudo nano /etc/nginx/sites-available/myapp
   ```
2. **Add Configuration**
   ```nginx
   server {
       listen 80;
       server_name your_domain_or_ip;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }

       location /static/ {
           alias /path/to/static/files/;
       }
   }
   ```
3. **Enable and Restart Nginx**
   ```bash
   sudo ln -s /etc/nginx/sites-available/myapp /etc/nginx/sites-enabled
   sudo nginx -t
   sudo systemctl restart nginx
   ```

### Gunicorn Configuration
1. **Create a Gunicorn Service File**
   ```bash
   sudo nano /etc/systemd/system/myapp.service
   ```
2. **Add Configuration**
   ```ini
   [Unit]
   Description=Gunicorn instance to serve myapp
   After=network.target

   [Service]
   User=www-data
   Group=www-data
   WorkingDirectory=/path/to/your/project
   Environment="PATH=/path/to/your/project/venv/bin"
   ExecStart=/path/to/your/project/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 app:app

   [Install]
   WantedBy=multi-user.target
   ```
3. **Start and Enable the Service**
   ```bash
   sudo systemctl start myapp
   sudo systemctl enable myapp
   ```

### Redis Configuration
1. **Start Redis**
   ```bash
   sudo systemctl start redis
   sudo systemctl enable redis
   ```
2. **Test Redis**
   ```bash
   redis-cli ping
   ```
   Expected output: `PONG`

### Adding RQ Workers
1. **Set Up a Template for RQ Workers**
   - Use the `rq-worker@` template for systemd to easily manage multiple workers.
   - Create the template service file:
     ```bash
     sudo nano /etc/systemd/system/rq-worker@.service
     ```
   - Add the following content:
     ```ini
     [Unit]
     Description=RQ Worker %i
     After=network.target

     [Service]
     User=www-data
     Group=www-data
     WorkingDirectory=/path/to/your/project
     Environment="PATH=/path/to/your/project/venv/bin"
     ExecStart=/path/to/your/project/venv/bin/rq worker

     [Install]
     WantedBy=multi-user.target
     ```

2. **Start and Enable Multiple Workers**
   - Start a single worker instance:
     ```bash
     sudo systemctl start rq-worker@1
     ```
   - Enable the worker instance to start on boot:
     ```bash
     sudo systemctl enable rq-worker@1
     ```
   - Start additional workers by specifying their indices:
     ```bash
     sudo systemctl start rq-worker@{2..8}
     ```
   - Enable them at boot:
     ```bash
     sudo systemctl enable rq-worker@{2..8}
     ```

3. **Check the Status of Workers**
   - View the status of a specific worker:
     ```bash
     sudo systemctl status rq-worker@1
     ```
   - View all workers:
     ```bash
     systemctl list-units --type=service | grep rq-worker
     ```

---

### HTTPS Configuration with Let’s Encrypt

1. **Install Certbot**
   ```bash
   sudo apt install -y certbot python3-certbot-nginx
   ```

2. **Obtain a Certificate**
   Run the following command to automatically configure HTTPS for your domain:
   ```bash
   sudo certbot --nginx -d your_domain
   ```
   Replace `your_domain` with your actual domain name.

3. **Test the Configuration**
   Verify that HTTPS is working by visiting `https://your_domain` in your browser.

4. **Set Up Automatic Certificate Renewal**
   Certbot automatically sets up a cron job for renewal. Test it using:
   ```bash
   sudo certbot renew --dry-run
   ```

---

## Running the Application
- Start the Gunicorn service:
  ```bash
  sudo systemctl start myapp
  ```
- Access the application in your browser via `http://your_domain_or_ip` or `https://your_domain` if HTTPS is configured.

---

## Changing the Admin Password
1. Log in to the application with the admin credentials.
2. Navigate to the **Change Password** page in the menu.
3. Enter the current password (`admin`) and a new secure password.
4. Save the changes. The admin password is now updated.

---

## Changing the Database Password
1. **Edit the Configuration File**
   - Open the `config.json` file in your project directory:
     ```bash
     nano config.json
     ```
   - Update the `SQLALCHEMY_DATABASE_URI` field with the new database password. For example:
     ```json
     {
         "SQLALCHEMY_DATABASE_URI": "mysql+pymysql://username:newpassword@localhost/dbname"
     }
     ```

2. **Restart the Application**
   - Restart the Gunicorn service to apply the changes:
     ```bash
     sudo systemctl restart myapp
     ```

3. **Test the Application**
   - Verify that the application is running correctly by accessing it in your browser.

---

## Updating the Application
1. Pull changes from GitHub:
   ```bash
   git pull origin main
   ```
2. Restart Gunicorn:
   ```bash
   sudo systemctl restart myapp
   ```

---

## License

This project is licensed under the BSD 3-Clause License. See the LICENSE file for details.

```text
BSD 3-Clause License

Copyright (c) 2024
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors
   may be used to endorse or promote products derived from this software
   without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```
