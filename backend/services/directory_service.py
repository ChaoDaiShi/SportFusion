"""
动态名录服务 — Phase 4: finalized enterprise directory.

Only confirmed/locked enterprises appear in the directory.
Pending/disputed enterprises are excluded.
"""

from dataclasses import dataclass, field
from typing import Any

from services.batch_service import BatchStore, get_batch_store


@dataclass
class DirectoryEntry:
    enterprise_id: str = ""
    credit_code: str = ""
    enterprise_name: str = ""
    region: str = ""
    industry_code: str = ""
    sport_score: float = 0.0
    evidence_relation: str = ""
    model_share: float | None = None
    fallback_share: float | None = None
    manual_share: float | None = None
    effective_share: float = 0.0
    share_source: str = "none"
    sport_category: str = ""
    crossover_type: str = ""
    review_status: str = ""
    priority: str = ""
    batch_id: str = ""
    is_finalized: bool = False
    provenance: dict[str, Any] = field(default_factory=dict)


class DirectoryService:
    """Read-only directory of finalized enterprises."""

    def __init__(self, store: BatchStore | None = None):
        self._store = store or get_batch_store()

    def get_directory(
        self,
        batch_id: str | None = None,
        region: str | None = None,
        category: str | None = None,
        crossover: bool | None = None,
        priority: str | None = None,
        review_status: str | None = None,
    ) -> list[DirectoryEntry]:
        """
        Query directory entries. Only returns finalized (confirmed/locked) enterprises.
        """
        entries = []
        batches_to_check = [batch_id] if batch_id else [
            b.batch_id for b in self._store.list_batches()
        ]

        for bid in batches_to_check:
            # Load recognition, share, and review results
            recs = self._store.load_results(bid, "recognition")
            shares = self._store.load_results(bid, "share")
            reviews = self._store.load_results(bid, "review")

            # Build lookup
            share_by_id: dict[str, dict] = {}
            for s in shares:
                eid = str(s.get("enterprise_id", ""))
                share_by_id[eid] = s

            review_by_id: dict[str, dict] = {}
            for r in reviews:
                eid = str(r.get("enterprise_id", ""))
                review_by_id[eid] = r

            batch = self._store.get_batch(bid)
            if batch is None:
                continue

            for rec in recs:
                eid = str(rec.get("enterprise_id", ""))
                share = share_by_id.get(eid, {})
                review = review_by_id.get(eid, {})

                rstatus = review.get("status", "")
                # Only include finalized
                if rstatus not in ("confirmed", "locked", "finalized"):
                    continue

                entry = DirectoryEntry(
                    enterprise_id=eid,
                    credit_code=rec.get("credit_code", ""),
                    enterprise_name=rec.get("enterprise_name", ""),
                    region=rec.get("region", ""),
                    industry_code=str(rec.get("industry_code", "")),
                    sport_score=rec.get("sport_score", 0.0),
                    evidence_relation=rec.get("evidence_relation", ""),
                    model_share=share.get("model_share"),
                    fallback_share=share.get("fallback_share"),
                    manual_share=share.get("manual_share"),
                    effective_share=share.get("effective_share", 0.0),
                    share_source=share.get("share_source", "none"),
                    sport_category=rec.get("sport_category", "非体育"),
                    crossover_type=rec.get("crossover_type", ""),
                    review_status=rstatus,
                    priority=review.get("priority", ""),
                    batch_id=bid,
                    is_finalized=(rstatus in ("confirmed", "locked", "finalized")),
                    provenance={
                        "batch_id": bid,
                        "data_mode": batch.data_mode,
                        "dictionary_version": batch.dictionary_version,
                        "feature_schema_version": batch.feature_schema_version,
                        "sportshare_model_version": batch.sportshare_model_version,
                    },
                )

                # Apply filters
                if region and entry.region != region:
                    continue
                if category and entry.sport_category != category:
                    continue
                if crossover is not None:
                    is_cross = bool(entry.crossover_type)
                    if is_cross != crossover:
                        continue
                if priority and entry.priority != priority:
                    continue
                if review_status and entry.review_status != review_status:
                    continue

                entries.append(entry)

        return entries

    def get_entry(self, enterprise_id: str, batch_id: str | None = None) -> DirectoryEntry | None:
        entries = self.get_directory(batch_id=batch_id)
        for e in entries:
            if e.enterprise_id == enterprise_id:
                return e
        return None
