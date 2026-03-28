FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libhdf5-dev libfreetype6-dev libpng-dev git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /data/slaapkliniek

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY myproject/ ./myproject/
COPY config.json.example ./config.json

RUN mkdir -p uploads processed logs instance .mplconfig .numba_cache \
    && chmod -R 755 /data/slaapkliniek

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/data/slaapkliniek/myproject \
    MPLCONFIGDIR=/data/slaapkliniek/.mplconfig \
    NUMBA_CACHE_DIR=/data/slaapkliniek/.numba_cache \
    YASAFLASKIFIED_UPLOAD_FOLDER=/data/slaapkliniek/uploads \
    YASAFLASKIFIED_PROCESSED_FOLDER=/data/slaapkliniek/processed \
    YASAFLASKIFIED_SQLALCHEMY_DATABASE_URI=sqlite:////data/slaapkliniek/instance/users.db \
    YASAFLASKIFIED_LOG_FILE=/data/slaapkliniek/logs/app.log \
    YASAFLASKIFIED_REDIS_HOST=redis \
    YASAFLASKIFIED_REDIS_PORT=6379

# Numba cache opwarmen tijdens build
RUN python3 -c "\
import warnings; warnings.filterwarnings('ignore'); \
import antropy, numpy as np; \
x = np.random.randn(1000); \
antropy.sample_entropy(x); \
antropy.perm_entropy(x, order=3); \
antropy.spectral_entropy(x, sf=256, method='welch'); \
print('Numba cache OK')" \
    && cp -r .numba_cache .numba_cache_seed

WORKDIR /data/slaapkliniek/myproject

COPY docker-init.sh /docker-init.sh
RUN chmod +x /docker-init.sh

EXPOSE 5000
ENTRYPOINT ["/docker-init.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:app"]
