import multiprocessing

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
timeout = 2400  # Default timeout is usually 30 seconds
