from __future__ import annotations

from sqlalchemy import create_engine, text

from scripts import post_migration_checks
from src.infrastructure.counter.postgres_repo import metadata


def test_post_checks_fail_on_bad_data(tmp_path, monkeypatch, caplog) -> None:
    db_path = tmp_path / "checks.sqlite"
    db_url = f"sqlite+pysqlite:///{db_path}"
    engine = create_engine(db_url, future=True)
    metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO counter_ledger (national_id, counter, year_code)
                VALUES ('1234567890', '543730001', '54')
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO counter_sequences (year_code, prefix, next_seq)
                VALUES ('54', '373', 10)
                """
            )
        )
    engine.dispose()

    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("PII_HASH_SALT", "salt")
    monkeypatch.setenv("COUNTER_ENV", "dev")

    caplog.set_level("ERROR")
    exit_code = post_migration_checks.main()
    assert exit_code == 1
    assert "Sequence alignment mismatches" in caplog.text
