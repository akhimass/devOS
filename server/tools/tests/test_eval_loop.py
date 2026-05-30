from __future__ import annotations

from tools import eval_loop as el


def test_metric_passed_uses_normalized_score():
    assert el.metric_passed({"score_normalized": 1}) is True
    assert el.metric_passed({"score_normalized": 0}) is False


def test_build_patch_block_includes_failure_names():
    failures = {
        "Agent Asked About Medical Attention": {
            "explanation": "did not ask about medical care",
            "score_normalized": 0,
        }
    }
    block = el.build_patch_block(failures)
    assert "Medical Attention" in block
    assert "REMINDER" in block


def test_apply_prompt_patches_replaces_markers(tmp_path, monkeypatch):
    prompt = tmp_path / "master_prompt.md"
    prompt.write_text(
        "before\n<!-- EVAL_LOOP_AUTO_START -->\nold\n<!-- EVAL_LOOP_AUTO_END -->\nafter\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("MASTER_PROMPT_PATH", str(prompt))

    el.apply_prompt_patches("new patch content")

    text = prompt.read_text(encoding="utf-8")
    assert "new patch content" in text
    assert "old" not in text
