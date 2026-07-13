from pm_os.infrastructure.guards.scope_guard import ScopeGuard


class FakeAIClient:
    def __init__(self, response: str = ""):
        self.last_prompt = ""
        self.response = response

    def generate(self, prompt: str) -> str:
        self.last_prompt = prompt
        return self.response


SAMPLE_CONTEXT = """
We want to improve the supplier query system.
The goal is to optimize the process and integrate everything.
"""


def test_scope_guard_parses_valid_response():
    ai_client = FakeAIClient(response="""
```json
{
  "warnings": [
    {
      "severity": "high",
      "category": "scope",
      "message": "'Integrate everything' is too vague",
      "suggestion": "Define which specific systems will be integrated"
    },
    {
      "severity": "medium",
      "category": "metrics",
      "message": "'Improve' and 'optimize' are not measurable",
      "suggestion": "Add specific targets with numbers"
    }
  ]
}
```
""")

    guard = ScopeGuard(ai_client=ai_client)
    warnings = guard.analyze(SAMPLE_CONTEXT)

    assert len(warnings) == 2

    assert warnings[0]["severity"] == "high"
    assert warnings[0]["category"] == "scope"
    assert "vague" in warnings[0]["message"]

    assert warnings[1]["severity"] == "medium"
    assert warnings[1]["category"] == "metrics"


def test_scope_guard_handles_empty_response():
    ai_client = FakeAIClient(response="")

    guard = ScopeGuard(ai_client=ai_client)
    warnings = guard.analyze(SAMPLE_CONTEXT)

    assert warnings == []


def test_scope_guard_handles_malformed_json():
    ai_client = FakeAIClient(response="Not JSON at all")

    guard = ScopeGuard(ai_client=ai_client)
    warnings = guard.analyze(SAMPLE_CONTEXT)

    assert warnings == []


def test_scope_guard_builds_prompt_with_context():
    ai_client = FakeAIClient(response="""```json
{
  "warnings": []
}
```""")

    guard = ScopeGuard(ai_client=ai_client)
    guard.analyze(SAMPLE_CONTEXT)

    assert "supplier query" in ai_client.last_prompt
    assert "warnings" in ai_client.last_prompt
