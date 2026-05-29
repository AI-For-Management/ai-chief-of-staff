"""管理API — 飞书配置/资产CRUD"""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import LarkConfig, LarkAsset
from app.schemas.lark import (
    LarkConfigCreate, LarkConfigResponse,
    LarkAssetCreate, LarkAssetResponse,
    TestConnectionRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])


# ========== LarkConfig CRUD ==========

@router.post("/lark-configs", response_model=LarkConfigResponse)
async def create_lark_config(data: LarkConfigCreate, db: AsyncSession = Depends(get_db)):
    config = LarkConfig(**data.model_dump())
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


@router.get("/lark-configs", response_model=list[LarkConfigResponse])
async def list_lark_configs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LarkConfig).order_by(LarkConfig.created_at.desc()))
    return result.scalars().all()


@router.delete("/lark-configs/{config_id}")
async def delete_lark_config(config_id: UUID, db: AsyncSession = Depends(get_db)):
    config = await db.get(LarkConfig, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    await db.delete(config)
    await db.commit()
    return {"status": "deleted"}


@router.post("/lark-configs/test")
async def test_lark_connection(data: TestConnectionRequest):
    from app.services.feishu.client import test_connection
    result = await test_connection(data.app_id, data.app_secret)
    return result


# ========== LarkAsset CRUD ==========

@router.post("/lark-assets", response_model=LarkAssetResponse)
async def create_lark_asset(data: LarkAssetCreate, db: AsyncSession = Depends(get_db)):
    asset = LarkAsset(**data.model_dump())
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset


@router.get("/lark-assets", response_model=list[LarkAssetResponse])
async def list_lark_assets(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LarkAsset).order_by(LarkAsset.created_at.desc()))
    return result.scalars().all()


@router.delete("/lark-assets/{asset_id}")
async def delete_lark_asset(asset_id: UUID, db: AsyncSession = Depends(get_db)):
    asset = await db.get(LarkAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    await db.delete(asset)
    await db.commit()
    return {"status": "deleted"}
