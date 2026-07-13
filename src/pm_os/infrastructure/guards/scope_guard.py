import json
import re

from pm_os.contracts.workflow_contracts import AIClientProtocol


class ScopeGuard:
    """
    Analyzes raw context before PRD generation.

    Detects vague scope, non-measurable objectives,
    missing information, and potential contradictions.
    """

    def __init__(self, ai_client: AIClientProtocol):
        self.ai_client = ai_client

    def analyze(self, context: str) -> list[dict]:
        prompt = self._build_prompt(context)
        response = self.ai_client.generate(prompt)
        return self._parse_response(response)

    def _build_prompt(self, context: str) -> str:
        return f"""
You are a Product Management scope analyst.

Analyze the following context that will be used to generate a PRD.
Identify potential problems BEFORE the PRD is written.

Return a JSON object with a "warnings" list.
Each warning must have:
- "severity": "high", "medium", or "low"
- "category": "scope", "metrics", "requirements", "risks", or "contradiction"
- "message": clear explanation of the problem
- "suggestion": how to fix it

Look for:
- **Vague scope**: terms like "integrate everything", "improve", "optimize" without specifics
- **Non-measurable objectives**: goals without clear success criteria
- **Missing information**: key aspects not mentioned (who, what, when)
- **Contradictions**: conflicting statements
- **Overly broad requirements**: impossible to implement in one initiative

Return ONLY valid JSON inside a ```json code block.

Context:

{context}
"""

    def _parse_response(self, response: str) -> list[dict]:
        json_match = re.search(r"```json\s*\n?(.*?)\n?```", response, re.DOTALL)
        if not json_match:
            json_match = re.search(r"\{.*\}", response, re.DOTALL)

        if not json_match:
            return []

        raw = json_match.group(1) if "```" in response else json_match.group(0)

        try:
            data = json.loads(raw.strip())
        except json.JSONDecodeError:
            return []

        return data.get("warnings", [])
