import pytest

EXPECTED_PATHS = {
    "/api/data/upload",
    "/api/recognition/single",
    "/api/measure/single",
    "/api/chart/dashboard",
    "/api/validate/summary",
    "/api/monitoring/overview",
    "/api/assistant/stream",
    "/api/share/estimate",
    "/api/scale/summary",
    "/api/review/tasks",
    "/api/system/batches",
}


def test_application_registers_current_route_surface(app):
    registered = {route.path for route in app.routes}
    assert EXPECTED_PATHS <= registered


def test_root_and_read_only_smoke_endpoints_return_structured_responses(client):
    root = client.get("/")
    categories = client.get("/api/recognition/categories")
    monitoring = client.get("/api/monitoring/overview")
    assert root.status_code == 200
    assert root.json()["docs"] == "/docs"
    assert categories.status_code == 200
    assert isinstance(categories.json()["data"], dict)
    assert monitoring.status_code == 200
    assert monitoring.json()["code"] == 200


@pytest.mark.xfail(
    strict=True,
    reason="P0-07: validate summary accesses comparison['traditional_detailed'], which service omits",
)
def test_validate_summary_does_not_crash_when_preprocessed_data_exists(client):
    from routers.data_preprocess import _preprocess_results

    file_id = 990001
    _preprocess_results[file_id] = {
        "records": [
            {"详细名称": "测试体育企业", "行业代码": "8911", "主要业务活动": "体育赛事组织"}
        ]
    }
    try:
        response = client.get(f"/api/validate/summary?file_id={file_id}")
    finally:
        _preprocess_results.pop(file_id, None)
    assert response.status_code != 500
