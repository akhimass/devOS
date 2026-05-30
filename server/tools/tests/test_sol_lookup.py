from __future__ import annotations

from datetime import date as real_date
from types import SimpleNamespace

import tools.sol_lookup as sol_lookup


class FixedDate:
    @classmethod
    def today(cls):
        return real_date(2025, 1, 1)

    @classmethod
    def fromisoformat(cls, value: str):
        return real_date.fromisoformat(value)


def test_check_sol_falls_back_to_table_when_bedrock_unavailable(monkeypatch):
    def fake_getenv(key, default=None):
        if key == "BEDROCK_KNOWLEDGE_BASE_ID":
            return None
        return default

    monkeypatch.setattr(sol_lookup, "date", FixedDate)
    monkeypatch.setattr(sol_lookup.os, "getenv", fake_getenv)

    result = sol_lookup.check_sol("CA", "2024-01-01", 30, "private")

    assert result["rag_source"] == "fallback_table"
    assert result["viable"] is True
    assert result["expired"] is False
    assert result["sol_years"] == 2.0
    assert result["sol_deadline"] == "2026-01-01"
    assert result["days_remaining"] == 365
    assert result["govt_notice_deadline"] is None
    assert result["govt_notice_days_remaining"] is None
    assert "SoL viable." in result["notes"]


def test_check_sol_uses_bedrock_and_applies_minority_tolling(monkeypatch):
    class FakeBoto3Module:
        class FakeClient:
            def retrieve_and_generate(self, **kwargs):
                assert kwargs["input"]["text"].startswith("What is the statute of limitations")
                return {
                    "output": {
                        "text": "The personal injury filing deadline is three years, and the government notice of claim deadline is 90 days."
                    }
                }

        def client(self, service_name, region_name=None):
            assert service_name == "bedrock-agent-runtime"
            assert region_name == "us-east-2"
            return self.FakeClient()

    def fake_getenv(key, default=None):
        values = {
            "BEDROCK_KNOWLEDGE_BASE_ID": "kb-123",
            "BEDROCK_MODEL_ARN": "model-arn-123",
            "AWS_DEFAULT_REGION": "us-east-2",
        }
        return values.get(key, default)

    monkeypatch.setattr(sol_lookup, "date", FixedDate)
    monkeypatch.setattr(sol_lookup.os, "getenv", fake_getenv)
    monkeypatch.setattr(sol_lookup.importlib, "import_module", lambda name: FakeBoto3Module() if name == "boto3" else __import__(name))

    result = sol_lookup.check_sol("NY", "2024-01-01", 17, "government")

    assert result["rag_source"] == "bedrock"
    assert result["tolling_applied"] is True
    assert result["tolling_reason"] == "minority"
    assert result["sol_years"] == 3.0
    assert result["sol_deadline"] == "2028-01-01"
    assert result["govt_notice_deadline"] == "2024-03-31"
    assert result["govt_notice_days_remaining"] == -276
    assert result["viable"] is True
    assert "Government defendant" in result["notes"]


def test_check_sol_parses_word_based_bedrock_values(monkeypatch):
    class FakeBoto3Module:
        class FakeClient:
            def retrieve_and_generate(self, **kwargs):
                return {"output": {"text": "This state has a two year deadline and a ninety day notice requirement."}}

        def client(self, service_name, region_name=None):
            return self.FakeClient()

    def fake_getenv(key, default=None):
        values = {
            "BEDROCK_KNOWLEDGE_BASE_ID": "kb-123",
            "AWS_DEFAULT_REGION": "us-east-2",
        }
        return values.get(key, default)

    monkeypatch.setattr(sol_lookup, "date", FixedDate)
    monkeypatch.setattr(sol_lookup.os, "getenv", fake_getenv)
    monkeypatch.setattr(sol_lookup.importlib, "import_module", lambda name: FakeBoto3Module() if name == "boto3" else __import__(name))

    result = sol_lookup.check_sol("NY", "2024-01-01", 30, "government")

    assert result["rag_source"] == "bedrock"
    assert result["sol_years"] == 2.0
    assert result["govt_notice_deadline"] == "2024-03-31"
