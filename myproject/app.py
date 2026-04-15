"""
app.py — YASAFlaskified (see version.py for version)
Automatische slaap- én pneumologische scoring via YASA + Flask

Originele code volledig bewaard (auth, chunked upload, EDFProcessor).
v7:   Uitgebreide YASA-analyses, kanaalkeuze UI, PDF, Excel, job-polling.
v7.1: Pneumo-scoring (AHI, apnea-types, SpO2, positie, PLM, snurk),
      respiratoir kanaalkeuze, patiëntgegevens formulier,
      klinisch PSG-rapport (conform ASZ Aalst lay-out).

Domeinen: sleepai.be / sleepai.eu
"""

# ── matplotlib config-map VOOR alle andere imports ──────────────
import os
import time
import re
from pathlib import Path


def _init_mplconfigdir() -> str:
    mpl_dir = os.environ.get("MPLCONFIGDIR")
    if not mpl_dir:
        for candidate in (
            "/data/slaapkliniek/.mplconfig",
            "/tmp/yasaflaskified-mplconfig",
        ):
            try:
                os.makedirs(candidate, exist_ok=True)
                mpl_dir = candidate
                break
            except Exception:
                continue
        if not mpl_dir:
            mpl_dir = "/tmp"
        os.environ["MPLCONFIGDIR"] = mpl_dir
    try:
        os.makedirs(mpl_dir, exist_ok=True)
    except Exception:
        pass
    return mpl_dir


_MPLCONFIGDIR = _init_mplconfigdir()

# ── Standaard imports ────────────────────────────────────────────
import logging
logger = logging.getLogger('yasaflaskified')
import json
import uuid
import warnings
import traceback
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler

import mne
import yasa
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from werkzeug.middleware.proxy_fix import ProxyFix
from version import __version__ as APP_VERSION, PSGSCORING_VERSION
from flask import (
    Flask, request, jsonify, redirect, url_for,
    flash, session, send_from_directory, send_file,
    render_template, abort,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException
from flask_login import (
    LoginManager, UserMixin,
    login_user, login_required, logout_user, current_user,
)
from flask_wtf.csrf import CSRFProtect, CSRFError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from redis import Redis
from rq import Queue
from rq.job import Job, NoSuchJobError
from sqlalchemy import text

# Pneumo-analyse (nieuw v7.1)
from pneumo_analysis import detect_channels as pneumo_detect_channels

warnings.filterwarnings("ignore", category=FutureWarning)


# ═══════════════════════════════════════════════════════════════
# CONFIGURATIE  (config.json + omgevingsvariabelen)
# ═══════════════════════════════════════════════════════════════

config = {}
try:
    with open("config.json", "r") as _f:
        config = json.load(_f)
except FileNotFoundError:
    config = {}

app = Flask(__name__)


def _cfg(key, default=None):
    env_key = f"YASAFLASKIFIED_{key}"
    if env_key in os.environ:
        return os.environ.get(env_key)
    return config.get(key, default)


# Paden
app.config["UPLOAD_FOLDER"]    = _cfg("UPLOAD_FOLDER",    "/data/slaapkliniek/uploads")
app.config["PROCESSED_FOLDER"] = _cfg("PROCESSED_FOLDER", "/data/slaapkliniek/processed")

# Flask core
app.config["SECRET_KEY"]         = _cfg("SECRET_KEY", "supersecretkey")
if app.config["SECRET_KEY"] == "supersecretkey":
    logger.warning("⚠️  SECURITY: Using default SECRET_KEY! Set YASAFLASKIFIED_SECRET_KEY in .env")
app.config["MAX_CONTENT_LENGTH"] = int(_cfg("MAX_CONTENT_LENGTH", 500 * 1024 * 1024))
app.config["MPLCONFIGDIR"]       = _cfg("MPLCONFIGDIR", os.environ.get("MPLCONFIGDIR", _MPLCONFIGDIR))

# Database
app.config["SQLALCHEMY_DATABASE_URI"]        = _cfg(
    "SQLALCHEMY_DATABASE_URI",
    "sqlite:////data/slaapkliniek/instance/users.db",
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = bool(config.get("SQLALCHEMY_TRACK_MODIFICATIONS", False))

# Sessie
app.config.update(
    SESSION_COOKIE_HTTPONLY   = True,
    SESSION_COOKIE_SAMESITE   = "Lax",
    SESSION_COOKIE_SECURE     = _cfg("SESSION_COOKIE_SECURE", "0") == "1",
    PERMANENT_SESSION_LIFETIME = timedelta(hours=int(_cfg("SESSION_LIFETIME_HOURS", 24))),
    REMEMBER_COOKIE_DURATION   = timedelta(days=7),
    REMEMBER_COOKIE_HTTPONLY   = True,
    REMEMBER_COOKIE_SAMESITE   = "Lax",
    WTF_CSRF_TIME_LIMIT       = 3600,
)

# Mappen aanmaken
for _d in [
    app.config["UPLOAD_FOLDER"],
    app.config["PROCESSED_FOLDER"],
    os.path.dirname(app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:////", "/")),
]:
    os.makedirs(_d, exist_ok=True)


# ═══════════════════════════════════════════════════════════════
# EXTENSIES
# ═══════════════════════════════════════════════════════════════

db            = SQLAlchemy(app)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
csrf          = CSRFProtect(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Redis + RQ
_redis_host = _cfg("REDIS_HOST", "localhost")
_redis_port = int(_cfg("REDIS_PORT", 6379))
try:
    redis_conn = Redis(host=_redis_host, port=_redis_port, decode_responses=False)
    redis_conn.ping()
except Exception as _e:
    logger.warning("Redis niet bereikbaar bij opstarten: %s", _e)
    redis_conn = Redis(host=_redis_host, port=_redis_port, decode_responses=False)

queue = Queue(connection=redis_conn)

# Rate limiting
if _cfg("ENABLE_RATE_LIMITING", True):
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["10000 per hour", "100000 per day"],
        storage_uri=f"redis://{_redis_host}:{_redis_port}",
    )
else:
    limiter = Limiter(app=app, key_func=get_remote_address, enabled=False)


# ═══════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════

_log_file = _cfg("LOG_FILE", "/var/log/yasaflaskified/app.log")
os.makedirs(os.path.dirname(_log_file), exist_ok=True)

_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
_fh = RotatingFileHandler(_log_file, maxBytes=5_000_000, backupCount=3)
_fh.setFormatter(_formatter)
_ch = logging.StreamHandler()
_ch.setFormatter(_formatter)

_log_level = getattr(logging, _cfg("LOG_LEVEL", "INFO"))
logging.basicConfig(level=_log_level, handlers=[_fh, _ch])
app.logger.setLevel(_log_level)
app.logger.addHandler(_fh)


# ═══════════════════════════════════════════════════════════════
# DATABASE MODELLEN  (v9.1 + v12)
# ═══════════════════════════════════════════════════════════════

class Site(db.Model):
    """Ziekenhuis / locatie. Elke user behoort tot max. 1 site."""
    id        = db.Column(db.Integer, primary_key=True)
    name      = db.Column(db.String(200), nullable=False)
    address   = db.Column(db.String(300), default="")
    phone     = db.Column(db.String(50),  default="")
    email     = db.Column(db.String(150), default="")
    logo_path = db.Column(db.String(300), default="")
    url       = db.Column(db.String(200), default="")
    language  = db.Column(db.String(5),   default="nl")
    users     = db.relationship("User", backref="site", lazy=True)

    def to_config_dict(self):
        return {
            "name":      self.name,
            "address":   self.address,
            "phone":     self.phone,
            "email":     self.email,
            "logo_path": self.logo_path,
            "url":       self.url,
        }


class User(UserMixin, db.Model):
    """
    Rollen (v9.1):
      admin  — volledige toegang, alle sites, gebruikersbeheer overal
      site   — beheert één site: eigen patiënten + gebruikers aanmaken
      user   — uploaden + eigen resultaten + resultaten eigen site (r/o)
    """
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role     = db.Column(db.String(20),  nullable=False, default="user")
    site_id  = db.Column(db.Integer, db.ForeignKey("site.id"), nullable=True)
    language = db.Column(db.String(5),   nullable=False, default="nl")

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def is_site_manager(self):
        return self.role in ("admin", "site")

    @property
    def can_see_all_sites(self):
        return self.role == "admin"

    @property
    def site_config(self):
        return self.site.to_config_dict() if self.site else None


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ═══════════════════════════════════════════════════════════════
# HULPKLASSEN — origineel volledig bewaard
# ═══════════════════════════════════════════════════════════════

class UploadError(Exception):
    pass


class EDFProcessingError(Exception):
    pass


def validate_password_strength(password):
    if not _cfg("REQUIRE_STRONG_PASSWORDS", True):
        return True, "Password accepted"
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number"
    return True, "Password is strong"


class FileUploadHandler:
    """Chunked upload — volledig origineel bewaard."""

    def __init__(self, upload_dir, redis_connection):
        self.upload_dir = upload_dir
        self.redis_conn = redis_connection
        os.makedirs(upload_dir, exist_ok=True)

    def validate_chunk_params(self, file_id, chunk_index, total_chunks, original_filename):
        if not file_id or not isinstance(file_id, str):
            raise UploadError("Invalid file_id")
        if not isinstance(chunk_index, int) or chunk_index < 0:
            raise UploadError("Invalid chunk_index")
        if not isinstance(total_chunks, int) or total_chunks < 1:
            raise UploadError("Invalid total_chunks")
        if chunk_index >= total_chunks:
            raise UploadError("chunk_index must be less than total_chunks")
        if not original_filename:
            raise UploadError("Missing original_filename")
        return True

    def sanitize_filename(self, filename):
        filename = secure_filename(filename.strip())
        filename = os.path.basename(filename)
        if not filename.lower().endswith(".edf"):
            filename = f"{filename}.edf"
        if len(filename) > 255:
            raise UploadError("Filename too long")
        if not filename or filename == ".edf":
            raise UploadError("Invalid filename")
        return filename

    def save_chunk(self, file_id, chunk_index, chunk_file):
        chunk_path = os.path.join(self.upload_dir, f"{file_id}_chunk_{chunk_index}")
        try:
            chunk_file.save(chunk_path)
            logger.info(f"Saved chunk {chunk_index} for file_id {file_id}")
            return chunk_path
        except Exception as e:
            logger.error(f"Failed to save chunk {chunk_index}: {e}")
            raise UploadError(f"Failed to save chunk: {str(e)}")

    def assemble_file(self, file_id, total_chunks, final_filename):
        assembled_path = os.path.join(self.upload_dir, f"{file_id}_assembled.edf")
        final_path     = os.path.join(self.upload_dir, final_filename)
        if os.path.exists(final_path):
            timestamp  = int(time.time())
            final_path = os.path.join(
                self.upload_dir,
                f"{os.path.splitext(final_filename)[0]}_{timestamp}.edf",
            )
            logger.warning(f"File exists, using new name: {final_path}")
        try:
            with open(assembled_path, "wb") as af:
                for i in range(total_chunks):
                    chunk_path = os.path.join(self.upload_dir, f"{file_id}_chunk_{i}")
                    if not os.path.exists(chunk_path):
                        raise FileNotFoundError(f"Missing chunk {i}")
                    with open(chunk_path, "rb") as cf:
                        af.write(cf.read())
                    os.remove(chunk_path)
            os.rename(assembled_path, final_path)
            logger.info(f"File assembled successfully: {final_path}")
            return final_path
        except Exception as e:
            if os.path.exists(assembled_path):
                os.remove(assembled_path)
            for i in range(total_chunks):
                cp = os.path.join(self.upload_dir, f"{file_id}_chunk_{i}")
                if os.path.exists(cp):
                    try:
                        os.remove(cp)
                    except Exception:
                        pass
            logger.error(f"Assembly failed: {e}")
            raise UploadError(f"Failed to assemble file: {str(e)}")

    def update_progress(self, file_id, progress):
        try:
            self.redis_conn.set(f"{file_id}_progress", progress, ex=3600)
        except Exception as e:
            logger.warning(f"Failed to update progress: {e}")

    def mark_completed(self, file_id, filepath):
        try:
            self.redis_conn.set(f"{file_id}_filepath", filepath, ex=3600)
            self.redis_conn.set(f"{file_id}_completed", 1, ex=3600)
            self.redis_conn.set(f"{file_id}_progress", 100, ex=3600)
        except Exception as e:
            logger.warning(f"Failed to mark completed: {e}")


class EDFProcessor:
    """Originele EDF-verwerking — volledig bewaard voor achterwaartse compatibiliteit."""

    def __init__(self, mpl_config_dir=None):
        if mpl_config_dir:
            plt.rcParams["savefig.directory"] = mpl_config_dir

    def parse_channels(self, filepath):
        try:
            edf      = mne.io.read_raw_edf(filepath, preload=False, verbose=False)
            channels = edf.info["ch_names"]
            eeg_ch   = self._identify_eeg_channels(channels)
            eog_ch   = self._identify_eog_channels(channels)
            emg_ch   = self._identify_emg_channels(channels)
            ecg_ch   = self._identify_ecg_channels(channels)
            other_ch = [ch for ch in channels if ch not in eeg_ch + eog_ch + emg_ch + ecg_ch]
            logger.info(f"Parsed {filepath}: EEG={len(eeg_ch)}, EOG={len(eog_ch)}, EMG={len(emg_ch)}")
            return {
                "eeg": eeg_ch, "eog": eog_ch,
                "emg": emg_ch, "ecg": ecg_ch,
                "others": other_ch, "all": channels,
            }
        except Exception as e:
            logger.error(f"Failed to parse EDF channels: {e}")
            raise EDFProcessingError(f"Failed to parse EDF file: {str(e)}")

    def _identify_eeg_channels(self, channels):
        patterns = ["FP","F","C","P","O","T","AF","FC","CP","PO","TP","FZ","CZ","PZ","OZ","EEG"]
        result = []
        for ch in channels:
            ch_upper = ch.upper()
            if any(ch_upper.startswith(p) for p in patterns):
                result.append(ch)
            elif ch_upper in ["A1","A2","M1","M2"]:
                result.append(ch)
        return result

    def _identify_eog_channels(self, channels):
        kw = ["EOG","E1","E2","LOC","ROC"]
        return [ch for ch in channels if any(k in ch.upper() for k in kw)]

    def _identify_emg_channels(self, channels):
        kw = ["EMG","CHIN","LEG","TIBIAL"]
        return [ch for ch in channels if any(k in ch.upper() for k in kw)]

    def _identify_ecg_channels(self, channels):
        kw = ["ECG","EKG","CARDIAC"]
        return [ch for ch in channels if any(k in ch.upper() for k in kw)]

    def process_sleep_staging(self, filepath, selected_channels, output_dir):
        """Originele pipeline: hypnogram PDF + CSV + statistieken .txt."""
        try:
            edf = mne.io.read_raw_edf(filepath, preload=True, verbose=False)
            eeg_channels = selected_channels.get("eeg", [])
            if not eeg_channels:
                all_channels = self.parse_channels(filepath)
                eeg_channels = all_channels["eeg"]
                if not eeg_channels:
                    raise EDFProcessingError("No EEG channels found for sleep staging")
            eeg_channel = eeg_channels[0]
            if eeg_channel not in edf.ch_names:
                raise EDFProcessingError(f"Selected EEG channel '{eeg_channel}' not found in data")
            logger.info(f"Running sleep staging with channel: {eeg_channel}")
            sls        = yasa.SleepStaging(edf, eeg_name=eeg_channel)
            hypno_pred = sls.predict()
            hypno_int  = yasa.hypno_str_to_int(hypno_pred)
            metadata   = self._extract_metadata(edf, selected_channels)
            pdf_path   = self._generate_hypnogram(hypno_int, filepath, metadata, output_dir)
            csv_path   = self._save_hypnogram_csv(hypno_int, filepath, output_dir)
            stats_path = self._save_sleep_statistics(hypno_int, filepath, output_dir)
            return {"pdf": pdf_path, "csv": csv_path, "stats": stats_path, "metadata": metadata}
        except Exception as e:
            logger.error(f"Sleep staging failed: {e}", exc_info=True)
            raise EDFProcessingError(f"Sleep staging failed: {str(e)}")

    def _extract_metadata(self, edf, selected_channels):
        info      = edf.info
        meas_date = info.get("meas_date")
        meas_date_str = meas_date.strftime("%Y-%m-%d %H:%M:%S") if meas_date else "Unknown"
        subject_info  = info.get("subject_info", {})
        parts = []
        for ch_type in ["eeg","eog","emg"]:
            chs = selected_channels.get(ch_type, [])
            if chs:
                parts.append(f"{ch_type.upper()}: {', '.join(chs)}")
        return {
            "recording_date":   meas_date_str,
            "patient_id":       subject_info.get("id", "Unknown"),
            "patient_name":     subject_info.get("his_id", "Unknown"),
            "channels_used":    "; ".join(parts) if parts else "Auto-detected",
            "duration_seconds": edf.n_times / edf.info["sfreq"],
            "sampling_rate":    edf.info["sfreq"],
        }

    def _generate_hypnogram(self, hypno_int, filepath, metadata, output_dir):
        filename    = Path(filepath).stem
        output_path = Path(output_dir) / f"{filename}_hypnogram.pdf"
        plt.figure(figsize=(11.69, 8.27))
        yasa.plot_hypnogram(hypno_int)
        title_text = (
            f"Sleep Hypnogram: {filename}\n"
            f"Recording Date: {metadata['recording_date']} | "
            f"Duration: {metadata['duration_seconds']/3600:.2f} hours\n"
            f"Channels: {metadata['channels_used']}\n"
            f"Patient ID: {metadata['patient_id']}"
        )
        plt.suptitle(title_text, fontsize=9, ha="center", va="top", y=0.98)
        plt.tight_layout(rect=[0, 0, 1, 0.92])
        plt.savefig(output_path, format="pdf", orientation="landscape", dpi=300)
        plt.close()
        logger.info(f"Generated hypnogram: {output_path}")
        return str(output_path)

    def _save_hypnogram_csv(self, hypno_int, filepath, output_dir):
        filename    = Path(filepath).stem
        output_path = Path(output_dir) / f"{filename}_hypnogram.csv"
        df = pd.DataFrame({
            "epoch":            np.arange(len(hypno_int)),
            "onset_seconds":    np.arange(len(hypno_int)) * 30,
            "stage":            hypno_int,
            "stage_label":      [yasa.hypno_int_to_str([s])[0] for s in hypno_int],
            "duration_seconds": 30,
        })
        df.to_csv(output_path, index=False)
        logger.info(f"Saved hypnogram CSV: {output_path}")
        return str(output_path)

    def _save_sleep_statistics(self, hypno_int, filepath, output_dir):
        filename    = Path(filepath).stem
        output_path = Path(output_dir) / f"{filename}_statistics.txt"
        stats = {
            "Total epochs":           len(hypno_int),
            "Total duration (hours)": len(hypno_int) * 30 / 3600,
        }
        stage_names = {-2:"Unscored",-1:"Artifact",0:"Wake",1:"N1",2:"N2",3:"N3",4:"REM"}
        for stage_int, stage_name in stage_names.items():
            count = np.sum(hypno_int == stage_int)
            if count > 0:
                duration_min = count * 30 / 60
                percentage   = (count / len(hypno_int)) * 100
                stats[f"{stage_name} (minutes)"] = f"{duration_min:.1f}"
                stats[f"{stage_name} (%)"]        = f"{percentage:.1f}%"
        with open(output_path, "w") as f:
            f.write(f"Sleep Statistics for {filename}\n")
            f.write("=" * 50 + "\n\n")
            for key, value in stats.items():
                f.write(f"{key}: {value}\n")
        logger.info(f"Saved statistics: {output_path}")
        return str(output_path)


# ═══════════════════════════════════════════════════════════════
# JINJA2 FILTERS
# ═══════════════════════════════════════════════════════════════

@app.template_filter("channel_type_badge")
def channel_type_badge(ch_name: str) -> str:
    ch = ch_name.upper()
    if any(x in ch for x in ["EOG","LOC","ROC","E1","E2"]):
        return '<span class="badge bg-warning text-dark">EOG</span>'
    if any(x in ch for x in ["EMG","CHIN","LEG","TIBIAL"]):
        return '<span class="badge bg-danger">EMG</span>'
    if any(x in ch for x in ["EEG","C3","C4","F3","F4","O1","O2","FZ","CZ","PZ"]):
        return '<span class="badge bg-primary">EEG</span>'
    if any(x in ch for x in ["ECG","EKG","CARDIAC"]):
        return '<span class="badge bg-success">ECG</span>'
    if any(x in ch for x in ["FLOW","NASAL","THERM"]):
        return '<span class="badge bg-info text-dark">RESP</span>'
    if any(x in ch for x in ["SPO2","SAO2"]):
        return '<span class="badge bg-success">SpO2</span>'
    return '<span class="badge bg-secondary">?</span>'


@app.template_filter("duration_fmt")
def duration_fmt(minutes):
    try:
        m = int(float(minutes))
        return f"{m // 60}h {m % 60}m"
    except (TypeError, ValueError):
        return "—"


app.jinja_env.globals["now"] = datetime.utcnow

# ── i18n (meertalig NL/FR/EN) ──
from i18n import (get_translation, TRANSLATIONS, DEFAULT_LANG,
                  LANG_NAMES, LANG_FLAGS, SUPPORTED_LANGS)

from functools import wraps


def requires_role(*roles):
    """Decoreer routes: @requires_role("admin") of @requires_role("admin","site")."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("login"))
            if current_user.role not in roles:
                flash(get_translation("insufficient_rights",
                                      session.get("lang", "nl")), "danger")
                return redirect(url_for("upload_file"))
            return f(*args, **kwargs)
        return decorated
    return decorator


@app.context_processor
def inject_i18n():
    """Injecteer vertaalfunctie en taalinfo in elke template.

    v0.8.11: LEEST session["lang"], schrijft er NOOIT naar.
    Schrijven naar session op elke request veroorzaakte Set-Cookie headers
    op elke response → redirect loops met Nginx proxy.
    """
    # Bepaal taal: session (gezet bij login) → user.language → default
    lang = session.get("lang", None)
    if not lang:
        try:
            if current_user.is_authenticated and current_user.language:
                lang = current_user.language
        except Exception:
            pass
    if not lang or lang not in SUPPORTED_LANGS:
        lang = DEFAULT_LANG

    def t(key):
        return get_translation(key, lang)

    _site = None
    try:
        if current_user.is_authenticated:
            _site = current_user.site
    except Exception:
        pass

    return {
        "t":            t,
        "LANGS":        LANG_NAMES,
        "LANG_FLAGS":   LANG_FLAGS,
        "current_lang": lang,
        "SUPPORTED_LANGS": SUPPORTED_LANGS,
        "current_site": _site,
        "APP_VERSION":  APP_VERSION,
        "PSGSCORING_VERSION": PSGSCORING_VERSION,
    }


@app.before_request
def _ensure_permanent_session():
    # v0.8.11: alleen zetten als nog niet permanent (voorkomt onnodige Set-Cookie)
    if not session.get("_fresh_set"):
        session.permanent = True
        session["_fresh_set"] = True


@app.route("/lang/<lang_code>")
def set_language(lang_code):
    """Wissel taal, sla op in session + DB, ga terug naar vorige pagina."""
    if lang_code in SUPPORTED_LANGS:
        session["lang"] = lang_code
        session.modified = True
        # v0.8.11: ook opslaan in user-profiel
        try:
            if current_user.is_authenticated:
                current_user.language = lang_code
                db.session.commit()
        except Exception:
            pass
    ref = request.referrer
    if ref and "/lang/" in ref:
        ref = None
    return redirect(ref or url_for("login"))


# ═══════════════════════════════════════════════════════════════
# HULPFUNCTIES
# ═══════════════════════════════════════════════════════════════

def _json_serializer(obj):
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    return str(obj)


def _load_results(job_id: str) -> dict:
    result_file = os.path.join(app.config["UPLOAD_FOLDER"], f"{job_id}_results.json")
    if not os.path.exists(result_file):
        abort(404, description="Resultaten niet gevonden.")
    with open(result_file) as f:
        return json.load(f)


# ═══════════════════════════════════════════════════════════════
# v0.8.11: MULTI-SITE TOEGANGSCONTROLE
# ═══════════════════════════════════════════════════════════════

def _get_job_site_id(job_id: str) -> int | None:
    """Haal site_id op voor een job (uit results.json of config.json)."""
    upload_folder = app.config["UPLOAD_FOLDER"]
    for suffix in ("_results.json", "_config.json"):
        path = os.path.join(upload_folder, f"{job_id}{suffix}")
        if os.path.exists(path):
            try:
                with open(path) as f:
                    data = json.load(f)
                sid = data.get("site_id")
                if sid is not None:
                    return int(sid)
            except Exception:
                pass
    return None


def _check_job_access(job_id: str) -> bool:
    """
    Controleer of current_user toegang heeft tot job_id.

    Regels (v0.8.11):
      admin  → altijd toegang (alle sites)
      site   → alleen als job.site_id == user.site_id
      user   → alleen als job.site_id == user.site_id OF zelf aangemaakt
    """
    if not current_user.is_authenticated:
        return False
    if current_user.role == "admin":
        return True

    job_site = _get_job_site_id(job_id)

    # Als job geen site_id heeft (legacy data van voor multi-site)
    # v0.8.11 FIX: enkel admin of de eigenaar heeft toegang
    if job_site is None:
        if current_user.role == "admin":
            return True
        # Check of de user de eigenaar is
        try:
            result_path = os.path.join(
                app.config["UPLOAD_FOLDER"], f"{job_id}_results.json")
            if os.path.exists(result_path):
                with open(result_path) as f:
                    data = json.load(f)
                if data.get("owner_username") == current_user.username:
                    return True
        except Exception:
            pass
        return False

    # Site-admin of user: alleen eigen site
    if current_user.site_id is not None and job_site == current_user.site_id:
        return True

    return False


def _require_job_access(job_id: str):
    """Abort 403 als current_user geen toegang heeft tot job_id."""
    if not _check_job_access(job_id):
        logger.warning("Toegang geweigerd: %s probeert job %s te openen (site %s vs %s)",
                       current_user.username, job_id,
                       current_user.site_id, _get_job_site_id(job_id))
        abort(403, description="Geen toegang tot deze studie.")


def _filter_studies_for_user(json_files: list) -> list:
    """
    Filter een lijst van result-bestanden op basis van site-toegang.

    v0.8.11: Centrale filterfunctie voor dashboard EN results-history.
    """
    upload_folder = app.config["UPLOAD_FOLDER"]
    filtered = []
    for jf in json_files:
        job_id = os.path.basename(jf).replace("_results.json", "")
        try:
            with open(jf) as f:
                data = json.load(f)
        except Exception:
            continue

        # Admin ziet alles
        if current_user.role == "admin":
            filtered.append((job_id, data, jf))
            continue

        stored_site = data.get("site_id")
        owner       = data.get("owner_username", "")

        # Geen site_id (legacy data van voor multi-site)
        # v0.8.11 FIX: enkel admin ziet legacy studies zonder site_id.
        # Site-managers en users zien alleen studies van hun eigen site.
        if stored_site is None:
            if current_user.role == "admin":
                filtered.append((job_id, data, jf))
            elif owner == current_user.username:
                # Eigen studie, ook al heeft die geen site_id
                filtered.append((job_id, data, jf))
            continue

        # Eigen site
        if current_user.site_id is not None and int(stored_site) == current_user.site_id:
            filtered.append((job_id, data, jf))
            continue

        # Eigen studie (voor users zonder site_id)
        if owner == current_user.username:
            filtered.append((job_id, data, jf))
            continue

    return filtered


def _looks_like_werkzeug_hash(value: str) -> bool:
    if not value:
        return False
    return value.startswith(("pbkdf2:","scrypt:","argon2:"))


def _sqlite_columns(table_name: str) -> list:
    try:
        with db.engine.connect() as conn:
            rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
            return [r[1] for r in rows]
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════
# AUTH ROUTES  — volledig origineel bewaard
# ═══════════════════════════════════════════════════════════════

@app.route("/login", methods=["GET","POST"])
@limiter.limit("5 per minute")
def login():
    # v0.8.11: als al ingelogd → door naar app
    if request.method == "GET" and current_user.is_authenticated:
        if current_user.role in ("admin", "site"):
            return redirect(url_for("dashboard"))
        return redirect(url_for("upload_file"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            flash(get_translation("login_failed", session.get("lang", "nl")), "danger")
            return redirect(url_for("login"))
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user, remember=True)
            session.permanent = True
            # v0.8.11 FIX: taal uit USER DATABASE, niet uit formulier
            # Het login-formulier heeft geen lang_select veld.
            # De user.language is gezet via admin user management.
            user_lang = getattr(user, "language", None) or "nl"
            if user_lang not in SUPPORTED_LANGS:
                user_lang = "nl"
            session["lang"] = user_lang
            session.modified = True
            flash(get_translation("login_success", user_lang), "success")
            next_page = request.args.get("next")
            if next_page:
                return redirect(next_page)
            if user.role in ("admin", "site"):
                return redirect(url_for("dashboard"))
            return redirect(url_for("upload_file"))
        logger.warning(f"Failed login for {username} from {request.remote_addr}")
        flash(get_translation("login_failed", session.get("lang", "nl")), "danger")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash(get_translation("logged_out", session.get("lang","nl")), "info")
    return redirect(url_for("login"))


@app.route("/register", methods=["GET","POST"])
@login_required
def register():
    if current_user.username != "admin":
        flash(get_translation("admin_only", session.get("lang","nl")), "danger")
        return redirect(url_for("upload_file"))
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if not username or not password:
            flash(get_translation("all_fields_required", session.get("lang","nl")), "danger")
            return redirect(url_for("register"))
        is_valid, message = validate_password_strength(password)
        if not is_valid:
            flash(message, "danger")
            return redirect(url_for("register"))
        if User.query.filter_by(username=username).first():
            flash(get_translation("username_exists", session.get("lang","nl")), "danger")
            return redirect(url_for("register"))
        hashed = generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)
        db.session.add(User(username=username, password=hashed))
        db.session.commit()
        logger.info(f"New user registered: {username}")
        flash(get_translation("user_created", session.get("lang","nl")), "success")
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/change_password", methods=["GET","POST"])
@login_required
def change_password():
    if request.method == "POST":
        current_password = request.form.get("current_password")
        new_password     = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")
        if not all([current_password, new_password, confirm_password]):
            flash(get_translation("all_fields_required", session.get("lang","nl")), "danger")
            return redirect(url_for("change_password"))
        if not check_password_hash(current_user.password, current_password):
            flash(get_translation("wrong_password", session.get("lang","nl")), "danger")
            return redirect(url_for("change_password"))
        if new_password != confirm_password:
            flash(get_translation("password_mismatch", session.get("lang","nl")), "danger")
            return redirect(url_for("change_password"))
        is_valid, message = validate_password_strength(new_password)
        if not is_valid:
            flash(message, "danger")
            return redirect(url_for("change_password"))
        current_user.password = generate_password_hash(
            new_password, method="pbkdf2:sha256", salt_length=16)
        db.session.commit()
        flash(get_translation("password_changed", session.get("lang","nl")), "success")
        return redirect(url_for("upload_file"))
    return render_template("change_password.html")


# ═══════════════════════════════════════════════════════════════
# ADMIN — GEBRUIKERSBEHEER  (v9.1)
# ═══════════════════════════════════════════════════════════════

def _is_admin():
    return current_user.is_authenticated and current_user.role == "admin"


@app.route("/admin/users")
@login_required
@requires_role("admin", "site")
def admin_users():
    # v0.8.11 FIX: site-managers zien enkel hun eigen site-users
    if current_user.role == "admin":
        users = User.query.order_by(User.id).all()
        sites = Site.query.order_by(Site.name).all()
    else:
        # Site-manager: alleen users van eigen site
        users = User.query.filter_by(site_id=current_user.site_id).order_by(User.id).all()
        sites = [current_user.site] if current_user.site else []
    return render_template("admin_users.html", users=users, sites=sites)


@app.route("/admin/users/add", methods=["POST"])
@login_required
@requires_role("admin", "site")
def admin_add_user():
    username = request.form.get("new_username", "").strip()
    password = request.form.get("new_password", "").strip()
    role     = request.form.get("new_role",     "user").strip()
    site_id  = request.form.get("new_site_id",  "").strip() or None
    lang     = request.form.get("new_lang",     "nl").strip()

    # Site-managers kunnen enkel 'user' aanmaken voor hun eigen site
    if current_user.role == "site":
        role    = "user"
        site_id = str(current_user.site_id) if current_user.site_id else None

    if role not in ("admin", "site", "user"):
        role = "user"
    if lang not in SUPPORTED_LANGS:
        lang = "nl"

    if not username or not password:
        flash(get_translation("all_fields_required", session.get("lang","nl")), "danger")
        return redirect(url_for("admin_users"))
    is_valid, message = validate_password_strength(password)
    if not is_valid:
        flash(message, "danger")
        return redirect(url_for("admin_users"))
    if User.query.filter_by(username=username).first():
        flash(f"{username}: " + get_translation("user_exists", session.get("lang","nl")), "danger")
        return redirect(url_for("admin_users"))
    hashed = generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)
    db.session.add(User(
        username=username, password=hashed,
        role=role, site_id=int(site_id) if site_id else None, language=lang))
    db.session.commit()
    logger.info(f"Admin created user: {username} (role={role}, site={site_id})")
    flash(f"{username}: " + get_translation("user_created", session.get("lang","nl")), "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/users/<int:user_id>/reset", methods=["POST"])
@login_required
@requires_role("admin", "site")
def admin_reset_password(user_id):
    user = User.query.get_or_404(user_id)
    # Site-managers mogen enkel hun eigen site-users resetten
    if current_user.role == "site" and user.site_id != current_user.site_id:
        abort(403)
    new_pw = request.form.get("reset_password", "").strip()
    if not new_pw:
        flash(get_translation("all_fields_required", session.get("lang","nl")), "danger")
        return redirect(url_for("admin_users"))
    is_valid, message = validate_password_strength(new_pw)
    if not is_valid:
        flash(message, "danger")
        return redirect(url_for("admin_users"))
    user.password = generate_password_hash(new_pw, method="pbkdf2:sha256", salt_length=16)
    db.session.commit()
    logger.info(f"Admin reset password for: {user.username}")
    flash(f"{user.username}: " + get_translation("password_changed", session.get("lang","nl")), "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@login_required
@requires_role("admin", "site")
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.username == "admin":
        flash(get_translation("admin_cannot_delete", session.get("lang","nl")), "danger")
        return redirect(url_for("admin_users"))
    if current_user.role == "site" and user.site_id != current_user.site_id:
        abort(403)
    logger.info(f"Admin deleted user: {user.username}")
    db.session.delete(user)
    db.session.commit()
    flash(f"{user.username}: " + get_translation("user_deleted", session.get("lang","nl")), "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/users/<int:user_id>/role", methods=["POST"])
@login_required
@requires_role("admin")
def admin_set_role(user_id):
    user = User.query.get_or_404(user_id)
    if user.username == "admin":
        flash(get_translation("admin_role_fixed", session.get("lang","nl")), "danger")
        return redirect(url_for("admin_users"))
    new_role = request.form.get("role", "user").strip()
    if new_role not in ("admin", "site", "user"):
        flash(get_translation("invalid_role", session.get("lang","nl")), "danger")
        return redirect(url_for("admin_users"))
    site_id  = request.form.get("site_id", "").strip() or None
    lang     = request.form.get("language", "nl").strip()
    user.role    = new_role
    user.site_id = int(site_id) if site_id else None
    user.language= lang if lang in SUPPORTED_LANGS else "nl"
    db.session.commit()
    logger.info(f"Admin updated {user.username}: role={new_role}, site={site_id}")
    flash(f"{user.username}: " + get_translation("user_updated", session.get("lang","nl")), "success")
    return redirect(url_for("admin_users"))


# ── Sitebeheer ──────────────────────────────────────────────────

@app.route("/admin/sites")
@login_required
@requires_role("admin")
def admin_sites():
    sites = Site.query.order_by(Site.name).all()
    return render_template("admin_sites.html", sites=sites)


@app.route("/admin/sites/add", methods=["POST"])
@login_required
@requires_role("admin")
def admin_add_site():
    name = request.form.get("name", "").strip()
    if not name:
        flash(get_translation("site_name_required", session.get("lang","nl")), "danger")
        return redirect(url_for("admin_sites"))
    lang = request.form.get("language", "nl")
    if lang not in SUPPORTED_LANGS:
        lang = "nl"
    site = Site(
        name=name,
        address  =request.form.get("address",   "").strip(),
        phone    =request.form.get("phone",     "").strip(),
        email    =request.form.get("email",     "").strip(),
        logo_path=request.form.get("logo_path", "").strip(),
        url      =request.form.get("url",       "").strip(),
        language =lang,
    )
    db.session.add(site)
    db.session.commit()
    flash(f"{name}: " + get_translation("site_created", session.get("lang","nl")), "success")
    return redirect(url_for("admin_sites"))


@app.route("/admin/sites/<int:site_id>/edit", methods=["POST"])
@login_required
@requires_role("admin")
def admin_edit_site(site_id):
    site = Site.query.get_or_404(site_id)
    site.name     = request.form.get("name",      site.name).strip()
    site.address  = request.form.get("address",   "").strip()
    site.phone    = request.form.get("phone",     "").strip()
    site.email    = request.form.get("email",     "").strip()
    site.logo_path= request.form.get("logo_path", "").strip()
    site.url      = request.form.get("url",       "").strip()
    lang = request.form.get("language", "nl")
    site.language = lang if lang in SUPPORTED_LANGS else "nl"
    db.session.commit()
    flash(f"{site.name}: " + get_translation("site_updated", session.get("lang","nl")), "success")
    return redirect(url_for("admin_sites"))


@app.route("/admin/sites/<int:site_id>/delete", methods=["POST"])
@login_required
@requires_role("admin")
def admin_delete_site(site_id):
    site = Site.query.get_or_404(site_id)
    if site.users:
        flash(f"{site.name}: " + get_translation("site_has_users", session.get("lang","nl")), "danger")
        return redirect(url_for("admin_sites"))
    name = site.name
    db.session.delete(site)
    db.session.commit()
    flash(f"{name}: " + get_translation("site_deleted", session.get("lang","nl")), "success")
    return redirect(url_for("admin_sites"))


# ═══════════════════════════════════════════════════════════════
# UPLOAD ROUTES — origineel bewaard
# ═══════════════════════════════════════════════════════════════

@app.route("/about")
def about():
    """Publieke landingspagina — geen login vereist."""
    return render_template("frontpage.html")


@app.route("/disclaimer")
def disclaimer_page():
    """Medical & clinical disclaimer — publiek toegankelijk."""
    return render_template("disclaimer.html")


@app.route("/")
def index():
    # v0.8.11: vermijd dubbele redirect (/ → /login → /dashboard)
    if current_user.is_authenticated:
        if current_user.role in ("admin", "site"):
            return redirect(url_for("dashboard"))
        return redirect(url_for("upload_file"))
    return redirect(url_for("login"))


@app.route("/upload", methods=["GET"])
@login_required
def upload_file():
    return render_template("upload.html")


@app.route("/upload_chunks", methods=["POST"])
@limiter.exempt
@login_required
@csrf.exempt
def upload_chunks():
    """Chunked EDF-upload — origineel volledig bewaard."""
    try:
        file_id = request.form.get("file_id")
        if not file_id:
            return jsonify({"success": False, "error": "Missing file_id"}), 400
        try:
            chunk_index  = int(request.form.get("chunk_index", 0))
            total_chunks = int(request.form.get("total_chunks", 1))
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "Invalid chunk parameters"}), 400

        original_filename = request.form.get("original_filename", "uploaded.edf")
        if "edf_file" not in request.files:
            return jsonify({"success": False, "error": "No file provided"}), 400
        chunk_file = request.files["edf_file"]
        if not chunk_file or chunk_file.filename == "":
            return jsonify({"success": False, "error": "Empty file"}), 400

        handler = FileUploadHandler(app.config["UPLOAD_FOLDER"], redis_conn)

        try:
            handler.validate_chunk_params(file_id, chunk_index, total_chunks, original_filename)
        except UploadError as e:
            return jsonify({"success": False, "error": str(e)}), 400

        try:
            final_filename = handler.sanitize_filename(original_filename)
        except UploadError as e:
            return jsonify({"success": False, "error": str(e)}), 400

        try:
            handler.save_chunk(file_id, chunk_index, chunk_file)
        except UploadError as e:
            return jsonify({"success": False, "error": str(e)}), 500

        progress = int(((chunk_index + 1) / total_chunks) * 50)
        handler.update_progress(file_id, progress)

        if chunk_index + 1 == total_chunks:
            try:
                filepath = handler.assemble_file(file_id, total_chunks, final_filename)
                handler.mark_completed(file_id, filepath)
                return jsonify({
                    "success":  True,
                    "filepath": filepath,
                    "progress": 100,
                    "message":  "File assembled successfully",
                })
            except UploadError as e:
                return jsonify({"success": False, "error": str(e)}), 500

        return jsonify({
            "success":  True,
            "progress": progress,
            "message":  f"Chunk {chunk_index + 1}/{total_chunks} uploaded",
        })
    except Exception as e:
        logger.error(f"Unexpected error in upload_chunks: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


@app.route("/parse_file", methods=["POST"])
@login_required
@csrf.exempt
def parse_file():
    """
    Parseert EDF-kanalen na assembly.
    UITGEBREID: genereert UUID job_id en slaat filepath op in Redis
    zodat /channel-select/<job_id> en /analyze dit kunnen ophalen.
    """
    try:
        file_id = request.form.get("file_id")
        if not file_id:
            return jsonify({"success": False, "error": "Missing file_id"}), 400

        filepath_bytes = redis_conn.get(f"{file_id}_filepath")
        if not filepath_bytes:
            return jsonify({"success": False, "error": "File not found. Please upload again."}), 400

        filepath = filepath_bytes.decode("utf-8")
        if not os.path.exists(filepath):
            return jsonify({"success": False, "error": "File no longer exists on server"}), 400

        try:
            processor = EDFProcessor(app.config["MPLCONFIGDIR"])
            channels  = processor.parse_channels(filepath)

            # ── NIEUW: UUID job_id voor uitgebreide analyse ──
            job_id = str(uuid.uuid4())
            redis_conn.set(f"{job_id}_filepath", filepath, ex=7200)       # 2 uur
            redis_conn.set(f"{job_id}_orig_file_id", file_id, ex=7200)
            logger.info(f"job_id {job_id} gekoppeld aan {filepath}")

            return jsonify({
                "success":  True,
                "job_id":   job_id,          # ← nieuw: frontend stuurt hiermee naar /channel-select/
                "eeg":      channels["eeg"],
                "eog":      channels["eog"],
                "emg":      channels["emg"],
                "ecg":      channels.get("ecg", []),
                "others":   channels["others"],
                "all":      channels["all"],
                "filepath": filepath,
                "message":  "File parsed successfully.",
            })
        except EDFProcessingError as e:
            logger.error(f"EDF processing error: {e}")
            return jsonify({"success": False, "error": f"Failed to parse EDF file: {str(e)}"}), 400
        except Exception as e:
            logger.error(f"Unexpected error parsing EDF: {e}", exc_info=True)
            return jsonify({"success": False, "error": "Failed to parse EDF file"}), 500

    except Exception as e:
        logger.error(f"Unexpected error in parse_file: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


@app.route("/upload_progress/<file_id>")
@login_required
def upload_progress(file_id):
    progress = redis_conn.get(f"{file_id}_progress")
    return jsonify({"progress": float(progress) if progress else 0})


@app.route("/progress_status", methods=["GET"])
@login_required
def progress_status():
    file_id   = request.args.get("file_id")
    progress  = redis_conn.get(f"{file_id}_progress")
    completed = redis_conn.get(f"{file_id}_completed")
    if progress is None or completed is None:
        return jsonify({"progress": 0, "completed": False}), 200
    return jsonify({"progress": int(progress), "completed": bool(int(completed))}), 200


# ═══════════════════════════════════════════════════════════════
# ORIGINELE VERWERKINGSROUTES — bewaard voor achterwaartse compat.
# ═══════════════════════════════════════════════════════════════

@app.route("/process_file", methods=["POST"])
@login_required
def process_file():
    """Originele enkelvoudige pipeline (hypnogram PDF/CSV/stats)."""
    raw_selected_channels = request.form.get("selected_channels", "{}").strip()
    filepath = request.form.get("filepath")
    if not filepath:
        flash(get_translation("invalid_file", session.get("lang","nl")), "danger")
        return redirect(url_for("upload_file"))
    try:
        selected_channels = json.loads(raw_selected_channels) if raw_selected_channels else {}
        job = queue.enqueue(
            "app.process_file_with_channels",
            filepath,
            selected_channels,
            job_timeout=int(_cfg("JOB_TIMEOUT_SECONDS", 6000)),
            result_ttl=3600,
        )
        logger.info(f"Job {job.id} enqueued for {filepath}")
        session["processed_files"] = session.get("processed_files", []) + [
            {"filename": os.path.basename(filepath), "job_id": job.id}
        ]
        flash(get_translation("processing_started", session.get("lang","nl")), "success")
        return redirect(url_for("processing"))
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON for selected_channels: {e}")
        flash(get_translation("invalid_channels", session.get("lang","nl")), "danger")
        return redirect(url_for("upload_file"))
    except Exception as e:
        logger.error(f"Error enqueuing file processing: {e}")
        flash(get_translation("processing_failed", session.get("lang","nl")), "danger")
        return redirect(url_for("upload_file"))


@app.route("/processing")
@login_required
def processing():
    """Originele statuspage voor enkelvoudige jobs."""
    processed_files = session.get("processed_files", [])
    job_statuses    = []
    updated_files   = []
    all_finished    = True

    for file_info in processed_files:
        try:
            job = Job.fetch(file_info["job_id"], connection=redis_conn)
            if job.is_failed:
                job_statuses.append({"filename": file_info["filename"], "status": "Failed"})
            elif not job.is_finished:
                job_statuses.append({"filename": file_info["filename"], "status": "Processing"})
                all_finished = False
            else:
                job_statuses.append({"filename": file_info["filename"], "status": "Finished"})
            updated_files.append(file_info)
        except Exception as e:
            logger.error(f"Error fetching job {file_info.get('job_id')}: {e}")
            job_statuses.append({"filename": file_info.get("filename","Unknown"), "status": "Missing"})
            all_finished = False
            updated_files.append(file_info)

    session["processed_files"] = updated_files
    if all_finished and processed_files:
        return redirect(url_for("results"))
    return render_template("processing.html", job_statuses=job_statuses)


def process_file_with_channels(filepath, selected_channels):
    """RQ worker taak — originele pipeline."""
    try:
        processor = EDFProcessor(app.config["MPLCONFIGDIR"])
        result    = processor.process_sleep_staging(
            filepath, selected_channels, app.config["PROCESSED_FOLDER"])
        logger.info(f"Successfully processed {filepath}")
        return result
    except Exception as e:
        logger.error(f"Error processing file {filepath}: {e}", exc_info=True)
        raise


@app.route("/results")
@login_required
def results():
    """Geschiedenispagina: gefilterd op site-toegang (v0.8.11)."""
    import glob
    upload_folder = app.config["UPLOAD_FOLDER"]
    json_files = sorted(
        glob.glob(os.path.join(upload_folder, "*_results.json")),
        key=os.path.getmtime, reverse=True
    )

    # v0.8.11: filter op site-toegang
    accessible = _filter_studies_for_user(json_files)

    studies = []
    for job_id, data, jf in accessible:
        try:
            meta = data.get("meta", {})
            pat = data.get("patient_info", {})
            stats = data.get("sleep_statistics", {}).get("stats", {})
            pneumo = data.get("pneumo", {}).get("respiratory", {}).get("summary", {})
            mtime = os.path.getmtime(jf)
            from datetime import datetime as _dt
            analyse_date = _dt.fromtimestamp(mtime).strftime("%d-%m-%Y %H:%M")

            studies.append({
                "job_id":       job_id,
                "patient_name": pat.get("patient_name", "—"),
                "patient_firstname": pat.get("patient_firstname", ""),
                "patient_id":   pat.get("patient_id", "—"),
                "date":         analyse_date,
                "duration_min": meta.get("duration_min", "—"),
                "eeg_ch":       meta.get("eeg_channel", "—"),
                "tst":          stats.get("TST", "—"),
                "se":           stats.get("SE", "—"),
                "ahi":          pneumo.get("ahi_total", "—"),
                "oahi":         pneumo.get("oahi", "—"),
                "severity":     pneumo.get("severity", "—"),
                "has_pdf":      os.path.exists(os.path.join(upload_folder, f"{job_id}_rapport.pdf")),
                "has_excel":    os.path.exists(os.path.join(upload_folder, f"{job_id}_rapport.xlsx")),
                "has_psg":      os.path.exists(os.path.join(upload_folder, f"{job_id}_rapport.pdf")),
                "has_edfplus":  os.path.exists(os.path.join(upload_folder, f"{job_id}_scored.edf")),
            })
        except Exception as e:
            logger.warning(f"Kon {jf} niet laden: {e}")

    return render_template("results_history.html", studies=studies)


@app.route("/download/<path:filename>")
@login_required
def download_file(filename):
    return send_from_directory(app.config["PROCESSED_FOLDER"], filename, as_attachment=True)


@app.route("/uploads/logos/<path:filename>")
@login_required
def serve_logo(filename):
    """v0.8.11: Serveer geüploade logo's voor rapport-preview."""
    logos_dir = os.path.join(os.path.dirname(__file__), "static", "logos")
    return send_from_directory(logos_dir, filename)


# ═══════════════════════════════════════════════════════════════
# NIEUW: KANAALKEUZE UI
# ═══════════════════════════════════════════════════════════════

@app.route("/channel-select/<job_id>")
@login_required
def channel_select(job_id):
    """
    Kanaalkeuze-pagina na EDF-upload.
    Toont zowel EEG/EOG/EMG-selectie als respiratoire kanaalkeuze
    en een formulier voor patiëntgegevens.
    """
    filepath_bytes = redis_conn.get(f"{job_id}_filepath")
    if not filepath_bytes:
        flash(get_translation("session_expired", session.get("lang","nl")), "danger")
        return redirect(url_for("upload_file"))

    filepath = filepath_bytes.decode("utf-8")
    if not os.path.exists(filepath):
        flash(get_translation("file_not_available", session.get("lang","nl")), "danger")
        return redirect(url_for("upload_file"))

    try:
        raw          = mne.io.read_raw_edf(filepath, preload=False, verbose=False)
        channels     = raw.ch_names
        sfreq        = raw.info["sfreq"]
        duration_min = round(raw.times[-1] / 60, 1)
        filename     = os.path.basename(filepath)

        recording_start = None
        try:
            meas_date = raw.info.get("meas_date")
            if meas_date:
                recording_start = meas_date.strftime("%Y-%m-%dT%H:%M")
        except Exception:
            pass

        # EEG/EOG/EMG auto-classificatie (originele EDFProcessor)
        processor = EDFProcessor()
        parsed    = processor.parse_channels(filepath)

        # Respiratoire kanaaldetectie (nieuw v7.1)
        pneumo_auto = pneumo_detect_channels(channels)

        # v0.8.11: Intelligente EEG-kanaalkeuze — YASA presteert best op C3/C4
        # Prioriteit: C4-M1 > C3-M2 > C4 > C3 > F4 > F3 > Cz > any EEG > first
        EEG_PRIORITY = [
            # Exacte referentieel (AASM standaard)
            "C4-M1", "C3-M2", "C4-A1", "C3-A2",
            # Met streepje-varianten
            "EEG C4-M1", "EEG C3-M2", "EEG C4-A1", "EEG C3-A2",
            # Monopolair centraal
            "C4", "C3", "EEG C4", "EEG C3",
            # Frontaal (goed voor slow waves)
            "F4-M1", "F3-M2", "F4", "F3", "EEG F4", "EEG F3",
            # Centraal z-lijn
            "Cz", "EEG Cz", "CZ", "EEG CZ",
            # Pariëtaal
            "P4", "P3", "EEG P4", "EEG P3",
            # Occipitaal (alpha-detectie)
            "O2", "O1", "EEG O2", "EEG O1",
        ]
        best_eeg = None
        ch_upper_map = {ch.upper().strip(): ch for ch in channels}
        for candidate in EEG_PRIORITY:
            if candidate.upper() in ch_upper_map:
                best_eeg = ch_upper_map[candidate.upper()]
                break
        # Fallback: eerste kanaal uit parsed EEG-lijst
        if not best_eeg and parsed.get("eeg"):
            best_eeg = parsed["eeg"][0]
        # Ultieme fallback: eerste kanaal
        if not best_eeg:
            best_eeg = channels[0] if channels else None
        logger.info("Beste EEG-kanaal: %s (uit %d kanalen)", best_eeg, len(channels))

        # Patiëntgegevens uit EDF-header (v0.8.22: eigen parser i.p.v. MNE)
        # MNE's subject_info is onbetrouwbaar: his_id bevat vaak patient_code
        # i.p.v. naam. Onze parser leest de raw 80-byte velden correct.
        from psgscoring.pipeline import _parse_edf_patient_info
        edf_pat = _parse_edf_patient_info(raw)

        edf_lastname = ""
        edf_firstname = ""
        if edf_pat.get("name"):
            parts = edf_pat["name"].split()
            if len(parts) >= 2:
                # v0.8.37: Handle Belgian/Dutch compound surnames
                # (Van, De, Van de, Van den, Van der, etc.)
                _PREFIXES = {
                    "van", "de", "den", "der", "het", "ten", "ter",
                    "le", "la", "du", "des", "von", "zu",
                }
                _COMPOUND = {
                    ("van", "de"), ("van", "den"), ("van", "der"),
                    ("van", "het"), ("de", "la"), ("von", "der"),
                }
                prefix_len = 0
                lp = [p.lower() for p in parts]
                # Check two-word prefix first (Van de, Van den, etc.)
                if len(lp) >= 3 and (lp[0], lp[1]) in _COMPOUND:
                    prefix_len = 2
                # Then single-word prefix (Van, De, etc.)
                elif len(lp) >= 3 and lp[0] in _PREFIXES:
                    prefix_len = 1

                if prefix_len > 0 and len(parts) > prefix_len + 1:
                    # Surname = prefix + next word(s) until we hit a clear firstname
                    # Heuristic: prefix + 1 word = surname, rest = firstname
                    edf_lastname = " ".join(parts[:prefix_len + 1])
                    edf_firstname = " ".join(parts[prefix_len + 1:])
                else:
                    edf_lastname = parts[0]
                    edf_firstname = " ".join(parts[1:])
            else:
                edf_lastname = edf_pat["name"]

        sex_str = {"M": "M", "F": "V"}.get(edf_pat.get("sex", ""), "")

        dob_str = ""
        if edf_pat.get("birthdate"):
            dob_str = edf_pat["birthdate"][:10]  # ISO date
        elif edf_pat.get("birthday_str"):
            dob_str = edf_pat["birthday_str"]

        patient_prefill = {
            "patient_id":        edf_pat.get("patient_code") or "",
            "patient_name":      edf_lastname,
            "patient_firstname": edf_firstname,
            "dob":               dob_str,
            "sex":               sex_str,
            "equipment":         edf_pat.get("equipment") or "",
            "technician":        edf_pat.get("technician") or "",
            "recording_date":    edf_pat.get("recording_date") or "",
        }

    except Exception as e:
        logger.error(f"Fout bij laden EDF voor kanaalkeuze: {e}", exc_info=True)
        flash(get_translation("edf_read_error", session.get("lang","nl")) + f": {e}", "danger")
        return redirect(url_for("upload_file"))

    return render_template(
        "channel_select.html",
        job_id           = job_id,
        channels         = channels,
        parsed           = parsed,
        pneumo_auto      = pneumo_auto,      # auto-gedetecteerde pneumo-kanalen
        best_eeg         = best_eeg,         # v0.8.11: optimaal EEG-kanaal
        sfreq            = sfreq,
        duration_min     = duration_min,
        filename         = filename,
        recording_start  = recording_start,
        patient_prefill  = patient_prefill,  # EDF-header patiëntdata
    )


# ═══════════════════════════════════════════════════════════════
# NIEUW: UITGEBREIDE ANALYSE STARTEN
# ═══════════════════════════════════════════════════════════════

@app.route("/analyze", methods=["POST"])
@login_required
def start_analysis():
    """
    Ontvangt volledige kanaalkeuze (EEG + pneumo) en patiëntgegevens,
    slaat config op en start de uitgebreide RQ-job:
    staging + spindles + SW + REM + bandpower + cycli + artefacten
    + pneumo (AHI, SpO2, positie, PLM, snurk) + PDF + Excel + PSG-rapport.
    """
    job_id    = request.form.get("job_id")
    eeg_ch    = request.form.get("eeg_ch")
    eog_ch    = request.form.get("eog_ch") or None
    emg_ch    = request.form.get("emg_ch") or None
    extra_eeg = request.form.getlist("extra_eeg_ch")
    rec_start = request.form.get("recording_start") or None

    # ── Pneumo-kanalen (v7.1) ──
    pneumo_channels = {}
    for ch_type in ["flow", "thorax", "abdomen", "spo2", "pulse",
                    "ecg", "position", "snore", "leg_l", "leg_r"]:
        val = request.form.get(f"pneumo_{ch_type}") or None
        if val:
            pneumo_channels[ch_type] = val

    # ── Patiëntgegevens (v8.0) ──
    patient_info = {
        "patient_name":      request.form.get("patient_name", "").strip(),
        "patient_firstname": request.form.get("patient_firstname", "").strip(),
        "patient_id":        request.form.get("patient_id",   "").strip(),
        "dob":               request.form.get("dob",          "").strip(),
        "sex":               request.form.get("sex",          "").strip(),
        "address":           request.form.get("address",      "").strip(),
        "bmi":               request.form.get("bmi",          "").strip(),
        "weight_kg":         request.form.get("weight_kg",    "").strip(),
        "height_cm":         request.form.get("height_cm",    "").strip(),
        "diagnosis":         request.form.get("diagnosis",    "").strip(),
        "comments":          request.form.get("comments",     "").strip(),
        "scorer":            request.form.get("scorer", "").strip() or current_user.username,
        "institution":       request.form.get("institution",  "").strip(),
        # v0.8.37: klinische velden (Medatec-pariteit)
        "ess":               request.form.get("ess",          "").strip() or None,
        "indication":        request.form.get("indication",   "").strip(),
        "referring_physician": request.form.get("referring_physician", "").strip(),
    }

    if not job_id or not eeg_ch:
        flash(get_translation("job_eeg_required", session.get("lang","nl")), "danger")
        return redirect(url_for("upload_file"))

    filepath_bytes = redis_conn.get(f"{job_id}_filepath")
    if not filepath_bytes:
        flash(get_translation("session_expired", session.get("lang","nl")), "danger")
        return redirect(url_for("upload_file"))
    filepath = filepath_bytes.decode("utf-8")

    if not os.path.exists(filepath):
        flash(get_translation("file_not_available", session.get("lang","nl")), "danger")
        return redirect(url_for("upload_file"))

    # Config opslaan voor de worker
    cfg = {
        "job_id":           job_id,
        "edf_path":         filepath,
        "eeg_ch":           eeg_ch,
        "eog_ch":           eog_ch,
        "emg_ch":           emg_ch,
        "extra_eeg_ch":     extra_eeg if extra_eeg else [eeg_ch],
        "recording_start":  rec_start,
        "pneumo_channels":  pneumo_channels,   # nieuw v7.1
        "patient_info":     patient_info,       # nieuw v7.1
        # v0.8.11: multi-site toegangscontrole
        "site_id":          current_user.site_id,
        "owner_username":   current_user.username,
        "language":         session.get("lang", "nl"),
        # v0.8.22: scoring profiel
        "scoring_profile":  request.form.get("scoring_profile", "standard"),
        "study_type":       request.form.get("study_type", "diagnostic_psg"),
    }
    cfg_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{job_id}_config.json")
    with open(cfg_path, "w") as f:
        json.dump(cfg, f)

    # RQ-job starten
    try:
        rq_job = queue.enqueue(
            "tasks.run_analysis_job",
            args=(job_id,),
            job_timeout=int(_cfg("JOB_TIMEOUT_SECONDS", 900)),
            result_ttl=86400,
        )
        # Koppel app job_id aan RQ job_id zodat de status-API het kan vinden
        redis_conn.set(f"{job_id}_rq_id", rq_job.id, ex=86400)
        logger.info(f"Analyse gestart: job_id={job_id}, rq={rq_job.id}")
    except Exception as e:
        logger.error(f"Fout bij starten analyse-job: {e}", exc_info=True)
        flash(get_translation("worker_unavailable", session.get("lang","nl")), "danger")
        return redirect(url_for("channel_select", job_id=job_id))

    return redirect(url_for("job_status", job_id=job_id))


# ═══════════════════════════════════════════════════════════════
# NIEUW: JOB STATUS (HTML + AJAX)
# ═══════════════════════════════════════════════════════════════

@app.route("/status/<job_id>")
@login_required
def job_status(job_id):
    """Polling-pagina voor lopende uitgebreide analyses."""
    return render_template("job_status.html", job_id=job_id)


@app.route("/api/status/<job_id>")
@login_required
@csrf.exempt
def api_job_status(job_id):
    """AJAX JSON-endpoint voor job-statuspolling."""
    try:
        # Haal echte RQ job_id op (app job_id ≠ RQ job_id)
        rq_id = redis_conn.get(f"{job_id}_rq_id")
        if rq_id:
            rq_id = rq_id.decode("utf-8") if isinstance(rq_id, bytes) else rq_id
            job    = Job.fetch(rq_id, connection=redis_conn)
        else:
            job    = Job.fetch(job_id, connection=redis_conn)  # fallback
        status = job.get_status()

        # Lees echte voortgang uit Redis (geschreven door worker)
        progress = {}
        try:
            raw = redis_conn.hgetall(f"job:{job_id}:progress")
            if raw:
                progress = {
                    k.decode("utf-8") if isinstance(k, bytes) else k:
                    v.decode("utf-8") if isinstance(v, bytes) else v
                    for k, v in raw.items()
                }
        except Exception:
            pass

        response = {
            "status":   str(status),
            "done":     status == "finished",
            "failed":   status == "failed",
            "progress": progress,
        }
        if status == "failed":
            response["error"] = str(job.exc_info) if job.exc_info else "Onbekende fout"
        if status == "finished":
            upload_folder = app.config["UPLOAD_FOLDER"]
            response["has_pdf"]   = os.path.exists(
                os.path.join(upload_folder, f"{job_id}_rapport.pdf"))
            response["has_excel"] = os.path.exists(
                os.path.join(upload_folder, f"{job_id}_rapport.xlsx"))
            response["has_psg"]   = os.path.exists(
                os.path.join(upload_folder, f"{job_id}_rapport.pdf"))
            response["has_edfplus"] = os.path.exists(
                os.path.join(upload_folder, f"{job_id}_scored.edf"))
        return jsonify(response)

    except NoSuchJobError:
        result_file = os.path.join(app.config["UPLOAD_FOLDER"], f"{job_id}_results.json")
        if os.path.exists(result_file):
            upload_folder = app.config["UPLOAD_FOLDER"]
            return jsonify({
                "status":    "finished",
                "done":      True,
                "failed":    False,
                "has_pdf":   os.path.exists(os.path.join(upload_folder, f"{job_id}_rapport.pdf")),
                "has_excel": os.path.exists(os.path.join(upload_folder, f"{job_id}_rapport.xlsx")),
                "has_psg":   os.path.exists(os.path.join(upload_folder, f"{job_id}_rapport.pdf")),
                "has_edfplus": os.path.exists(os.path.join(upload_folder, f"{job_id}_scored.edf")),
            })
        return jsonify({"status": "not_found", "done": False, "failed": False}), 404

    except Exception as e:
        logger.error(f"Fout bij ophalen job-status {job_id}: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════
# NIEUW: UITGEBREIDE RESULTATEN (HTML tabs + PDF + Excel)
# ═══════════════════════════════════════════════════════════════

@app.route("/results/<job_id>")
@login_required
def show_results(job_id):
    """Uitgebreide resultatenpagina: YASA-tabs + pneumo-sectie."""
    _require_job_access(job_id)
    data   = _load_results(job_id)
    pneumo = data.get("pneumo", {})
    return render_template(
        "results_extended.html",
        data=data, job_id=job_id, pneumo=pneumo,
    )


@app.route("/results/<job_id>/pdf")
@login_required
def download_pdf(job_id):
    """Download PDF-rapport. Genereert on-the-fly indien nodig."""
    _require_job_access(job_id)
    pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{job_id}_rapport.pdf")
    if not os.path.exists(pdf_path):
        try:
            from generate_pdf_report import generate_pdf_report
            data = _load_results(job_id)
            generate_pdf_report(data, pdf_path, lang=session.get("lang","nl"))
        except Exception as e:
            logger.error(f"PDF genereren mislukt voor {job_id}: {e}", exc_info=True)
            abort(500, description=f"PDF kon niet gegenereerd worden: {e}")
    return send_file(
        pdf_path,
        as_attachment=True,
        download_name=f"slaaprapport_{job_id[:8]}.pdf",
        mimetype="application/pdf",
    )


@app.route("/results/<job_id>/excel")
@login_required
def download_excel(job_id):
    """Download Excel-rapport. Genereert on-the-fly indien nodig."""
    _require_job_access(job_id)
    xlsx_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{job_id}_rapport.xlsx")
    if not os.path.exists(xlsx_path):
        try:
            from generate_excel_report import generate_excel_report
            data = _load_results(job_id)
            generate_excel_report(data, xlsx_path)
        except Exception as e:
            logger.error(f"Excel genereren mislukt voor {job_id}: {e}", exc_info=True)
            abort(500, description=f"Excel kon niet gegenereerd worden: {e}")
    return send_file(
        xlsx_path,
        as_attachment=True,
        download_name=f"slaaprapport_{job_id[:8]}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.route("/results/<job_id>/psg")
@login_required
def download_psg(job_id):
    """
    PSG-rapport = zelfde als PDF-rapport (portrait A4, AASM-conform).
    Redirect naar PDF-download.
    """
    _require_job_access(job_id)
    return redirect(url_for("download_pdf", job_id=job_id))


@app.route("/results/<job_id>/delete", methods=["POST"])
@login_required
def delete_study(job_id):
    """Verwijder een studie en alle bijhorende bestanden.
    Admin: mag alles verwijderen.
    Andere gebruikers: alleen eigen studies.
    """
    _require_job_access(job_id)
    import glob as _glob
    upload_folder = app.config["UPLOAD_FOLDER"]
    processed_folder = app.config.get("PROCESSED_FOLDER", upload_folder)
    lang = session.get("lang", "nl")

    # ── Permissiecheck ──
    if not current_user.is_admin:
        # Check eigendom: laad results en vergelijk scorer
        result_path = os.path.join(upload_folder, f"{job_id}_results.json")
        if os.path.exists(result_path):
            try:
                with open(result_path) as f:
                    data = json.load(f)
                scorer = data.get("patient_info", {}).get("scorer", "")
                site_id = data.get("site_id")
                # User mag verwijderen als: zelf gescoord OF zelfde site (site_manager)
                if scorer != current_user.username:
                    if not (current_user.role == "site" and site_id == current_user.site_id):
                        logger.warning("Delete geweigerd: %s probeert %s te verwijderen (eigenaar: %s)",
                                      current_user.username, job_id, scorer)
                        flash(get_translation("delete_not_allowed", lang), "danger")
                        return redirect(request.referrer or url_for("dashboard"))
            except Exception as e:
                logger.warning("Kan eigendom niet checken voor %s: %s", job_id, e)

    # ── Zoek bestanden in BEIDE mappen ──
    files = []
    for folder in set([upload_folder, processed_folder]):
        pattern = os.path.join(folder, f"{job_id}*")
        files.extend(_glob.glob(pattern))

    # Ook conclusie-bestand
    conclusion_path = os.path.join(upload_folder, f"{job_id}_conclusion.json")
    if os.path.exists(conclusion_path):
        files.append(conclusion_path)

    if not files:
        logger.warning("Delete: geen bestanden gevonden voor %s in %s", job_id, upload_folder)
        flash(get_translation("study_not_found", lang), "warning")
        return redirect(request.referrer or url_for("dashboard"))

    # ── Verwijder bestanden ──
    deleted = 0
    errors_list = []
    for f in files:
        try:
            os.remove(f)
            deleted += 1
        except Exception as e:
            logger.error("Kan %s niet verwijderen: %s", f, e)
            errors_list.append(str(e))

    # ── Redis cache opschonen ──
    try:
        for key_suffix in ["_filepath", "_config", "_progress"]:
            redis_conn.delete(f"{job_id}{key_suffix}")
    except Exception:
        pass

    logger.info("Studie verwijderd: %s (%d bestanden, %d fouten) door %s",
                job_id, deleted, len(errors_list), current_user.username)

    if errors_list:
        flash(f"{get_translation('study_deleted', lang)} ({deleted} bestanden, {len(errors_list)} fouten)", "warning")
    else:
        flash(get_translation("study_deleted", lang), "success")

    return redirect(request.referrer or url_for("dashboard"))


# ═══════════════════════════════════════════════════════════════
# v13.1: HER-ANALYSE
# ═══════════════════════════════════════════════════════════════

@app.route("/results/<job_id>/reanalyze")
@login_required
def reanalyze_study(job_id):
    """
    Her-analyse van een bestaande studie.
    Zoekt het originele EDF-bestand, zet het in Redis,
    en stuurt door naar kanaalkeuze.
    """
    _require_job_access(job_id)
    upload_folder = app.config["UPLOAD_FOLDER"]
    lang = session.get("lang", "nl")

    # ── Zoek EDF-bestand ──
    edf_path = None

    # 1. Via config JSON (meest betrouwbaar)
    cfg_path = os.path.join(upload_folder, f"{job_id}_config.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path) as f:
                cfg = json.load(f)
            edf_path = cfg.get("edf_path")
        except Exception:
            pass

    # 2. Fallback: standaard naamgeving
    if not edf_path or not os.path.exists(edf_path):
        import glob as _glob
        candidates = _glob.glob(os.path.join(upload_folder, f"{job_id}*.edf"))
        candidates = [c for c in candidates if "_scored.edf" not in c]
        if candidates:
            edf_path = candidates[0]

    if not edf_path or not os.path.exists(edf_path):
        flash(get_translation("edf_not_found", lang), "danger")
        return redirect(request.referrer or url_for("dashboard"))

    # ── Zet filepath in Redis (zodat channel_select het vindt) ──
    redis_conn.set(f"{job_id}_filepath", edf_path, ex=7200)

    logger.info("Her-analyse gestart: %s → %s door %s",
                job_id, os.path.basename(edf_path), current_user.username)
    flash(get_translation("reanalyze_started", lang), "info")

    return redirect(url_for("channel_select", job_id=job_id))


@app.route("/results/<job_id>/edfplus")
@login_required
def download_edfplus(job_id):
    """Download gescoord EDF+ bestand. Genereert on-the-fly als niet aanwezig."""
    _require_job_access(job_id)
    upload_folder = app.config["UPLOAD_FOLDER"]
    scored_path = os.path.join(upload_folder, f"{job_id}_scored.edf")

    # Al beschikbaar? Direct download.
    if os.path.exists(scored_path):
        data = _load_results(job_id)
        pat_name = data.get("patient_info", {}).get("patient_name", "").replace(" ", "_") or job_id[:8]
        return send_file(
            scored_path, as_attachment=True,
            download_name=f"{pat_name}_scored.edf",
            mimetype="application/octet-stream",
        )

    # Niet aanwezig → genereer nu (v14: edfio is snel, <10s)
    lang = session.get("lang", "nl")
    try:
        from generate_edfplus import generate_edfplus

        # Zoek origineel EDF
        edf_path = None
        cfg_path = os.path.join(upload_folder, f"{job_id}_config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path) as f:
                edf_path = json.load(f).get("edf_path")
        if not edf_path or not os.path.exists(edf_path):
            import glob as _glob
            candidates = [c for c in _glob.glob(os.path.join(upload_folder, f"{job_id}*.edf"))
                         if "_scored.edf" not in c]
            edf_path = candidates[0] if candidates else None

        if not edf_path or not os.path.exists(edf_path):
            flash(get_translation("edf_not_found", lang), "danger")
            return redirect(url_for("show_results", job_id=job_id))

        # Laad resultaten en genereer
        results = _load_results(job_id)
        if not results:
            flash(get_translation("study_not_found", lang), "warning")
            return redirect(url_for("show_results", job_id=job_id))

        generate_edfplus(edf_path, results, scored_path)
        logger.info("EDF+ on-the-fly gegenereerd: %s", scored_path)

        pat_name = results.get("patient_info", {}).get("patient_name", "").replace(" ", "_") or job_id[:8]
        return send_file(
            scored_path, as_attachment=True,
            download_name=f"{pat_name}_scored.edf",
            mimetype="application/octet-stream",
        )

    except Exception as e:
        logger.error("EDF+ generatie mislukt: %s", e, exc_info=True)
        flash(get_translation("edfplus_failed", lang) + f": {e}", "danger")
        return redirect(url_for("show_results", job_id=job_id))


@app.route("/api/edfplus/<job_id>/status")
@login_required
@csrf.exempt
def api_edfplus_status(job_id):
    """Check of EDF+ bestand beschikbaar is."""
    _require_job_access(job_id)
    edf_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{job_id}_scored.edf")
    return jsonify({
        "ready": os.path.exists(edf_path),
        "job_id": job_id,
    })


# ═══════════════════════════════════════════════════════════════
# v13: CONCLUSIE / BESLUIT API
# ═══════════════════════════════════════════════════════════════

STANDARD_CONCLUSIONS = {
    "normal": {
        "nl": "Normaal polysomnogram. Geen aanwijzingen voor obstructief slaapapneusyndroom (OSAS). Normale slaaparchitectuur. Geen klinisch significante periodieke beenbewegingen.",
        "fr": "Polysomnogramme normal. Aucun signe de syndrome d'apnées obstructives du sommeil (SAOS). Architecture du sommeil normale. Pas de mouvements périodiques des jambes cliniquement significatifs.",
        "en": "Normal polysomnogram. No evidence of obstructive sleep apnea syndrome (OSAS). Normal sleep architecture. No clinically significant periodic limb movements.",
    },
    "mild_osas": {
        "nl": "Licht obstructief slaapapneusyndroom (licht OSAS). Behandelingssuggesties: positietherapie (vermijden rugligging), mandibulair repositieapparaat (MRA) overwegen, slaaphygiëne optimaliseren.",
        "fr": "Syndrome d'apnées obstructives du sommeil léger (SAOS léger). Suggestions thérapeutiques : thérapie positionnelle (éviter le décubitus dorsal), envisager une orthèse d'avancée mandibulaire (OAM), optimiser l'hygiène du sommeil.",
        "en": "Mild obstructive sleep apnea syndrome (mild OSAS). Treatment suggestions: positional therapy (avoid supine), consider mandibular advancement device (MAD), optimize sleep hygiene.",
    },
    "moderate_osas": {
        "nl": "Matig obstructief slaapapneusyndroom (matig OSAS). Behandelingssuggesties: CPAP-therapie aanbevolen (eerste keuze), alternatief mandibulair repositieapparaat (MRA) bij CPAP-intolerantie, positietherapie als adjuvante behandeling.",
        "fr": "Syndrome d'apnées obstructives du sommeil modéré (SAOS modéré). Suggestions thérapeutiques : CPAP recommandé (premier choix), alternative orthèse d'avancée mandibulaire (OAM) en cas d'intolérance à la CPAP, thérapie positionnelle en traitement adjuvant.",
        "en": "Moderate obstructive sleep apnea syndrome (moderate OSAS). Treatment suggestions: CPAP therapy recommended (first-line), mandibular advancement device (MAD) if CPAP-intolerant, positional therapy as adjunctive treatment.",
    },
    "severe_osas": {
        "nl": "Ernstig obstructief slaapapneusyndroom (ernstig OSAS). Behandelingssuggesties: CPAP-therapie strikt aanbevolen (eerste keuze, dringend), bij ernstige desaturaties evaluatie voor zuurstoftherapie, KNO-evaluatie voor chirurgische opties bij anatomische obstructie.",
        "fr": "Syndrome d'apnées obstructives du sommeil sévère (SAOS sévère). Suggestions thérapeutiques : CPAP strictement recommandé (premier choix, urgent), évaluation pour oxygénothérapie en cas de désaturations sévères, évaluation ORL pour options chirurgicales en cas d'obstruction anatomique.",
        "en": "Severe obstructive sleep apnea syndrome (severe OSAS). Treatment suggestions: CPAP therapy strictly recommended (first-line, urgent), evaluate supplemental O2 for severe desaturations, ENT evaluation for surgical options with anatomical obstruction.",
    },
    "plms": {
        "nl": "Klinisch significante periodieke beenbewegingen tijdens slaap (PLMS). Suggestie: IJzerstatus (ferritine) controleren. Bij ferritine < 75 µg/L: ijzersuppletie. Bij persisterende klachten: dopamine-agonist overwegen.",
        "fr": "Mouvements périodiques des jambes pendant le sommeil cliniquement significatifs (MPJS). Suggestion : contrôler le statut en fer (ferritine). Si ferritine < 75 µg/L : supplémentation en fer. En cas de plaintes persistantes : envisager un agoniste dopaminergique.",
        "en": "Clinically significant periodic limb movements during sleep (PLMS). Suggestion: check iron status (ferritin). If ferritin < 75 µg/L: iron supplementation. If persistent symptoms: consider dopamine agonist.",
    },
    "insomnia": {
        "nl": "Aanwijzingen voor insomnie. Verminderde slaapkwaliteit. Suggestie: Cognitieve gedragstherapie voor insomnie (CGT-i) is eerste keuze. Evaluatie slaaphygiëne. Medicamenteuze behandeling enkel op korte termijn.",
        "fr": "Signes d'insomnie. Qualité de sommeil réduite. Suggestion : la thérapie cognitivo-comportementale de l'insomnie (TCC-i) est le premier choix. Évaluation de l'hygiène du sommeil. Traitement médicamenteux uniquement à court terme.",
        "en": "Indicators of insomnia. Reduced sleep quality. Suggestion: Cognitive behavioral therapy for insomnia (CBT-I) is first-line. Sleep hygiene evaluation. Pharmacotherapy only short-term.",
    },
    "weight_loss": {
        "nl": "Gewichtsreductie sterk aanbevolen. Vermagering kan de ernst van OSAS significant verminderen.",
        "fr": "Perte de poids fortement recommandée. La perte de poids peut réduire significativement la sévérité du SAOS.",
        "en": "Weight reduction strongly recommended. Weight loss can significantly reduce OSAS severity.",
    },
}


@app.route("/api/results/<job_id>/conclusion")
@login_required
@csrf.exempt
def api_get_conclusion(job_id):
    """Haal conclusie-data op: auto-suggestie + huidige manuele tekst."""
    data = _load_results(job_id)
    lang = session.get("lang", "nl")

    pat = data.get("patient_info", {})
    pneumo = data.get("pneumo", {})
    stats = data.get("sleep_statistics", {}).get("stats", {})
    rsum = pneumo.get("respiratory", {}).get("summary", {})
    plm_sum = pneumo.get("plm", {}).get("summary", {})

    ahi = float(rsum.get("ahi_total", 0) or 0)
    oahi = float(rsum.get("oahi", 0) or 0)
    plmi = float(plm_sum.get("plm_index", 0) or 0)
    se = float(str(stats.get("SE", 0) or 0).replace("%", ""))
    tst = float(str(stats.get("TST", 0) or 0))

    # Bepaal welke standaardbesluiten van toepassing zijn
    applicable = []
    if ahi < 5 and plmi < 15 and se >= 85:
        applicable.append("normal")
    if 5 <= ahi < 15:
        applicable.append("mild_osas")
    if 15 <= ahi < 30:
        applicable.append("moderate_osas")
    if ahi >= 30:
        applicable.append("severe_osas")
    if plmi >= 15:
        applicable.append("plms")
    if se < 85 or tst < 360:
        applicable.append("insomnia")

    bmi_raw = pat.get("bmi", "")
    try:
        bmi = float(str(bmi_raw).replace(",", "."))
    except (ValueError, TypeError):
        bmi = None
    if bmi and bmi > 28 and ahi >= 5:
        applicable.append("weight_loss")

    # Bouw auto-conclusie
    auto_parts = []
    for key in applicable:
        auto_parts.append(STANDARD_CONCLUSIONS[key].get(lang, STANDARD_CONCLUSIONS[key]["nl"]))
    auto_conclusion = "\n".join(auto_parts)

    # Check of er een manuele conclusie opgeslagen is
    conclusion_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{job_id}_conclusion.json")
    manual_conclusion = ""
    if os.path.exists(conclusion_path):
        with open(conclusion_path) as f:
            cdata = json.load(f)
        manual_conclusion = cdata.get("conclusion", "")

    # Alle standaardbesluiten voor de dropdown
    all_standards = {}
    for key, texts in STANDARD_CONCLUSIONS.items():
        all_standards[key] = texts.get(lang, texts["nl"])

    return jsonify({
        "auto_conclusion": auto_conclusion,
        "manual_conclusion": manual_conclusion,
        "applicable": applicable,
        "all_standards": all_standards,
        "metrics": {
            "ahi": round(ahi, 1),
            "oahi": round(oahi, 1),
            "plmi": round(plmi, 1),
            "se": round(se, 1),
            "tst": round(tst, 0),
            "bmi": round(bmi, 1) if bmi else None,
        },
    })


@app.route("/api/results/<job_id>/conclusion", methods=["POST"])
@login_required
@csrf.exempt
def api_save_conclusion(job_id):
    """Sla manuele conclusie op en regenereer PDF."""
    req = request.get_json(force=True)
    conclusion_text = req.get("conclusion", "").strip()

    # Sla conclusie op
    conclusion_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{job_id}_conclusion.json")
    with open(conclusion_path, "w") as f:
        json.dump({
            "conclusion": conclusion_text,
            "saved_by": current_user.username,
            "saved_at": datetime.utcnow().isoformat(),
        }, f, indent=2)

    # Update results JSON met conclusie
    result_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{job_id}_results.json")
    if os.path.exists(result_path):
        with open(result_path) as f:
            data = json.load(f)
        if "patient_info" not in data:
            data["patient_info"] = {}
        data["patient_info"]["diagnosis"] = conclusion_text
        with open(result_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    # Regenereer PDF
    try:
        from generate_pdf_report import generate_pdf_report
        pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{job_id}_rapport.pdf")
        generate_pdf_report(data, pdf_path, lang=session.get("lang","nl"))
        return jsonify({"status": "ok", "pdf_regenerated": True})
    except Exception as e:
        logger.error(f"PDF regeneratie mislukt: {e}")
        return jsonify({"status": "ok", "pdf_regenerated": False, "error": str(e)})


# ═══════════════════════════════════════════════════════════════
# v14: RAPPORT EDITOR
# ═══════════════════════════════════════════════════════════════

@app.route("/results/<job_id>/edit")
@login_required
def edit_report(job_id):
    """Rapport-editor pagina."""
    _require_job_access(job_id)
    return render_template("report_editor.html", job_id=job_id)


@app.route("/api/results/<job_id>/report")
@login_required
@csrf.exempt
def api_get_report(job_id):
    """Haal alle bewerkbare rapportgegevens op."""
    _require_job_access(job_id)
    data = _load_results(job_id)
    # v0.8.11: site config meegeven voor header-velden defaults
    site_cfg = {}
    try:
        for p in [os.path.join(os.path.dirname(__file__), "..", "config.json"), "config.json"]:
            if os.path.exists(p):
                with open(p) as f:
                    site_cfg = json.load(f).get("site", {})
                break
    except Exception:
        pass
    return jsonify({
        "patient_info": data.get("patient_info", {}),
        "site_config": site_cfg,
        "job_id": job_id,
    })


@app.route("/api/results/<job_id>/report", methods=["POST"])
@login_required
@csrf.exempt
def api_save_report(job_id):
    """
    Sla alle rapportgegevens op, update results JSON,
    regenereer PDF en EDF+.
    """
    _require_job_access(job_id)
    req = request.get_json(force=True)
    upload_folder = app.config["UPLOAD_FOLDER"]
    result_path = os.path.join(upload_folder, f"{job_id}_results.json")

    if not os.path.exists(result_path):
        return jsonify({"status": "error", "error": "Results niet gevonden"}), 404

    try:
        with open(result_path) as f:
            data = json.load(f)

        # Update patient_info
        new_pat = req.get("patient_info", {})
        if "patient_info" not in data:
            data["patient_info"] = {}
        for key in ("patient_name", "patient_firstname", "patient_id",
                     "dob", "sex", "bmi", "weight_kg", "height_cm",
                     "diagnosis", "comments", "scorer", "institution",
                     # v0.8.11: verificatie + header
                     "verified_role", "verified_by", "verified_date",
                     "report_header_name", "report_header_address",
                     "report_header_phone",
                     # v0.8.37: klinische velden
                     "ess", "indication", "referring_physician"):
            if key in new_pat:
                data["patient_info"][key] = new_pat[key]

        # v0.8.11: Logo opslaan (base64 → bestand in static/logos/)
        logo_b64 = req.get("logo_base64")
        logo_fname = req.get("logo_filename", "")
        if logo_b64 and logo_fname:
            try:
                import base64
                logos_dir = os.path.join(os.path.dirname(__file__), "static", "logos")
                os.makedirs(logos_dir, exist_ok=True)
                # Bestandsnaam veilig maken
                safe_name = secure_filename(f"{job_id}_{logo_fname}")
                logo_path = os.path.join(logos_dir, safe_name)
                # Strip data URI prefix
                if "," in logo_b64:
                    logo_b64 = logo_b64.split(",", 1)[1]
                with open(logo_path, "wb") as lf:
                    lf.write(base64.b64decode(logo_b64))
                data["patient_info"]["report_logo_path"] = safe_name
                logger.info("Logo opgeslagen: %s", logo_path)
            except Exception as e:
                logger.warning("Logo opslaan mislukt: %s", e)

        # Sla ook conclusie apart op (backward compatible)
        conclusion_text = new_pat.get("diagnosis", "").strip()
        conclusion_path = os.path.join(upload_folder, f"{job_id}_conclusion.json")
        with open(conclusion_path, "w") as f:
            json.dump({
                "conclusion": conclusion_text,
                "saved_by": current_user.username,
                "saved_at": datetime.utcnow().isoformat(),
            }, f, indent=2)

        # Sla results JSON op
        with open(result_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        logger.info("Rapport bijgewerkt: %s door %s", job_id, current_user.username)

        # Regenereer PDF
        pdf_ok = False
        try:
            from generate_pdf_report import generate_pdf_report
            pdf_path = os.path.join(upload_folder, f"{job_id}_rapport.pdf")
            generate_pdf_report(data, pdf_path, lang=session.get("lang","nl"))
            pdf_ok = True
        except Exception as e:
            logger.error("PDF regeneratie mislukt: %s", e)

        # Regenereer EDF+ (snel met edfio)
        edfplus_ok = False
        try:
            from generate_edfplus import generate_edfplus
            edf_path = data.get("meta", {}).get("edf_path") or \
                       os.path.join(upload_folder, f"{job_id}*.edf")
            # Zoek origineel EDF
            import glob as _glob
            candidates = [c for c in _glob.glob(os.path.join(upload_folder, f"{job_id}*.edf"))
                         if "_scored.edf" not in c]
            if candidates:
                scored_path = os.path.join(upload_folder, f"{job_id}_scored.edf")
                generate_edfplus(candidates[0], data, scored_path)
                edfplus_ok = True
        except Exception as e:
            logger.warning("EDF+ regeneratie overgeslagen: %s", e)

        return jsonify({
            "status": "ok",
            "pdf_regenerated": pdf_ok,
            "edfplus_regenerated": edfplus_ok,
        })

    except Exception as e:
        logger.error("Rapport opslaan mislukt: %s", e, exc_info=True)
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/results/<job_id>/pneumo")
@login_required
@csrf.exempt
def api_pneumo_results(job_id):
    """JSON API — enkel pneumologische analyseresultaten."""
    _require_job_access(job_id)
    data = _load_results(job_id)
    return jsonify(data.get("pneumo", {}))


@app.route("/api/results/<job_id>/channels")
@login_required
@csrf.exempt
def api_detected_channels(job_id):
    """
    Geeft auto-gedetecteerde respiratoire kanalen terug voor een job.
    Bruikbaar voor UI-feedback na kanaalkeuze.
    """
    _require_job_access(job_id)
    data     = _load_results(job_id)
    pneumo   = data.get("pneumo", {})
    channels = pneumo.get("meta", {}).get("channels_used", {})
    avail    = pneumo.get("channel_availability", {})
    return jsonify({"channels_used": channels, "availability": avail})


@app.route("/api/results/<job_id>")
@login_required
@csrf.exempt
def api_results(job_id):
    """JSON API — volledige analyseresultaten."""
    _require_job_access(job_id)
    return jsonify(_load_results(job_id))


# ═══════════════════════════════════════════════════════════════
# OVERIGE ROUTES
# ═══════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════
# DASHBOARD  (v9.1)
# ═══════════════════════════════════════════════════════════════

@app.route("/dashboard")
@login_required
def dashboard():
    """Patiëntenoverzicht — gefilterd op rol."""
    import glob
    upload_folder = app.config["UPLOAD_FOLDER"]
    json_files = sorted(
        glob.glob(os.path.join(upload_folder, "*_results.json")),
        key=os.path.getmtime, reverse=True
    )[:300]

    studies = []
    # v0.8.11: centraal site-filter (vervangt inline rolfilter)
    accessible = _filter_studies_for_user(json_files)
    for job_id, data, jf in accessible:
        try:
            pat    = data.get("patient_info", {})
            meta   = data.get("meta", {})
            stats  = data.get("sleep_statistics", {}).get("stats", {})
            rsum   = data.get("pneumo", {}).get("respiratory", {}).get("summary", {})
            scorer = pat.get("scorer", "")

            ahi = rsum.get("ahi_total")
            try:
                ahi_f = float(ahi)
                sev_cls = "success" if ahi_f < 5 else \
                          "warning" if ahi_f < 15 else \
                          "orange"  if ahi_f < 30 else "danger"
            except Exception:
                ahi_f = None; sev_cls = "secondary"

            from datetime import datetime as _dt
            analyse_date = _dt.fromtimestamp(os.path.getmtime(jf)).strftime("%d-%m-%Y %H:%M")

            studies.append({
                "job_id":            job_id,
                "patient_name":      pat.get("patient_name", "—"),
                "patient_firstname": pat.get("patient_firstname", ""),
                "patient_id":        pat.get("patient_id", "—"),
                "dob":               pat.get("dob", "—"),
                "date":              analyse_date,
                "duration_min":      meta.get("duration_min", "—"),
                "tst":               stats.get("TST", "—"),
                "se":                stats.get("SE", "—"),
                "ahi":               f"{ahi_f:.1f}" if ahi_f is not None else "—",
                "ahi_sev":           rsum.get("severity", "—"),
                "sev_cls":           sev_cls,
                "scorer":            scorer or "—",
                "status":            "klaar",
                "has_pdf":     os.path.exists(os.path.join(upload_folder, f"{job_id}_rapport.pdf")),
                "has_psg":     os.path.exists(os.path.join(upload_folder, f"{job_id}_rapport.pdf")),
                "has_excel":   os.path.exists(os.path.join(upload_folder, f"{job_id}_rapport.xlsx")),
                "has_edfplus": os.path.exists(os.path.join(upload_folder, f"{job_id}_scored.edf")),
            })
        except Exception as e:
            logger.warning(f"Dashboard: {jf}: {e}")

    sites = Site.query.order_by(Site.name).all() if current_user.is_admin else []
    return render_template("dashboard.html", studies=studies, total=len(studies), sites=sites)


# ═══════════════════════════════════════════════════════════════
# FHIR R4 EXPORT  (v9.0)
# ═══════════════════════════════════════════════════════════════

@app.route("/results/<job_id>/fhir")
@login_required
def download_fhir(job_id):
    """FHIR R4 DiagnosticReport export als JSON."""
    _require_job_access(job_id)
    try:
        from fhir_export import results_to_fhir
        data     = _load_results(job_id)
        site_cfg = current_user.site_config or {}
        fhir     = results_to_fhir(data, job_id, site_cfg)
        resp     = jsonify(fhir)
        resp.headers["Content-Disposition"] = (
            f"attachment; filename=fhir_{job_id[:8]}.json")
        return resp
    except Exception as e:
        logger.error(f"FHIR export mislukt voor {job_id}: {e}", exc_info=True)
        abort(500, description=f"FHIR export mislukt: {e}")


# ═══════════════════════════════════════════════════════════════
# MANUELE SCORER v10 (epoch-per-epoch)
# ═══════════════════════════════════════════════════════════════

@app.route("/score/<job_id>")
@login_required
def score_editor(job_id):
    """Epoch-per-epoch scorer zonder EDF-viewer (v10)."""
    data = _load_results(job_id)
    pat  = data.get("patient_info", {})
    tl   = data.get("hypnogram_timeline", {}).get("timeline", [])
    hypno = data.get("staging", {}).get("hypnogram", [])
    if not hypno and tl:
        hypno = [ep.get("stage", "W") for ep in tl]
    corr_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{job_id}_corrections.json")
    active_hypno = hypno
    if os.path.exists(corr_path):
        with open(corr_path) as f:
            active_hypno = json.load(f).get("hypnogram", hypno)
    stats = data.get("sleep_statistics", {}).get("stats", {})
    n     = len(active_hypno)
    return render_template("score_editor.html",
        job_id=job_id, ai_stages=hypno, active_stages=active_hypno,
        n_epochs=n, duration_h=f"{n*30/3600:.1f}" if n else "—",
        patient_name=" ".join(filter(None,[pat.get("patient_name",""),
                                           pat.get("patient_firstname","")])) or None,
        stats=stats)


@app.route("/score_v12/<job_id>")
@login_required
def score_v12(job_id):
    """Gecombineerde scorer + EDF-viewer + event-overlay (v12)."""
    _require_job_access(job_id)
    data = _load_results(job_id)
    pat  = data.get("patient_info", {})
    tl   = data.get("hypnogram_timeline", {}).get("timeline", [])
    hypno = data.get("staging", {}).get("hypnogram", [])
    if not hypno and tl:
        hypno = [ep.get("stage", "W") for ep in tl]
    corr_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{job_id}_corrections.json")
    active_hypno = hypno
    if os.path.exists(corr_path):
        with open(corr_path) as f:
            active_hypno = json.load(f).get("hypnogram", hypno)

    try:
        from event_api import load_events, _calc_stats, _get_tst_hours
        events    = load_events(job_id, app.config["UPLOAD_FOLDER"])
        tst_h     = _get_tst_hours(job_id, app.config["UPLOAD_FOLDER"])
        ev_stats  = _calc_stats(events, tst_h)
    except Exception:
        events = []; ev_stats = {}

    from collections import Counter
    ev_counts = Counter(e.get("type") for e in events)
    rsum      = data.get("pneumo", {}).get("respiratory", {}).get("summary", {})
    stats     = data.get("sleep_statistics", {}).get("stats", {})
    n         = len(active_hypno)

    return render_template("scorer_v12.html",
        job_id        = job_id,
        ai_stages     = hypno,
        active_stages = active_hypno,
        n_epochs      = n,
        duration_h    = f"{n*30/3600:.1f}" if n else "—",
        patient_name  = " ".join(filter(None,[
            pat.get("patient_name",""), pat.get("patient_firstname","")])) or None,
        stats         = stats,
        ahi           = rsum.get("ahi_total"),
        oahi          = rsum.get("oahi"),
        event_counts  = dict(ev_counts))


@app.route("/api/scoring/<job_id>/save", methods=["POST"])
@login_required
@csrf.exempt
def api_save_scoring(job_id):
    """Sla manuele hypnogram-correcties op en start herberekening."""
    try:
        payload     = request.get_json(force=True)
        hypnogram   = payload.get("hypnogram", [])
        corrections = payload.get("corrections", {})
        n_changes   = int(payload.get("n_changes", 0))
        if not hypnogram:
            return jsonify({"success": False, "error": "Geen hypnogram data"}), 400
        valid = {"W","N1","N2","N3","R"}
        for s in hypnogram:
            if s not in valid:
                return jsonify({"success": False, "error": f"Ongeldig stadium: {s}"}), 400
        corr_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{job_id}_corrections.json")
        with open(corr_path, "w") as f:
            json.dump({
                "hypnogram":   hypnogram,
                "corrections": corrections,
                "n_changes":   n_changes,
                "scorer":      current_user.username,
                "saved_at":    datetime.utcnow().isoformat(),
            }, f, indent=2)
        try:
            rq_job = queue.enqueue("tasks.regenerate_with_corrections",
                args=(job_id,), job_timeout=600, result_ttl=86400)
            redis_conn.set(f"{job_id}_regen_rq", rq_job.id, ex=86400)
        except Exception as e:
            return jsonify({"success": True,
                            "warning": f"Opgeslagen maar herberekening mislukt: {e}",
                            "n_changes": n_changes})
        return jsonify({"success": True, "n_changes": n_changes, "rq_id": rq_job.id})
    except Exception as e:
        logger.error(f"api_save_scoring {job_id}: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/scoring/<job_id>/status")
@login_required
@csrf.exempt
def api_scoring_status(job_id):
    try:
        rq_id_b = redis_conn.get(f"{job_id}_regen_rq")
        if not rq_id_b:
            return jsonify({"status": "none", "done": False})
        rq_id  = rq_id_b.decode() if isinstance(rq_id_b, bytes) else rq_id_b
        job    = Job.fetch(rq_id, connection=redis_conn)
        status = str(job.get_status())
        return jsonify({"status": status, "done": status=="finished", "failed": status=="failed"})
    except NoSuchJobError:
        return jsonify({"status": "finished", "done": True})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════
# EDF API  (v11 + v12)
# ═══════════════════════════════════════════════════════════════

@app.route("/api/edf/<job_id>/info")
@login_required
@csrf.exempt
def api_edf_info(job_id):
    _require_job_access(job_id)
    try:
        from edf_api import edf_info
        return jsonify(edf_info(job_id, app.config["UPLOAD_FOLDER"]))
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.error(f"api_edf_info {job_id}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/edf/<job_id>/epoch/<int:epoch_idx>")
@login_required
@csrf.exempt
def api_edf_epoch(job_id, epoch_idx):
    _require_job_access(job_id)
    try:
        from edf_api import edf_epoch
        channels_param = request.args.get("channels")
        channels = channels_param.split(",") if channels_param else None
        return jsonify(edf_epoch(job_id, epoch_idx,
                                 app.config["UPLOAD_FOLDER"], channels))
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except IndexError as e:
        return jsonify({"error": str(e)}), 416
    except Exception as e:
        logger.error(f"api_edf_epoch {job_id}/{epoch_idx}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/edf/<job_id>/epochs/<int:start>/<int:end>")
@login_required
@csrf.exempt
def api_edf_epochs(job_id, start, end):
    _require_job_access(job_id)
    try:
        from edf_api import edf_multi_epoch
        channels_param = request.args.get("channels")
        channels = channels_param.split(",") if channels_param else None
        return jsonify(edf_multi_epoch(job_id, start, end,
                                       app.config["UPLOAD_FOLDER"], channels))
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.error(f"api_edf_epochs {job_id}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════
# EVENT API  (v12)
# ═══════════════════════════════════════════════════════════════

@app.route("/api/edf/<job_id>/events/<int:epoch_idx>")
@login_required
@csrf.exempt
def api_edf_events_epoch(job_id, epoch_idx):
    _require_job_access(job_id)
    try:
        from event_api import events_for_epoch
        evs = events_for_epoch(job_id, app.config["UPLOAD_FOLDER"], epoch_idx)
        return jsonify({"epoch": epoch_idx, "events": evs})
    except Exception as e:
        logger.error(f"api_edf_events_epoch {job_id}/{epoch_idx}: {e}")
        return jsonify({"epoch": epoch_idx, "events": [], "error": str(e)})


@app.route("/api/edf/<job_id>/events/all")
@login_required
@csrf.exempt
def api_edf_events_all(job_id):
    _require_job_access(job_id)
    try:
        from event_api import load_events, _calc_stats, _get_tst_hours, EVENT_TYPES
        events = load_events(job_id, app.config["UPLOAD_FOLDER"])
        tst_h  = _get_tst_hours(job_id, app.config["UPLOAD_FOLDER"])
        stats  = _calc_stats(events, tst_h)
        return jsonify({"job_id": job_id, "events": events, "stats": stats,
                        "event_types": {t: m["label"] for t,m in EVENT_TYPES.items()}})
    except Exception as e:
        logger.error(f"api_edf_events_all {job_id}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/edf/<job_id>/events/toggle", methods=["POST"])
@login_required
@csrf.exempt
def api_edf_events_toggle(job_id):
    _require_job_access(job_id)
    try:
        from event_api import toggle_event_at, EVENT_TYPES as EV_TYPES
        payload  = request.get_json(force=True)
        ev_type  = payload.get("type", "OA")
        t_click  = float(payload.get("t_click", 0))
        duration = float(payload.get("duration", 10))
        if ev_type not in EV_TYPES:
            return jsonify({"error": f"Ongeldig type: {ev_type}"}), 400
        result = toggle_event_at(
            job_id=job_id,
            upload_folder=app.config["UPLOAD_FOLDER"],
            ev_type=ev_type,
            t_click=t_click,
            default_duration=duration,
            scorer=current_user.username)
        return jsonify(result)
    except Exception as e:
        logger.error(f"api_edf_events_toggle {job_id}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500



@app.route("/health")
@limiter.exempt
def health():
    redis_ok = False
    try:
        redis_conn.ping()
        redis_ok = True
    except Exception:
        pass
    return jsonify({
        "status":    "ok" if redis_ok else "degraded",
        "redis":     redis_ok,
        "timestamp": datetime.utcnow().isoformat(),
        "version":   APP_VERSION,
    }), 200 if redis_ok else 503


# ═══════════════════════════════════════════════════════════════
# ERROR HANDLERS
# ═══════════════════════════════════════════════════════════════

@app.errorhandler(CSRFError)
def csrf_error(e):
    logger.warning(f"CSRF-fout: {e.description}")
    if request.is_json or request.path.startswith("/api/"):
        return jsonify({"error": "CSRF-token ongeldig of verlopen.", "code": 400}), 400
    flash(get_translation("session_expired", session.get("lang","nl")), "warning")
    return redirect(url_for("index"))

@app.errorhandler(413)
def too_large(e):
    max_mb = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
    if request.is_json or request.path.startswith("/api/"):
        return jsonify({"error": f"Bestand te groot (max {max_mb} MB)"}), 413
    flash(f"Bestand te groot. Maximum is {max_mb} MB.", "danger")
    return redirect(url_for("upload_file"))

@app.errorhandler(403)
def forbidden(e):
    if request.is_json or request.path.startswith("/api/"):
        return jsonify({"error": str(e.description), "code": 403}), 403
    flash(str(e.description), "danger")
    return redirect(url_for("dashboard"))

@app.errorhandler(404)
def not_found(e):
    if request.is_json or request.path.startswith("/api/"):
        return jsonify({"error": str(e.description), "code": 404}), 404
    flash(str(e.description), "warning")
    return redirect(url_for("index"))

@app.errorhandler(429)
def ratelimit_exceeded(e):
    if request.is_json or request.path.startswith("/api/"):
        return jsonify({"error": "Te veel verzoeken. Wacht even.", "code": 429}), 429
    # v0.8.11 FIX: NIET redirecten — dat veroorzaakt een loop
    # (429 → redirect(index) → redirect(login) → 429 → ...)
    return render_template("generic.html",
        title="429", message=get_translation("rate_limited", session.get("lang","nl")),
    ), 429

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"500-fout: {e}\n{traceback.format_exc()}")
    if request.is_json or request.path.startswith("/api/"):
        return jsonify({"error": "Interne serverfout.", "code": 500}), 500
    return render_template("generic.html",
        title="500", message=get_translation("internal_error", session.get("lang","nl")),
    ), 500


# ═══════════════════════════════════════════════════════════════
# DATABASE INITIALISATIE — origineel volledig bewaard
# ═══════════════════════════════════════════════════════════════

def initialize_database():
    with app.app_context():
        db.create_all()

        if db.engine.dialect.name == "sqlite":
            # ── Bestaande user-kolommen migreren ──────────────────
            cols = _sqlite_columns("user")

            for col, ctype in [
                ("password",  "VARCHAR(150)"),
                ("role",      "VARCHAR(20) DEFAULT 'user'"),
                ("site_id",   "INTEGER"),
                ("language",  "VARCHAR(5) DEFAULT 'nl'"),
            ]:
                if cols and col not in cols:
                    try:
                        with db.engine.begin() as conn:
                            conn.execute(text(
                                f"ALTER TABLE user ADD COLUMN {col} {ctype}"))
                        logger.info("Kolom '%s' toegevoegd aan user", col)
                    except Exception as e:
                        logger.warning("Migratie '%s' mislukt: %s", col, e)

            # Legacy wachtwoordveld kopiëren indien nodig
            cols2 = _sqlite_columns("user")
            legacy_sources = ["password_hash", "hashed_password", "password_digest"]
            src = next((c for c in legacy_sources if c in cols2), None)
            if src:
                try:
                    with db.engine.begin() as conn:
                        conn.execute(text(
                            f"UPDATE user SET password = {src} "
                            f"WHERE password IS NULL OR password = ''"))
                except Exception:
                    pass

        # ── Admin-gebruiker aanmaken / herstellen ─────────────────
        admin_plain = _cfg("ADMIN_PASSWORD", "admin")
        admin = User.query.filter_by(username="admin").first()
        if not admin:
            admin = User(
                username="admin",
                password=generate_password_hash(
                    admin_plain, method="pbkdf2:sha256", salt_length=16),
                role="admin",
                language="nl",
            )
            db.session.add(admin)
            db.session.commit()
        else:
            changed = False
            if not admin.password or not _looks_like_werkzeug_hash(admin.password):
                admin.password = generate_password_hash(
                    admin_plain, method="pbkdf2:sha256", salt_length=16)
                changed = True
            if admin.role != "admin":
                admin.role = "admin"
                changed = True
            if changed:
                db.session.commit()

        # ── Default site aanmaken als er nog geen is ──────────────
        if not Site.query.first():
            site_cfg = {}
            try:
                cfg_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
                if not os.path.exists(cfg_path):
                    cfg_path = "config.json"
                with open(cfg_path) as f:
                    site_cfg = json.load(f).get("site", {})
            except Exception:
                pass
            default_site = Site(
                name     = site_cfg.get("name",  "SleepAI"),
                address  = site_cfg.get("address",""),
                phone    = site_cfg.get("phone",  ""),
                email    = site_cfg.get("email",  ""),
                logo_path= site_cfg.get("logo_path",""),
                url      = site_cfg.get("url",    "https://sleepai.be"),
                language = "nl",
            )
            db.session.add(default_site)
            db.session.commit()
            logger.info("Default site aangemaakt: %s", default_site.name)


# ═══════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    initialize_database()
    port  = int(os.environ.get("PORT", 5000))
    debug = _cfg("DEBUG", "0") == "1"
    app.logger.info(f"YASAFlaskified v{APP_VERSION} starten op poort %d (debug=%s)", port, debug)
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=debug)
