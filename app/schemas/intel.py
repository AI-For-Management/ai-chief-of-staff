"""情报模块Pydantic模型"""
from pydantic import BaseModel


class BriefingRequest(BaseModel):
    topics: list[str] = ["AI行业动态", "半导体产业", "科技公司财报"]
    send_to_chat_id: str = ""  # 飞书群ID，为空则不发送


class BriefingResponse(BaseModel):
    content: str
    topic_count: int
    sent: bool = False
