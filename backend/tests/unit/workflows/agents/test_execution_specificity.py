import pytest

from app.domains.analysis.workflows.agents import execution, result_processing

@pytest.mark.unit


@pytest.mark.asyncio
async def test_specificity_retry_then_success(monkeypatch):
    attempts: list[float] = [0.5, 0.9]
    invoke_calls = []
    process_calls = []

    async def fake_emit_agent_progress(*_args, **_kwargs):
        return None

    async def fake_invoke_agent(*_args, **_kwargs):
        invoke_calls.append(1)
        return {"result": f"run-{len(invoke_calls)}"}

    def fake_extract_structured_response(result, _agent_type):
        return {"output": result["result"]}

    def fake_score_agent_output(_findings, agent_type: str):
        score_value = attempts[len(invoke_calls) - 1]
        return type("Score", (), {"overall_score": score_value})()

    async def fake_process_agent_result(**_kwargs):
        process_calls.append(1)
        return {"ok": True}

    # Set threshold to 0.7 to test retry logic (conftest sets it to 0.0)

    monkeypatch.setenv("SPECIFICITY_MIN_SCORE", "0.7")
    monkeypatch.setattr(execution, "emit_agent_progress", fake_emit_agent_progress)
    monkeypatch.setattr(execution, "invoke_agent", fake_invoke_agent)
    monkeypatch.setattr(execution, "extract_structured_response", fake_extract_structured_response)
    monkeypatch.setattr(execution, "score_agent_output", fake_score_agent_output)
    monkeypatch.setattr(execution, "process_agent_result", fake_process_agent_result)
    monkeypatch.setattr(result_processing, "emit_agent_progress", fake_emit_agent_progress)

    result = await execution.run_agent_with_tracking(
        agent=None,
        content="content",
        content_type="article",
        analysis_id="123",
        agent_type="tech_comparator",
        session=None,
    )

    assert result == {"ok": True}
    assert len(invoke_calls) == 2  # retried once then succeeded
    assert len(process_calls) == 1


@pytest.mark.asyncio
async def test_specificity_failure_after_retries(monkeypatch):
    attempts: list[float] = [0.4, 0.5]
    invoke_calls = []

    async def fake_emit_agent_progress(*_args, **_kwargs):
        return None

    async def fake_invoke_agent(*_args, **_kwargs):
        invoke_calls.append(1)
        return {"result": f"run-{len(invoke_calls)}"}

    def fake_extract_structured_response(result, _agent_type):
        return {"output": result["result"]}

    def fake_score_agent_output(_findings, agent_type: str):
        score_value = attempts[len(invoke_calls) - 1]
        return type("Score", (), {"overall_score": score_value})()

    async def fake_process_agent_result(**_kwargs):
        return {"ok": True}

    monkeypatch.setattr(execution, "emit_agent_progress", fake_emit_agent_progress)
    monkeypatch.setattr(execution, "invoke_agent", fake_invoke_agent)
    monkeypatch.setattr(execution, "extract_structured_response", fake_extract_structured_response)
    monkeypatch.setattr(execution, "score_agent_output", fake_score_agent_output)
    monkeypatch.setattr(execution, "process_agent_result", fake_process_agent_result)
    # Set threshold to 0.7 to test retry logic (conftest sets it to 0.0)

    monkeypatch.setenv("SPECIFICITY_MIN_SCORE", "0.7")
    monkeypatch.setenv("SPECIFICITY_MAX_RETRIES", "1")
    monkeypatch.setattr(result_processing, "emit_agent_progress", fake_emit_agent_progress)

    with pytest.raises(ValueError):
        await execution.run_agent_with_tracking(
            agent=None,
            content="content",
            content_type="article",
            analysis_id="123",
            agent_type="tech_comparator",
            session=None,
        )

    assert len(invoke_calls) == 2  # initial + one retry
