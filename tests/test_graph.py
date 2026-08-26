"""时序图谱单元测试。"""
import tempfile
from pathlib import Path

from app.graph import TemporalGraph
from app.models import Claim


def test_upsert_and_role_skills():
    with tempfile.TemporaryDirectory() as d:
        g = TemporalGraph(Path(d))
        g.upsert_node("role:X", "Role", name="X")
        g.add_edge("role:X", "skill:Python", "requires", is_required=True,
                   valid_from="2026-01-01", trust_score=0.9)
        sets = g.role_skills("role:X")
        assert len(sets["required"]) == 1
        assert sets["required"][0]["name"] == "Python"


def test_commit_and_rollback():
    with tempfile.TemporaryDirectory() as d:
        g = TemporalGraph(Path(d))
        g.upsert_node("role:X", "Role", name="X")
        v1 = g.commit("v1")
        g.upsert_node("role:Y", "Role", name="Y")
        g.commit("v2")
        assert g.rollback(v1)
        assert "role:Y" not in g.G
        assert "role:X" in g.G


def test_add_claim():
    with tempfile.TemporaryDirectory() as d:
        g = TemporalGraph(Path(d))
        claim = Claim(claim_id="c1", subject="role:X", predicate="requires",
                      object="skill:Python", evidence_span="熟练 Python",
                      trust_score=0.88, is_required=True)
        g.add_claim(claim)
        assert "role:X" in g.G
        assert "skill:Python" in g.G
