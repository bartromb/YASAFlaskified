# YASA Flaskified

<img src="logo.png" alt="YASA Flaskified Logo" width="150" height="150">

## Overview
YASA Flaskified is a web application designed to streamline EEG data processing and sleep analysis. Built on Flask, Redis, Gunicorn, and Nginx, it integrates the **YASA** Python library for automated sleep staging and hypnogram generation. This platform allows users to upload EEG files, process them asynchronously, and visualize the results in an easy-to-use interface.

YASA Flaskified is built upon the **YASA** library developed by Raphaël Vallat. YASA is a powerful tool for sleep analysis using machine learning techniques, enabling precise and efficient sleep staging and event detection. Special thanks to the original author for his contributions to the scientific community.

- Learn more about the YASA library on [Raphaël Vallat’s website](https://raphaelvallat.com/yasa/)
- Explore the related article published in **eLife**: [Automated sleep staging with YASA](https://elifesciences.org/articles/70092)

The deployment is simplified with an automated script (`deploy.sh`) to set up the application on a fresh Ubuntu 24.04 server.

You can find the full project on GitHub at: [YASA Flaskified Repository](https://github.com/bartromb/YASAFlaskified)

**Disclaimer**

Use of this software is at your own risk. YASA Flaskified is provided "as is," without warranty of any kind, express or implied. The developers assume no responsibility for any damages or consequences resulting from the use of this application.

---

## New Features

1. **Channel Selection Before Processing**
   - When a file is uploaded, the script extracts metadata and channels (EEG, EOG, EMG, etc.) from the EDF file.
   - Users can select specific channels to use for processing.
   - Processing is currently limited to **one file at a time** to ensure stability.

2. **Two-Step File Upload and Parsing**
   - File uploads are now chunked and assembled on the server side via the `/upload_chunks` route.
   - Once the file is assembled, it can be parsed separately through the `/parse_file` route, ensuring modularity and robustness.
   - Redis is used to track file paths and upload progress.

3. **Enhanced Hypnogram Output**
   - The generated hypnogram PDF now includes:
     - The selected channels.
     - Additional metadata such as the date of the PSG (Polysomnography), patient identification, and more.
   - The output is formatted for A4 landscape printing.

4. **Improved User Experience**
   - Detailed error handling for file uploads and processing.
   - Clear instructions and feedback at every step.

5. **Showcase Deployment**
   - The platform is deployed at [sleepai.be](https://sleepai.be) and [sleepai.eu](https://sleepai.eu) for demonstration purposes.
   - For the best results, it is recommended to deploy the application on your own server.

---

## Screenshots

### 1. **Login Page**
The secure login page ensures access control for authenticated users:
![Login Page](images/login.png)

### 2. **Upload Page**
Easily upload EEG files (e.g., `.edf`) for processing:
![Upload Page](images/upload.png)

### 3. **Channel Selection Page**
Select specific channels for processing after file analysis:
![Channel Selection Page](images/channelselect.png)

### 4. **Results Page**
View and download processed results, including hypnograms and CSV files:
![Results Page](images/results.png)

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

4. **Let’s Encrypt for Domain-Based Deployments**
   If you select a domain-based deployment, the script will automatically configure and request a Let's Encrypt SSL certificate for secure HTTPS access. Ensure your domain name points to the server's IP address before running the script. Let's Encrypt certificates are free, but they need to be renewed every 90 days. You can automate renewal using certbot:
   ```bash
   sudo certbot renew --quiet
   ```

5. **What the Script Does**:
   - Installs essential packages: Python, Redis, Nginx, SQLite, and Certbot.
   - Sets up the virtual environment and installs project dependencies.
   - Initializes the database and creates an `admin` user with the default password `admin`.
   - Configures Gunicorn to serve the Flask app.
   - Configures Nginx to support the new `/upload_chunks` and `/parse_file` routes.
   - Starts and enables Redis, RQ Worker, Gunicorn, and Nginx as system services.

6. **Access the Application**
   - For local deployments: Visit `http://<server-ip>`
   - For domain-based deployments: Visit `https://<your-domain>`

7. **Post-Deployment Checklist**
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

## Additional Notes

1. **Single File Limitation**
   - Currently, the application processes one file at a time to ensure performance and stability. Batch processing may be introduced in future updates.

2. **Channel Selection Feature**
   - After uploading an EDF file, metadata and channels are extracted and presented for user selection.
   - This ensures precise control over the data used for analysis.

3. **Best Deployment Practice**
   - The showcase deployment on [sleepai.be](https://sleepai.be) and [sleepai.eu](https://sleepai.eu) demonstrates the platform’s capabilities. For production use, it is recommended to deploy on your own server for better performance and control.

---

## License
This project is licensed under the BSD 3-Clause License. See the LICENSE file for details.

