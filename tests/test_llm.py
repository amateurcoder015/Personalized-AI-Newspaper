from app.llm.base import LLMProvider
from app.llm.editor import LLMEditor
from app.database.models import Article, Story


class MockLLMProvider(LLMProvider):
    def generate(self, prompt: str, system_prompt=None) -> str:
        return "Mock generated text."

    def generate_structured(self, prompt: str, schema=None, system_prompt=None):
        if "Synthesize" in prompt:
            return {
                "headline": "RBI Maintains Repo Rate at 6.5%",
                "summary": "The Reserve Bank of India kept borrowing costs unchanged today.",
                "why_it_matters": "Maintains stability across Indian financial and banking sectors.",
                "category": "india"
            }
        elif "Gold" in prompt:
            return {
                "gold_driver": "Gold prices held steady as central bank rate expectations adjusted.",
                "silver_driver": "Silver tracked precious metal market sentiment."
            }
        elif "causal" in prompt.lower() or "connection" in prompt.lower():
            return {
                "connections": [
                    {
                        "title": "Yield Movements and Gold Pricing",
                        "premise": "Rising bond yields increased opportunity costs for non-yielding assets.",
                        "chain_steps": ["Yields ↑", "USD ↑", "Gold pressure"],
                        "why_matters": "Illustrates monetary transmission into commodity pricing."
                    }
                ]
            }
        elif "Concept" in prompt:
            return {
                "concept": "Repo Rate Transmission",
                "explanation": "Repo rate transmission is the process by which central bank policy rate changes affect bank lending rates.",
                "why_relevant_today": "Directly links to today's RBI policy rate decision.",
                "numerical_example": "A 25 bps cut on a ₹50L EMI reduces monthly payment by ~₹800."
            }
        else:
            return {
                "summary": "Crisp mock summary of news story.",
                "why_it_matters": "Key implication for investors.",
                "topics": ["Finance"]
            }


def test_llm_editor_process_story():
    mock_provider = MockLLMProvider()
    editor = LLMEditor(provider=mock_provider)

    a1 = Article(title="RBI Holds Rate", url="https://example.com/a1", source="Source1")
    a2 = Article(title="RBI Keeps Repo Rate", url="https://example.com/a2", source="Source2")
    story = Story(headline="RBI Interest Rate Decision", articles=[a1, a2], sources=["Source1", "Source2"])

    processed = editor.process_story(story)
    assert processed.headline == "RBI Maintains Repo Rate at 6.5%"
    assert "Reserve Bank of India" in processed.summary
    assert processed.why_it_matters != ""


def test_llm_editor_edit_stories():
    mock_provider = MockLLMProvider()
    editor = LLMEditor(provider=mock_provider)

    story = Story(headline="Test Story", articles=[Article(title="T1", url="https://example.com/1", source="S1")])
    top_stories, sections, sector_stories, connections, drivers = editor.edit_stories([story], top_limit=1)

    assert len(top_stories) == 1
    assert "gold_driver" in drivers
    assert len(connections) == 1
