from __future__ import annotations

from dataclasses import dataclass
import json
import os
import textwrap
import urllib.request
from typing import Optional

import lean_check as lc
import repair_loop as rl


class LLMPolicy:
    def propose(self, nl: str, ctx: str, cand: str, check_result: lc.CheckResult) -> str:
        raise NotImplementedError


@dataclass
class HeuristicPolicy(LLMPolicy):
    def propose(self, nl: str, ctx: str, cand: str, check_result: lc.CheckResult) -> str:
        return rl.default_policy(nl, ctx, cand, check_result)


@dataclass
class OpenAIChatPolicy(LLMPolicy):
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: str = "https://api.openai.com/v1"
    timeout_s: float = 30.0
    organization: Optional[str] = None
    project: Optional[str] = None
    fallback: Optional[LLMPolicy] = None

    def propose(self, nl: str, ctx: str, cand: str, check_result: lc.CheckResult) -> str:
        fallback = self.fallback or HeuristicPolicy()

        api_key = self.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            return fallback.propose(nl, ctx, cand, check_result)

        model = self.model or os.getenv("OPENAI_MODEL")
        if not model:
            return fallback.propose(nl, ctx, cand, check_result)

        base_url = (os.getenv("OPENAI_BASE_URL") or self.base_url).rstrip("/")

        try:
            text = _call_openai(
                base_url=base_url,
                api_key=api_key,
                model=model,
                nl=nl,
                ctx=ctx,
                cand=cand,
                check_result=check_result,
                timeout_s=self.timeout_s,
                organization=self.organization or os.getenv("OPENAI_ORG"),
                project=self.project or os.getenv("OPENAI_PROJECT"),
            )
        except Exception:
            return fallback.propose(nl, ctx, cand, check_result)

        sanitized = lc.sanitize_candidate(_extract_candidate(text))
        if sanitized is None:
            return fallback.propose(nl, ctx, cand, check_result)
        return sanitized


def _call_openai(
    base_url: str,
    api_key: str,
    model: str,
    nl: str,
    ctx: str,
    cand: str,
    check_result: lc.CheckResult,
    timeout_s: float,
    organization: Optional[str],
    project: Optional[str],
) -> str:
    instructions = textwrap.dedent(
        """
        You repair Lean theorem statements. Output exactly one Lean theorem or lemma declaration header.
        Do not include a proof, `:=`, backticks, or any extra text. Do not add imports or namespaces.
        """
    ).strip()

    user = textwrap.dedent(
        f"""
        Natural language: {nl.strip()}
        Context:
        {ctx.strip()}

        Candidate:
        {cand.strip()}

        Errors:
        {_format_errors(check_result)}

        Return a corrected single theorem or lemma header only.
        """
    ).strip()

    payload = {
        "model": model,
        "instructions": instructions,
        "input": user,
    }

    url = f"{base_url}/responses"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if organization:
        headers["OpenAI-Organization"] = organization
    if project:
        headers["OpenAI-Project"] = project

    req = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        body = resp.read().decode("utf-8")
    data = json.loads(body)
    return _extract_output_text(data)


def _extract_output_text(data: object) -> str:
    if isinstance(data, dict):
        direct = data.get("output_text")
        if isinstance(direct, str) and direct.strip():
            return direct

        output = data.get("output")
        if isinstance(output, list):
            parts: list[str] = []
            for item in output:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "message":
                    content = item.get("content")
                    if isinstance(content, list):
                        for piece in content:
                            if not isinstance(piece, dict):
                                continue
                            text = piece.get("text")
                            if isinstance(text, str):
                                parts.append(text)
                            text = piece.get("output_text")
                            if isinstance(text, str):
                                parts.append(text)
            if parts:
                return "\n".join(parts).strip()

        choices = data.get("choices")
        if isinstance(choices, list):
            for choice in choices:
                if not isinstance(choice, dict):
                    continue
                message = choice.get("message")
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, str) and content.strip():
                        return content

    return ""


def _extract_candidate(text: str) -> str:
    cleaned = text.strip()
    if "```" in cleaned:
        parts = cleaned.split("```")
        if len(parts) >= 2:
            cleaned = parts[1].strip()
    return cleaned


def _format_errors(result: lc.CheckResult) -> str:
    if not result.errors:
        return "(none)"
    lines: list[str] = []
    for err in result.errors:
        loc = ""
        if err.line is not None and err.column is not None:
            loc = f"{err.line}:{err.column} "
        lines.append(f"- {err.kind}: {loc}{err.message}")
    return "\n".join(lines)


__all__ = ["LLMPolicy", "HeuristicPolicy", "OpenAIChatPolicy"]
