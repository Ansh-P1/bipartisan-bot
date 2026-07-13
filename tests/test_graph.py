from unittest.mock import patch

from agents.graph import GuardrailOutput, ModeratorOutput, build_graph


class FakeResponse:
    def __init__(self, content):
        self.content = content


class FakeStructuredLLM:
    def __init__(self, schema):
        self.schema = schema

    def invoke(self, prompt):
        if self.schema is ModeratorOutput:
            return ModeratorOutput(
                topic_summary="Stub neutral summary of the policy topic.",
                case_for=[{"point": "Point A", "raised_by": "Right", "source_url": ""}],
                case_against=[{"point": "Point B", "raised_by": "Left", "source_url": ""}],
                common_ground=["Both agree implementation details matter."],
                key_facts=["Fact 1"],
                sources=[{"title": "Test Source", "url": "http://example.com", "source": "test"}],
            )
        if self.schema is GuardrailOutput:
            return GuardrailOutput(passed=True, notes="No violations found.")
        raise ValueError(f"Unexpected structured output schema: {self.schema}")


class FakeLLM:
    def invoke(self, prompt):
        return FakeResponse("stub response")

    def with_structured_output(self, schema):
        return FakeStructuredLLM(schema)


def fake_search_news(topic, max_results=6):
    return [
        {
            "title": "Test News Item",
            "url": "http://example.com",
            "snippet": "A relevant snippet.",
            "source": "test",
        }
    ]


@patch("agents.graph.search_news", side_effect=fake_search_news)
@patch("agents.graph.get_llm", return_value=FakeLLM())
def test_graph_runs_end_to_end(mock_get_llm, mock_search_news):
    graph = build_graph()
    result = graph.invoke({"topic": "Test policy topic", "news_context": []})

    assert result["right_opening"] == "stub response"
    assert result["left_opening"] == "stub response"
    assert result["right_rebuttal"] == "stub response"
    assert result["left_rebuttal"] == "stub response"

    summary = result["moderator_summary"]
    assert summary["topic_summary"]
    assert summary["case_for"][0]["point"] == "Point A"
    assert summary["case_against"][0]["point"] == "Point B"
    assert summary["common_ground"]
    assert summary["sources"][0]["url"] == "http://example.com"

    assert result["guardrail_passed"] is True
    assert result["guardrail_notes"] == "No violations found."


@patch("agents.graph.search_news", side_effect=fake_search_news)
@patch("agents.graph.get_llm", return_value=FakeLLM())
def test_graph_fetches_news_before_openings(mock_get_llm, mock_search_news):
    graph = build_graph()
    result = graph.invoke({"topic": "Another topic", "news_context": []})

    assert len(result["news_context"]) == 1
    assert result["news_context"][0]["title"] == "Test News Item"
