from sqlalchemy import create_engine, inspect

EXPECTED_TABLES = {
    "enterprises",
    "enterprise_businesses",
    "measurements",
    "data_sources",
    "model_metrics",
    "batches",
    "recognition_results_v2",
    "sport_share_results",
    "enterprise_scales",
    "regional_scale_results",
    "review_tasks",
    "review_records",
    "arbitration_records",
    "operation_logs",
}


def test_current_orm_metadata_creates_expected_tables(tmp_path):
    from models import Base

    engine = create_engine(f"sqlite:///{tmp_path / 'metadata.db'}")
    Base.metadata.create_all(engine)
    assert EXPECTED_TABLES <= set(inspect(engine).get_table_names())
