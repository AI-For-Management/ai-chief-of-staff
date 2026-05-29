"""飞书云文档/Wiki读取 + Markdown转换"""
import logging
import httpx

from app.services.feishu.client import get_tenant_access_token
from app.utils.retry import feishu_retry

logger = logging.getLogger(__name__)
BASE_URL = "https://open.feishu.cn/open-apis"


async def _headers() -> dict:
    token = await get_tenant_access_token()
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@feishu_retry
async def get_doc_content(document_id: str) -> dict:
    """获取云文档内容（富文本JSON）"""
    url = f"{BASE_URL}/docx/v1/documents/{document_id}"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=await _headers())
        resp.raise_for_status()
        return resp.json().get("data", {})


@feishu_retry
async def get_doc_blocks(document_id: str) -> list[dict]:
    """获取文档所有块"""
    url = f"{BASE_URL}/docx/v1/documents/{document_id}/blocks"
    all_blocks = []
    page_token = ""

    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            params = {"page_size": 500}
            if page_token:
                params["page_token"] = page_token

            resp = await client.get(url, headers=await _headers(), params=params)
            resp.raise_for_status()
            data = resp.json().get("data", {})

            items = data.get("items", [])
            all_blocks.extend(items)

            if not data.get("has_more"):
                break
            page_token = data.get("page_token", "")

    return all_blocks


@feishu_retry
async def get_wiki_node(space_id: str, node_token: str) -> dict:
    """获取知识库节点信息"""
    url = f"{BASE_URL}/wiki/v2/spaces/{space_id}/nodes/{node_token}"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=await _headers())
        resp.raise_for_status()
        return resp.json().get("data", {})


def blocks_to_markdown(blocks: list[dict]) -> str:
    """将飞书文档blocks转为Markdown文本"""
    lines = []

    for block in blocks:
        block_type = block.get("block_type", 0)

        # 1=页面, 2=文本, 3=标题1, 4=标题2, ...
        if block_type == 2:  # text
            text = _extract_text(block)
            if text:
                lines.append(text)

        elif block_type in (3, 4, 5, 6, 7, 8, 9):  # heading 1-7
            level = block_type - 2
            text = _extract_text(block)
            if text:
                lines.append(f"{'#' * level} {text}")

        elif block_type == 10:  # bullet list
            text = _extract_text(block)
            if text:
                lines.append(f"- {text}")

        elif block_type == 11:  # ordered list
            text = _extract_text(block)
            if text:
                lines.append(f"1. {text}")

        elif block_type == 12:  # code block
            text = _extract_text(block)
            lang = block.get("code", {}).get("style", {}).get("language", "")
            lines.append(f"```{lang}")
            lines.append(text or "")
            lines.append("```")

        elif block_type == 13:  # quote
            text = _extract_text(block)
            if text:
                lines.append(f"> {text}")

        elif block_type == 17:  # divider
            lines.append("---")

        elif block_type == 22:  # todo
            checked = block.get("todo", {}).get("style", {}).get("done", False)
            text = _extract_text(block)
            mark = "x" if checked else " "
            if text:
                lines.append(f"- [{mark}] {text}")

    return "\n\n".join(lines)


def _extract_text(block: dict) -> str:
    """从block中提取纯文本"""
    # 飞书block中文本存在多个可能的字段
    for key in ("text", "heading", "bullet", "ordered", "code", "quote", "todo"):
        content = block.get(key, {})
        elements = content.get("elements", [])
        if elements:
            parts = []
            for el in elements:
                text_run = el.get("text_run", {})
                parts.append(text_run.get("content", ""))
            return "".join(parts)
    return ""
