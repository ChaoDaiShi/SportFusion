"""
Recognition result repository — formal: DB, demo: file, test: memory.
"""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class RecognitionRepository(ABC):
    @abstractmethod
    def save_batch(self, batch_id: str, results: list[dict]) -> None:
        ...

    @abstractmethod
    def load_batch(self, batch_id: str) -> list[dict]:
        ...

    @abstractmethod
    def delete_batch(self, batch_id: str) -> None:
        ...


class FileRecognitionRepository(RecognitionRepository):
    """File-based storage for demo/test."""
    def __init__(self, base_dir: str = "data/batches"):
        self._dir = Path(base_dir)

    def _path(self, batch_id: str) -> Path:
        return self._dir / batch_id / "recognition_results.json"

    def save_batch(self, batch_id: str, results: list[dict]) -> None:
        p = self._path(batch_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(results, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    def load_batch(self, batch_id: str) -> list[dict]:
        p = self._path(batch_id)
        if not p.exists():
            return []
        return json.loads(p.read_text(encoding="utf-8"))

    def delete_batch(self, batch_id: str) -> None:
        p = self._path(batch_id)
        if p.exists():
            p.unlink()


class MemoryRecognitionRepository(RecognitionRepository):
    """In-memory storage for tests."""
    def __init__(self):
        self._store: dict[str, list[dict]] = {}

    def save_batch(self, batch_id: str, results: list[dict]) -> None:
        self._store[batch_id] = list(results)

    def load_batch(self, batch_id: str) -> list[dict]:
        return list(self._store.get(batch_id, []))

    def delete_batch(self, batch_id: str) -> None:
        self._store.pop(batch_id, None)


class DBRecognitionRepository(RecognitionRepository):
    """
    Formal DB-backed recognition result repository.
    Uses EnterpriseBusiness table + RecognitionResult metadata.
    """
    def save_batch(self, batch_id: str, results: list[dict]) -> None:
        from models.database import SessionLocal
        db = SessionLocal()
        try:
            for r in results:
                existing = db.execute(
                    "SELECT id FROM enterprise_businesses WHERE enterprise_id = :eid",
                    {"eid": r.get("enterprise_id")},
                ).fetchone()
                if existing:
                    db.execute(
                        """UPDATE enterprise_businesses SET
                           sport_category=:cat, confidence=:conf, keywords=:kw,
                           sport_revenue_ratio=:ratio
                           WHERE enterprise_id=:eid""",
                        {
                            "cat": r.get("sport_category", ""),
                            "conf": r.get("confidence", 0.0),
                            "kw": json.dumps(r.get("keywords", [])),
                            "ratio": r.get("sport_score", 0.0),
                            "eid": r.get("enterprise_id"),
                        },
                    )
                else:
                    db.execute(
                        """INSERT INTO enterprise_businesses
                           (enterprise_id, sport_category, confidence, keywords, sport_revenue_ratio)
                           VALUES (:eid, :cat, :conf, :kw, :ratio)""",
                        {
                            "eid": r.get("enterprise_id"),
                            "cat": r.get("sport_category", ""),
                            "conf": r.get("confidence", 0.0),
                            "kw": json.dumps(r.get("keywords", [])),
                            "ratio": r.get("sport_score", 0.0),
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
                "SELECT enterprise_id, sport_category, confidence, keywords, sport_revenue_ratio FROM enterprise_businesses"
            ).fetchall()
            return [
                {
                    "enterprise_id": r[0],
                    "sport_category": r[1],
                    "confidence": r[2],
                    "keywords": json.loads(r[3]) if r[3] else [],
                    "sport_score": r[4] or 0.0,
                }
                for r in rows
            ]
        finally:
            db.close()

    def delete_batch(self, batch_id: str) -> None:
        from models.database import SessionLocal
        db = SessionLocal()
        try:
            db.execute("DELETE FROM enterprise_businesses")
            db.commit()
        finally:
            db.close()
