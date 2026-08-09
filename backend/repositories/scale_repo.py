"""Scale/Scenario/Validation repositories — formal: DB, demo: file, test: memory."""

import json
from abc import ABC, abstractmethod
from pathlib import Path


class ScaleRepository(ABC):
    @abstractmethod
    def save_batch(self, batch_id: str, results: list[dict]) -> None: ...
    @abstractmethod
    def load_batch(self, batch_id: str) -> list[dict]: ...
    @abstractmethod
    def delete_batch(self, batch_id: str) -> None: ...

class ScenarioRepository(ABC):
    @abstractmethod
    def save_batch(self, batch_id: str, results: list[dict]) -> None: ...
    @abstractmethod
    def load_batch(self, batch_id: str) -> list[dict]: ...
    @abstractmethod
    def delete_batch(self, batch_id: str) -> None: ...

class ValidationRepository(ABC):
    @abstractmethod
    def save_batch(self, batch_id: str, results: list[dict]) -> None: ...
    @abstractmethod
    def load_batch(self, batch_id: str) -> list[dict]: ...
    @abstractmethod
    def delete_batch(self, batch_id: str) -> None: ...


# ---- File implementations ----

class _FileRepo:
    def __init__(self, base_dir: str, name: str):
        self._dir = Path(base_dir)
        self._name = name
    def _path(self, b: str): return self._dir / b / f"{self._name}_results.json"
    def save_batch(self, b, r): p=self._path(b);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(r,indent=2,ensure_ascii=False,default=str),encoding="utf-8")
    def load_batch(self, b): p=self._path(b);return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    def delete_batch(self, b): p=self._path(b);p.unlink(missing_ok=True)

class FileScaleRepository(_FileRepo, ScaleRepository):
    def __init__(self, base_dir="data/batches"): super().__init__(base_dir, "scale")

class FileScenarioRepository(_FileRepo, ScenarioRepository):
    def __init__(self, base_dir="data/batches"): super().__init__(base_dir, "scenario")

class FileValidationRepository(_FileRepo, ValidationRepository):
    def __init__(self, base_dir="data/batches"): super().__init__(base_dir, "validation")


# ---- Memory implementations ----

class _MemRepo:
    def __init__(self): self._store: dict[str, list[dict]] = {}
    def save_batch(self, b, r): self._store[b] = list(r)
    def load_batch(self, b): return list(self._store.get(b, []))
    def delete_batch(self, b): self._store.pop(b, None)

class MemoryScaleRepository(_MemRepo, ScaleRepository): pass
class MemoryScenarioRepository(_MemRepo, ScenarioRepository): pass
class MemoryValidationRepository(_MemRepo, ValidationRepository): pass


# ---- DB implementations (formal canonical) ----

class DBScaleRepository(ScaleRepository):
    """Formal DB-backed using macro_calibrations table."""
    def save_batch(self, batch_id: str, results: list[dict]) -> None:
        from models.database import SessionLocal
        db = SessionLocal()
        try:
            for r in results:
                db.execute(
                    "INSERT INTO macro_calibrations (year, region, official_total_output, unit, source, source_version, metadata_json) "
                    "VALUES (:y, :reg, :tot, :unit, :src, :sv, :mj)",
                    {"y": 2022, "reg": "四川省", "tot": r.get("total_allocated", r.get("official_total", 2170.80)),
                     "unit": "亿元", "src": "batch export", "sv": batch_id, "mj": json.dumps(r)},
                )
            db.commit()
        finally:
            db.close()

    def load_batch(self, batch_id: str) -> list[dict]:
        from models.database import SessionLocal
        db = SessionLocal()
        try:
            rows = db.execute(
                "SELECT metadata_json FROM macro_calibrations WHERE source_version = :sv", {"sv": batch_id}
            ).fetchall()
            return [json.loads(r[0]) for r in rows if r[0]]
        finally:
            db.close()

    def delete_batch(self, batch_id: str) -> None:
        from models.database import SessionLocal
        db = SessionLocal()
        try: db.execute("DELETE FROM macro_calibrations WHERE source_version = :sv", {"sv": batch_id}); db.commit()
        finally: db.close()


class DBScenarioRepository(ScenarioRepository):
    """Formal DB-backed using scenario_runs table."""
    def save_batch(self, batch_id: str, results: list[dict]) -> None:
        from models.database import SessionLocal
        db = SessionLocal()
        try:
            for r in results:
                db.execute(
                    "INSERT INTO scenario_runs (scenario_id, evidence_calibration, alpha, total_allocated, "
                    "category_outputs_json, boundary_outputs_json, status, provenance_json) "
                    "VALUES (:sid, :ec, :a, :ta, :co, :bo, :st, :pj)",
                    {"sid": r.get("scenario_id", ""), "ec": r.get("evidence_calibration", ""),
                     "a": r.get("alpha", 0.0), "ta": r.get("total_allocated", 0.0),
                     "co": json.dumps(r.get("category_outputs", {})),
                     "bo": json.dumps(r.get("boundary_outputs", {})),
                     "st": r.get("status", "ok"), "pj": json.dumps(r.get("provenance", {}))},
                )
            db.commit()
        finally:
            db.close()

    def load_batch(self, batch_id: str) -> list[dict]:
        from models.database import SessionLocal
        db = SessionLocal()
        try:
            rows = db.execute(
                "SELECT scenario_id, evidence_calibration, alpha, total_allocated, "
                "category_outputs_json, boundary_outputs_json, status "
                "FROM scenario_runs"
            ).fetchall()
            return [
                {"scenario_id": r[0], "evidence_calibration": r[1], "alpha": r[2],
                 "total_allocated": r[3], "category_outputs": json.loads(r[4]) if r[4] else {},
                 "boundary_outputs": json.loads(r[5]) if r[5] else {}, "status": r[6]}
                for r in rows
            ]
        finally:
            db.close()

    def delete_batch(self, batch_id: str) -> None:
        from models.database import SessionLocal
        db = SessionLocal()
        try: db.execute("DELETE FROM scenario_runs"); db.commit()
        finally: db.close()


class DBValidationRepository(ValidationRepository):
    """Formal DB-backed using validation_runs table."""
    def save_batch(self, batch_id: str, results: list[dict]) -> None:
        from models.database import SessionLocal
        db = SessionLocal()
        try:
            for r in results:
                db.execute(
                    "INSERT INTO validation_runs (validation_type, metrics_json, n_samples, metadata_json) "
                    "VALUES (:vt, :mj, :n, :md)",
                    {"vt": r.get("type", "batch"), "mj": json.dumps(r),
                     "n": r.get("n_samples", 0), "md": json.dumps({"batch_id": batch_id})},
                )
            db.commit()
        finally:
            db.close()

    def load_batch(self, batch_id: str) -> list[dict]:
        from models.database import SessionLocal
        db = SessionLocal()
        try:
            rows = db.execute(
                "SELECT metrics_json FROM validation_runs WHERE metadata_json LIKE :bid",
                {"bid": f"%{batch_id}%"},
            ).fetchall()
            return [json.loads(r[0]) for r in rows if r[0]]
        finally:
            db.close()

    def delete_batch(self, batch_id: str) -> None:
        from models.database import SessionLocal
        db = SessionLocal()
        try: db.execute("DELETE FROM validation_runs WHERE metadata_json LIKE :bid", {"bid": f"%{batch_id}%"}); db.commit()
        finally: db.close()
