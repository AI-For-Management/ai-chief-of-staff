"""任务管理Pydantic模型"""
from pydantic import BaseModel


class TaskDecomposeRequest(BaseModel):
    user_input: str  # CEO的宏观指令
    bitable_app_token: str = ""  # 目标多维表格
    bitable_table_id: str = ""
    chat_id: str = ""  # 审批卡片发送目标


class DecomposedTask(BaseModel):
    name: str
    assignee: str = ""
    deadline: str = ""
    dependencies: list[str] = []
    priority: str = "medium"


class TaskDecomposeResponse(BaseModel):
    thread_id: str
    status: str  # waiting_approval | completed | failed
    tasks: list[DecomposedTask] = []
    message: str = ""
