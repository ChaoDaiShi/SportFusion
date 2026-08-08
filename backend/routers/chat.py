"""智能助手聊天路由 — SSE 流式对话接口"""

import json
import logging
import asyncio
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List

from services.chat_service import (
    stream_chat,
    send_chat,
    get_preset_questions,
    filter_input,
    filter_output,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================
# 请求模型
# ============================================================
class ChatMessage(BaseModel):
    role: str = Field(..., description="消息角色: user / assistant")
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    message: str = Field(..., description="用户输入的消息")
    history: Optional[List[ChatMessage]] = Field(
        default_factory=list, description="历史对话记录"
    )


# ============================================================
# 预设问题接口
# ============================================================
@router.get("/presets", summary="获取预设智能问题")
async def get_presets():
    """返回6个预设智能问题，供前端快捷提问"""
    presets = get_preset_questions()
    return {
        "code": 200,
        "message": "获取预设问题成功",
        "data": presets,
    }


# ============================================================
# 流式聊天接口 (SSE)
# ============================================================
@router.post("/stream", summary="流式AI对话（SSE）")
async def chat_stream(req: ChatRequest):
    """
    SSE 流式对话接口。

    请求体: {"message": "这个平台有什么功能？", "history": [...]}
    响应: text/event-stream，每个 data 帧包含一个 token 片段

    事件类型:
    - data: {"type": "token", "content": "文字片段"}
    - data: {"type": "done", "content": "完整回复文本"}
    - data: {"type": "error", "content": "错误信息"}
    - data: {"type": "rejected", "content": "拒绝原因"}
    """

    # 1. 输入过滤
    filter_result = filter_input(req.message)
    if not filter_result["allowed"]:
        async def reject_stream():
            yield f"data: {json.dumps({'type': 'rejected', 'content': filter_result['reason']}, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            reject_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # 2. 构建消息历史
    messages = []
    for h in (req.history or []):
        messages.append({"role": h.role, "content": h.content})
    messages.append({"role": "user", "content": req.message})

    # 只保留最近10轮对话（避免token超限）
    if len(messages) > 20:
        messages = messages[-20:]

    # 3. 流式生成
    async def event_stream():
        full_response = ""
        try:
            async for token in stream_chat(messages):
                full_response += token
                payload = json.dumps(
                    {"type": "token", "content": token}, ensure_ascii=False
                )
                yield f"data: {payload}\n\n"
                # 让出事件循环，确保前端能及时收到每个token
                await asyncio.sleep(0)

            # 4. 输出审查
            review = filter_output(full_response)

            # 发送完成信号 + 完整文本
            done_payload = json.dumps(
                {
                    "type": "done",
                    "content": full_response,
                    "review": {
                        "passed": review["passed"],
                        "warnings": review["warnings"],
                    },
                },
                ensure_ascii=False,
            )
            yield f"data: {done_payload}\n\n"

        except Exception as e:
            logger.error(f"流式对话异常: {str(e)}")
            error_payload = json.dumps(
                {"type": "error", "content": f"AI服务暂时不可用，请稍后重试。"},
                ensure_ascii=False,
            )
            yield f"data: {error_payload}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用nginx缓冲
        },
    )


# ============================================================
# 非流式聊天接口（备用）
# ============================================================
@router.post("/send", summary="非流式AI对话（备用）")
async def chat_send(req: ChatRequest):
    """
    非流式对话接口（备用），一次性返回完整回复。
    当 SSE 不可用时可以使用此接口。
    """
    # 1. 输入过滤
    filter_result = filter_input(req.message)
    if not filter_result["allowed"]:
        return {
            "code": 200,
            "message": "问题超出平台范围",
            "data": {
                "reply": filter_result["reason"],
                "rejected": True,
            },
        }

    # 2. 构建消息
    messages = []
    for h in (req.history or []):
        messages.append({"role": h.role, "content": h.content})
    messages.append({"role": "user", "content": req.message})

    if len(messages) > 20:
        messages = messages[-20:]

    # 3. 调用 API
    try:
        reply = await send_chat(messages)

        # 4. 输出审查
        review = filter_output(reply)

        return {
            "code": 200,
            "message": "对话成功",
            "data": {
                "reply": reply,
                "review": {
                    "passed": review["passed"],
                    "warnings": review["warnings"],
                },
            },
        }
    except Exception as e:
        logger.error(f"非流式对话异常: {str(e)}")
        return {
            "code": 500,
            "message": f"AI服务调用失败: {str(e)}",
            "data": None,
        }
