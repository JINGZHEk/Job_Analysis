"""FastAPI 端点集成测试。"""
import json

from fastapi.testclient import TestClient

from app.main import app, pipeline


def _bootstrap():
    from app.pipeline import bootstrap
    from pathlib import Path
    return bootstrap(Path("data"))


client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_roles():
    _bootstrap()
    r = client.get("/api/v1/roles")
    assert r.status_code == 200
    assert len(r.json()["roles"]) >= 10


def test_discover_roles():
    _bootstrap()
    r = client.post("/api/v1/roles/discover", json={"known_roles": []})
    assert r.status_code == 200
    assert r.json()["count"] >= 1


def test_panorama():
    _bootstrap()
    r = client.get("/api/v1/graph/panorama")
    assert r.status_code == 200
    assert len(r.json()["nodes"]) > 0


def test_matching_diagnose():
    _bootstrap()
    r = client.post("/api/v1/matching/diagnose", json={
        "resume_text": "技能：Python、PyTorch、Deep Learning、Machine Learning",
        "role_name": "人工智能算法工程师",
    })
    assert r.status_code == 200
    assert "match" in r.json()
    assert "learning_path" in r.json()


def test_timeline():
    _bootstrap()
    r = client.get("/api/v1/roles/人工智能算法工程师/timeline",
                   params={"window_a": "2025-01-01", "window_b": "2026-01-01"})
    assert r.status_code == 200
    assert "summary" in r.json()


def test_learning_paths():
    _bootstrap()
    r = client.post("/api/v1/learning-paths", json={
        "resume_text": "技能：Python、PyTorch、Deep Learning",
        "role_name": "人工智能算法工程师",
    })
    assert r.status_code == 200
    assert "learning_path" in r.json()
