"""飞书相关Pydantic模型"""
import uuid
from pydantic import BaseModel
from datetime import datetime


class LarkConfigCreate(BaseModel):
    name: str
    app_id: str
    app_secret: str
    encrypt_key: str = ""
    verification_token: str = ""


class LarkConfigResponse(BaseModel):
    id: uuid.UUID
    name: str
    app_id: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LarkAssetCreate(BaseModel):
    config_id: uuid.UUID
    asset_type: str  # bitable|doc|wiki|chat
    asset_token: str
    asset_name: str = ""
    table_id: str = ""
    field_mapping: dict = {}
    cron_expression: str = "0 */6 * * *"


class LarkAssetResponse(BaseModel):
    id: uuid.UUID
    config_id: uuid.UUID
    asset_type: str
    asset_token: str
    asset_name: str
    table_id: str
    field_mapping: dict
    cron_expression: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class FeishuWebhookEvent(BaseModel):
    """飞书Webhook事件通用结构"""
    schema_: str | None = None
    header: dict | None = None
    event: dict | None = None
    # 验证回调
    challenge: str | None = None
    token: str | None = None
    type: str | None = None

    model_config = {"populate_by_name": True}


class TestConnectionRequest(BaseModel):
    app_id: str
    app_secret: str
