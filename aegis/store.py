import json
import sqlite3
import time
from contextlib import contextmanager


class Store:
    def __init__(self, home):
        self.path = home / "aegis.db"
        with self.db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS runs (
                  id TEXT PRIMARY KEY, started REAL, status TEXT, payload TEXT);
                CREATE TABLE IF NOT EXISTS reservations (
                  id TEXT PRIMARY KEY, amount REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS costs (
                  id TEXT PRIMARY KEY, amount REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS cache (
                  key TEXT PRIMARY KEY, scope TEXT, vector TEXT, payload TEXT, expires REAL);
            """)

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def reserve(self, rid, amount, budget):
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            spent = db.execute("SELECT coalesce(sum(amount),0) FROM costs").fetchone()[0]
            held = db.execute("SELECT coalesce(sum(amount),0) FROM reservations").fetchone()[0]
            if spent + held + amount > budget:
                return False
            db.execute("INSERT INTO reservations VALUES (?,?)", (rid, amount))
            return True

    def finish(self, run, cost, uncertain=False):
        with self.db() as db:
            # Unknown usage retains the conservative reservation until reviewed.
            if not uncertain:
                db.execute("DELETE FROM reservations WHERE id=?", (run["id"],))
            db.execute("INSERT OR REPLACE INTO costs VALUES (?,?)", (run["id"], cost))
            db.execute(
                "INSERT OR REPLACE INTO runs VALUES (?,?,?,?)",
                (run["id"], run["started"], run["status"], json.dumps(run)),
            )

    def runs(self, limit=100):
        with self.db() as db:
            return [
                json.loads(r[0])
                for r in db.execute("SELECT payload FROM runs ORDER BY started DESC LIMIT ?", (limit,))
            ]

    def budget_state(self):
        with self.db() as db:
            return {
                "spent": db.execute("SELECT coalesce(sum(amount),0) FROM costs").fetchone()[0],
                "reserved": db.execute("SELECT coalesce(sum(amount),0) FROM reservations").fetchone()[0],
            }

    def cache_get(self, scope):
        with self.db() as db:
            db.execute("DELETE FROM cache WHERE expires < ?", (time.time(),))
            return [dict(r) for r in db.execute("SELECT * FROM cache WHERE scope=?", (scope,))]

    def cache_put(self, key, scope, vector, payload, ttl):
        with self.db() as db:
            db.execute("DELETE FROM cache WHERE expires < ?", (time.time(),))
            # Bounded storage for the local lab.
            db.execute(
                "DELETE FROM cache WHERE key IN (SELECT key FROM cache ORDER BY expires LIMIT max(0,(SELECT count(*) FROM cache)-199))"
            )
            db.execute(
                "INSERT OR REPLACE INTO cache VALUES (?,?,?,?,?)",
                (key, scope, json.dumps(vector), json.dumps(payload), time.time() + ttl),
            )
