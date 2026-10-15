import sqlite3
from pathlib import Path
from datetime import datetime

from sqlalchemy import inspect, text

from database import engine, Base
import models


def migrate():
    tables = inspect(engine).get_table_names()

    if "events" in tables:
        columns = {
            column["name"]
            for column in inspect(engine).get_columns("events")
        }

        missing = {
            "total_tickets",
            "reserved_tickets",
        } - columns

        if missing:
            if engine.dialect.name != "sqlite":
                raise RuntimeError(
                    "This migration supports SQLite only."
                )

            filename = engine.url.database

            if filename and filename != ":memory:":
                backup = (
                    str(Path(filename).resolve())
                    + ".phase4-"
                    + datetime.now().strftime(
                        "%Y%m%d-%H%M%S-%f"
                    )
                    + ".bak"
                )

                with (
                    sqlite3.connect(filename) as source,
                    sqlite3.connect(backup) as destination,
                ):
                    source.backup(destination)

                print("Database backup:", backup)

            with engine.begin() as connection:
                if "total_tickets" in missing:
                    connection.execute(
                        text(
                            "ALTER TABLE events "
                            "ADD COLUMN total_tickets INTEGER"
                        )
                    )

                if "reserved_tickets" in missing:
                    connection.execute(
                        text(
                            "ALTER TABLE events "
                            "ADD COLUMN reserved_tickets "
                            "INTEGER NOT NULL DEFAULT 0"
                        )
                    )

                    if "bookings" in tables:
                        connection.execute(
                            text(
                                """
                                UPDATE events
                                SET reserved_tickets = COALESCE(
                                    (
                                        SELECT SUM(ticket_quantity)
                                        FROM bookings
                                        WHERE bookings.event_id = events.id
                                        AND booking_status IN (
                                            'PENDING',
                                            'PROCESSING',
                                            'CONFIRMED'
                                        )
                                    ),
                                    0
                                )
                                """
                            )
                        )

    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    migrate()
    print("Phase 4 database ready.")