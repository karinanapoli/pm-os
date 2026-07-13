from pathlib import Path

from pm_os.bootstrap import create_scope_guard_instance
from pm_os.infrastructure.ai.clients.ollama_client import OllamaConnectionError


CONTEXT_DIR = (
    "workspace/initiatives/"
    "INT-0001-smart-supplier-query/"
    "context"
)


def main() -> None:
    guard = create_scope_guard_instance()

    try:
        context_parts = []
        context_path = Path(CONTEXT_DIR)
        if context_path.exists():
            for md_file in sorted(context_path.glob("*.md")):
                context_parts.append(md_file.read_text(encoding="utf-8"))

        context = "\n\n".join(context_parts)

        if not context.strip():
            print("\nNo context files found.")
            return

        warnings = guard.analyze(context)

        if not warnings:
            print("\n✅ No scope issues detected.")
            return

        print(f"\n⚠️  {len(warnings)} scope issue(s) detected:\n")

        for w in warnings:
            emoji = {"high": "🔴", "medium": "🟠", "low": "🟡"}.get(
                w.get("severity", "low"), "🟡"
            )
            print(f"{emoji} [{w.get('category', 'unknown').upper()}] {w.get('message', '')}")
            print(f"   💡 {w.get('suggestion', '')}\n")

    except OllamaConnectionError:
        print(
            "\nCould not connect to Ollama.\n\n"
            "Make sure the server is running with:\n\n"
            "ollama serve"
        )


if __name__ == "__main__":
    main()
