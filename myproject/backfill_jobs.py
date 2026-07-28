#!/usr/bin/env python3
"""
backfill_jobs.py — vul de Job-registry aan met bestaande studies.

De Job-tabel is nieuw; alle studies van vóór die tabel bestaan alleen als
{job_id}_results.json / {job_id}_config.json in UPLOAD_FOLDER. Dit script
leest die bestanden en maakt de ontbrekende rijen aan, zodat de
toegangscontrole op de database kan draaien in plaats van op schijf.

Idempotent: bestaande rijen worden nooit gedupliceerd. Herhaald draaien bij
elke deploy is veilig — dat is precies hoe deploy.sh het aanroept.

Draaien:
    docker compose exec app python -m myproject.backfill_jobs
    python -m backfill_jobs            # vanuit myproject/ (container WORKDIR)
    python myproject/backfill_jobs.py

Exit-code 0 bij succes, 1 als er niets ingelezen kon worden.
"""
import glob
import json
import os
import sys

# `import app` moet werken ongeacht hoe dit script wordt aangeroepen. app.py
# gebruikt platte imports (from version import ...), dus myproject/ zelf moet
# op sys.path staan — bij `python -m myproject.backfill_jobs` is dat niet zo.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from app import Job, User, app, db  # noqa: E402

_SUFFIXES = ("_results.json", "_config.json")


def _job_ids_in(upload_folder):
    """Alle job_id's waarvoor metadata op schijf staat, gesorteerd."""
    ids = set()
    for suffix in _SUFFIXES:
        for path in glob.glob(os.path.join(upload_folder, f"*{suffix}")):
            ids.add(os.path.basename(path)[: -len(suffix)])
    return sorted(ids)


def _metadata_for(upload_folder, job_id):
    """
    Metadata voor één job. results.json wint van config.json (die is
    definitief), maar ontbrekende velden worden uit config.json aangevuld.
    """
    meta = {}
    for suffix in reversed(_SUFFIXES):          # eerst _config, dan _results
        path = os.path.join(upload_folder, f"{job_id}{suffix}")
        if not os.path.exists(path):
            continue
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception as e:
            print(f"  ! {job_id}{suffix}: onleesbaar ({e})")
            continue
        if not isinstance(data, dict):
            continue
        for key in ("owner_username", "site_id", "edf_path"):
            val = data.get(key)
            if val not in (None, ""):
                meta[key] = val
    return meta


def backfill(upload_folder=None, verbose=True):
    """
    Maak ontbrekende Job-rijen aan. Retourneert een samenvattend dict.

    Moet binnen een Flask app-context draaien.
    """
    upload_folder = upload_folder or app.config["UPLOAD_FOLDER"]
    job_ids = _job_ids_in(upload_folder)

    existing = {row.job_id for row in Job.query.with_entities(Job.job_id).all()}
    users = {u.username: u for u in User.query.all()}

    created, skipped, orphans = 0, 0, []

    for job_id in job_ids:
        if job_id in existing:
            skipped += 1
            continue

        meta = _metadata_for(upload_folder, job_id)
        owner_username = meta.get("owner_username") or None
        site_id = meta.get("site_id")
        edf_path = meta.get("edf_path") or ""

        user = users.get(owner_username) if owner_username else None
        if site_id is not None:
            try:
                site_id = int(site_id)
            except (TypeError, ValueError):
                site_id = None

        row = Job(
            job_id=job_id,
            owner_id=user.id if user else None,
            owner_username=owner_username,
            site_id=site_id,
            filename=os.path.basename(edf_path)[:300] if edf_path else "",
            status="backfilled",
        )
        db.session.add(row)
        created += 1

        if owner_username is None and site_id is None:
            orphans.append(job_id)
            if verbose:
                print(f"  ! {job_id}: geen owner_username en geen site_id in de "
                      f"metadata — rij aangemaakt zonder eigenaar")
        elif user is None and owner_username:
            if verbose:
                print(f"  ~ {job_id}: owner '{owner_username}' bestaat niet meer "
                      f"als user — owner_username bewaard, owner_id leeg")

    db.session.commit()

    summary = {
        "scanned": len(job_ids),
        "created": created,
        "already_present": skipped,
        "orphans": orphans,
    }

    if verbose:
        print()
        print(f"  upload-map        : {upload_folder}")
        print(f"  studies gevonden  : {summary['scanned']}")
        print(f"  rijen aangemaakt  : {summary['created']}")
        print(f"  reeds aanwezig    : {summary['already_present']}")
        print(f"  zonder eigenaar   : {len(orphans)}")
        if orphans:
            print("  → deze jobs hebben geen herleidbare eigenaar:")
            for job_id in orphans:
                print(f"      {job_id}")
            print("  → met JOB_ACCESS_STRICT=1 zijn ze alleen voor admins zichtbaar.")

    return summary


def main():
    print("═" * 62)
    print("  Job-registry backfill")
    print("═" * 62)
    with app.app_context():
        db.create_all()          # tabel kan nog ontbreken bij een eerste run
        try:
            summary = backfill()
        except Exception as e:
            print(f"  BACKFILL MISLUKT: {e}")
            return 1
    print("═" * 62)
    return 0


if __name__ == "__main__":
    sys.exit(main())
