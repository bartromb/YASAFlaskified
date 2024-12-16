import os
import logging
import json
import warnings
import mne
import yasa
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from flask import Flask, request, jsonify, redirect, url_for, flash, session, send_from_directory, render_template
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from redis import Redis
from rq import Queue
from rq.job import Job

# Suppress warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# Load configuration from JSON
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

# Setup app and configurations
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = config.get('UPLOAD_FOLDER', '/home/bart/myproject/uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
app.config['PROCESSED_FOLDER'] = config.get('PROCESSED_FOLDER', '/home/bart/myproject/processed')
os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)
app.config['SECRET_KEY'] = config.get('SECRET_KEY', 'supersecretkey')
app.config['SQLALCHEMY_DATABASE_URI'] = config.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.get('SQLALCHEMY_TRACK_MODIFICATIONS', False)

# Setup database and login manager
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Setup Redis and RQ
redis_conn = Redis(host='localhost', port=6379)
queue = Queue(connection=redis_conn)

# Setup logging
log_file = config.get('LOG_FILE', '/home/bart/myproject/logs/app.log')
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(level=logging.DEBUG, filename=log_file, filemode='a', format='%(name)s - %(levelname)s - %(message)s')

# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'edf'}

# Function to process EEG file
def process_file(file_path, output_folder):
    logging.info(f'Start processing {file_path}')
    try:
        fname = os.path.basename(file_path)
        edf = mne.io.read_raw_edf(file_path, preload=True)

        # Log all available channels
        available_channels = edf.info['ch_names']
        logging.info(f"Available channels: {available_channels}")

        eeg_prefixes = ['Fp', 'F', 'C', 'P', 'O', 'T']  # Standard prefixes for EEG channels
        eeg_channels = [
            ch for ch in available_channels
            if any(ch.upper().startswith(prefix.upper()) for prefix in eeg_prefixes) and any(c.isdigit() for c in ch)
        ]

        if not eeg_channels:
            logging.error(f"No EEG channels found in the file: {file_path}.")
            flash(f"No EEG channels found in {fname}. Skipping file.", 'warning')
            return None, None

        hypno_results = {}
        for eeg_channel in eeg_channels:
            logging.info(f'Processing EEG channel: {eeg_channel}')
            sls = yasa.SleepStaging(edf, eeg_name=eeg_channel)
            hypno_pred = sls.predict()
            hypno_pred = yasa.hypno_str_to_int(hypno_pred)
            hypno_results[eeg_channel] = hypno_pred

        combined_hypno = np.round(np.mean(list(hypno_results.values()), axis=0)).astype(int)

        plt.figure(figsize=(11.69, 8.27))
        yasa.plot_hypnogram(combined_hypno)
        plt.title(f'Hypnogram for {fname}')
        pdf_path = os.path.join(output_folder, f'{fname}_hypnogram.pdf')
        plt.savefig(pdf_path)
        plt.close()

        hypno_export = pd.DataFrame({
            "onset": np.arange(len(combined_hypno)) * 30,
            "label": combined_hypno,
            "duration": 30
        })
        csv_path = os.path.join(output_folder, f'{fname}.csv')
        hypno_export.to_csv(csv_path, index=False)

        logging.info(f'Finished processing {file_path}')
        return pdf_path, csv_path
    except Exception as e:
        logging.error(f'Error processing {file_path}: {e}')
        raise

# RQ task wrapper for process_file
def background_task(filepath):
    return process_file(filepath, app.config['PROCESSED_FOLDER'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        logging.info("Login attempt received.")
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            logging.info(f"User {username} logged in successfully.")
            return redirect(url_for('upload_file'))
        else:
            flash('Invalid credentials.', 'danger')
            logging.warning(f"Failed login attempt for user {username}.")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logging.info(f"User {current_user.username} logged out.")
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
@login_required
def upload_file():
    logging.info("Accessed upload route.")
    if request.method == 'POST':
        logging.info("Received POST request for file upload.")
        if 'files[]' not in request.files:
            flash('No files part', 'danger')
            logging.error("No files part in the request.")
            return redirect(request.url)

        files = request.files.getlist('files[]')
        processed_files = []

        for file in files:
            if file.filename == '':
                logging.warning("File with empty filename skipped.")
                continue

            if file and allowed_file(file.filename):
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                logging.info(f"Saving file to {filepath}")
                file.save(filepath)

                job_timeout = config.get('JOB_TIMEOUT', 6000)
                job = queue.enqueue(background_task, filepath, job_timeout=job_timeout)
                processed_files.append({'filename': file.filename, 'job_id': job.id})
                logging.info(f"Enqueued job for file {file.filename} with job ID {job.id}")

        if not processed_files:
            flash('No files could be processed. Please try again.', 'danger')
            return redirect(request.url)

        flash('Files successfully uploaded and processing started!', 'success')
        session['processed_files'] = processed_files
        return redirect(url_for('processing'))

    return render_template('upload.html')

@app.route('/processing')
@login_required
def processing():
    logging.info("Accessed processing page.")
    processed_files = session.get('processed_files', [])
    if not processed_files:
        flash('No jobs are being processed.', 'info')
        return redirect(url_for('upload_file'))

    job_statuses = []
    all_finished = True

    for file_info in processed_files:
        try:
            job = Job.fetch(file_info['job_id'], connection=redis_conn)
            if not job.is_finished:
                all_finished = False
                job_statuses.append({'filename': file_info['filename'], 'status': 'Processing'})
            elif job.is_failed:
                job_statuses.append({'filename': file_info['filename'], 'status': 'Failed'})
            else:
                job_statuses.append({'filename': file_info['filename'], 'status': 'Finished'})
        except Exception as e:
            logging.error(f"Error fetching job {file_info['job_id']}: {e}")
            job_statuses.append({'filename': file_info['filename'], 'status': 'Error'})

    if request.args.get('ajax') == 'true':
        return jsonify({'job_statuses': job_statuses, 'all_finished': all_finished})

    return render_template('processing.html', job_statuses=job_statuses)

@app.route('/results')
@login_required
def results():
    logging.info("Accessed results route.")
    processed_files = session.get('processed_files', [])
    if not processed_files:
        flash('No files have been processed yet or session expired.', 'info')
        return redirect(url_for('upload_file'))

    file_links = []
    for file_info in processed_files:
        try:
            job = Job.fetch(file_info['job_id'], connection=redis_conn)
            if job.is_finished and job.result:
                file_links.append({
                    'filename': os.path.basename(job.result[0]),
                    'pdf_url': url_for('download_file', filename=f"{os.path.basename(job.result[0])}"),
                    'csv_url': url_for('download_file', filename=f"{os.path.basename(job.result[1])}")
                })
        except rq.exceptions.NoSuchJobError:
            logging.warning(f"Job {file_info['job_id']} no longer exists.")

    return render_template('results.html', files=file_links)

@app.route('/download/<path:filename>')
@login_required
def download_file(filename):
    logging.info(f"Download request received for file: {filename}")
    return send_from_directory(app.config['PROCESSED_FOLDER'], filename, as_attachment=True)

@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    # Only allow the administrator to access this route
    if current_user.username != 'admin':
        flash('You are not authorized to access this page.', 'danger')
        return redirect(url_for('upload_file'))

    if request.method == 'POST':
        logging.info("Received registration request.")
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        logging.info(f"New user registered: {username}")
        flash('User registered successfully', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        # Verify the current password
        if not check_password_hash(current_user.password, current_password):
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('change_password'))

        # Check if the new password and confirmation match
        if new_password != confirm_password:
            flash('New password and confirmation do not match.', 'danger')
            return redirect(url_for('change_password'))

        # Update the password
        current_user.password = generate_password_hash(new_password, method='pbkdf2:sha256', salt_length=8)
        db.session.commit()
        logging.info(f"Password changed for user: {current_user.username}")
        flash('Password changed successfully.', 'success')
        return redirect(url_for('upload_file'))

    return render_template('change_password.html')

@app.route('/job_status/<job_id>')
@login_required
def job_status(job_id):
    logging.info(f"Job status request received for job: {job_id}")
    job = Job.fetch(job_id, connection=redis_conn)
    if job.is_finished:
        logging.info(f"Job {job_id} finished successfully.")
        return jsonify({'status': 'finished', 'result': job.result})
    elif job.is_failed:
        logging.error(f"Job {job_id} failed with error: {job.exc_info}")
        return jsonify({'status': 'failed', 'error': str(job.exc_info)})
    else:
        logging.info(f"Job {job_id} is in progress.")
        return jsonify({'status': 'in progress'})

# Initialize database
def initialize_database():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin_password = generate_password_hash(config.get('ADMIN_PASSWORD', 'admin'), method='pbkdf2:sha256', salt_length=8)
            admin = User(username='admin', password=admin_password)
            db.session.add(admin)
            db.session.commit()
            logging.info("Admin user created.")

if __name__ == '__main__':
    initialize_database()
    app.run(debug=True)
