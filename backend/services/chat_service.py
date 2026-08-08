"""DeepSeek AI 智能客服服务层 — 流式对话、防幻觉、内容审查"""

import os
import re
import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

# ============================================================
# 配置
# ============================================================
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# ============================================================
# 系统提示词 — 严格限定 AI 回答范围
# ============================================================
SYSTEM_PROMPT = """你是体融识界的统计分析助手。只依据请求中提供的数据上下文回答体育产业边界识别、经营比重、规模测算、模型评估和风险研判问题。先给结论，再解释依据。没有数据时明确说明缺口，不得编造数值、企业或来源。使用专业称谓，不使用拟人化昵称或表情符号。"""

# ============================================================
# 预设智能问题
# ============================================================
PRESET_QUESTIONS = [
    {
        "id": 1,
        "text": "这个平台有哪些主要功能？",
        "icon": "ChatLineSquare",
    },
    {
        "id": 2,
        "text": "企业体育业务识别是怎么做的？",
        "icon": "Search",
    },
    {
        "id": 3,
        "text": "产值测算使用了什么方法？",
        "icon": "DataAnalysis",
    },
    {
        "id": 4,
        "text": "如何理解体育业务边界识别？",
        "icon": "Connection",
    },
    {
        "id": 5,
        "text": "数据上传支持哪些格式？",
        "icon": "Upload",
    },
    {
        "id": 6,
        "text": "产业全景大屏有哪些图表？",
        "icon": "Monitor",
    },
]

# ============================================================
# 输入关键词过滤 — 防幻觉第一层
# ============================================================
# 项目相关的关键词库（中文）
RELEVANT_KEYWORDS = [
    # 体育相关
    "体育", "运动", "赛事", "健身", "培训", "用品", "竞技",
    # 产业/业务相关
    "产业", "业务", "企业", "公司", "行业", "经营", "商业",
    # 平台功能相关
    "数据", "上传", "导入", "清洗", "预处理", "识别", "NLP", "文本",
    "测算", "产值", "规模", "营收", "占比", "比重",
    "图表", "可视化", "大屏", "仪表盘", "报表", "导出", "报告",
    "边界", "多元", "跨界", "业态", "分类",
    # 验证/模型相关
    "模型", "验证", "对比", "算法", "准确率", "置信度", "关键词",
    # 平台本身
    "平台", "系统", "功能", "使用", "操作", "流程", "帮助", "方法",
]

# 明显的无关话题关键词（快速拦截）
IRRELEVANT_PATTERNS = [
    r"(今天|明天|后天|昨天).{0,5}天气",
    r"天气预报",
    r"(帮我|给我|我想).{0,3}(写|编|创作|生成).{0,5}(小说|故事|诗|歌|文章|作文)",
    r"(推荐|介绍).{0,5}(电影|游戏|电视剧|动漫|小说|音乐)",
    r"(教|学).{0,3}(编程|写代码|python|java|javascript)",
    r"(做|帮我|给我).{0,3}(饭|菜|食谱|菜单)",
    r"(股票|基金|理财|投资).{0,3}(推荐|建议|分析)",
    r"(你是谁|你叫什么|你的名字)",  # 这个可以通过 - 介绍自己
]


def filter_input(user_message: str) -> dict:
    """
    输入层关键词过滤 — 检查用户问题是否与项目相关。

    返回: {"allowed": bool, "reason": str}
    - allowed=True: 可以通过
    - allowed=False: 应拒绝，reason 为拒绝原因
    """
    if not user_message or not user_message.strip():
        return {"allowed": False, "reason": "输入为空"}

    msg = user_message.strip()

    # 1. 检查是否匹配无关话题
    for pattern in IRRELEVANT_PATTERNS[:-1]:  # 排除"你是谁"（允许这个）
        if re.search(pattern, msg):
            logger.info(f"[filter_input] 匹配无关模式: {pattern}")
            # 不做硬拒绝，交给 AI 自行礼貌拒绝（更自然）

    # 2. 检查是否包含项目相关关键词
    matched_keywords = []
    for kw in RELEVANT_KEYWORDS:
        if kw in msg:
            matched_keywords.append(kw)

    if not matched_keywords:
        # 没有任何相关关键词 — 可能是无关问题
        # 再做一次宽松检测：判断是否在询问平台本身
        if len(msg) < 5:
            return {"allowed": False, "reason": "问题过短，无法判断相关性"}

        # 对短消息放宽：如果是问候语
        greetings = ["你好", "hi", "hello", "嗨", "在吗", "在不在"]
        if any(g in msg.lower() for g in greetings):
            return {"allowed": True, "reason": "问候语"}

        # 对"你是谁"类问题放行
        who_am_i = ["你是谁", "你叫什么", "你的名字", "你是干嘛", "你是做什么"]
        if any(w in msg for w in who_am_i):
            return {"allowed": True, "reason": "询问助手身份"}

        return {
            "allowed": False,
            "reason": "抱歉，我是平台专属助手，只能回答与体育产业规模测算平台相关的问题。\n\n您可以问我：\n• 数据上传与管理\n• 企业体育业务识别\n• 产业产值测算方法\n• 可视化大屏功能\n• 报表导出操作",
        }

    logger.info(f"[filter_input] 匹配关键词: {matched_keywords}")
    return {"allowed": True, "reason": f"匹配关键词: {matched_keywords}"}


# ============================================================
# 输出内容审查 — 防幻觉第三层
# ============================================================
# 检测 AI 可能编造的内容模式
HALLUCINATION_PATTERNS = [
    # 电话号码（中国）
    (r"1[3-9]\d{9}", "疑似手机号码"),
    (r"0\d{2,3}-?\d{7,8}", "疑似座机号码"),
    # URL
    (r"https?://[^\s]+", "疑似外部链接"),
    # 身份证号
    (r"\d{17}[\dXx]", "疑似身份证号"),
    # 过于精确的金额（带小数点的万元/亿元数字，可能是编造的）
    # 不拦截整数金额，只标记可疑的大段数字引用
    (r"\d{3,}\.\d{2,}\s*(万|亿|元|美元)", "疑似编造的具体金额"),
]


def filter_output(ai_response: str) -> dict:
    """
    输出层审查 — 扫描 AI 回复中的潜在幻觉内容。

    返回: {"passed": bool, "warnings": list, "cleaned_text": str}
    """
    if not ai_response:
        return {"passed": True, "warnings": [], "cleaned_text": ""}

    warnings = []
    for pattern, desc in HALLUCINATION_PATTERNS:
        matches = re.findall(pattern, ai_response)
        if matches:
            warnings.append({
                "pattern": pattern,
                "description": desc,
                "matches": matches[:5],  # 最多列出5个
            })
            logger.warning(f"[filter_output] 检测到可疑内容: {desc} → {matches[:5]}")

    # 目前不做硬屏蔽，只告警
    passed = len(warnings) == 0
    return {
        "passed": passed,
        "warnings": warnings,
        "cleaned_text": ai_response,
    }


# ============================================================
# DeepSeek API 流式调用
# ============================================================
def _get_client():
    """延迟导入 OpenAI 客户端（避免启动时因缺少依赖而崩溃）"""
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError(
            "openai 库未安装，请运行: pip install openai>=1.0.0"
        )

    if not DEEPSEEK_API_KEY:
        raise ValueError(
            "DEEPSEEK_API_KEY 环境变量未设置，请在 .env 文件或环境变量中配置"
        )

    return OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )


async def stream_chat(
    messages: list,
    model: str = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> AsyncGenerator[str, None]:
    """
    流式调用 DeepSeek API，逐 token yield。

    Args:
        messages: OpenAI 格式的消息列表 [{"role": "user", "content": "..."}]
        model: 模型名，默认从环境变量读取
        temperature: 采样温度
        max_tokens: 最大输出 token 数

    Yields:
        str: 每个 token 的内容片段
    """
    if model is None:
        model = DEEPSEEK_MODEL

    client = _get_client()

    # 在消息列表前插入系统提示词
    full_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *messages,
    ]

    try:
        stream = client.chat.completions.create(
            model=model,
            messages=full_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            timeout=60.0,
        )

        for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content

    except Exception as e:
        logger.error(f"DeepSeek API 调用失败: {str(e)}")
        yield f"\n[错误] AI 服务暂时不可用，请稍后重试。详情: {str(e)}"


async def send_chat(
    messages: list,
    model: str = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> str:
    """
    非流式调用 DeepSeek API，返回完整回复（备用接口）。
    """
    if model is None:
        model = DEEPSEEK_MODEL

    client = _get_client()

    full_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *messages,
    ]

    try:
        response = client.chat.completions.create(
            model=model,
            messages=full_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
            timeout=60.0,
        )

        content = response.choices[0].message.content
        return content if content else ""

    except Exception as e:
        logger.error(f"DeepSeek API 非流式调用失败: {str(e)}")
        raise


def get_preset_questions() -> list:
    """返回预设智能问题列表"""
    return PRESET_QUESTIONS


def build_system_prompt() -> str:
    """返回系统提示词（供调试使用）"""
    return SYSTEM_PROMPT
