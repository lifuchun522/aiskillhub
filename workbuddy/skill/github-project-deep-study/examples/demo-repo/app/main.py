"""DemoClip API 入口 —— 演示两种路由声明形式的枚举。"""
from fastapi import APIRouter, FastAPI

app = FastAPI(title="DemoClip API", version="0.1.0")
router = APIRouter()


@router.get("/api/v1/ping")
def ping():
    return {"ok": True}


@router.post("/api/v1/task")
def create_task():
    return {"task_id": "demo-0001", "state": "queued"}


def get_task(task_id: str):
    return {"task_id": task_id, "state": "done"}


def download(task_id: str):
    return {"task_id": task_id}


# 一条路径挂多个方法：计数口径要与 openapi.json 对齐（方法级端点 > 路径数）
router.add_api_route("/api/v1/task/{task_id}", get_task, methods=["GET", "HEAD"])
router.add_api_route("/api/v1/download/{task_id}", download, methods=["GET", "HEAD"])

app.include_router(router)
