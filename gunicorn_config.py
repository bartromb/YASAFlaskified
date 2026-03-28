# Gunicorn configuration for YASAFlaskified
import multiprocessing

# Server socket
# IMPORTANT: Use 0.0.0.0 for Docker (not 127.0.0.1)
# This allows external connections to the container
bind = "0.0.0.0:8000"

# Worker processes
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 300
keepalive = 5

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = "info"

# Process naming
proc_name = "yasaflaskified"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (disabled by default, configure nginx for SSL termination)
keyfile = None
certfile = None
