"""
tests/test_job_model.py — Job-registry: model, registratie en backfill.

De Job-tabel is de nieuwe autorisatiebron voor alles met een <job_id>.
Vóór deze tabel leefde die informatie alleen in JSON-bestanden op schijf.
Deze tests pinnen: de rij ontstaat bij submissie, de backfill haalt
bestaande studies in, en herhaald draaien dupliceert niets.

Run:
    pytest myproject/tests/test_job_model.py -v
"""
import json
import os

import pytest
from app import Job, Site, User, _register_job, app, db
from backfill_jobs import backfill


@pytest.fixture()
def ctx(tmp_path):
    """
    Schone database + eigen upload-map per test.

    De database is de wegwerp-SQLite die conftest.py via
    YASAFLASKIFIED_SQLALCHEMY_DATABASE_URI aanwijst; die moet vóór de import
    van `app` vastliggen, want Flask-SQLAlchemy cachet de engine — achteraf
    SQLALCHEMY_DATABASE_URI aanpassen doet niets. Isolatie komt hier dus van
    drop_all()/create_all() per test, niet van een aparte engine.

    UPLOAD_FOLDER wordt wél per test overschreven: dat leest de app pas op
    het moment van gebruik.
    """
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()

    prev_upload = app.config["UPLOAD_FOLDER"]
    app.config["UPLOAD_FOLDER"] = str(upload_dir)

    with app.app_context():
        db.drop_all()
        db.create_all()

        site_a = Site(name="Site A")
        site_b = Site(name="Site B")
        db.session.add_all([site_a, site_b])
        db.session.commit()

        alice = User(username="alice", password="x", role="user", site_id=site_a.id)
        bob = User(username="bob", password="x", role="user", site_id=site_b.id)
        db.session.add_all([alice, bob])
        db.session.commit()

        yield {
            "upload_dir": str(upload_dir),
            "alice": alice,
            "bob": bob,
            "site_a": site_a,
            "site_b": site_b,
        }

        db.session.remove()
        db.drop_all()

    app.config["UPLOAD_FOLDER"] = prev_upload


def _write_meta(upload_dir, job_id, suffix="_results.json", **fields):
    path = os.path.join(upload_dir, f"{job_id}{suffix}")
    with open(path, "w") as f:
        json.dump(fields, f)
    return path


# ══════════════════════════════════════════════════════════════
#  1. Registratie bij submissie
# ══════════════════════════════════════════════════════════════

def test_register_job_creates_row_with_owner_and_site(ctx):
    alice = ctx["alice"]
    _register_job("job-1", alice, filename="study.edf", status="parsed")

    row = Job.query.filter_by(job_id="job-1").first()
    assert row is not None
    assert row.owner_id == alice.id
    assert row.owner_username == "alice"
    assert row.site_id == ctx["site_a"].id
    assert row.filename == "study.edf"
    assert row.status == "parsed"
    assert row.created_at is not None
    assert row.archived is False


def test_register_job_is_idempotent_and_updates_status(ctx):
    alice = ctx["alice"]
    _register_job("job-1", alice, filename="study.edf", status="parsed")
    _register_job("job-1", alice, filename="study.edf", status="submitted",
                  site_id=alice.site_id)

    rows = Job.query.filter_by(job_id="job-1").all()
    assert len(rows) == 1, "submissie mag geen tweede rij maken"
    assert rows[0].status == "submitted"


def test_register_job_keeps_site_none_for_user_without_site(ctx):
    """site_id=None is een geldige waarde, geen 'niet meegegeven'."""
    loner = User(username="loner", password="x", role="user", site_id=None)
    db.session.add(loner)
    db.session.commit()

    _register_job("job-solo", loner, filename="s.edf", site_id=None)
    row = Job.query.filter_by(job_id="job-solo").first()
    assert row.site_id is None
    assert row.owner_username == "loner"


def test_register_job_survives_db_error(ctx, monkeypatch):
    """
    Een DB-probleem mag een upload nooit laten crashen: _register_job
    geeft None terug en de aanroeper gaat gewoon verder.
    """
    def _boom():
        raise RuntimeError("database is locked")

    monkeypatch.setattr(db.session, "commit", _boom)
    assert _register_job("job-boom", ctx["alice"], filename="s.edf") is None


def test_register_job_without_user_still_creates_row(ctx):
    """Zonder (geauthenticeerde) user: rij bestaat, eigenaar leeg."""
    row = _register_job("job-anon", None, filename="s.edf")
    assert row is not None
    assert row.owner_id is None
    assert row.owner_username is None


# ══════════════════════════════════════════════════════════════
#  2. Backfill
# ══════════════════════════════════════════════════════════════

def test_backfill_creates_rows_for_existing_studies(ctx):
    up = ctx["upload_dir"]
    _write_meta(up, "old-1", owner_username="alice",
                site_id=ctx["site_a"].id, edf_path="/data/uploads/one.edf")
    _write_meta(up, "old-2", owner_username="bob",
                site_id=ctx["site_b"].id, edf_path="/data/uploads/two.edf")
    _write_meta(up, "old-3", suffix="_config.json", owner_username="alice",
                site_id=ctx["site_a"].id, edf_path="/data/uploads/three.edf")

    summary = backfill(upload_folder=up, verbose=False)

    assert summary["scanned"] == 3
    assert summary["created"] == 3
    assert Job.query.count() == 3

    row = Job.query.filter_by(job_id="old-1").first()
    assert row.owner_username == "alice"
    assert row.owner_id == ctx["alice"].id
    assert row.site_id == ctx["site_a"].id
    assert row.filename == "one.edf"
    assert row.status == "backfilled"


def test_backfill_is_idempotent(ctx):
    up = ctx["upload_dir"]
    for i in range(3):
        _write_meta(up, f"old-{i}", owner_username="alice",
                    site_id=ctx["site_a"].id, edf_path=f"/x/{i}.edf")

    first = backfill(upload_folder=up, verbose=False)
    second = backfill(upload_folder=up, verbose=False)

    assert first["created"] == 3
    assert second["created"] == 0, "tweede run mag geen rijen toevoegen"
    assert second["already_present"] == 3
    assert Job.query.count() == 3


def test_backfill_job_without_metadata_gets_orphan_row(ctx):
    """Geen owner en geen site → rij zonder eigenaar, geen crash."""
    up = ctx["upload_dir"]
    _write_meta(up, "nometa")                       # leeg JSON-object

    summary = backfill(upload_folder=up, verbose=False)

    assert summary["created"] == 1
    assert summary["orphans"] == ["nometa"]
    row = Job.query.filter_by(job_id="nometa").first()
    assert row.owner_id is None
    assert row.owner_username is None
    assert row.site_id is None


def test_backfill_unreadable_json_does_not_crash(ctx):
    up = ctx["upload_dir"]
    with open(os.path.join(up, "broken_results.json"), "w") as f:
        f.write("{ this is not json")

    summary = backfill(upload_folder=up, verbose=False)

    assert summary["created"] == 1
    assert Job.query.filter_by(job_id="broken").first() is not None


def test_backfill_owner_no_longer_a_user(ctx):
    """Verwijderde user: owner_username blijft, owner_id leeg."""
    up = ctx["upload_dir"]
    _write_meta(up, "ghost", owner_username="deleted_user",
                site_id=ctx["site_a"].id, edf_path="/x/g.edf")

    backfill(upload_folder=up, verbose=False)

    row = Job.query.filter_by(job_id="ghost").first()
    assert row.owner_username == "deleted_user"
    assert row.owner_id is None
    assert row.site_id == ctx["site_a"].id


def test_backfill_results_json_wins_over_config_json(ctx):
    up = ctx["upload_dir"]
    _write_meta(up, "both", suffix="_config.json",
                owner_username="bob", site_id=ctx["site_b"].id,
                edf_path="/x/from_config.edf")
    _write_meta(up, "both", suffix="_results.json",
                owner_username="alice", site_id=ctx["site_a"].id,
                edf_path="/x/from_results.edf")

    summary = backfill(upload_folder=up, verbose=False)

    assert summary["scanned"] == 1, "één job_id, twee bestanden"
    row = Job.query.filter_by(job_id="both").first()
    assert row.owner_username == "alice"
    assert row.site_id == ctx["site_a"].id
    assert row.filename == "from_results.edf"


def test_backfill_fills_gaps_from_config_json(ctx):
    """results.json zonder site_id → aanvullen uit config.json."""
    up = ctx["upload_dir"]
    _write_meta(up, "partial", suffix="_config.json", site_id=ctx["site_b"].id)
    _write_meta(up, "partial", suffix="_results.json", owner_username="bob",
                edf_path="/x/p.edf")

    backfill(upload_folder=up, verbose=False)

    row = Job.query.filter_by(job_id="partial").first()
    assert row.owner_username == "bob"
    assert row.site_id == ctx["site_b"].id


def test_backfill_leaves_rows_from_submission_untouched(ctx):
    """Een rij die de webapp al maakte mag de backfill niet overschrijven."""
    up = ctx["upload_dir"]
    _register_job("live-1", ctx["alice"], filename="live.edf", status="submitted")
    _write_meta(up, "live-1", owner_username="bob", site_id=ctx["site_b"].id,
                edf_path="/x/other.edf")

    summary = backfill(upload_folder=up, verbose=False)

    assert summary["created"] == 0
    row = Job.query.filter_by(job_id="live-1").first()
    assert row.owner_username == "alice"
    assert row.status == "submitted"


def test_backfill_empty_upload_folder(ctx):
    summary = backfill(upload_folder=ctx["upload_dir"], verbose=False)
    assert summary == {"scanned": 0, "created": 0,
                       "already_present": 0, "orphans": []}
