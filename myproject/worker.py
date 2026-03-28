#!/usr/bin/env python3
"""
RQ Worker for YASAFlaskified
Processes background jobs for sleep staging analysis
"""
import os
import sys

# Ensure psgscoring and other myproject modules are importable
_myproject_dir = os.path.dirname(os.path.abspath(__file__))
if _myproject_dir not in sys.path:
    sys.path.insert(0, _myproject_dir)

import json
import redis
from rq import Worker, Queue

def load_config():
    """Load configuration from config.json"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}

def main():
    """Main worker function"""
    # Load config
    config = load_config()
    
    # Get Redis configuration (prioritize env vars, fallback to config.json)
    redis_host = os.environ.get('REDIS_HOST', config.get('REDIS_HOST', 'localhost'))
    redis_port = int(os.environ.get('REDIS_PORT', config.get('REDIS_PORT', 6379)))
    
    print(f"🔗 Connecting to Redis at {redis_host}:{redis_port}")
    
    # Connect to Redis
    try:
        # IMPORTANT: Do NOT use decode_responses=True with RQ!
        # RQ expects bytes, not strings
        conn = redis.Redis(host=redis_host, port=redis_port)
        conn.ping()  # Test connection
        print(f"✓ Connected to Redis successfully")
    except redis.ConnectionError as e:
        print(f"❌ Failed to connect to Redis: {e}")
        print(f"   Host: {redis_host}")
        print(f"   Port: {redis_port}")
        sys.exit(1)
    
    # Create queue
    queue = Queue('default', connection=conn)
    
    # Create worker
    worker = Worker([queue], connection=conn)
    
    print(f"🎧 Worker listening on queue: default")
    print(f"🚀 Starting worker...")
    
    # Start processing
    worker.work()

if __name__ == '__main__':
    main()
