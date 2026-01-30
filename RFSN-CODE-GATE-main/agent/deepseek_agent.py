"""SWE-bench agent functions wired to DeepSeek R1.

This module provides the three core functions needed by the agent loop:
- propose_fn: Uses DeepSeek R1 to generate proposals
- gate_fn: Validates proposals against profile constraints
- exec_fn: Executes proposals (apply patches, run tests, etc.)
"""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from agent.types import (
    AgentState,
    Proposal,
    GateDecision,
    ExecResult,
    Phase,
)
from agent.profiles import Profile

# Try to import the DeepSeek client
try:
    from rfsn_controller.llm.deepseek import call_model
    HAS_DEEPSEEK = True
except ImportError:
    HAS_DEEPSEEK = False
    def call_model(model_input: str, temperature: float = 0.0) -> dict:
        """Fallback when DeepSeek is not available."""
        return {
            "mode": "tool_request",
            "requests": [],
            "why": "DeepSeek client not available",
        }

try:
    from rfsn_controller.structured_logging import get_logger
except ImportError:
    import logging
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger(__name__)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _clean_search_term(term: str) -> str:
    """Clean a search term by removing punctuation and formatting characters."""
    # Remove markdown formatting
    term = term.replace("`", "").replace("*", "").replace("_", " ").replace("__", " ")
    # Remove common punctuation
    term = re.sub(r"['\"`.,;:!?\(\)\[\]\{\}<>]", "", term)
    # Clean up whitespace
    term = term.strip()
    return term


def _extract_code_identifiers(text: str) -> list[str]:
    """Extract likely code identifiers from problem text."""
    identifiers = []
    
    # Find function/method names (word_word pattern)
    snake_case = re.findall(r'\b([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\b', text)
    identifiers.extend(snake_case)
    
    # Find class names (CamelCase)
    camel_case = re.findall(r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b', text)
    identifiers.extend(camel_case)
    
    # Find module paths (word.word.word)
    module_paths = re.findall(r'\b([a-z][a-z0-9]*(?:\.[a-z][a-z0-9]*)+)\b', text)
    identifiers.extend(module_paths)
    
    # Find backtick-wrapped code
    backtick_code = re.findall(r'`([^`]+)`', text)
    for code in backtick_code:
        clean = _clean_search_term(code)
        if len(clean) > 3 and clean.replace("_", "").isalnum():
            identifiers.append(clean)
    
    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for ident in identifiers:
        if ident not in seen and len(ident) > 3:
            seen.add(ident)
            unique.append(ident)
    
    return unique[:20]  # Limit to 20


# =============================================================================
# PROPOSE FUNCTION - Uses DeepSeek R1 to generate proposals
# =============================================================================

def propose(profile: Profile, state: AgentState) -> Proposal:
    """Generate a proposal using DeepSeek R1."""
    prompt = _build_prompt(profile, state)
    
    logger.debug("Calling DeepSeek R1", phase=state.phase.value, prompt_len=len(prompt))
    
    try:
        response = call_model(prompt, temperature=0.0)
    except Exception as e:
        logger.error("DeepSeek call failed", error=str(e))
        return _fallback_proposal(state, str(e))
    
    return _parse_response_to_proposal(response, state)


def _fallback_proposal(state: AgentState, error: str) -> Proposal:
    """Generate a fallback proposal based on current phase."""
    problem = state.notes.get("problem_statement", "")
    
    # In LOCALIZE, try to search for keywords from problem statement
    if state.phase == Phase.LOCALIZE:
        # Extract potential search terms from problem
        keywords = [w for w in problem.split() if len(w) > 5 and w.isalpha()][:3]
        if keywords:
            return Proposal(
                kind="search",
                rationale=f"Fallback search for: {keywords[0]}",
                inputs={"query": keywords[0]},
                evidence=[],
            )
    
    return Proposal(
        kind="inspect",
        rationale=f"LLM call failed: {error}",
        inputs={"query": "problem_statement"},
        evidence=[],
    )

def _build_prompt(profile: Profile, state: AgentState) -> str:
    """Build a comprehensive prompt with history for DeepSeek."""
    parts = []
    
    # Task context
    problem = state.notes.get("problem_statement", "")
    parts.append(f"# TASK\n{problem}")
    
    # File contents from last read - SHOW PROMINENTLY WITH LINE NUMBERS
    last_contents = state.notes.get("last_file_contents", {})
    if last_contents:
        parts.append("\n# ⚠️ CRITICAL: FILE CONTENTS (with line numbers for your diff)")
        parts.append("You MUST use exact line content from below when generating patches:")
        for fname, content in list(last_contents.items())[:3]:
            # Add line numbers to help with diff generation
            lines = content.split("\n")[:150]  # Limit to 150 lines
            numbered_lines = [f"{i+1:4}: {line}" for i, line in enumerate(lines)]
            numbered_content = "\n".join(numbered_lines)
            parts.append(f"\n## {fname}\n```\n{numbered_content}\n```")
    
    # Current phase with detailed instructions
    parts.append(f"\n# CURRENT PHASE: {state.phase.value}")
    parts.append(_get_phase_instruction(state.phase))
    
    # Budget status
    parts.append("\n# BUDGET STATUS")
    parts.append(f"- Round: {state.budget.round_idx}/{profile.max_rounds}")
    parts.append(f"- Patch attempts: {state.budget.patch_attempts}/{profile.max_patch_attempts}")
    parts.append(f"- Test runs: {state.budget.test_runs}/{profile.max_test_runs}")
    
    # Add history of what was already done
    if "action_history" not in state.notes:
        state.notes["action_history"] = []
    
    history = state.notes["action_history"]
    if history:
        parts.append("\n# ACTIONS ALREADY TAKEN (DO NOT REPEAT)")
        for h in history[-8:]:  # Last 8 actions
            parts.append(f"- {h}")
    
    # Localization hits
    if state.localization_hits:
        parts.append("\n# LOCALIZATION HITS (files likely to need changes)")
        for hit in state.localization_hits[:10]:
            parts.append(f"- {hit.get('file', 'unknown')}: {hit.get('reason', '')}")
    
    # Files already read
    files_read = state.notes.get("files_read", [])
    if files_read:
        parts.append(f"\n# FILES ALREADY READ: {', '.join(files_read[-10:])}")
    
    # Last failures
    if state.last_failures:
        parts.append("\n# LAST TEST FAILURES")
        for f in state.last_failures[:3]:
            parts.append(f"- {f.nodeid}: {f.message[:100]}")
    
    # Last gate rejection
    if "last_gate_reject" in state.notes:
        parts.append(f"\n# LAST GATE REJECTION: {state.notes['last_gate_reject']}")
    
    return "\n".join(parts)


def _get_phase_instruction(phase: Phase) -> str:
    """Get detailed instruction for current phase."""
    instructions = {
        Phase.INGEST: """
INSTRUCTION: Parse the problem statement carefully.
- Identify the bug or feature request
- Note any specific file paths, function names, or class names mentioned
- Output: tool_request to read the most relevant file
""",
        Phase.LOCALIZE: """
INSTRUCTION: Find the exact code location that needs to be changed.
- Use grep/search to find relevant functions, classes, or patterns
- Read specific files to understand the code structure
- DO NOT just read README.md - search for actual code files
- Output: tool_request with grep/search for specific terms from the problem
""",
        Phase.PLAN: """
INSTRUCTION: Plan the minimal fix.
- Based on localization, identify exactly what needs to change
- Consider edge cases
- Output: Continue inspecting if needed, or move to generating a patch
""",
        Phase.PATCH_CANDIDATES: """
YOU MUST NOW GENERATE A PATCH. Output EXACTLY this JSON format:

{"mode": "patch", "diff": "--- a/filename.py\\n+++ b/filename.py\\n@@ -line,count +line,count @@\\n context line\\n-removed line\\n+added line\\n context line", "why": "explanation"}

CRITICAL RULES:
1. EDIT SOURCE FILES ONLY - NOT test files! Fix the bug in the actual implementation.
2. Do NOT add tests or modify test files - fix the code that is being tested.
3. You MUST output mode: "patch" - no other mode allowed here
4. The diff MUST have actual changes (removed lines different from added lines)
5. Use \\n for newlines in the JSON string
6. Match exact whitespace from the original file you read earlier

Example:
{"mode": "patch", "diff": "--- a/src/utils.py\\n+++ b/src/utils.py\\n@@ -10,3 +10,3 @@\\n def foo():\\n-    return x + 1\\n+    return x * 2\\n", "why": "Fixed operator"}
""",
        Phase.TEST_STAGE: """
INSTRUCTION: Run tests to verify the fix.
- Run the specific test mentioned in the problem if any
- Or run the relevant test suite
- Output: tool_request with sandbox.run_command for pytest
""",
        Phase.DIAGNOSE: """
INSTRUCTION: Analyze why tests are failing.
- Review the test output
- Identify what went wrong with your patch
- Output: tool_request to read failing test or patched code
""",
        Phase.MINIMIZE: """
INSTRUCTION: Ensure the patch is minimal.
- Remove any unnecessary changes
- Verify tests still pass
- Output: final patch or tool_request for verification
""",
        Phase.FINALIZE: """
INSTRUCTION: Finalize the solution.
- Confirm tests pass
- Output: {"mode": "feature_summary", "summary": "...", "completion_status": "complete"}
""",
    }
    return instructions.get(phase, "Proceed with the task.")


def _parse_response_to_proposal(response: dict, state: AgentState) -> Proposal:
    """Parse DeepSeek JSON response into a Proposal."""
    mode = response.get("mode", "tool_request")
    why = response.get("why", "")
    
    # Track this action in history
    if "action_history" not in state.notes:
        state.notes["action_history"] = []
    
    if mode == "patch":
        diff = response.get("diff", "")
        files = _extract_files_from_diff(diff)
        state.notes["action_history"].append(f"Generated patch for {files}")
        return Proposal(
            kind="edit",
            rationale=why or "Generated patch",
            inputs={"diff": diff, "files": files},
            evidence=[],
        )
    
    elif mode == "tool_request":
        requests = response.get("requests", [])
        if not requests:
            return _infer_proposal_from_phase(state, why)
        
        # Parse all requests
        first_req = requests[0]
        tool = first_req.get("tool", "")
        args = first_req.get("args", {})
        
        # Determine proposal kind and inputs
        if any(kw in tool for kw in ["grep", "search", "find", "rg"]):
            query = args.get("query", args.get("pattern", ""))
            state.notes["action_history"].append(f"Search: {query}")
            return Proposal(
                kind="search",
                rationale=why or f"Search for: {query}",
                inputs={"query": query},
                evidence=[],
            )
        
        elif any(kw in tool for kw in ["read", "cat", "view"]):
            path = args.get("path", args.get("file", ""))
            # Avoid re-reading the same file
            files_read = state.notes.get("files_read", [])
            if path in files_read:
                # Force a search instead
                return _infer_proposal_from_phase(state, f"Already read {path}, trying search")
            state.notes["action_history"].append(f"Read: {path}")
            return Proposal(
                kind="inspect",
                rationale=why or f"Read file: {path}",
                inputs={"files": [path]},
                evidence=[],
            )
        
        elif any(kw in tool for kw in ["test", "pytest", "run"]):
            cmd = args.get("command", args.get("cmd", "pytest"))
            state.notes["action_history"].append(f"Run: {cmd}")
            return Proposal(
                kind="run_tests",
                rationale=why or f"Run tests: {cmd}",
                inputs={"command": cmd},
                evidence=[],
            )
        
        else:
            # Unknown tool - try to infer from args
            if "path" in args:
                return Proposal(
                    kind="inspect",
                    rationale=why or "Read file",
                    inputs={"files": [args["path"]]},
                    evidence=[],
                )
            return _infer_proposal_from_phase(state, why)
    
    elif mode == "feature_summary":
        state.notes["action_history"].append("Finalize")
        return Proposal(
            kind="finalize",
            rationale=why or "Task complete",
            inputs={
                "summary": response.get("summary", ""),
                "status": response.get("completion_status", "complete"),
            },
            evidence=[],
        )
    
    return _infer_proposal_from_phase(state, why)


def _infer_proposal_from_phase(state: AgentState, why: str) -> Proposal:
    """Infer a sensible proposal based on current phase when parsing fails."""
    problem = state.notes.get("problem_statement", "")
    files_read = state.notes.get("files_read", [])
    history = state.notes.get("action_history", [])
    last_contents = state.notes.get("last_file_contents", {})
    
    # Use regex-based extraction for clean code identifiers
    code_terms = _extract_code_identifiers(problem)
    
    # Check if we've already searched these terms
    searched_terms = [h.split(": ")[-1] for h in history if "search" in h.lower()]
    unsearched_terms = [t for t in code_terms if t not in searched_terms]
    
    # CRITICAL: In PATCH_CANDIDATES phase with file contents - force edit proposal
    if state.phase == Phase.PATCH_CANDIDATES and last_contents and files_read:
        # We have read files and have content - generate a placeholder edit
        first_file = list(last_contents.keys())[0]
        state.notes["action_history"].append(f"Forcing edit for: {first_file}")
        return Proposal(
            kind="edit",
            rationale="Generating patch based on analyzed file contents",
            inputs={
                "files": [first_file],
                "diff": "",  # LLM should have generated this, but fallback is empty
            },
            evidence=[],
        )
    
    # In LOCALIZE, PLAN phases - try searching if we have clean terms
    if state.phase in [Phase.LOCALIZE, Phase.PLAN] and unsearched_terms:
        term = unsearched_terms[0]
        state.notes["action_history"].append(f"Inferred search: {term}")
        return Proposal(
            kind="search",
            rationale=why or f"Search for code term: {term}",
            inputs={"query": term},
            evidence=[],
        )
    
    # If we have localization hits, read the most recent unread file
    if state.localization_hits:
        for hit in state.localization_hits:
            fname = hit.get("file", "")
            if fname and fname not in files_read:
                state.notes["action_history"].append(f"Inferred read: {fname}")
                return Proposal(
                    kind="inspect",
                    rationale=why or f"Read localized file: {fname}",
                    inputs={"files": [fname]},
                    evidence=[],
                )
    
    # Try fallback search terms if no code identifiers found
    if state.phase in [Phase.LOCALIZE, Phase.PLAN, Phase.PATCH_CANDIDATES]:
        # Search for common patterns
        fallback_terms = ["def ", "class ", "import "]
        for term in fallback_terms:
            if term not in searched_terms:
                state.notes["action_history"].append(f"Fallback search: {term}")
                return Proposal(
                    kind="search",
                    rationale=f"Searching for {term.strip()} patterns",
                    inputs={"query": term},
                    evidence=[],
                )
    
    # Only fall back to problem_statement once
    ps_reads = sum(1 for h in history if "problem_statement" in h.lower())
    if ps_reads < 1:
        state.notes["action_history"].append("Read problem_statement")
        return Proposal(
            kind="inspect",
            rationale=why or "Review problem statement",
            inputs={"query": "problem_statement"},
            evidence=[],
        )
    
    # Force finalize if we've exhausted all options
    if state.phase in [Phase.PATCH_CANDIDATES, Phase.PLAN]:
        state.notes["action_history"].append("Force finalize - no more actions")
        return Proposal(
            kind="finalize",
            rationale="Exhausted search options",
            inputs={"summary": "Could not generate a valid patch", "status": "incomplete"},
            evidence=[],
        )
    
    # Generic search as absolute last resort
    state.notes["action_history"].append("Generic search: error")
    return Proposal(
        kind="search",
        rationale="Searching for error patterns",
        inputs={"query": "error"},
        evidence=[],
    )


def _extract_files_from_diff(diff: str) -> list[str]:
    """Extract file paths from a unified diff."""
    files = []
    for line in diff.split("\n"):
        if line.startswith("+++ b/") or line.startswith("--- a/"):
            path = line[6:].strip()
            if path and path != "/dev/null":
                files.append(path)
    return list(set(files))


# =============================================================================
# GATE FUNCTION - Validates proposals against constraints
# =============================================================================

def gate(profile: Profile, state: AgentState, proposal: Proposal) -> GateDecision:
    """Validate a proposal against profile constraints."""
    # 1. Check phase constraints
    allowed_kinds = _allowed_kinds_for_phase(state.phase)
    if proposal.kind not in allowed_kinds:
        return GateDecision(
            accept=False,
            reason=f"Action '{proposal.kind}' not allowed in phase {state.phase.value}. Allowed: {allowed_kinds}",
        )
    
    # 2. Check budget constraints
    if proposal.kind == "run_tests":
        if state.budget.test_runs >= profile.max_test_runs:
            return GateDecision(
                accept=False,
                reason=f"Test budget exhausted ({state.budget.test_runs}/{profile.max_test_runs})",
            )
    
    if proposal.kind == "edit":
        if state.budget.patch_attempts >= profile.max_patch_attempts:
            return GateDecision(
                accept=False,
                reason=f"Patch budget exhausted ({state.budget.patch_attempts}/{profile.max_patch_attempts})",
            )
    
    # 3. Check file constraints for edits
    if proposal.kind == "edit":
        files = proposal.inputs.get("files", [])
        
        if len(files) > profile.max_files_touched:
            return GateDecision(
                accept=False,
                reason=f"Too many files ({len(files)} > {profile.max_files_touched})",
            )
        
        forbidden_dirs = ["vendor/", "node_modules/", ".venv/", "dist/", "build/", "target/"]
        for f in files:
            for forbidden in forbidden_dirs:
                if f.startswith(forbidden) or f"/{forbidden}" in f:
                    return GateDecision(
                        accept=False,
                        reason=f"Cannot edit forbidden directory: {forbidden}",
                    )
        
        diff = proposal.inputs.get("diff", "")
        diff_lines = len([line for line in diff.split("\n") 
                         if line.startswith("+") or line.startswith("-")])
        if diff_lines > profile.max_diff_lines:
            return GateDecision(
                accept=False,
                reason=f"Diff too large ({diff_lines} > {profile.max_diff_lines} lines)",
            )
    
    # 4. Check test modification constraint
    if profile.forbid_test_modifications and proposal.kind == "edit":
        files = proposal.inputs.get("files", [])
        for f in files:
            if "test" in f.lower() or f.startswith("tests/"):
                return GateDecision(
                    accept=False,
                    reason=f"Test modification forbidden by profile: {f}",
                )
    
    return GateDecision(accept=True, reason="All constraints satisfied")


def _allowed_kinds_for_phase(phase: Phase) -> list[str]:
    """Get allowed proposal kinds for a given phase."""
    return {
        Phase.INGEST: ["inspect", "search"],
        Phase.LOCALIZE: ["inspect", "search"],
        Phase.PLAN: ["inspect", "search", "edit"],  # Allow edit from PLAN
        Phase.PATCH_CANDIDATES: ["edit", "inspect", "search"],
        Phase.TEST_STAGE: ["run_tests", "inspect"],
        Phase.DIAGNOSE: ["inspect", "search", "edit"],
        Phase.MINIMIZE: ["edit", "inspect", "run_tests"],
        Phase.FINALIZE: ["finalize", "run_tests"],
        Phase.DONE: [],
    }.get(phase, ["inspect"])


# =============================================================================
# EXEC FUNCTION - Executes proposals
# =============================================================================

def execute(profile: Profile, state: AgentState, proposal: Proposal) -> ExecResult:
    """Execute a proposal."""
    logger.info("Executing proposal", kind=proposal.kind)
    
    if proposal.kind == "inspect":
        return _exec_inspect(state, proposal)
    elif proposal.kind == "search":
        return _exec_search(state, proposal)
    elif proposal.kind == "edit":
        return _exec_edit(state, proposal)
    elif proposal.kind == "run_tests":
        return _exec_run_tests(state, proposal)
    elif proposal.kind == "finalize":
        return _exec_finalize(state, proposal)
    else:
        return ExecResult(status="fail", summary=f"Unknown proposal kind: {proposal.kind}")


def _exec_inspect(state: AgentState, proposal: Proposal) -> ExecResult:
    """Execute an inspect proposal."""
    workdir = Path(state.repo.workdir)
    
    files = proposal.inputs.get("files", [])
    query = proposal.inputs.get("query", "")
    
    if query == "problem_statement":
        content = state.notes.get("problem_statement", "No problem statement available")
        return ExecResult(
            status="ok",
            summary=f"Problem statement: {content[:200]}...",
            artifacts=[],
            metrics={"content": content},
        )
    
    if files:
        contents = {}
        files_read = state.notes.get("files_read", [])
        
        for f in files:
            path = workdir / f
            if path.exists():
                try:
                    file_content = path.read_text()[:8000]
                    contents[f] = file_content
                    if f not in files_read:
                        files_read.append(f)
                except Exception as e:
                    contents[f] = f"Error reading: {e}"
            else:
                contents[f] = "File not found"
        
        state.notes["files_read"] = files_read
        state.notes["last_file_contents"] = contents
        
        # Add to localization hits if file contains useful info
        for fname in contents:
            if contents[fname] != "File not found":
                state.localization_hits.append({
                    "file": fname,
                    "reason": "file read",
                    "type": "read",
                })
        
        return ExecResult(
            status="ok",
            summary=f"Read {len(contents)} files: {list(contents.keys())}",
            artifacts=list(contents.keys()),
            metrics={"contents": contents},
        )
    
    return ExecResult(status="ok", summary="No files to inspect")


def _exec_search(state: AgentState, proposal: Proposal) -> ExecResult:
    """Execute a search proposal using ripgrep, grep, or Python fallback."""
    workdir = Path(state.repo.workdir)
    query = proposal.inputs.get("query", "")
    
    if not query:
        return ExecResult(status="fail", summary="No search query provided")
    
    files = []
    
    # Try ripgrep first
    try:
        result = subprocess.run(
            ["rg", "-l", "--max-count", "5", query],
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()][:20]
    except FileNotFoundError:
        pass  # rg not available
    
    # Try grep if rg didn't work
    if not files:
        try:
            result = subprocess.run(
                ["grep", "-rl", "--include=*.py", query, "."],
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()][:20]
        except FileNotFoundError:
            pass  # grep not available
    
    # Python fallback - walk directory and search
    if not files:
        try:
            for root, dirs, filenames in workdir.walk():
                # Skip hidden and common non-code directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in [
                    '__pycache__', 'node_modules', 'venv', '.git', 'build', 'dist'
                ]]
                
                for fname in filenames:
                    if not fname.endswith('.py'):
                        continue
                    fpath = root / fname
                    try:
                        content = fpath.read_text(errors='ignore')
                        if query in content:
                            rel_path = str(fpath.relative_to(workdir))
                            files.append(rel_path)
                            if len(files) >= 20:
                                break
                    except Exception:
                        pass
                if len(files) >= 20:
                    break
        except Exception as e:
            return ExecResult(status="fail", summary=f"Python search failed: {e}")
    
    # Update localization hits
    for f in files:
        state.localization_hits.append({
            "file": f,
            "reason": f"match for '{query}'",
            "type": "search",
        })
    
    if files:
        return ExecResult(
            status="ok",
            summary=f"Found {len(files)} files matching '{query}': {files[:5]}",
            artifacts=files,
            metrics={"query": query, "matches": files},
        )
    else:
        return ExecResult(
            status="ok",
            summary=f"No files found matching '{query}'",
            artifacts=[],
            metrics={"query": query, "matches": []},
        )


def _exec_edit(state: AgentState, proposal: Proposal) -> ExecResult:
    """Execute an edit proposal by applying a patch."""
    workdir = Path(state.repo.workdir)
    diff = proposal.inputs.get("diff", "")
    
    if not diff:
        return ExecResult(status="fail", summary="No diff provided")
    
    # Validate patch before attempting to apply
    is_valid, error = _validate_patch(diff)
    if not is_valid:
        logger.warning("Invalid patch detected", error=error)
        return ExecResult(
            status="fail",
            summary=f"Invalid patch: {error}",
            metrics={"validation_error": error, "diff_preview": diff[:500]},
        )
    
    # Try to repair common patch issues
    diff = _repair_patch(diff)
    
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False) as f:
            f.write(diff)
            patch_path = f.name
        
        # Check first
        result = subprocess.run(
            ["git", "apply", "--check", patch_path],
            cwd=workdir,
            capture_output=True,
            text=True,
            check=False,
        )
        
        if result.returncode != 0:
            # Log the failed patch for debugging
            logger.warning(
                "Patch check failed",
                error=result.stderr[:500],
                diff_preview=diff[:500],
            )
            
            # Try to apply as a direct file edit if patch fails
            edit_result = _try_direct_edit(state, proposal, diff)
            if edit_result:
                return edit_result
            
            # Try structured SEARCH/REPLACE approach
            structured_result = _try_structured_edit(state, proposal, diff)
            if structured_result:
                return structured_result
            
            return ExecResult(
                status="fail",
                summary=f"Patch check failed: {result.stderr[:200]}",
                metrics={"stderr": result.stderr, "diff": diff[:1000]},
            )
        
        # Apply with --3way for more lenient patching
        result = subprocess.run(
            ["git", "apply", "--3way", patch_path],
            cwd=workdir,
            capture_output=True,
            text=True,
            check=False,
        )
        
        if result.returncode == 0:
            files = proposal.inputs.get("files", [])
            state.budget.patch_attempts += 1
            return ExecResult(
                status="ok",
                summary=f"Patch applied successfully ({len(files)} files)",
                artifacts=files,
            )
        else:
            return ExecResult(status="fail", summary=f"Patch apply failed: {result.stderr[:200]}")
    except Exception as e:
        return ExecResult(status="fail", summary=f"Edit failed: {e}")


def _validate_patch(diff: str) -> tuple[bool, str]:
    """Validate that a patch contains actual changes.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not diff or not diff.strip():
        return False, "Empty diff"
    
    lines = diff.split("\n")
    removals = []
    additions = []
    
    for line in lines:
        # Skip headers and context
        if line.startswith("---") or line.startswith("+++") or line.startswith("@@"):
            continue
        if line.startswith("diff --git"):
            continue
        
        # Collect actual changes
        if line.startswith("-") and not line.startswith("---"):
            removals.append(line[1:])  # Strip the - prefix
        elif line.startswith("+") and not line.startswith("+++"):
            additions.append(line[1:])  # Strip the + prefix
    
    if not removals and not additions:
        return False, "No changes in diff (no + or - lines)"
    
    # Check for no-op: all removals match all additions
    if removals == additions:
        return False, "No-op patch: removed lines identical to added lines"
    
    # Check for minimal change (at least one actual difference)
    has_real_change = False
    for i, (rem, add) in enumerate(zip(removals, additions)):
        if rem.strip() != add.strip():
            has_real_change = True
            break
    
    # If lengths differ, there's definitely a change
    if len(removals) != len(additions):
        has_real_change = True
    
    if not has_real_change and removals and additions:
        return False, "No meaningful changes (only whitespace differences)"
    
    return True, ""


def _try_structured_edit(state: AgentState, proposal: Proposal, diff: str) -> ExecResult | None:
    """Try to apply changes using SEARCH/REPLACE blocks extracted from diff.
    
    This is a more robust approach when unified diffs fail.
    """
    workdir = Path(state.repo.workdir)
    files = proposal.inputs.get("files", [])
    
    if not files:
        # Try to extract from diff
        files = _extract_files_from_diff(diff)
    
    if not files:
        return None
    
    # Parse diff to extract old/new code blocks
    lines = diff.split("\n")
    current_file = None
    removals = []
    additions = []
    changes_made = False
    
    for line in lines:
        if line.startswith("--- a/"):
            current_file = line[6:].split("\t")[0]
        elif line.startswith("+++ b/"):
            current_file = line[6:].split("\t")[0]
        elif line.startswith("-") and not line.startswith("---"):
            removals.append(line[1:])
        elif line.startswith("+") and not line.startswith("+++"):
            additions.append(line[1:])
    
    if not current_file or not (removals or additions):
        return None
    
    file_path = workdir / current_file
    if not file_path.exists():
        return None
    
    try:
        original = file_path.read_text()
        modified = original
        
        # Try to find and replace the removed block with the added block
        if removals:
            old_block = "\n".join(removals)
            new_block = "\n".join(additions) if additions else ""
            
            if old_block in original:
                modified = original.replace(old_block, new_block, 1)
                changes_made = True
            else:
                # Try line-by-line fuzzy matching
                for old_line in removals:
                    old_stripped = old_line.strip()
                    if old_stripped and old_stripped in original:
                        # Find the index of matching additions
                        idx = removals.index(old_line)
                        new_line = additions[idx] if idx < len(additions) else ""
                        # Replace preserving indentation
                        for orig_line in original.split("\n"):
                            if orig_line.strip() == old_stripped:
                                indent = len(orig_line) - len(orig_line.lstrip())
                                new_with_indent = " " * indent + new_line.strip()
                                modified = modified.replace(orig_line, new_with_indent, 1)
                                changes_made = True
                                break
        
        if changes_made and modified != original:
            file_path.write_text(modified)
            state.budget.patch_attempts += 1
            return ExecResult(
                status="ok",
                summary=f"Applied structured edit to {current_file}",
                artifacts=[current_file],
            )
    except Exception as e:
        logger.warning(f"Structured edit failed: {e}")
    
    return None

def _repair_patch(diff: str) -> str:
    """Try to repair common patch format issues."""
    lines = diff.split("\n")
    repaired = []
    
    in_header = True
    for i, line in enumerate(lines):
        # Fix missing diff header
        if in_header and line.startswith("---") and i == 0:
            # Check if there's a missing diff --git line
            if i + 1 < len(lines) and lines[i + 1].startswith("+++"):
                # Extract paths, stripping existing a/ or b/ prefixes
                src = line[4:].strip().split("\t")[0]
                dst = lines[i + 1][4:].strip().split("\t")[0]
                
                # Strip existing a/ or b/ prefixes to avoid doubling
                if src.startswith("a/"):
                    src = src[2:]
                if dst.startswith("b/"):
                    dst = dst[2:]
                
                if not any(ln.startswith("diff --git") for ln in lines[:i]):
                    repaired.append(f"diff --git a/{src} b/{dst}")
        
        if line.startswith("@@"):
            in_header = False
        
        repaired.append(line)
    
    # Ensure proper line endings
    result = "\n".join(repaired)
    if not result.endswith("\n"):
        result += "\n"
    
    return result


def _try_direct_edit(state: AgentState, proposal: Proposal, diff: str) -> ExecResult | None:
    """Try to apply changes directly to files when patch format is invalid."""
    workdir = Path(state.repo.workdir)
    
    # Look for file and content in the diff
    files = _extract_files_from_diff(diff)
    if not files:
        return None
    
    # Try to extract the actual changes from the diff
    # Look for +/- lines that aren't headers
    additions = []
    deletions = []
    
    for line in diff.split("\n"):
        if line.startswith("+") and not line.startswith("+++"):
            additions.append(line[1:])
        elif line.startswith("-") and not line.startswith("---"):
            deletions.append(line[1:])
    
    if not additions and not deletions:
        return None
    
    # Combine deletions and additions into blocks
    old_block = "\n".join(deletions)
    new_block = "\n".join(additions)
    
    # Try to find and modify the file
    for fname in files:
        fpath = workdir / fname
        if not fpath.exists():
            continue
        
        try:
            content = fpath.read_text()
            modified = content
            
            # Strategy 1: Replace exact block
            if old_block and old_block in modified:
                modified = modified.replace(old_block, new_block, 1)
            
            # Strategy 2: Try line-by-line replacements
            elif deletions:
                for i, old_line in enumerate(deletions):
                    if old_line and old_line in modified:
                        new_line = additions[i] if i < len(additions) else ""
                        modified = modified.replace(old_line, new_line, 1)
            
            # Strategy 3: Just insert additions after a context line
            elif additions and not deletions:
                # Look for context in the diff (lines without +/-)
                context_lines = [l for l in diff.split("\n") 
                                if l and not l.startswith(("+", "-", "@", "diff", "---", "+++"))]
                for ctx in context_lines[:3]:
                    if ctx.strip() and ctx.strip() in content:
                        # Insert after context
                        idx = content.find(ctx.strip()) + len(ctx.strip())
                        modified = content[:idx] + "\n" + new_block + content[idx:]
                        break
            
            if modified != content:
                fpath.write_text(modified)
                state.budget.patch_attempts += 1
                return ExecResult(
                    status="ok",
                    summary=f"Applied direct edit to {fname}",
                    artifacts=[fname],
                )
        except Exception:
            continue
    
    return None


def _exec_run_tests(state: AgentState, proposal: Proposal) -> ExecResult:
    """Execute a test run proposal."""
    workdir = Path(state.repo.workdir)
    command = proposal.inputs.get("command", "pytest")
    
    cmd_parts = command.split() if isinstance(command, str) else command
    
    try:
        result = subprocess.run(
            cmd_parts,
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        
        passed = result.returncode == 0
        
        if not passed:
            failures = []
            for line in result.stdout.split("\n"):
                if "FAILED" in line:
                    failures.append({"nodeid": line.strip(), "message": line.strip()})
            
            from agent.types import TestFailure
            state.last_failures = [
                TestFailure(nodeid=f["nodeid"], message=f["message"])
                for f in failures[:5]
            ]
        else:
            state.last_failures = []
        
        return ExecResult(
            status="ok" if passed else "fail",
            summary=f"Tests {'passed' if passed else 'failed'}",
            artifacts=[],
            metrics={
                "test_result": {
                    "passed": passed,
                    "returncode": result.returncode,
                    "stdout_tail": result.stdout[-1000:] if result.stdout else "",
                }
            },
        )
    except subprocess.TimeoutExpired:
        return ExecResult(status="fail", summary="Test run timed out (5 min)")
    except Exception as e:
        return ExecResult(status="fail", summary=f"Test run failed: {e}")


def _exec_finalize(state: AgentState, proposal: Proposal) -> ExecResult:
    """Execute a finalize proposal."""
    summary = proposal.inputs.get("summary", "")
    status = proposal.inputs.get("status", "complete")
    
    state.notes["solved"] = status == "complete"
    state.notes["final_summary"] = summary
    
    return ExecResult(
        status="ok",
        summary=f"Task finalized: {status}",
        metrics={"final_summary": summary, "completion_status": status},
    )
