"""
模型验证 API — Phase 3: evaluation, ablation, threshold, benchmark, audit.

Endpoints:
    GET  /recognition   — binary recognition evaluation
    GET  /category      — multiclass category evaluation
    GET  /ablation      — feature ablation results
    GET  /threshold     — threshold sensitivity sweep
    GET  /benchmark     — performance benchmark
    GET  /audit         — 24-check audit results
"""
from fastapi import APIRouter
from services.validation_service import (
    run_audit_checks,
)

router = APIRouter()


@router.get("/recognition", summary="二元识别验证")
async def validate_recognition():
    """
    二元识别评估 (Accuracy/Precision/Recall/F1)。
    需要正式参考标签 artifacts。
    """
    return {
        "code": 200,
        "message": "识别验证端点就绪",
        "data": {
            "status": "artifact_required",
            "required_artifacts": ["reference_labels_300.json"],
            "metrics": None,
        },
    }


@router.get("/category", summary="业态分类验证")
async def validate_category():
    """
    九类业态分类评估 (macro-F1 + confusion matrix)。
    需要正式业态标签 artifacts。
    """
    return {
        "code": 200,
        "message": "业态验证端点就绪",
        "data": {
            "status": "artifact_required",
            "required_artifacts": ["category_labels_184.json"],
            "metrics": None,
        },
    }


@router.get("/ablation", summary="消融实验")
async def ablation():
    """W1-W4 特征消融实验结果 (需要模型 + 标签)"""
    return {
        "code": 200,
        "message": "消融实验端点就绪",
        "data": {"status": "artifact_required", "variants": ["full", "without_W1", "without_W2", "without_W3", "without_W4"]},
    }


@router.get("/threshold", summary="阈值敏感性扫描")
async def threshold_sweep():
    """SportScore 阈值扫描 (需要标签)"""
    return {
        "code": 200,
        "message": "阈值扫描端点就绪",
        "data": {"status": "artifact_required"},
    }


@router.get("/benchmark", summary="性能基准")
async def benchmark():
    """识别 pipeline 性能基准 (需要正式数据集)"""
    return {
        "code": 200,
        "message": "基准测试端点就绪",
        "data": {"status": "artifact_required", "methodology": "3 warmups + 5 repeats"},
    }


@router.get("/audit", summary="24项审计")
async def audit():
    """运行 24 项审计检查"""
    result = run_audit_checks()
    return {
        "code": 200,
        "message": f"审计完成: {result.passed}/{result.total} passed",
        "data": {
            "summary": result.summary,
            "checks": [
                {"id": c.id, "name": c.name, "status": c.status, "severity": c.severity}
                for c in result.checks
            ],
        },
    }
