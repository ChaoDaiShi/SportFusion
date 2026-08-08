"""Structured, grounded streaming assistant API."""

import json
import logging
from typing import Any, Literal, Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from routers.monitoring import get_monitoring_snapshot
from services.chat_service import stream_chat
from services.decision_assistant import build_grounding

router = APIRouter()
logger = logging.getLogger(__name__)


class AssistantMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AssistantRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[AssistantMessage] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)
    file_id: Optional[int] = None


def sse(event_type: str, data: dict[str, Any]) -> str:
    return f"data: {json.dumps({'type': event_type, **data}, ensure_ascii=False)}\n\n"


@router.post("/stream", summary="基于监测上下文的流式研判")
async def assistant_stream(payload: AssistantRequest):
    async def event_stream():
        try:
            snapshot = await get_monitoring_snapshot(payload.file_id)
            grounding = build_grounding(payload.message, snapshot)
            provenance = snapshot["provenance"]
            yield sse(
                "context_ready",
                {
                    "data_version": provenance["data_version"],
                    "model_version": provenance["model_version"],
                    "fallback_mode": provenance["mode"],
                    "missing_fields": provenance["missing_fields"],
                },
            )
            yield sse("tool_started", {"label": "读取监测快照"})
            yield sse("tool_finished", {"label": "读取监测快照"})

            prompt = (
                f"用户问题：{payload.message}\n"
                f"页面筛选上下文：{json.dumps(payload.context, ensure_ascii=False)}\n"
                f"可引用的监测数据：\n{grounding['context_text']}"
            )
            messages = [item.model_dump() for item in payload.history[-10:]]
            messages.append({"role": "user", "content": prompt})
            buffered_tokens: list[str] = []
            model_failed = False
            try:
                async for token in stream_chat(
                    messages,
                    temperature=0.2,
                    max_tokens=900,
                ):
                    if "[错误]" in token:
                        model_failed = True
                        break
                    buffered_tokens.append(token)
            except Exception:
                logger.warning("模型不可用，切换规则研判", exc_info=True)
                model_failed = True

            warnings: list[str] = []
            if model_failed or not buffered_tokens:
                warnings.append("MODEL_UNAVAILABLE_RULE_FALLBACK")
                yield sse(
                    "answer_delta",
                    {"content": grounding["fallback_answer"]},
                )
            else:
                for token in buffered_tokens:
                    yield sse("answer_delta", {"content": token})

            yield sse(
                "citations_ready",
                {"citations": grounding["citations"]},
            )
            yield sse("actions_ready", {"actions": grounding["actions"]})
            yield sse("completed", {"warnings": warnings})
        except Exception:
            logger.exception("结构化研判失败")
            yield sse("error", {"content": "研判服务暂不可用，请稍后重试"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
