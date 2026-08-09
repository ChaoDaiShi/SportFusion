"""
批次管理服务 — Phase 4: batch as core primary key for all formal computation.

Every formal computation must belong to a batch.
Replaces global dict / timestamp cache_key patterns.
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from knowledge.loader import get_active_version_metadata


class BatchStatus(str, Enum):
    CREATED = "created"
    DATA_READY = "data_ready"
    IMPORTING = "importing"
    IMPORTED = "imported"
    RECOGNITION_RUNNING = "recognition_running"
    RECOGNITION_DONE = "recognition_done"
    SHARE_RUNNING = "share_running"
    SHARE_DONE = "share_done"
    SCALE_RUNNING = "scale_running"
    SCALE_DONE = "scale_done"
    VALIDATION_RUNNING = "validation_running"
    VALIDATION_DONE = "validation_done"
    REVIEWING = "reviewing"
    REVIEW_DONE = "review_done"
    FINALIZED = "finalized"
    LOCKED = "locked"
    ERROR = "error"


class DataMode(str, Enum):
    FORMAL = "formal"
    DEMO = "demo"
    TEST = "test"


@dataclass
class BatchRecord:
    """批次记录 — all formal computation belongs here"""

    batch_id: str = ""
    batch_number: str = ""
    data_mode: str = DataMode.FORMAL.value

    # Data versions
    data_version: str = ""
    source_file_name: str = ""
    source_file_sha256: str = ""
    total_rows: int = 0

    # Knowledge versions (from Phase 2)
    dictionary_version: str = ""
    industry_code_map_version: str = ""
    feature_schema_version: str = ""

    # Model versions (from Phase 3)
    sportscore_parameter_version: str = ""
    sportshare_model_version: str = ""
    macro_calibration_version: str = ""
    scenario_version: str = ""

    # Provenance
    commit_sha: str = ""

    # Status
    status: str = BatchStatus.CREATED.value
    operator: str = ""

    # Timestamps
    created_at: str = ""
    completed_at: str | None = None
    locked_at: str | None = None

    # Stats
    sport_count: int = 0
    crossover_count: int = 0
    model_estimated_count: int = 0
    fallback_estimated_count: int = 0

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditLogEntry:
    """审计日志条目"""
    id: str = ""
    batch_id: str = ""
    actor: str = ""
    action: str = ""
    target: str = ""
    timestamp: str = ""
    before_summary: str = ""
    after_summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# ---- Batch Store ----

class BatchStore:
    """
    File-based batch store (delegates to DB when available).

    Provides CRUD for BatchRecord and associates all results with a batch.
    Survives server restarts by persisting to disk/DB.
    """

    def __init__(self, storage_dir: str | Path = "data/batches"):
        self._dir = Path(storage_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._dir / "batch_index.json"

    def _load_index(self) -> dict[str, dict]:
        if self._index_path.exists():
            return json.loads(self._index_path.read_text(encoding="utf-8"))
        return {}

    def _save_index(self, index: dict) -> None:
        self._index_path.write_text(
            json.dumps(index, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    def create_batch(
        self,
        data_mode: str = DataMode.FORMAL.value,
        source_file_name: str = "",
        source_file_sha256: str = "",
        total_rows: int = 0,
        operator: str = "",
    ) -> BatchRecord:
        """Create a new batch with full provenance."""
        batch_id = f"BATCH-{datetime.now(UTC).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        versions = get_active_version_metadata()

        batch = BatchRecord(
            batch_id=batch_id,
            batch_number=batch_id,
            data_mode=data_mode,
            source_file_name=source_file_name,
            source_file_sha256=source_file_sha256,
            total_rows=total_rows,
            dictionary_version=versions.get("dictionary_version", ""),
            industry_code_map_version=versions.get("industry_code_map_version", ""),
            feature_schema_version=versions.get("feature_schema_version", ""),
            sportscore_parameter_version=versions.get("parameter_version", ""),
            sportshare_model_version="SPORTSHARE-RF-2026-08",
            macro_calibration_version="OFFICIAL-TOTALS-2026-08",
            scenario_version="SCENARIO-2026-08",
            operator=operator,
            created_at=datetime.now(UTC).isoformat(),
            status=BatchStatus.CREATED.value,
        )

        batch_dir = self._dir / batch_id
        batch_dir.mkdir(parents=True, exist_ok=True)

        self._save_batch(batch)
        self._audit(batch_id, operator, "CREATE_BATCH", batch_id)

        return batch

    def _save_batch(self, batch: BatchRecord) -> None:
        index = self._load_index()
        index[batch.batch_id] = {
            k: v for k, v in batch.__dict__.items()
            if not k.startswith("_")
        }
        self._save_index(index)

    def get_batch(self, batch_id: str) -> BatchRecord | None:
        index = self._load_index()
        data = index.get(batch_id)
        if data is None:
            return None
        return BatchRecord(**data)

    def update_status(self, batch_id: str, status: str) -> None:
        index = self._load_index()
        if batch_id in index:
            index[batch_id]["status"] = status
            if status == BatchStatus.LOCKED.value:
                index[batch_id]["locked_at"] = datetime.now(UTC).isoformat()
            self._save_index(index)

    def lock_batch(self, batch_id: str, operator: str = "") -> bool:
        batch = self.get_batch(batch_id)
        if batch is None:
            return False
        self.update_status(batch_id, BatchStatus.LOCKED.value)
        self._audit(batch_id, operator, "LOCK_BATCH", batch_id)
        return True

    def is_locked(self, batch_id: str) -> bool:
        batch = self.get_batch(batch_id)
        return batch is not None and batch.status == BatchStatus.LOCKED.value

    def list_batches(self, data_mode: str | None = None) -> list[BatchRecord]:
        index = self._load_index()
        batches = [BatchRecord(**d) for d in index.values()]
        if data_mode:
            batches = [b for b in batches if b.data_mode == data_mode]
        return sorted(batches, key=lambda b: b.created_at, reverse=True)

    def _audit(self, batch_id: str, actor: str, action: str, target: str) -> None:
        entry = AuditLogEntry(
            id=uuid.uuid4().hex[:12],
            batch_id=batch_id,
            actor=actor,
            action=action,
            target=target,
            timestamp=datetime.now(UTC).isoformat(),
        )
        audit_file = self._dir / batch_id / "audit_log.jsonl"
        with open(audit_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.__dict__, ensure_ascii=False, default=str) + "\n")

    def get_audit_log(self, batch_id: str) -> list[AuditLogEntry]:
        audit_file = self._dir / batch_id / "audit_log.jsonl"
        if not audit_file.exists():
            return []
        entries = []
        for line in audit_file.read_text(encoding="utf-8").strip().split("\n"):
            if line.strip():
                entries.append(AuditLogEntry(**json.loads(line)))
        return entries

    def save_results(self, batch_id: str, result_type: str, results: list[dict]) -> None:
        """Save batch results (recognition, share, scale, etc.) to disk."""
        if self.is_locked(batch_id):
            raise ValueError(f"Batch {batch_id} is locked — cannot modify results")
        result_file = self._dir / batch_id / f"{result_type}_results.json"
        result_file.write_text(
            json.dumps(results, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    def load_results(self, batch_id: str, result_type: str) -> list[dict]:
        result_file = self._dir / batch_id / f"{result_type}_results.json"
        if not result_file.exists():
            return []
        return json.loads(result_file.read_text(encoding="utf-8"))


# Global singleton
_batch_store: BatchStore | None = None


def get_batch_store() -> BatchStore:
    global _batch_store
    if _batch_store is None:
        _batch_store = BatchStore()
    return _batch_store
