import pytest


def _generate_one_task(client):
    response = client.post(
        "/api/review/tasks/generate",
        json={
            "batch_id": 20260803,
            "recognition_results": [
                {
                    "enterprise_id": "E-API",
                    "enterprise_name": "复核接口测试企业",
                    "credit_code": "91510000EAPI",
                    "is_sport": True,
                    "sport_score": 0.72,
                    "sport_category": "健身休闲",
                    "code_type": "indirect",
                    "confidence": 0.82,
                    "evidence_relation": "code_text_consistent",
                    "is_crossover": False,
                    "keywords": ["健身"],
                    "total_business_lines": 2,
                    "sport_business_lines": 1,
                }
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["tasks"][0]


def test_application_imports_review_router():
    try:
        from main import app
    except ImportError as exc:
        pytest.fail(f"review API must import current service contract: {exc}")

    assert "/api/review/tasks" in {route.path for route in app.routes}


def test_generate_tasks_uses_current_service_and_frontend_shape(client):
    response = client.post(
        "/api/review/tasks/generate",
        json={
            "batch_id": 20260803,
            "recognition_results": [
                {
                    "enterprise_id": "E-001",
                    "enterprise_name": "示例体育赛事公司",
                    "credit_code": "91510000E001",
                    "is_sport": True,
                    "sport_score": 0.88,
                    "sport_category": "体育赛事",
                    "code_type": "none",
                    "confidence": 0.91,
                    "evidence_relation": "text_only",
                    "is_crossover": True,
                    "keywords": ["体育赛事"],
                    "total_business_lines": 2,
                    "sport_business_lines": 1,
                },
                {
                    "enterprise_id": "E-002",
                    "enterprise_name": "示例商贸公司",
                    "credit_code": "91510000E002",
                    "is_sport": False,
                    "sport_score": 0.0,
                    "sport_category": "",
                    "code_type": "none",
                    "confidence": 0.0,
                    "evidence_relation": "no_evidence",
                    "is_crossover": False,
                    "keywords": [],
                    "total_business_lines": 1,
                    "sport_business_lines": 0,
                },
            ],
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["code"] == 200
    assert len(payload["data"]["tasks"]) == 2
    task = payload["data"]["tasks"][0]
    assert task["id"].startswith("REVIEW-")
    assert task["sport_share"] == 0.0
    assert task["status_label"] == "待分配"
    stats = payload["data"]["stats"]
    assert stats["total_tasks"] == 2
    assert sum(stats[f"p{i}_count"] for i in range(1, 5)) == 2


def test_list_tasks_serializes_current_review_task_objects(client):
    generated = _generate_one_task(client)

    response = client.get("/api/review/tasks", params={"priority": generated["priority"]})

    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["total"] == 1
    assert payload["tasks"][0]["id"] == generated["id"]
    assert payload["stats"]["total_tasks"] == 1


def test_task_detail_accepts_service_string_id(client):
    generated = _generate_one_task(client)

    response = client.get(f"/api/review/tasks/{generated['id']}")

    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["task"]["id"] == generated["id"]
    assert payload["record_a"] is None
    assert payload["record_b"] is None


def test_assign_task_updates_current_review_task(client):
    generated = _generate_one_task(client)

    response = client.post(
        f"/api/review/tasks/{generated['id']}/assign",
        json={
            "task_ids": [generated["id"]],
            "reviewer_a": "复核员甲",
            "reviewer_b": "复核员乙",
        },
    )

    assert response.status_code == 200, response.text
    task = response.json()["data"]
    assert task["assigned_to_a"] == "复核员甲"
    assert task["assigned_to_b"] == "复核员乙"
    assert task["status"] == "assigned"
    filtered = client.get("/api/review/tasks", params={"assignee": "复核员甲"})
    assert filtered.json()["data"]["total"] == 1


def test_dual_review_consensus_updates_api_state(client):
    generated = _generate_one_task(client)
    task_id = generated["id"]

    for role, reviewer in (("A", "复核员甲"), ("B", "复核员乙")):
        response = client.post(
            "/api/review/records",
            json={
                "review_task_id": task_id,
                "reviewer_name": reviewer,
                "reviewer_role": role,
                "sport_attribute": "yes",
                "sport_category_override": "健身休闲",
                "sport_share_override": 0.55,
                "reason": "证据一致",
            },
        )
        assert response.status_code == 200, response.text

    consensus = client.get(f"/api/review/tasks/{task_id}/consensus")
    assert consensus.status_code == 200, consensus.text
    assert consensus.json()["data"]["is_consensus"] is True
    detail = client.get(f"/api/review/tasks/{task_id}").json()["data"]
    assert detail["task"]["status"] == "confirmed"
    assert detail["record_a"]["reviewer_name"] == "复核员甲"
    assert detail["record_b"]["reviewer_name"] == "复核员乙"


def test_arbitration_locks_a_disputed_task(client):
    generated = _generate_one_task(client)
    task_id = generated["id"]
    for role, attribute in (("A", "yes"), ("B", "no")):
        response = client.post(
            "/api/review/records",
            json={
                "review_task_id": task_id,
                "reviewer_name": f"复核员{role}",
                "reviewer_role": role,
                "sport_attribute": attribute,
                "sport_category_override": "健身休闲" if attribute == "yes" else None,
                "sport_share_override": 0.55 if attribute == "yes" else 0.0,
                "reason": "独立判断",
            },
        )
        assert response.status_code == 200, response.text

    response = client.post(
        "/api/review/arbitrate",
        json={
            "review_task_id": task_id,
            "arbiter_name": "仲裁员丙",
            "final_sport_attribute": "yes",
            "final_sport_category": "健身休闲",
            "final_sport_share": 0.5,
            "decision_reason": "补充证据支持体育属性",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"]["status"] == "locked"
    detail = client.get(f"/api/review/tasks/{task_id}").json()["data"]
    assert detail["task"]["status"] == "locked"
    assert detail["arbitration"]["arbiter"] == "仲裁员丙"


def test_stats_endpoint_returns_frontend_shape(client):
    _generate_one_task(client)

    response = client.get("/api/review/stats", params={"batch_id": 20260803})

    assert response.status_code == 200, response.text
    stats = response.json()["data"]
    assert stats["total_tasks"] == 1
    assert stats["pending"] == 1
    assert "by_status" not in stats
