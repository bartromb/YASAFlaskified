#!/bin/bash
# Herplaats de analyse die bij de 0.38.0-uitrol (2026-09-03 09:47) verweesd
# raakte: job 910f0a91 startte om 09:44:46, tussen de jobcontrole en de
# herstart in, en staat nu als AbandonedJobError in de failed-registry.
# Herplaatsen laat hem meteen op app 0.38.0 / psgscoring 0.32.0 draaien.
#
# Gebruik:  bash scripts/requeue_verweesde_job.sh [job-id]
set -euo pipefail

JOB_ID="${1:-910f0a91-f67f-42d7-adbf-98d1da0a28b6}"

ssh root@65.108.230.243 "cd /data/slaapkliniek && docker compose exec -T app python -c \"
from redis import Redis
from rq import Queue
from rq.registry import FailedJobRegistry
q = Queue(connection=Redis(host='redis'))
FailedJobRegistry(queue=q).requeue('${JOB_ID}')
print('opnieuw in wachtrij; queued:', len(q))\""
