"""Preview or remove only meetings whose titles are used by Playwright tests."""

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text


TEST_MEETING_TITLES = (
    "Playwright meeting",
    "Playwright cancellation test",
    "Họp Đánh Giá Đồ An",
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="delete matching test meetings (default is a dry run)",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    load_dotenv(project_root / ".env")
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        parser.error("DATABASE_URL is not set in the environment or project .env")

    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        if not inspect(engine).has_table("meetings"):
            raise RuntimeError("The configured database has no meetings table.")

        title_parameters = {
            f"title_{index}": title
            for index, title in enumerate(TEST_MEETING_TITLES)
        }
        placeholders = ", ".join(f":{name}" for name in title_parameters)
        matching_meetings = text(
            f"SELECT id, title FROM meetings "
            f"WHERE title IN ({placeholders}) ORDER BY id"
        )
        delete_meetings = text(
            f"DELETE FROM meetings WHERE title IN ({placeholders})"
        )

        with engine.begin() as connection:
            rows = connection.execute(matching_meetings, title_parameters).all()
            if not rows:
                print("No Playwright test meetings matched the cleanup allowlist.")
                return

            print("Matching meeting rows:")
            for meeting_id, title in rows:
                print(f"  id={meeting_id}: {title}")

            if not args.apply:
                print("Dry run only. Pass --apply to delete these meeting rows.")
                return

            result = connection.execute(delete_meetings, title_parameters)
            print(f"Deleted {result.rowcount} matching meeting row(s).")
            print("Rooms and user accounts were not modified.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
