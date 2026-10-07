import sqlite3
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from encyclopedia.models import Entry


class Command(BaseCommand):
    help = "Import missing encyclopedia entries from the project's SQLite database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sqlite",
            type=Path,
            default=Path(settings.BASE_DIR) / "db.sqlite3",
            help="Path to the source SQLite database (defaults to BASE_DIR/db.sqlite3).",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Write missing entries to the configured Django database. By default, only preview.",
        )

    def handle(self, *args, **options):
        database_path = options["sqlite"].expanduser().resolve()
        if not database_path.is_file():
            raise CommandError(f"SQLite database not found: {database_path}")

        try:
            source = sqlite3.connect(f"{database_path.as_uri()}?mode=ro", uri=True)
            try:
                table_exists = source.execute(
                    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                    ["encyclopedia_entry"],
                ).fetchone()
                if table_exists is None:
                    raise CommandError("SQLite table 'encyclopedia_entry' was not found.")

                columns = {
                    row[1] for row in source.execute("PRAGMA table_info(encyclopedia_entry)")
                }
                if not {"title", "content"}.issubset(columns):
                    raise CommandError(
                        "SQLite table 'encyclopedia_entry' must contain title and content columns."
                    )

                image_column = "image" if "image" in columns else "NULL"
                ordering = " ORDER BY id" if "id" in columns else ""
                rows = source.execute(
                    f"SELECT title, content, {image_column} FROM encyclopedia_entry{ordering}"
                ).fetchall()
            finally:
                source.close()
        except sqlite3.Error as error:
            raise CommandError(f"Could not read SQLite database: {error}") from error

        existing_titles = set(Entry.objects.values_list("title", flat=True))
        missing_entries = []
        skipped = 0

        for title, content, image_reference in rows:
            if title in existing_titles:
                skipped += 1
                continue

            missing_entries.append(
                Entry(
                    title=title,
                    content=content,
                    image=image_reference or None,
                )
            )
            existing_titles.add(title)

        self.stdout.write(f"SQLite entries found: {len(rows)}")
        self.stdout.write(f"Entries already in PostgreSQL or repeated in SQLite: {skipped}")
        self.stdout.write(f"Entries to import: {len(missing_entries)}")

        if not options["apply"]:
            self.stdout.write(self.style.WARNING("Dry run only; PostgreSQL was not changed."))
            self.stdout.write("Run again with --apply to import the missing entries.")
            return

        if missing_entries:
            with transaction.atomic():
                Entry.objects.bulk_create(
                    missing_entries,
                    batch_size=500,
                    ignore_conflicts=True,
                )

        self.stdout.write(self.style.SUCCESS("SQLite import completed."))