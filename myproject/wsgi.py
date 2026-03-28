#!/usr/bin/env python3
"""
WSGI entry point for YASAFlaskified
Used by Gunicorn to serve the Flask application
"""
import os
import sys
import time
# Ensure myproject/ directory is on sys.path so that psgscoring and other
# sibling modules are importable regardless of the working directory.
_myproject_dir = os.path.dirname(os.path.abspath(__file__))
if _myproject_dir not in sys.path:
    sys.path.insert(0, _myproject_dir)



# Check if database exists BEFORE importing app
# This prevents issues during initialization
db_path = os.path.join(os.path.dirname(__file__), 'instance', 'users.db')
instance_dir = os.path.dirname(db_path)

# Ensure instance directory exists
os.makedirs(instance_dir, exist_ok=True)

# If database doesn't exist, initialize it
# This handles the case where wsgi.py is called before docker-init.sh finishes
# or for traditional deployment where DB is created on first run
if not os.path.exists(db_path) or os.path.getsize(db_path) == 0:
    lock_file = os.path.join(instance_dir, '.db_init.lock')
    
    # Try to create lock file atomically
    try:
        # Use exclusive creation to avoid race condition
        fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        os.close(fd)
        
        # This worker won the race - it initializes the database
        print(f"[Worker {os.getpid()}] Initializing database...")
        
        from app import initialize_database
        try:
            initialize_database()
            print(f"[Worker {os.getpid()}] ✓ Database initialized successfully")
        except Exception as e:
            print(f"[Worker {os.getpid()}] Database initialization error: {e}")
            # If it's a UNIQUE constraint error, DB probably exists - ignore
            if "UNIQUE constraint" not in str(e):
                # Clean up lock file on other failures
                try:
                    os.remove(lock_file)
                except:
                    pass
                raise
        
        # Clean up lock file after successful init
        try:
            os.remove(lock_file)
        except:
            pass
            
    except FileExistsError:
        # Another worker is initializing - wait for it to finish
        print(f"[Worker {os.getpid()}] Waiting for database initialization...")
        for i in range(30):  # Wait up to 30 seconds
            if os.path.exists(db_path) and os.path.getsize(db_path) > 0:
                print(f"[Worker {os.getpid()}] ✓ Database ready")
                break
            time.sleep(1)
        else:
            print(f"[Worker {os.getpid()}] ⚠️  Database initialization timeout, continuing anyway...")

# Now import app (database should exist)
from app import app

if __name__ == "__main__":
    app.run()


