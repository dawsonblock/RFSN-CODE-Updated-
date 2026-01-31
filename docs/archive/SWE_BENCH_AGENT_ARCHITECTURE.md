# SWE-bench Agent Stack - Complete Architecture

**Date:** January 30, 2026  
**Repository:** https://github.com/dawsonblock/RFSN-GATE-CLEANED  
**Status:** 🚧 FOUNDATION COMPLETE - Building Full Stack

---

## 🎯 Mission

Transform RFSN Controller into a SWE-bench killer through systematic addition of:
1. **Serialagent loop** with explicit state machine
2. **3-layer localization** (trace + ripgrep + embeddings)
3. **N-candidate patch search** with scoring
4. **Staged test runner** (0→1→2→3 escalation)
5. **Outcome database + bandit learning** (upstream of gate)
6. **Role separation** (localizer, patcher, reviewer, minimizer)
7. **Two profiles** (Lite: fast, Verified: strict)

---

## 📐 Architecture Principles

### Core Invariants
1. **Serial authority:** One proposal at a time, always gated
2. **Gate is frozen:** No learning in the gate, ever
3. **Learning upstream:** Bandits, outcomes, retrieval BEFORE proposals
4. **One codebase:** Same agent, two profiles (Lite vs Verified)
5. **Append-only ledger:** All decisions auditable

### What Lives Where
- **Gate:** Deterministic constraints (phase, files, tests, diffs)
- **Planner:** Hypothesis management, micro-steps, strategy selection
- **Bandit:** Which strategy to try first (learned from outcomes)
- **Outcome DB:** What worked before on similar tasks
- **Retrieval:** Repo facts + fix patterns (citation-grounded)

---

## 🏗️ Directory Structure

```
agent/
  __init__.py
  types.py           ✅ Core contracts (Proposal, GateDecision, LedgerEvent, Phase)
  profiles.py        ✅ Profile loading (Lite vs Verified)
  loop.py            🚧 Serial loop: propose → gate → execute → log
  state.py           🚧 AgentState management
  budgets.py         🚧 Budget tracking (rounds, patches, tests, model calls)
  stop.py            🚧 Halt conditions (solved, exhausted, stuck, unsafe)

gate_ext/
  __init__.py        🚧 Main wrapper: gate_with_profile()
  policy_phase.py    🚧 Phase → allowed proposal kinds
  policy_files.py    🚧 Max touched files, vendor/CI forbid
  policy_tests.py    🚧 Test modification rules, full suite requirement
  policy_diff.py     🚧 Diff size limits, risk scoring

localize/
  __init__.py
  types.py           🚧 LocalizationHit (file, span, evidence, score)
  trace.py           🚧 Parse stack traces → suspect files
  ripgrep.py         🚧 Lexical search (keywords from issue + tests)
  embed_index.py     🚧 Semantic search (FAISS + embeddings)
  rank.py            🚧 Merge + rank localization signals

patch/
  __init__.py
  types.py           🚧 PatchCandidate (diff, confidence, risk)
  gen.py             🚧 Generate N candidates constrained to spans
  score.py           🚧 Heuristic scoring (lint, type hints, risk)
  apply.py           🚧 Safe apply/revert in worktrees
  minimize.py        🚧 Shrink diff after green tests

runner/
  __init__.py
  types.py           🚧 TestResult, TestFailure
  stages.py          🚧 Stage 0→1→2→3 escalation
  pytest_runner.py   🚧 Targeted pytest selection
  artifacts.py       🚧 Capture logs, traces, timings
  sandbox.py         🚧 Integration with existing sandbox

triage/
  __init__.py
  types.py           🚧 FailureClass enum
  classify.py        🚧 Bucket failures (import, assertion, type, etc.)
  playbooks.py       🚧 Map failure class → strategies

memory/
  __init__.py
  schema.sql         🚧 Outcome database schema
  outcomes.py        🚧 Query outcomes by (task features, repo)
  log.py             🚧 Append ledger events to JSONL

learn/
  __init__.py
  types.py           🚧 TaskFeatures, StrategyChoice
  bandit.py          🚧 Thompson sampling or UCB
  features.py        🚧 Extract features from task/repo/failures
  policy.py          🚧 Map bandit choice → strategy knobs

roles/
  __init__.py
  types.py           🚧 RoleProposal
  localizer.py       🚧 Propose localization searches
  patcher.py         🚧 Propose patch candidates
  reviewer.py        🚧 Try to break proposed patches
  minimizer.py       🚧 Shrink patch after success

eval/
  __init__.py
  run.py             🚧 Entrypoint: --profile lite|verified --split dev
  swebench.py        🚧 SWE-bench harness integration
  report.py          🚧 Generate solve rate, metrics, artifacts
  types.py           🚧 EpisodeResult, BenchmarkMetrics

profiles/
  swebench_lite.yaml      ✅ Fast iteration profile
  swebench_verified.yaml  ✅ Strict reproducibility profile
```

**Legend:**
- ✅ Complete
- 🚧 In progress / stub
- ⏳ Not started

---

## 📋 Core Contracts (agent/types.py)

###Phase State Machine

```
INGEST → LOCALIZE → PLAN → PATCH_CANDIDATES → TEST_STAGE → DIAGNOSE
                                                    ↓
                                                 SUCCESS?
                                                    ↓
                                            MINIMIZE → FINALIZE → DONE
```

### Proposal

```python
@dataclass(frozen=True)
class Proposal:
    kind: ProposalKind  # inspect, search, edit, run_tests, finalize
    rationale: str      # Short, testable hypothesis
    inputs: Dict[str, Any]
    expected_signal: Dict[str, Any]
    evidence: List[Evidence]  # Citations (trace/grep/embed)
```

### GateDecision

```python
@dataclass(frozen=True)
class GateDecision:
    accept: bool
    reason: str
    constraints: Dict[str, Any]
```

### LedgerEvent (Append-Only)

```python
@dataclass(frozen=True)
class LedgerEvent:
    ts_unix: float
    task_id: str
    repo_id: str
    phase: Phase
    proposal_hash: str
    proposal: Dict
    gate: Dict
    exec: Dict
    result: Dict
```

---

## 🎚️ Profile System

### SWE-bench Lite (profiles/swebench_lite.yaml)

**Goal:** Fast iteration, aggressive search

- max_rounds: 8
- patch_candidates_per_round: 12
- max_files_touched: 6
- test_stage_cap: 2 (don't always run full suite)
- forbid_test_modifications: false

### SWE-bench Verified (profiles/swebench_verified.yaml)

**Goal:** Strict reproducibility, conservative edits

- max_rounds: 10
- patch_candidates_per_round: 8
- max_files_touched: 3
- test_stage_cap: 3 (always run full suite)
- require_full_suite_for_finalize: true
- forbid_test_modifications: true (NEVER touch tests)

---

## 🔐 Gate Extension Policies

All policies are DETERMINISTIC. No learning.

### Phase Policy (gate_ext/policy_phase.py)

```
INGEST: {inspect}
LOCALIZE: {inspect, search}
PLAN: {inspect, search}
PATCH_CANDIDATES: {edit, inspect, search}
TEST_STAGE: {run_tests, inspect}
DIAGNOSE: {inspect, search}
MINIMIZE: {edit, inspect}
FINALIZE: {finalize, run_tests, inspect}
```

### File Policy (gate_ext/policy_files.py)

- Enforce max_files_touched per episode
- Forbid vendor/ and third_party/ edits (unless profile allows)
- Forbid .github/workflows/ edits (unless profile allows)

### Test Policy (gate_ext/policy_tests.py)

- Verified: NEVER allow test modifications
- Verified: Require full suite pass before finalize
- Lite: Allow test edits, stage 2 sufficient

### Diff Policy (gate_ext/policy_diff.py)

- Enforce max_diff_lines
- Risk scoring (large deletions, API changes)

---

## 🎯 Localization (3 Layers)

### Layer 1: Trace-Driven (localize/trace.py)

- Parse stack traces from failing tests
- Extract file paths + line numbers
- Highest confidence signal

### Layer 2: Lexical (localize/ripgrep.py)

- Ripgrep for keywords from issue description
- Ripgrep for symbols from failing test names
- Ripgrep for error message patterns
- Fast, deterministic

### Layer 3: Semantic (localize/embed_index.py)

- Embeddings over repo chunks (files, symbols, docstrings)
- FAISS or sqlite+ann for fast retrieval
- Returns file + span + similarity score
- Citation-grounded

### Ranking (localize/rank.py)

Merge all signals:
- Trace hits: weight 1.0 (highest confidence)
- Ripgrep hits: weight 0.7
- Embedding hits: weight 0.5
- Return top-k with evidence

---

## 🔧 Patch Search (N Candidates)

### Generation (patch/gen.py)

- Generate N candidates (8-12) constrained to localized spans
- Use multiple models if ensemble enabled
- Vary prompt strategies (direct fix, refactor, defensive)

### Scoring (patch/score.py)

- Static checks: lint, type hints (if present)
- Risk score: lines changed, files touched, deletes
- Confidence score: LLM logprobs if available

### Testing Strategy

1. Generate N candidates
2. Score statically (cheap)
3. Test top-k in parallel (stage 1: targeted tests)
4. Test winner at higher stages (2, 3)

### Minimization (patch/minimize.py)

After green tests:
1. Remove hunks one by one
2. Re-test after each removal
3. Keep minimal working patch

---

## 🧪 Staged Test Runner

### Stage 0: Compile/Import Smoke

```bash
python -m compileall .
python -c "import main_module"
```

Fast fail if syntax/import broken.

### Stage 1: Targeted Tests

Infer from:
- Failing test names (run those)
- Touched file names (pytest -k pattern)
- Stack trace files (pytest path/to/file.py)

### Stage 2: Broader Subset

- Related test modules
- Full test file if only one file

### Stage 3: Full Suite

- Entire test suite
- Required for Verified finalize
- Expensive, run last

### Artifact Capture (runner/artifacts.py)

Every test run:
- Failing test node IDs
- Stack traces (full, not truncated)
- Logs (stdout/stderr, last 1000 lines)
- Timing (per-test durations)

---

## 🧠 Learning System (Upstream of Gate)

### Outcome Database (memory/outcomes.py)

Schema:
```sql
CREATE TABLE outcomes (
    task_id TEXT,
    repo_hash TEXT,
    failure_class TEXT,
    strategy TEXT,
    localization_top_k INT,
    patch_count INT,
    test_runs INT,
    success BOOLEAN,
    duration_s REAL,
    ts_unix REAL
);
```

Query by:
- (repo_hash, failure_class) → what worked before
- (language, framework) → best default strategy

### Bandit (learn/bandit.py)

Thompson sampling over strategies:
- Which localization depth (top-k)
- Which patch generator (model/prompt)
- How many candidates to generate
- When to escalate tests

### Features (learn/features.py)

```python
@dataclass
class TaskFeatures:
    language: str
    framework: str  # pytest, unittest, jest
    failure_class: str  # import, assertion, type, etc.
    repo_size: int  # LOC
    test_count: int
```

### Policy (learn/policy.py)

Map bandit choice → strategy knobs:
```python
choice = bandit.select(features)
strategy = {
    "localization_depth": choice.top_k,
    "patch_count": choice.candidates,
    "model": choice.model,
}
```

---

## 👥 Role Separation

Roles propose options, controller commits serially.

### Localizer Role (roles/localizer.py)

Input: Issue text + failing tests
Output: List of (file, span, evidence, score)

### Patcher Role (roles/patcher.py)

Input: Localized spans + failure traces
Output: N patch candidates

### Reviewer Role (roles/reviewer.py)

Input: Patch candidate
Output: Potential issues (edge cases, regressions)

### Minimizer Role (roles/minimizer.py)

Input: Passing patch
Output: Minimal diff that still passes

---

## 📊 Evaluation Harness

### Entrypoint (eval/run.py)

```bash
python -m eval.run \
    --profile swebench_lite \
    --split dev \
    --limit 200 \
    --output runs/$(date +%Y%m%d_%H%M%S)
```

### Outputs

```
runs/<timestamp>/
  episodes.csv          # Per-task results
  events.jsonl          # All ledger events
  artifacts/            # Logs, diffs, traces
    task_001/
      diff.patch
      test_logs/
      localization.json
  summary.json          # Aggregate metrics
```

### Metrics (eval/report.py)

- Solve rate (% tasks solved)
- Median wall time per task
- Test invocations per solve
- Patch attempts per solve
- Localization hit rate
- Gate reject rate

---

## 🚀 Build Order (Priority)

### Phase 1: Foundation ✅ COMPLETE
- [x] Core types (agent/types.py)
- [x] Profile system (agent/profiles.py)
- [x] Two profiles (Lite, Verified)
- [x] Directory structure

### Phase 2: Loop + Gate Extensions 🚧 NEXT
- [ ] agent/loop.py (serial loop)
- [ ] gate_ext/policy_*.py (all policies)
- [ ] memory/log.py (ledger)
- [ ] Integration with existing gate

### Phase 3: Localization (Core Differentiator)
- [ ] localize/trace.py
- [ ] localize/ripgrep.py
- [ ] localize/embed_index.py
- [ ] localize/rank.py

### Phase 4: Patch Search
- [ ] patch/gen.py (N candidates)
- [ ] patch/score.py
- [ ] patch/apply.py

### Phase 5: Staged Runner
- [ ] runner/stages.py
- [ ] runner/pytest_runner.py
- [ ] runner/artifacts.py
- [ ] triage/classify.py

### Phase 6: Learning
- [ ] memory/outcomes.py + schema.sql
- [ ] learn/bandit.py
- [ ] learn/features.py
- [ ] learn/policy.py

### Phase 7: Roles
- [ ] roles/localizer.py
- [ ] roles/patcher.py
- [ ] roles/reviewer.py
- [ ] roles/minimizer.py

### Phase 8: Evaluation
- [ ] eval/run.py
- [ ] eval/swebench.py
- [ ] eval/report.py

---

## 📈 Expected Impact

### From Existing Controller Baseline

| Upgrade | Expected Gain | Reason |
|---------|---------------|--------|
| 3-layer localization | +15-25% | Most failures from bad localization |
| N-candidate search | +10-15% | Stop betting on one patch |
| Staged tests | +5-10% | Faster feedback loops |
| Bandit selection | +5-8% | Learn which strategies work |
| Diff minimization | +3-5% | Cleaner, safer patches |
| Reviewer role | +2-5% | Catch edge cases |

**Cumulative:** 40-68% improvement over baseline

### Target Benchmarks

- **SWE-bench Lite:** 60%+ solve rate (current SOTA ~50%)
- **SWE-bench Verified:** 45%+ solve rate (current SOTA ~35%)

---

## 🔬 Research Questions (To Validate)

1. **Localization:** Does embedding retrieval beat ripgrep alone?
2. **Patch count:** Is N=8 optimal, or should we go higher?
3. **Test stages:** Does stage 1 catch 80%+ of failures?
4. **Bandit:** Does Thompson sampling converge faster than UCB?
5. **Minimization:** Does minimizing diffs improve acceptance?

Track in outcome DB and analyze after 200+ episodes.

---

## 🎯 Success Criteria

### Tier 1: Foundation (This PR)
- ✅ Types and contracts defined
- ✅ Profile system working
- ✅ Directory structure in place

### Tier 2: Functional Agent (Next 2 weeks)
- [ ] Loop + gate extensions working
- [ ] Localization returning ranked hits
- [ ] Patch generation producing candidates
- [ ] Staged tests running
- [ ] Outcome DB logging

### Tier 3: Learning Agent (Next 4 weeks)
- [ ] Bandit converging on strategies
- [ ] Outcome DB showing patterns
- [ ] Role separation improving quality

### Tier 4: Benchmark Killer (Next 8 weeks)
- [ ] SWE-bench Lite >55% solve rate
- [ ] SWE-bench Verified >40% solve rate
- [ ] Reproducible, deterministic results

---

## 📝 Next Immediate Steps

1. **Implement agent/loop.py** (serial loop core)
2. **Implement gate_ext policies** (phase, files, tests, diff)
3. **Implement memory/log.py** (ledger append)
4. **Wire to existing gate** (adapt gate signature)
5. **Test loop with stub planner** (verify gate enforcement)

Then build localization layer (the 80/20 of solve rate).

---

**Status:** Foundation complete, ready to build full stack  
**Repository:** https://github.com/dawsonblock/RFSN-GATE-CLEANED  
**Quality:** Production-grade types and contracts  
**Next Milestone:** Functional agent loop with localization
