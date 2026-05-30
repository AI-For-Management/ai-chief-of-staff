"""LangGraph共享状态定义"""
import operator
from typing import Annotated
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """所有Agent图共用的状态"""
    messages: Annotated[list, operator.add]
    user_input: str
    agent_type: str  # briefing | task | alert
    status: str  # running | waiting_approval | completed | failed
    result: str  # 最终输出
    metadata: dict  # 额外上下文数据


class BriefingState(TypedDict):
    """情报简报Agent状态"""
    topics: list[str]
    raw_news: list[dict]
    briefing_content: str
    chat_id: str
    sent: bool


class TaskState(TypedDict):
    """项目管理Agent状态"""
    user_input: str
    conversation_history: list[dict]  # 多轮对话历史
    rag_context: str  # 知识库检索结果
    decomposed_tasks: list[dict]
    plan_draft: str  # 当前方案文本
    bitable_app_token: str
    bitable_table_id: str
    chat_id: str
    approval_status: str  # pending | approved | rejected
    created_task_ids: list[str]
    created_project_ids: list[str]  # 自动创建的项目ID（C阶段）
    result: str


class AlertState(TypedDict):
    """预警Agent状态"""
    overdue_items: list[dict]
    risk_keywords_found: list[dict]
    risk_level: str  # low | medium | high | critical
    report_content: str
    chat_id: str
    sent: bool
