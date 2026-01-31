# SWE-Bench Killer Agent Stack - Implementation Status

## 🎯 Objective
Build a production-ready SWE-bench killer agent that implements the outer task loop:
1. Ingest issue (problem statement + repo snapshot)
2. Localize likely files/regions  
3. Plan micro-steps
4. Propose action
5. Gate validates
6. Execute
7. Evaluate
8. Store outcome + update priors
9. Stop when solved or budget exhausted

## ✅ Completed Components

### 1. Evaluation Harness (`eval/`)
**Files**: `eval/run.py`, `eval/swebench.py`

**Capabilities**:
- `EvalRunner`: Main evaluation loop for SWE-bench tasks
- `SWEBenchTask`: Task data structure with problem statement, repo, commit, test patch
- `EvalResult`: Comprehensive result tracking with metrics
- `EvalConfig`: Configurable evaluation parameters
- Task loading from JSONL datasets (Lite, Verified, Full)
- Sample task generation for testing
- Result export in SWE-bench format for official scoring
- Parallel and serial task execution
- Resource tracking (LLM calls, tokens, subprocess calls)

**Integration Points**:
- Calls `agent.loop.run_episode()` for each task
- Uses `agent.profiles` for task-specific configuration
- Logs events via `memory.log.append_event()`

### 2. Multi-Layer Localization Stack (`localize/`)
**Files**: `localize/__init__.py`, `localize/ripgrep.py`, `localize/embeddings.py`, `localize/symbol_index.py`, `localize/types.py`, `localize/trace.py`

**Three-Layer Architecture**:

#### Layer 1: Trace Parsing (Highest Confidence)
- `parse_python_traceback()`: Extract file/line from stack traces
- Confidence: 1.0 (direct evidence)
- Fast, no dependencies

#### Layer 2a: Ripgrep Lexical Search (Fast)
- `localize_from_issue()`: Extract keywords from problem statement
- `localize_from_trace()`: Extract keywords from error messages
- `extract_keywords()`: Filter stopwords, extract identifiers
- `extract_identifiers()`: Find CamelCase and snake_case
- Ripgrep JSON output parsing with fallback to Python search
- Confidence: 0.7 (keyword matching)

#### Layer 2b: Symbol/Import Graph (Structural)
- `SymbolIndex`: Index of functions, classes, methods
- `find_callers()`: Track call graph relationships
- `find_related_files()`: Import dependency traversal
- Uses ctags when available, falls back to regex
- Confidence: 0.9 (high for definitions, medium for callers)

#### Layer 3: Embedding Semantic Search (Deep Understanding)
- `EmbeddingLocalizer`: FAISS-based semantic search
- `build_index()`: Index repo chunks with caching
- `search()`: Semantic similarity query
- Model: `all-MiniLM-L6-v2` (fast, compact)
- Confidence: 0.8 (semantic understanding)
- Optional dependency: `sentence-transformers`, `faiss-cpu`

**Unified API**:
- `MultiLayerLocalizer`: Combines all layers with score fusion
- `localize_issue()`: High-level entry point
- Deduplication and ranking by combined scores
- Configurable layer weights and result limits

**Output Format**:
```python
LocalizationHit(
    file_path="src/module.py",
    line_start=42,
    line_end=50,
    score=0.85,
    evidence="Matched keywords: function_name, error_type",
    method="ripgrep_lexical+symbol_definition",
)
```

### 3. Patch Generation Foundation (`patch/`)
**Files**: `patch/gen.py`, `patch/types.py`

**Data Structures**:
- `Patch`: Core patch object with diff, metadata, scores
- `PatchCandidate`: Patch with priority and parent/child links
- `PatchGenerationRequest`: Input parameters for generation
- `PatchGenerationResult`: Output with candidates and metrics
- `PatchStrategy`: Enum of generation strategies
- `PatchStatus`: Lifecycle tracking
- `FileDiff`: Per-file diff representation

**Generation Strategies**:
1. **DIRECT_FIX**: Generate from localization hits
2. **TEST_DRIVEN**: Focus on passing failing tests
3. **HYPOTHESIS**: Try multiple bug hypotheses
4. **INCREMENTAL**: Build on previous patches
5. **ENSEMBLE**: Combine multiple strategies

**Features**:
- Constrained to localized file spans
- Max files per patch configurable
- Max lines per file configurable
- Unified diff generation
- LLM integration points (placeholder for now)
- Priority scoring for candidate ranking

**Integration Points**:
- Takes `LocalizationHit` list as input
- Produces `Patch` objects for scoring/testing
- Ready for LLM client injection

## 🚧 In Progress / Next Steps

### 4. Patch Scoring & Minimization
**Needed**: `patch/score.py`, `patch/minimize.py`, `patch/apply.py`

**Scoring Components**:
- Static analysis (syntax, imports, style)
- Test delta (incremental test running)
- Diff risk (complexity, size, critical sections)
- Combined score with weights

**Minimization**:
- Remove unnecessary changes
- Split multi-file patches
- Delta debugging for minimal failing diff

**Application**:
- Safe patch application with rollback
- Worktree isolation
- Git integration

### 5. Staged Test Runner (`runner/`)
**Needed**: `runner/tests.py`, `runner/stages.py`, `runner/artifacts.py`

**Stages**:
1. Syntax check (fast fail)
2. Import validation
3. Unit tests (focused)
4. Integration tests
5. Full test suite

**Artifacts**:
- Failing test names/counts
- Stack traces
- Coverage deltas
- Timing data
- Log captures

### 6. Triage System (`triage/`)
**Needed**: `triage/failures.py`, `triage/classify.py`

**Capabilities**:
- Classify test failures (syntax, import, assertion, timeout)
- Extract actionable feedback
- Suggest next actions
- Identify flaky tests

### 7. Memory & Learning Layer (`memory/`, `learn/`)
**Needed**: 
- `memory/outcomes.sqlite` schema
- `memory/log_event.py` (append-only outcome log)
- `learn/bandit.py` (strategy selection)
- `learn/features.py` (task feature extraction)
- `learn/policy.py` (policy learning)

**Schema**:
```sql
CREATE TABLE outcomes (
    task_id TEXT,
    repo_hash TEXT,
    localization_hits TEXT,  -- JSON
    patch_strategy TEXT,
    patch_hash TEXT,
    tests_run INTEGER,
    tests_passed INTEGER,
    result TEXT,  -- success/failure
    cost_tokens INTEGER,
    timestamp INTEGER
);
```

**Bandit Learning**:
- Thompson sampling or UCB1
- Feature vectors: repo size, test count, error type
- Stable, non-gradient learning
- Cooldown periods after failures

### 8. Role Separation (`roles/`)
**Needed**: `roles/localizer.py`, `roles/patcher.py`, `roles/reviewer.py`, `roles/minimizer.py`

**Architecture**:
- Each role is a specialized LLM call
- Serial authority (no parallel cleverness)
- Localizer → Patcher → Reviewer → Minimizer
- Clear handoffs with structured data

### 9. Episode Loop Integration (`agent/loop.py`)
**Needed**: Wire full propose/gate/exec cycle

**Current State**:
- `run_episode()` exists but needs integration
- `_advance_phase()` handles state transitions
- Needs connection to:
  - `localize.localize_issue()`
  - `patch.generate_patches()`
  - `runner` (staged tests)
  - `gate_ext.gate_with_profile()`
  - `memory.log.append_event()`

**Phases to Implement**:
```python
INGEST → LOCALIZE → PLAN → PATCH_CANDIDATES → 
TEST_STAGE → DIAGNOSE → MINIMIZE → FINALIZE → DONE
```

### 10. Gate Extensions (`gate_ext/`)
**Status**: Partially complete

**Existing**:
- `gate_ext/policy_phase.py`: Phase-specific rules
- `gate_ext/policy_files.py`: File count/pattern limits
- `gate_ext/policy_tests.py`: Test coverage requirements
- `gate_ext/policy_diff.py`: Diff size constraints
- `gate_ext/__init__.py`: `gate_with_profile()`

**Needed**:
- Wire into controller loop
- Add profile-specific thresholds (Lite vs Verified)
- Logging and audit trail

## 📊 Code Metrics

### New Code Added
- **eval/**: ~600 lines
- **localize/**: ~1,500 lines (4 modules)
- **patch/**: ~580 lines (2 modules)
- **Total**: ~2,700 lines of production code

### Test Coverage
- `tests/test_async_multi_tier_cache.py`: 16 tests ✅
- `tests/test_integration.py`: 12 tests ✅
- `tests/test_optimizations.py`: 11 tests ✅
- **Total**: 39 tests passing

### Dependencies
**Core (required)**:
- `aiosqlite`: Async database
- `pytest-asyncio`: Async test support

**Optional (recommended)**:
- `sentence-transformers`: Semantic localization
- `faiss-cpu`: Vector search
- `ripgrep`: Fast text search (external)
- `ctags`: Symbol indexing (external)

## 🔗 Integration Architecture

```
eval/run.py (Outer Loop)
    ↓
agent/loop.py (Episode Loop)
    ↓
┌──────────────────────────────────┐
│ 1. INGEST: Load problem + repo  │
└──────────────────────────────────┘
    ↓
┌──────────────────────────────────┐
│ 2. LOCALIZE: Multi-layer search │
│    - localize.localize_issue()   │
└──────────────────────────────────┘
    ↓
┌──────────────────────────────────┐
│ 3. PLAN: Select strategy         │
│    - learn/bandit.py             │
└──────────────────────────────────┘
    ↓
┌──────────────────────────────────┐
│ 4. PATCH: Generate candidates    │
│    - patch.generate_patches()    │
└──────────────────────────────────┘
    ↓
┌──────────────────────────────────┐
│ 5. GATE: Validate proposal       │
│    - gate_ext.gate_with_profile()│
└──────────────────────────────────┘
    ↓
┌──────────────────────────────────┐
│ 6. EXECUTE: Apply + test         │
│    - runner/stages.py            │
└──────────────────────────────────┘
    ↓
┌──────────────────────────────────┐
│ 7. EVALUATE: Score results       │
│    - patch/score.py              │
└──────────────────────────────────┘
    ↓
┌──────────────────────────────────┐
│ 8. STORE: Update memory          │
│    - memory/log_event.py         │
│    - learn/bandit.update()       │
└──────────────────────────────────┘
    ↓
┌──────────────────────────────────┐
│ 9. DECIDE: Continue or done?     │
└──────────────────────────────────┘
```

## 🚀 Quick Start Guide

### Running Evaluation

```python
from eval.run import EvalConfig, run_eval

# Configure evaluation
config = EvalConfig(
    dataset="swebench_lite",
    max_tasks=10,
    profile_name="swebench_lite",
    max_time_per_task=1800,  # 30 minutes
    max_steps_per_task=50,
)

# Run evaluation
results = await run_eval(config)

# Results saved to eval_results/
```

### Using Localization

```python
from pathlib import Path
from localize import localize_issue

# Localize an issue
hits = localize_issue(
    problem_statement="The function returns None instead of the expected value",
    repo_dir=Path("/path/to/repo"),
    traceback="File 'module.py', line 42...",
)

# Top hits
for hit in hits[:5]:
    print(f"{hit.file_path}:{hit.line_start} (score: {hit.score:.2f})")
    print(f"  Evidence: {hit.evidence}")
```

### Generating Patches

```python
from patch.gen import generate_patches
from patch.types import PatchStrategy

# Generate patches
patches = generate_patches(
    problem_statement="Fix the bug...",
    repo_dir=Path("/path/to/repo"),
    localization_hits=hits,
    strategy=PatchStrategy.DIRECT_FIX,
    max_patches=5,
)

# Review patches
for patch in patches:
    print(f"Patch {patch.patch_id}:")
    print(patch.diff_text)
```

## 📈 Performance Optimizations

### Already Implemented
- `rfsn_controller/file_cache.py`: LRU cache with staleness detection
- `rfsn_controller/early_stop_optimizer.py`: Fast-fail on critical errors
- `rfsn_controller/batch_file_ops.py`: Batched I/O operations
- `rfsn_controller/async_multi_tier_cache.py`: Async database with pooling

### Planned
- Parallel patch evaluation
- Incremental test running (test only changed files)
- FAISS index caching
- Symbol index caching
- LLM response caching

## 🎯 Immediate Next Steps (Priority Order)

1. **Patch Scoring** (`patch/score.py`): Static analysis + test delta scoring
2. **Staged Test Runner** (`runner/tests.py`, `runner/stages.py`): Fast-fail pipeline
3. **Episode Loop Wiring** (`agent/loop.py`): Connect all components
4. **Memory Layer** (`memory/log_event.py`): Outcome persistence
5. **Bandit Learning** (`learn/bandit.py`): Strategy selection
6. **Integration Tests**: End-to-end validation
7. **Planner v5 Feedback**: Wire outcomes → state tracker

## 📝 Design Decisions & Rationale

### Why Multi-Layer Localization?
- **Layer 1 (Trace)**: Catches obvious bugs with stack traces
- **Layer 2a (Ripgrep)**: Fast, works without ML dependencies
- **Layer 2b (Symbols)**: Structural understanding, finds related code
- **Layer 3 (Embeddings)**: Deep semantic understanding, catches subtle bugs

### Why Multiple Patch Strategies?
- **DIRECT_FIX**: Works for simple bugs
- **TEST_DRIVEN**: Essential for test-driven development
- **HYPOTHESIS**: Explores alternative explanations
- **INCREMENTAL**: Learns from previous attempts
- **ENSEMBLE**: Robustness through diversity

### Why Staged Test Running?
- **Fast Fail**: Syntax errors in <1s vs full test suite in minutes
- **Resource Efficiency**: Don't waste compute on broken patches
- **Better Feedback**: Specific error types enable targeted fixes
- **Budget Control**: Stop early to try more candidates

### Why Append-Only Memory?
- **Reproducibility**: Never modify historical data
- **Audit Trail**: Full history of decisions
- **Learning Stability**: Stable substrate for bandit algorithms
- **Debugging**: Can replay any episode

## 🔧 Technical Debt & Known Issues

1. **LLM Integration**: Placeholder implementations need real LLM calls
2. **Error Handling**: Need more robust error recovery
3. **Testing**: Need integration tests for full pipeline
4. **Documentation**: Need API docs and examples
5. **Performance**: Need benchmarking and profiling
6. **Caching**: Need smarter cache invalidation
7. **Parallelism**: Need safe parallel patch evaluation

## 📚 References

- **SWE-bench Paper**: https://arxiv.org/abs/2310.06770
- **SWE-bench Lite**: Curated subset of 300 tasks
- **SWE-bench Verified**: Human-verified test patches
- **FAISS**: https://github.com/facebookresearch/faiss
- **Sentence Transformers**: https://www.sbert.net/

## 🏆 Success Criteria

### MVP (Minimum Viable Product)
- ✅ Eval harness can load and run tasks
- ✅ Localization produces ranked file/line hits
- ✅ Patch generation creates valid diffs
- ⏳ Patches can be applied and tested
- ⏳ Results are scored and stored
- ⏳ Full episode loop completes

### Production Ready
- ⏳ Pass rate > 10% on SWE-bench Lite (state-of-art: ~40%)
- ⏳ Average resolution time < 15 minutes per task
- ⏳ Cost < $0.50 per task (LLM + compute)
- ⏳ 100% test coverage on core modules
- ⏳ Documentation complete
- ⏳ Performance benchmarks established

### SWE-bench Killer
- ⏳ Pass rate > 50% on SWE-bench Lite
- ⏳ Pass rate > 30% on SWE-bench Verified
- ⏳ Automated error recovery
- ⏳ Bandit learning improves over time
- ⏳ Sub-10-minute average resolution
- ⏳ Cost < $0.20 per task

---

**Status**: Foundation complete, ready for integration and testing
**Last Updated**: 2026-01-30
**Version**: 0.4.0-dev
