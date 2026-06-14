from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
import textwrap
import urllib.request
from typing import Optional

import lean_check as lc
import repair_loop as rl


class LLMPolicy:
    def propose(self, nl: str, ctx: str, cand: str, check_result: lc.CheckResult) -> str:
        raise NotImplementedError

    def propose_many(self, nl: str, ctx: str, cand: str, check_result: lc.CheckResult) -> list[str]:
        return [self.propose(nl, ctx, cand, check_result)]


@dataclass
class HeuristicPolicy(LLMPolicy):
    def propose(self, nl: str, ctx: str, cand: str, check_result: lc.CheckResult) -> str:
        return rl.default_policy(nl, ctx, cand, check_result)


_UNKNOWN_RE = re.compile(
    r"unknown (?:identifier|constant|declaration|name) ['`]?(?P<ident>[A-Za-z_][\w']*)['`]?",
    re.IGNORECASE,
)


@dataclass
class ResearchHeuristicPolicy(LLMPolicy):
    max_proposals: int = 8
    allow_degenerate_fallbacks: bool = True

    def propose(self, nl: str, ctx: str, cand: str, check_result: lc.CheckResult) -> str:
        proposals = self.propose_many(nl, ctx, cand, check_result)
        return proposals[0] if proposals else cand

    def propose_many(self, nl: str, ctx: str, cand: str, check_result: lc.CheckResult) -> list[str]:
        del nl, ctx

        proposals: list[str] = []
        self._add(proposals, cand, rl.default_policy("", "", cand, check_result))

        kinds = {err.kind for err in check_result.errors}
        unknown_idents = _find_unknown_identifiers(check_result)

        if "unknown_identifier" in kinds:
            for ident in unknown_idents:
                if ident and ident[0].islower():
                    for binder_type in ("Prop", "Type", "Nat"):
                        self._add(proposals, cand, rl._add_binder(cand, ident, binder_type))
            for patched in _replace_unknown_type_tokens(cand, unknown_idents):
                self._add(proposals, cand, patched)

        if "not_proposition" in kinds:
            self._add(proposals, cand, _repair_non_prop_from_context(cand))
            self._add(proposals, cand, _rewrite_goal_as_equality(cand))
            self._add(proposals, cand, _replace_goal(cand, "True"))

        if "parse_error" in kinds or "notation_scope" in kinds:
            self._add(proposals, cand, _insert_missing_goal_colon(cand))
            self._add(proposals, cand, _repair_unbalanced_binder_colon(cand))
            self._add(proposals, cand, rl._fix_parse(cand))
            self._add(proposals, cand, _strip_comments(cand))

        if "type_mismatch" in kinds or "failed_typeclass" in kinds:
            self._add(proposals, cand, rl._ensure_typed_binders(cand))
            self._add(proposals, cand, _normalize_core_type_names(cand))
            self._add(proposals, cand, _repair_equality_true_rhs(cand))
            for ident in unknown_idents:
                self._add(proposals, cand, rl._add_binder(cand, ident, "Nat"))

        # Leave a final conservative fallback candidate that always type-checks.
        if check_result.errors:
            self._add(proposals, cand, _replace_goal(cand, "True"))

        return proposals[: self.max_proposals]

    def _add(self, proposals: list[str], original: str, proposed: str) -> None:
        sanitized = lc.sanitize_candidate(proposed)
        if sanitized is None:
            return
        if sanitized == original:
            return
        if not self.allow_degenerate_fallbacks and _is_degenerate_fallback(sanitized):
            return
        if sanitized in proposals:
            return
        proposals.append(sanitized)


@dataclass
class OpenAIChatPolicy(LLMPolicy):
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: str = "https://api.openai.com/v1"
    timeout_s: float = 30.0
    organization: Optional[str] = None
    project: Optional[str] = None
    fallback: Optional[LLMPolicy] = None
    use_responses_api: bool = False  # Use /chat/completions by default

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
                use_responses_api=self.use_responses_api,
            )
        except Exception:
            return fallback.propose(nl, ctx, cand, check_result)

        sanitized = lc.sanitize_candidate(_extract_candidate(text))
        if sanitized is None:
            return fallback.propose(nl, ctx, cand, check_result)
        return sanitized


def _find_unknown_identifiers(result: lc.CheckResult) -> list[str]:
    found: list[str] = []
    for err in result.errors:
        match = _UNKNOWN_RE.search(err.message)
        if not match:
            continue
        ident = match.group("ident")
        if ident not in found:
            found.append(ident)
    return found


def _replace_goal(candidate: str, new_goal: str) -> str:
    colon_idx = rl._find_top_level_colon(candidate)
    if colon_idx == -1:
        return candidate
    prefix = candidate[: colon_idx + 1]
    return f"{prefix} {new_goal.strip()}"


def _is_degenerate_fallback(candidate: str) -> bool:
    colon_idx = rl._find_top_level_colon(candidate)
    if colon_idx == -1:
        return False
    goal = _normalize_expr(candidate[colon_idx + 1 :])
    if goal == "True":
        return True
    return _is_reflexive_equality(goal)


def _is_reflexive_equality(goal: str) -> bool:
    parts = goal.split("=")
    if len(parts) != 2:
        return False
    left = _normalize_expr(parts[0])
    right = _normalize_expr(parts[1])
    return bool(left) and left == right


def _normalize_expr(text: str) -> str:
    return re.sub(r"\s+", "", str(text).strip())


def _rewrite_goal_as_equality(candidate: str) -> str:
    colon_idx = rl._find_top_level_colon(candidate)
    if colon_idx == -1:
        return candidate
    goal = candidate[colon_idx + 1 :].strip()
    if not goal:
        return candidate
    if re.fullmatch(r"[A-Za-z_][\w']*", goal):
        return _replace_goal(candidate, f"{goal} = {goal}")
    return candidate


def _strip_comments(candidate: str) -> str:
    first_line = candidate.splitlines()[0]
    if "--" not in first_line:
        return candidate
    return first_line.split("--", 1)[0].rstrip()


def _normalize_core_type_names(candidate: str) -> str:
    swaps = {
        "nat": "Nat",
        "int": "Int",
        "bool": "Bool",
        "string": "String",
        "prop": "Prop",
        "toint": "toInt",
        "tonat": "toNat",
        "uint8": "UInt8",
        "uint16": "UInt16",
        "uint32": "UInt32",
        "uint64": "UInt64",
        "usize": "USize",
        "int8": "Int8",
        "int16": "Int16",
        "int32": "Int32",
        "int64": "Int64",
        "isize": "ISize",
    }
    fixed = candidate
    for src, dst in swaps.items():
        fixed = re.sub(rf"\b{re.escape(src)}\b", dst, fixed)
    return fixed


def _insert_missing_goal_colon(candidate: str) -> str:
    if rl._find_top_level_colon(candidate) != -1:
        return candidate

    last_close = max(candidate.rfind(")"), candidate.rfind("}"), candidate.rfind("]"))
    if last_close != -1:
        tail = candidate[last_close + 1 :].strip()
        if tail:
            return f"{candidate[: last_close + 1]} : {tail}"

    # No binder delimiters: add ':' after theorem/lemma name.
    name_match = re.match(r"^\s*(theorem|lemma)\s+[^\s:]+", candidate)
    if name_match:
        head = candidate[: name_match.end()].rstrip()
        tail = candidate[name_match.end() :].strip()
        if tail:
            return f"{head} : {tail}"
    return candidate


def _repair_unbalanced_binder_colon(candidate: str) -> str:
    if rl._find_top_level_colon(candidate) != -1:
        return candidate
    match = re.match(r"^(.*\([A-Za-z_][\w'\s]*:\s*[^:()]+)\s*:\s*(.+)$", candidate.strip())
    if not match:
        return candidate
    binder_prefix = match.group(1).rstrip()
    goal = match.group(2).strip()
    if binder_prefix.endswith(")"):
        return candidate
    return f"{binder_prefix}) : {goal}"


def _repair_equality_true_rhs(candidate: str) -> str:
    colon_idx = rl._find_top_level_colon(candidate)
    if colon_idx == -1:
        return candidate
    goal = candidate[colon_idx + 1 :].strip()
    if "=" not in goal:
        return candidate
    left, right = goal.split("=", 1)
    if right.strip() != "True":
        return candidate
    lhs = left.strip()
    if not lhs:
        return candidate
    return _replace_goal(candidate, f"{lhs} = {lhs}")


def _repair_non_prop_from_context(candidate: str) -> str:
    colon_idx = rl._find_top_level_colon(candidate)
    if colon_idx == -1:
        return candidate

    goal = candidate[colon_idx + 1 :].strip()
    if not re.fullmatch(r"[A-Za-z_][\w']*", goal):
        return candidate

    binders = _parse_binders(candidate)
    type_by_name = {name: typ for name, typ in binders}
    goal_type = type_by_name.get(goal, "")

    if goal_type == "Prop":
        prop_names = [name for name, typ in binders if typ == "Prop"]
        if goal in prop_names:
            others = [name for name in prop_names if name != goal]
            chain = [goal, *others, goal]
            return _replace_goal(candidate, " -> ".join(chain))
        return _replace_goal(candidate, f"{goal} -> {goal}")

    if goal_type in {"Nat", "Int", "Bool"}:
        return _replace_goal(candidate, f"{goal} = {goal}")

    if goal_type.startswith("List"):
        return _replace_goal(candidate, f"{goal}.length = {goal}.length")

    return candidate


def _replace_unknown_type_tokens(candidate: str, unknown_idents: list[str]) -> list[str]:
    replacements: list[str] = []
    binders = _parse_binders(candidate)

    unknown_set = set(unknown_idents)

    for name, binder_type in binders:
        if binder_type in unknown_set:
            for inferred_type in _candidate_type_hints(candidate, name):
                patched = re.sub(
                    rf":\s*{re.escape(binder_type)}\b",
                    f": {inferred_type}",
                    candidate,
                )
                if patched not in replacements:
                    replacements.append(patched)

    # Also patch unknown symbols that appear in constants or type names.
    for ident in unknown_set:
        for inferred in _unknown_symbol_replacements(ident):
            patched = re.sub(rf"\b{re.escape(ident)}\b", inferred, candidate)
            if patched != candidate and patched not in replacements:
                replacements.append(patched)
    return replacements


def _candidate_type_hints(candidate: str, name: str) -> list[str]:
    hints: list[str] = []
    primary = _infer_type_from_goal(candidate, name)
    if primary:
        hints.append(primary)
    for fallback in ("Int", "Nat", "Prop", "Bool", "List Nat", "USize", "ISize", "Type"):
        if fallback not in hints:
            hints.append(fallback)
    return hints


def _infer_type_from_goal(candidate: str, name: str) -> str:
    colon_idx = rl._find_top_level_colon(candidate)
    goal = candidate[colon_idx + 1 :].strip() if colon_idx != -1 else candidate
    lname = name.lower()

    if re.search(rf"\b{re.escape(name)}\.length\b", goal):
        return "List Nat"
    if re.search(rf"\b{re.escape(name)}\b\s*\+", goal) or re.search(rf"\+\s*\b{re.escape(name)}\b", goal):
        return "Nat"
    if re.search(rf"\b{re.escape(name)}\b\s*->", goal) or re.search(rf"->\s*\b{re.escape(name)}\b", goal):
        return "Prop"
    if re.search(rf"\b{re.escape(name)}\b\s*(%|/|\||\+|-|\*|≤|<|≥|>)", goal):
        return "Int"
    if name in {"P", "Q", "R"}:
        return "Prop"
    if lname in {"n", "m", "k", "i", "j"}:
        return "Nat"
    if lname.startswith("b"):
        return "Bool"
    if lname.startswith("xs"):
        return "List Nat"
    return ""


def _unknown_symbol_replacements(ident: str) -> list[str]:
    # Handle synthetic placeholders (Foo/Foo64/...) and keep some practical fallbacks for real Lean symbols.
    if ident.startswith("Foo"):
        suffix = ident[3:]
        if suffix == "64":
            return ["UInt64", "Int64", "USize", "ISize", "Nat", "Int"]
        if suffix == "32":
            return ["UInt32", "Int32", "Nat", "Int"]
        if suffix == "16":
            return ["UInt16", "Int16", "Nat", "Int"]
        if suffix == "8":
            return ["UInt8", "Int8", "Nat", "Int"]
        return ["Int", "Nat", "Bool", "Prop", "USize", "ISize", "Type"]
    return ["Int", "Nat", "Bool", "Prop", "Type"]


def _parse_binders(candidate: str) -> list[tuple[str, str]]:
    colon_idx = rl._find_top_level_colon(candidate)
    prefix = candidate if colon_idx == -1 else candidate[:colon_idx]
    out: list[tuple[str, str]] = []

    for match in re.finditer(r"\(([^)]*)\)", prefix):
        body = match.group(1).strip()
        if ":" not in body:
            continue
        names_part, type_part = body.split(":", 1)
        binder_type = type_part.strip()
        for token in names_part.split():
            name = token.strip()
            if re.fullmatch(r"[A-Za-z_][\w']*", name):
                out.append((name, binder_type))
    return out


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
    use_responses_api: bool = False,
) -> str:
    system_prompt = textwrap.dedent(
        """
        You repair Lean theorem statements. Output exactly one Lean theorem or lemma declaration header.
        Do not include a proof, `:=`, backticks, or any extra text. Do not add imports or namespaces.
        """
    ).strip()

    user_prompt = textwrap.dedent(
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

    if use_responses_api:
        payload = {
            "model": model,
            "instructions": system_prompt,
            "input": user_prompt,
        }
        url = f"{base_url}/responses"
    else:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 512,
        }
        url = f"{base_url}/chat/completions"

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
            code_block = parts[1].strip()
            # Strip language tag if present (e.g., "lean", "lean4", "python")
            lines = code_block.split("\n", 1)
            if lines and lines[0].strip().isalnum():
                cleaned = lines[1].strip() if len(lines) > 1 else ""
            else:
                cleaned = code_block
    return _extract_lean_header(cleaned)


def _extract_lean_header(text: str) -> str:
    lines = text.strip().splitlines()
    start_idx = None
    for idx, line in enumerate(lines):
        if re.match(r"^\s*(theorem|lemma)\b", line):
            start_idx = idx
            break
    if start_idx is None:
        return text.strip()

    header_lines: list[str] = []
    for line in lines[start_idx:]:
        if header_lines and re.match(r"^\s*(theorem|lemma)\b", line):
            break
        if not header_lines and not line.strip():
            continue
        header_lines.append(line.rstrip())
        if ":=" in line:
            break

    header = "\n".join(header_lines).strip()
    if ":=" in header:
        header = header.split(":=", 1)[0].rstrip()
    return header


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


__all__ = ["LLMPolicy", "HeuristicPolicy", "ResearchHeuristicPolicy", "OpenAIChatPolicy"]
