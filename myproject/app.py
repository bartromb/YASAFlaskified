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

# Load configuration
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

# Flask app setup
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = config.get('UPLOAD_FOLDER', '/path/to/uploads')
app.config['PROCESSED_FOLDER'] = config.get('PROCESSED_FOLDER', '/path/to/processed')
app.config['SECRET_KEY'] = config.get('SECRET_KEY', 'supersecretkey')
app.config['SQLALCHEMY_DATABASE_URI'] = config.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.get('SQLALCHEMY_TRACK_MODIFICATIONS', False)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)

# Setup database
db = SQLAlchemy(app)

# Login manager setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Redis and RQ setup
redis_conn = Redis(host='localhost', port=6379)
queue = Queue(connection=redis_conn)

# Logging setup
log_file = config.get('LOG_FILE', '/path/to/logs/app.log')
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(
    level=logging.DEBUG,
    filename=log_file,
    filemode='a',
    format='%(name)s - %(levelname)s - %(message)s'
)

# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'edf'}

# Route: Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('upload_file'))
        else:
            flash('Invalid credentials.', 'danger')
    return render_template('login.html')

# Route: Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Route: Register
@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    if current_user.username != 'admin':
        flash('Only administrators can register new users.', 'danger')
        return redirect(url_for('upload_file'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('User registered successfully.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# Route: Change Password
@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if not check_password_hash(current_user.password, current_password):
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('change_password'))

        if new_password != confirm_password:
            flash('New password and confirmation do not match.', 'danger')
            return redirect(url_for('change_password'))

        current_user.password = generate_password_hash(new_password, method='pbkdf2:sha256', salt_length=8)
        db.session.commit()
        flash('Password changed successfully.', 'success')
        return redirect(url_for('upload_file'))

    return render_template('change_password.html')

# Route: Upload and Parse File
@app.route('/upload_and_parse', methods=['POST'])
@login_required
def upload_and_parse():
    if 'edf_file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['edf_file']
    if file and allowed_file(file.filename):
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)

        try:
            # Parse the EDF file
            edf = mne.io.read_raw_edf(filepath, preload=False)
            edf.load_data()  # Explicitly load data into memory

            logging.debug(f"Loaded EDF file: {filepath}")
            channels = edf.info['ch_names']

            # Categorize channels
            eeg_channels = [ch for ch in channels if ch.startswith(('Fp', 'F', 'C', 'P', 'O', 'T'))]
            eog_channels = [ch for ch in channels if 'EOG' in ch.upper()]
            emg_channels = [ch for ch in channels if 'EMG' in ch.upper()]
            other_channels = [ch for ch in channels if ch not in eeg_channels + eog_channels + emg_channels]

            logging.debug(f"Channels categorized: EEG={len(eeg_channels)}, EOG={len(eog_channels)}, EMG={len(emg_channels)}, Others={len(other_channels)}")
            return jsonify({
                'eeg': eeg_channels,
                'eog': eog_channels,
                'emg': emg_channels,
                'others': other_channels,
                'filepath': filepath
            })
        except Exception as e:
            logging.error(f"Error parsing EDF file: {e}")
            flash('Error analyzing file. Processing aborted.', 'danger')
            return redirect(url_for('upload_file'))


    return jsonify({'error': 'Invalid file type'}), 400

# Route: Upload Files
@app.route('/', methods=['GET', 'POST'])
@login_required
def upload_file():
    if request.method == 'POST':
        # Handle file upload
        if 'files[]' not in request.files:
            flash('No file part in the request.', 'danger')
            return redirect(request.url)

        files = request.files.getlist('files[]')
        processed_files = []

        for file in files:
            if file and allowed_file(file.filename):
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(filepath)
                job = queue.enqueue(process_file_with_channels, filepath, {}, job_timeout=6000)
                processed_files.append({'filename': file.filename, 'job_id': job.id})

        session['processed_files'] = processed_files
        flash('Files uploaded and processing started.', 'success')
        return redirect(url_for('processing'))

    return render_template('upload.html')

# Route: Process File
@app.route('/process_file', methods=['POST'])
@login_required
def process_file():
    raw_selected_channels = request.form.get('selected_channels', '{}').strip()
    filepath = request.form.get('filepath')

    if not filepath:
        flash('Invalid file path received.', 'danger')
        return redirect(url_for('upload_file'))

    try:
        if raw_selected_channels:
            selected_channels = json.loads(raw_selected_channels)
        else:
            selected_channels = {}

        job = queue.enqueue(
            process_file_with_channels,
            filepath,
            selected_channels,  # Ensure channels are passed here
            job_timeout=6000,
            result_ttl=3600
        )
        logging.debug(f"Job {job.id} enqueued with selected channels: {selected_channels}")
        session['processed_files'] = session.get('processed_files', []) + [{'filename': os.path.basename(filepath), 'job_id': job.id}]
        flash('Processing started successfully!', 'success')
        return redirect(url_for('processing'))
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON for selected_channels: {e}")
        flash('Invalid channel selection. Please try again.', 'danger')
        return redirect(url_for('upload_file'))
    except Exception as e:
        logging.error(f"Error enqueuing file processing: {e}")
        flash('Failed to start processing. Please try again.', 'danger')
        return redirect(url_for('upload_file'))

# Route: Processing Status
@app.route('/processing')
@login_required
def processing():
    processed_files = session.get('processed_files', [])
    job_statuses = []
    updated_files = []  # Store valid jobs here
    all_finished = True  # Flag to track if all jobs are finished

    for file_info in processed_files:
        try:
            job = Job.fetch(file_info['job_id'], connection=redis_conn)
            if not job.is_finished:
                job_statuses.append({'filename': file_info['filename'], 'status': 'Processing'})
                updated_files.append(file_info)
                all_finished = False
            elif job.is_failed:
                job_statuses.append({'filename': file_info['filename'], 'status': 'Failed'})
                updated_files.append(file_info)
            else:
                job_statuses.append({'filename': file_info['filename'], 'status': 'Finished'})
                updated_files.append(file_info)
        except Exception as e:
            logging.error(f"Error fetching job {file_info['job_id']}: {e}")
            job_statuses.append({'filename': file_info['filename'], 'status': 'Missing'})
            all_finished = False

    # Update the session to remove old or invalid jobs
    session['processed_files'] = updated_files

    # Redirect to results if all jobs are finished
    if all_finished and processed_files:
        return redirect(url_for('results'))

    return render_template('processing.html', job_statuses=job_statuses)



# File processing logic
def process_file_with_channels(filepath, selected_channels):
    try:
        edf = mne.io.read_raw_edf(filepath, preload=True)

        # Extract selected channels and construct metadata
        eeg_channels = selected_channels.get('eeg', [])
        eog_channels = selected_channels.get('eog', [])
        emg_channels = selected_channels.get('emg', [])
        channels_used = ", ".join(eeg_channels + eog_channels + emg_channels) or "None Selected"

        # Log selected channels for debugging
        logging.debug(f"Selected channels: EEG={eeg_channels}, EOG={eog_channels}, EMG={emg_channels}")

        # Extract additional metadata
        start_time = edf.info['meas_date'] if edf.info['meas_date'] else "Unknown"
        patient_info = edf.info.get('subject_info', {})
        patient_id = patient_info.get('id', "Unknown")
        patient_name = patient_info.get('name', "Unknown")

        # Process the EEG data
        eeg_name = eeg_channels[0] if eeg_channels else edf.info['ch_names'][0]
        sls = yasa.SleepStaging(edf, eeg_name=eeg_name)
        hypno_pred = sls.predict()
        hypno_pred = yasa.hypno_str_to_int(hypno_pred)

        # Save results
        output_folder = app.config['PROCESSED_FOLDER']
        os.makedirs(output_folder, exist_ok=True)

        fname = os.path.basename(filepath)
        pdf_path = os.path.join(output_folder, f"{fname}_hypnogram.pdf")
        csv_path = os.path.join(output_folder, f"{fname}.csv")

        # Generate the hypnogram with metadata
        plt.figure(figsize=(11.69, 8.27))  # A4 landscape dimensions in inches
        yasa.plot_hypnogram(hypno_pred)
        plt.suptitle(f"Hypnogram for {fname}\n"
                     f"Date: {start_time}\n"
                     f"Channels Used: {channels_used}\n"
                     f"Patient ID: {patient_id}, Name: {patient_name}",
                     x=0.5, y=0.98, fontsize=10, ha='center', va='top')
        plt.tight_layout(rect=[0, 0, 1, 0.92])
        plt.savefig(pdf_path, orientation='landscape', format='pdf')
        plt.close()

        # Save hypnogram predictions as CSV
        pd.DataFrame({
            "onset": np.arange(len(hypno_pred)) * 30,  # Assuming 30-second epochs
            "label": hypno_pred,
            "duration": 30
        }).to_csv(csv_path, index=False)

        return pdf_path, csv_path
    except Exception as e:
        logging.error(f"Error processing file {filepath}: {e}")
        raise

# Route: Results Page
@app.route('/results')
@login_required
def results():
    processed_files = session.get('processed_files', [])
    file_links = []

    for file_info in processed_files:
        file_links.append({
            "filename": os.path.basename(file_info['filename']),
            "pdf_url": url_for('download_file', filename=f"{file_info['filename']}_hypnogram.pdf"),
            "csv_url": url_for('download_file', filename=f"{file_info['filename']}.csv")
        })

    return render_template('results.html', files=file_links)

# Route: File Download
@app.route('/download/<path:filename>')
@login_required
def download_file(filename):
    return send_from_directory(app.config['PROCESSED_FOLDER'], filename, as_attachment=True)

# Initialize database
def initialize_database():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin_password = generate_password_hash(config.get('ADMIN_PASSWORD', 'admin'), method='pbkdf2:sha256', salt_length=8)
            admin = User(username='admin', password=admin_password)
            db.session.add(admin)
            db.session.commit()

if __name__ == '__main__':
    initialize_database()
    app.run(debug=True)
