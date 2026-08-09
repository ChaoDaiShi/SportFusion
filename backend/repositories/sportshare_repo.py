"""SportShare prediction repository — formal: DB, demo: file, test: memory."""

import json
from abc import ABC, abstractmethod
from pathlib import Path


class SportShareRepository(ABC):
    @abstractmethod
    def save_batch(self, batch_id: str, results: list[dict]) -> None: ...
    @abstractmethod
    def load_batch(self, batch_id: str) -> list[dict]: ...
    @abstractmethod
    def delete_batch(self, batch_id: str) -> None: ...


class FileSportShareRepository(SportShareRepository):
    def __init__(self, base_dir: str = "data/batches"):
        self._dir = Path(base_dir)
    def _path(self, b: str) -> Path: return self._dir / b / "share_results.json"
    def save_batch(self, b, r): p=self._path(b);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(r,indent=2,ensure_ascii=False,default=str),encoding="utf-8")
    def load_batch(self, b): p=self._path(b);return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    def delete_batch(self, b): p=self._path(b);p.unlink(missing_ok=True)


class MemorySportShareRepository(SportShareRepository):
    def __init__(self): self._store: dict[str, list[dict]] = {}
    def save_batch(self, b, r): self._store[b] = list(r)
    def load_batch(self, b): return list(self._store.get(b, []))
    def delete_batch(self, b): self._store.pop(b, None)


class DBSportShareRepository(SportShareRepository):
    """Formal DB-backed SportShare repository using sportshare_predictions table."""
    def save_batch(self, batch_id: str, results: list[dict]) -> None:
        from models.database import SessionLocal
        db = SessionLocal()
        try:
            for r in results:
                db.execute(
                    """INSERT OR REPLACE INTO sportshare_predictions
                       (enterprise_id, credit_code, model_share, fallback_share,
                        manual_share, effective_share, share_source,
                        lower_bound, upper_bound, model_version, residual_q90,
                        sport_score, sport_category, metadata_json)
                       VALUES (:eid, :cc, :ms, :fs, :mas, :es, :ss,
                               :lb, :ub, :mv, :rq, :sc, :cat, :mj)""",
                    {
                        "eid": str(r.get("enterprise_id", "")),
                        "cc": r.get("credit_code", ""),
                        "ms": r.get("model_share"),
                        "fs": r.get("fallback_share"),
                        "mas": r.get("manual_share"),
                        "es": r.get("effective_share", 0.0),
                        "ss": r.get("share_source", "none"),
                        "lb": r.get("lower_bound", 0.0),
                        "ub": r.get("upper_bound", 1.0),
                        "mv": r.get("model_version", ""),
                        "rq": r.get("residual_q90"),
                        "sc": r.get("sport_score", 0.0),
                        "cat": r.get("sport_category", ""),
                        "mj": json.dumps(r.get("metadata", {})),
                    },
                )
            db.commit()
        finally:
            db.close()

    def load_batch(self, batch_id: str) -> list[dict]:
        from models.database import SessionLocal
        db = SessionLocal()
        try:
            rows = db.execute(
                "SELECT enterprise_id, credit_code, model_share, fallback_share, manual_share, "
                "effective_share, share_source, lower_bound, upper_bound, model_version, "
                "residual_q90, sport_score, sport_category, metadata_json FROM sportshare_predictions"
            ).fetchall()
            return [
                {"enterprise_id": r[0], "credit_code": r[1], "model_share": r[2],
                 "fallback_share": r[3], "manual_share": r[4], "effective_share": r[5],
                 "share_source": r[6], "lower_bound": r[7], "upper_bound": r[8],
                 "model_version": r[9], "residual_q90": r[10], "sport_score": r[11],
                 "sport_category": r[12], "metadata": json.loads(r[13]) if r[13] else {}}
                for r in rows
            ]
        finally:
            db.close()

    def delete_batch(self, batch_id: str) -> None:
        from models.database import SessionLocal
        db = SessionLocal()
        try: db.execute("DELETE FROM sportshare_predictions"); db.commit()
        finally: db.close()
