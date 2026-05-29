"""Streamlit工具函数 — 调用FastAPI后端"""
import requests

API_BASE = "http://fastapi:8000"


def api_get(path: str) -> dict | list:
    resp = requests.get(f"{API_BASE}{path}", timeout=10)
    resp.raise_for_status()
    return resp.json()


def api_post(path: str, data: dict) -> dict:
    resp = requests.post(f"{API_BASE}{path}", json=data, timeout=10)
    resp.raise_for_status()
    return resp.json()


def api_delete(path: str) -> dict:
    resp = requests.delete(f"{API_BASE}{path}", timeout=10)
    resp.raise_for_status()
    return resp.json()
