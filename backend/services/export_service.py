"""
成果导出服务 — Phase 4: batch/database based export (not browser table).

Supports: candidate_enterprises, sportshare_results, category_scale,
          regional_scale, review_results, directory, validation_summary,
          provenance_manifest.

XLSX multi-sheet preferred; CSV fallback.
Locked batches → final submission export; unlocked → draft (marked).
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO

from services.batch_service import get_batch_store
from services.directory_service import DirectoryService


@dataclass
class ExportManifest:
    batch_id: str = ""
    export_type: str = "draft"  # draft | final
    generated_at: str = ""
    sheets: list[str] = None

    def __post_init__(self):
        if self.sheets is None:
            self.sheets = []


def export_to_xlsx_bytes(batch_id: str, sheets: list[str] | None = None) -> bytes:
    """
    Export batch results as XLSX bytes (multi-sheet).

    If openpyxl is not available, falls back to CSV per sheet.
    """
    store = get_batch_store()
    batch = store.get_batch(batch_id)
    if batch is None:
        raise ValueError(f"Batch not found: {batch_id}")

    export_type = "final" if store.is_locked(batch_id) else "draft"
    all_sheets = sheets or [
        "candidate_enterprises", "sportshare_results", "category_scale",
        "regional_scale", "review_results", "directory",
        "validation_summary", "provenance_manifest",
    ]

    # Collect data
    recs = store.load_results(batch_id, "recognition")
    shares = store.load_results(batch_id, "share")
    reviews = store.load_results(batch_id, "review")
    scale_runs = store.load_results(batch_id, "scale")

    try:
        import openpyxl
        wb = openpyxl.Workbook()
        wb.remove(wb.active)  # Remove default sheet

        for sheet_name in all_sheets:
            ws = wb.create_sheet(title=sheet_name[:31])  # Excel 31-char limit
            _write_sheet(ws, sheet_name, recs, shares, reviews, scale_runs, batch, export_type)

        output = BytesIO()
        wb.save(output)
        return output.getvalue()
    except ImportError:
        # Fallback: CSV per sheet as single file
        return _export_csv_fallback(
            batch_id, all_sheets, recs, shares, reviews, scale_runs, batch, export_type
        )


def _write_sheet(ws, sheet_name: str, recs, shares, reviews, scale_runs, batch, export_type) -> None:
    """Write one sheet of the export."""
    if sheet_name == "candidate_enterprises":
        ws.append(["enterprise_id", "credit_code", "enterprise_name", "sport_score",
                    "sport_category", "code_type", "evidence_relation", "is_sport",
                    "confidence", "keywords"])
        for r in recs:
            ws.append([r.get("enterprise_id"), r.get("credit_code"), r.get("enterprise_name"),
                       r.get("sport_score"), r.get("sport_category"), r.get("code_type"),
                       r.get("evidence_relation"), r.get("is_sport"), r.get("confidence"),
                       ",".join(r.get("keywords", []))])

    elif sheet_name == "sportshare_results":
        ws.append(["enterprise_id", "model_share", "fallback_share", "manual_share",
                    "effective_share", "share_source", "lower_bound", "upper_bound"])
        for s in shares:
            ws.append([s.get("enterprise_id"), s.get("model_share"), s.get("fallback_share"),
                       s.get("manual_share"), s.get("effective_share"), s.get("share_source"),
                       s.get("lower_bound"), s.get("upper_bound")])

    elif sheet_name == "category_scale":
        ws.append(["category", "allocated_output", "output_share"])
        for sr in scale_runs:
            if sr.get("type") == "category":
                for cat, val in sr.get("outputs", {}).items():
                    ws.append([cat, val, ""])

    elif sheet_name == "review_results":
        ws.append(["task_id", "enterprise_id", "priority", "status", "final_attribute",
                    "reviewer_a", "reviewer_b", "arbiter"])
        for r in reviews:
            ws.append([r.get("task_id"), r.get("enterprise_id"), r.get("priority"),
                       r.get("status"), r.get("final_sport_attribute"),
                       r.get("reviewer_a"), r.get("reviewer_b"), r.get("arbiter")])

    elif sheet_name == "directory":
        dir_svc = DirectoryService()
        entries = dir_svc.get_directory(batch_id=batch_id)
        ws.append(["enterprise_id", "credit_code", "enterprise_name", "region",
                    "sport_score", "sport_category", "effective_share", "share_source",
                    "review_status", "priority"])
        for e in entries:
            ws.append([e.enterprise_id, e.credit_code, e.enterprise_name, e.region,
                       e.sport_score, e.sport_category, e.effective_share, e.share_source,
                       e.review_status, e.priority])

    elif sheet_name == "validation_summary":
        ws.append(["metric", "value"])
        ws.append(["export_type", export_type])
        ws.append(["batch_status", batch.status])

    elif sheet_name == "provenance_manifest":
        ws.append(["field", "value"])
        for k, v in {
            "batch_id": batch.batch_id,
            "data_mode": batch.data_mode,
            "dictionary_version": batch.dictionary_version,
            "industry_code_map_version": batch.industry_code_map_version,
            "feature_schema_version": batch.feature_schema_version,
            "sportscore_parameter_version": batch.sportscore_parameter_version,
            "sportshare_model_version": batch.sportshare_model_version,
            "macro_calibration_version": batch.macro_calibration_version,
            "scenario_version": batch.scenario_version,
            "export_type": export_type,
            "generated_at": datetime.now(UTC).isoformat(),
        }.items():
            ws.append([k, str(v)])


def _export_csv_fallback(batch_id, sheets, recs, shares, reviews, scale_runs, batch, export_type) -> bytes:
    """CSV fallback when openpyxl is not available."""
    lines = [f"# Export for batch {batch_id} ({export_type})"]
    for sheet in sheets:
        lines.append(f"\n# --- Sheet: {sheet} ---")
        if sheet == "candidate_enterprises":
            lines.append("enterprise_id,enterprise_name,sport_score,sport_category,code_type")
            for r in recs:
                lines.append(f"{r.get('enterprise_id')},{r.get('enterprise_name')},{r.get('sport_score')},{r.get('sport_category')},{r.get('code_type')}")
        elif sheet == "sportshare_results":
            lines.append("enterprise_id,model_share,effective_share,share_source")
            for s in shares:
                lines.append(f"{s.get('enterprise_id')},{s.get('model_share')},{s.get('effective_share')},{s.get('share_source')}")
        elif sheet == "provenance_manifest":
            for k, v in {"batch_id": batch.batch_id, "data_mode": batch.data_mode}.items():
                lines.append(f"{k},{v}")
    return "\n".join(lines).encode("utf-8")
