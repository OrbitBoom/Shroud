"""Local, single-writer SQLite journal. No pygame or network dependency."""
import argparse
import json
import sqlite3
from pathlib import Path
from uuid import uuid4

from shroud.profiling import Interpreter, RULE_VERSION, scores

DEFAULT_PATH = Path.home() / ".shroud" / "profile.sqlite3"
APPLICATION_ID = 0x53485244  # SHRD
GAME_VERSION = "0.1.0"  # Matches pyproject.toml, including source checkouts.
MIGRATIONS = (
    (
        "CREATE TABLE sessions(id TEXT PRIMARY KEY, started TEXT DEFAULT CURRENT_TIMESTAMP, game_version TEXT, status TEXT)",
        "CREATE TABLE runs(id TEXT PRIMARY KEY, session TEXT REFERENCES sessions, status TEXT)",
        "CREATE TABLE attempts(id TEXT PRIMARY KEY, run TEXT REFERENCES runs, start_reason TEXT, status TEXT, seconds REAL DEFAULT 0)",
        """CREATE TABLE events(id INTEGER PRIMARY KEY, attempt TEXT REFERENCES attempts, seq INTEGER,
           seconds REAL, name TEXT, kind TEXT, developer INTEGER, schema_version INTEGER,
           context TEXT, details TEXT, UNIQUE(attempt,seq))""",
    ), (
        """CREATE TABLE evidence(id INTEGER PRIMARY KEY, event INTEGER REFERENCES events, version INTEGER,
           signal TEXT, value INTEGER CHECK(value IN (-1,1)), reason TEXT, sources TEXT)""",
        "CREATE TABLE updates(evidence INTEGER PRIMARY KEY REFERENCES evidence, profile TEXT)",
        "CREATE VIEW preferences AS SELECT * FROM events WHERE name IN ('reward_offered','reward_reopened','reward_confirmed','route_offered','route_taken')",
        "CREATE VIEW behaviour AS SELECT * FROM events WHERE kind IN ('use','movement','environment') OR name='route_taken'",
        "CREATE VIEW performance AS SELECT * FROM events WHERE kind='performance'",
        """CREATE VIEW area_time AS SELECT attempt, json_extract(context,'$.level') AS level,
           json_extract(details,'$.area') AS area, sum(json_extract(details,'$.seconds')) AS seconds
           FROM events WHERE name='area_sample' GROUP BY attempt,level,area""",
        """CREATE VIEW run_summary AS SELECT runs.*, coalesce(sum(attempts.seconds),0) AS seconds,
           count(attempts.id) AS attempts, sum(CASE WHEN attempts.status='death' THEN 1 ELSE 0 END) AS deaths
           FROM runs LEFT JOIN attempts ON attempts.run=runs.id GROUP BY runs.id""",
    ),
)


class ProfileStore:
    def __init__(self, path=DEFAULT_PATH, *, playing=True):
        path = Path(path)
        if not playing and not path.is_file():
            raise ValueError("No profile database at this path")
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=0.25)
        self.db.row_factory = sqlite3.Row
        self.run = self.attempt = self.session = None
        self.enabled = True
        self.interpreter = Interpreter()
        try:
            self.db.execute("PRAGMA foreign_keys=ON")
            self.db.execute("PRAGMA secure_delete=ON")
            # Retain the file lock between commits. Only an abandoned writer can be recovered.
            self.db.execute("PRAGMA locking_mode=EXCLUSIVE")
            with self.db:
                self.db.execute("BEGIN EXCLUSIVE")
                tag = self.db.execute("PRAGMA application_id").fetchone()[0]
                version = self.db.execute("PRAGMA user_version").fetchone()[0]
                empty = not self.db.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchone()
                if tag != APPLICATION_ID and not (playing and empty and tag == version == 0):
                    raise ValueError("Unrecognised database; choose a SHROUD profile file")
                if not 0 <= version <= len(MIGRATIONS):
                    raise ValueError("Unsupported profile schema")
                self.db.execute(f"PRAGMA application_id={APPLICATION_ID}")
                for number in range(version, len(MIGRATIONS)):
                    for statement in MIGRATIONS[number]:
                        self.db.execute(statement)
                    if number == 1 and version == 1:
                        self._interpret_existing_events()
                    self.db.execute(f"PRAGMA user_version={number + 1}")
                if playing:
                    for table in ("attempts", "runs", "sessions"):
                        self.db.execute(f"UPDATE {table} SET status='interrupted' WHERE status='playing'")
                    self.session = uuid4().hex
                    self.db.execute("INSERT INTO sessions(id,game_version,status) VALUES(?,?,'playing')",
                                    (self.session, GAME_VERSION))
        except Exception:
            self.db.close()
            raise

    def begin_run(self):
        with self.db:
            self._end_run("replaced")
            self.run = uuid4().hex
            self.db.execute("INSERT INTO runs VALUES(?,?,'playing')", (self.run, self.session))
            self._new_attempt("start")

    def _new_attempt(self, reason):
        self.attempt = uuid4().hex
        self.interpreter = Interpreter()
        self.db.execute("INSERT INTO attempts(id,run,start_reason,status) VALUES(?,?,?,'playing')",
                        (self.attempt, self.run, reason))

    def next_attempt(self, reason):
        with self.db:
            status = self.db.execute("SELECT status FROM runs WHERE id=?", (self.run,)).fetchone()[0]
            if status == "completed":
                self.run = uuid4().hex
                self.db.execute("INSERT INTO runs VALUES(?,?,'playing')", (self.run, self.session))
            else:
                self.db.execute("UPDATE attempts SET status='restarted' WHERE id=? AND status='playing'", (self.attempt,))
                self.db.execute("UPDATE runs SET status='playing' WHERE id=?", (self.run,))
            self._new_attempt(reason)

    def record(self, row):
        with self.db:
            details = dict(row["details"])
            if row["event"] == "retry_started":
                previous = self.db.execute("""SELECT events.id FROM events
                    JOIN attempts ON attempts.id=events.attempt
                    WHERE attempts.run=? AND events.name='run_ended'
                    AND json_extract(events.details,'$.reason')='death' ORDER BY events.id DESC LIMIT 1""",
                    (self.run,)).fetchone()
                if previous:
                    details["previous_death_event"] = previous[0]
            event = self.db.execute(
                """INSERT INTO events(attempt,seq,seconds,name,kind,developer,schema_version,context,details)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (self.attempt, row["sequence"], row["timestamp"], row["event"], row["kind"],
                 row["developer"], row["schema_version"], json.dumps(row["context"]), json.dumps(details))
            ).lastrowid
            self.db.execute("UPDATE attempts SET seconds=? WHERE id=?", (row["timestamp"], self.attempt))
            if row["event"] == "run_ended":
                outcome = details["reason"]
                self.db.execute("UPDATE attempts SET status=? WHERE id=?", (outcome, self.attempt))
                self.db.execute("UPDATE runs SET status=? WHERE id=?", (outcome, self.run))
            self._interpret(dict(row, details=details), event)

    def _interpret(self, row, event):
        if row["developer"]:
            return
        for item in self.interpreter.consume(row, event):
            evidence = self.db.execute(
                "INSERT INTO evidence(event,version,signal,value,reason,sources) VALUES(?,?,?,?,?,?)",
                (event, RULE_VERSION, item.signal, item.value, item.reason, json.dumps(item.sources))
            ).lastrowid
            self.db.execute("INSERT INTO updates VALUES(?,?)", (evidence, json.dumps(self.profile())))

    def _interpret_existing_events(self):
        previous_attempt = None
        for row in self.db.execute("SELECT * FROM events ORDER BY id"):
            if row["attempt"] != previous_attempt:
                self.interpreter = Interpreter()
                previous_attempt = row["attempt"]
            self._interpret(dict(event=row["name"], timestamp=row["seconds"], developer=row["developer"],
                                 context=json.loads(row["context"]), details=json.loads(row["details"])), row["id"])

    def profile(self):
        rows = self.db.execute("""SELECT signal,value,attempts.run,json_extract(context,'$.level'),
            json_extract(context,'$.biome'),json_extract(context,'$.difficulty')
            FROM evidence JOIN events ON events.id=evidence.event JOIN attempts ON attempts.id=events.attempt
            WHERE evidence.version=? ORDER BY evidence.id""", (RULE_VERSION,))
        return scores(rows)

    def _end_run(self, reason):
        for table, key in (("attempts",self.attempt), ("runs",self.run)):
            self.db.execute(f"UPDATE {table} SET status=? WHERE id=? AND status='playing'", (reason,key))

    def close(self, reason="quit"):
        try:
            if self.session:
                with self.db:
                    self._end_run(reason)
                    self.db.execute("UPDATE sessions SET status=? WHERE id=?", (reason,self.session))
        finally:
            self.db.close()

    def export(self, destination):
        tables = ("sessions","runs","attempts","events","evidence","updates")
        result = {"schema_version": len(MIGRATIONS), "rule_version": RULE_VERSION, "profile": self.profile()}
        for table in tables:
            result[table] = [dict(row) for row in self.db.execute(f"SELECT * FROM {table} ORDER BY rowid")]
            for row in result[table]:
                for field in ("context","details","sources","profile"):
                    if field in row:
                        row[field] = json.loads(row[field])
        with Path(destination).open("x", encoding="utf8") as file:
            json.dump(result,file,indent=2)

    def delete_data(self):
        if self.session:
            raise ValueError("Close the game before clearing its profile")
        with self.db:
            for table in ("updates","evidence","events","attempts","runs","sessions"):
                self.db.execute(f"DELETE FROM {table}")


def main():
    parser = argparse.ArgumentParser(description="Inspect SHROUD's offline gameplay profile with the game closed")
    parser.add_argument("--db", type=Path, default=DEFAULT_PATH)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("show")
    commands.add_parser("export").add_argument("destination")
    commands.add_parser("delete", help="Erase all profile data from this database")
    args = parser.parse_args()
    try:
        store = ProfileStore(args.db, playing=False)
        try:
            if args.command == "show":
                print(json.dumps(store.profile(),indent=2))
            elif args.command == "export":
                store.export(args.destination)
            else:
                store.delete_data()
        finally:
            store.close()
    except (ValueError, OSError, sqlite3.Error) as error:
        parser.exit(1,f"{error}\n")


if __name__ == "__main__":
    main()
