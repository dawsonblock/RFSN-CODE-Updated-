# Episode Orchestrator - Integration Documentation

## Overview

The Episode Orchestrator (`agent/orchestrator.py`) is the **integration layer** that wires together all major components of the SWE-Bench Killer system into a cohesive, end-to-end bug-fixing pipeline.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Episode Orchestrator                      │
│  (agent/orchestrator.py + agent/loop.py)                    │
└─────────────────────────────────────────────────────────────┘
                            │
       ┌────────────────────┼────────────────────┐
       │                    │                    │
       ▼                    ▼                    ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ Localization │   │  LLM Patch   │   │ Test Runner  │
│  (localize/) │   │  Generation  │   │  (runner/)   │
│              │   │   (llm/)     │   │              │
│ • Trace      │   │ • OpenAI     │   │ • Baseline   │
│ • Ripgrep    │   │ • Anthropic  │   │ • Validation │
│ • Symbols    │   │ • DeepSeek   │   │ • Regression │
│ • Embeddings │   │              │   │ • Smoke      │
└──────────────┘   └──────────────┘   └──────────────┘
       │                    │                    │
       │                    ▼                    │
       │           ┌──────────────┐             │
       │           │ Patch Score  │             │
       │           │  (patch/)    │             │
       │           └──────────────┘             │
       │                    │                    │
       └────────────────────┼────────────────────┘
                            ▼
                   ┌──────────────┐
                   │   Failure    │
                   │   Triage     │
                   │  (triage/)   │
                   └──────────────┘
```

## Components Integrated

### 1. Multi-Layer Localization
- **Path**: `localize/`
- **Function**: Find relevant files/regions from problem statement
- **Layers**:
  - Stack trace parsing (confidence: 1.0)
  - Ripgrep lexical search (confidence: 0.7)
  - Symbol index (confidence: 0.9)
  - Embedding semantic search (confidence: 0.8)

### 2. LLM Patch Generation
- **Path**: `llm/`
- **Function**: Generate patches using LLM reasoning
- **Providers**:
  - OpenAI (GPT-4, GPT-4-turbo)
  - Anthropic (Claude 3.5 Sonnet)
  - DeepSeek (deepseek-chat)
- **Strategies**:
  - Direct Fix (single-shot)
  - Test-Driven (generate test first)
  - Hypothesis-Driven (multiple hypotheses)
  - Incremental (step-by-step)
  - Ensemble (combine multiple)

### 3. Staged Test Runner
- **Path**: `runner/tests.py`
- **Function**: Validate patches through 4 test stages
- **Stages**:
  - **Stage 0**: Compilation/syntax check
  - **Stage 1**: Targeted tests (mentioned in issue)
  - **Stage 2**: Subset (related files)
  - **Stage 3**: Full regression suite
- **Features**:
  - Docker isolation (optional)
  - Timeout handling
  - Artifact capture
  - Test comparison (baseline vs post-patch)

### 4. Failure Triage
- **Path**: `triage/failures.py`
- **Function**: Classify and diagnose test failures
- **Failure Types** (12):
  - Assertion, Import, Attribute, Type, Value, Key, Index, Timeout, Segfault, Syntax, Regression, Flaky
- **Severity Levels** (5):
  - Critical, High, Medium, Low, Info
- **Features**:
  - Root cause analysis
  - Suggested fixes
  - Confidence scoring
  - Regression detection

### 5. Patch Processing
- **Path**: `patch/`
- **Functions**:
  - **Scoring** (`score.py`): Multi-factor patch quality assessment
  - **Minimization** (`minimize.py`): Delta debugging to shrink patch
  - **Safe Application** (`apply.py`): Atomic apply with automatic rollback

## Episode Phases

The orchestrator follows a state machine with these phases:

```
INGEST → LOCALIZE → PLAN → PATCH_CANDIDATES → TEST_STAGE
   ↓                                              ↓
   └─────────────── DIAGNOSE ←──────────────────┘
                      ↓
           (Success) TEST_STAGE → MINIMIZE → FINALIZE → DONE
```

### Phase Details

| Phase | Action | Components Used |
|-------|--------|----------------|
| **INGEST** | Load problem statement | - |
| **LOCALIZE** | Find relevant code | Localization (3-layer) |
| **PLAN** | Decompose into steps | - |
| **PATCH_CANDIDATES** | Generate patches | LLM + Patch Score |
| **TEST_STAGE** | Validate patch | Test Runner (4 stages) |
| **DIAGNOSE** | Analyze failures | Failure Triage |
| **MINIMIZE** | Shrink patch | Patch Minimizer |
| **FINALIZE** | Commit/PR | - |
| **DONE** | Complete | - |

## Usage

### Command Line

```bash
# Run with OpenAI GPT-4
python run_episode.py \
  --task-id test-001 \
  --problem "Fix AttributeError in dataclass init" \
  --repo-path /tmp/myrepo \
  --test-command "pytest tests/test_models.py" \
  --llm-provider openai \
  --llm-model gpt-4-turbo-preview

# Run with Anthropic Claude
python run_episode.py \
  --task-id test-002 \
  --problem "Fix import error" \
  --repo-path . \
  --test-command "python -m pytest" \
  --llm-provider anthropic \
  --llm-model claude-3-5-sonnet-20241022

# Run with DeepSeek (cost-effective)
python run_episode.py \
  --task-id test-003 \
  --problem "Fix type error" \
  --repo-path . \
  --llm-provider deepseek \
  --llm-model deepseek-chat

# Run with Docker isolation
python run_episode.py \
  --task-id test-004 \
  --problem "Fix security bug" \
  --repo-path /tmp/repo \
  --use-docker \
  --output results.json
```

### Python API

```python
from agent.orchestrator import run_orchestrated_episode

# Run complete episode
final_state = run_orchestrated_episode(
    task_id="django-12345",
    problem_statement="Fix AttributeError in model initialization",
    repo_path="/tmp/django",
    test_command="pytest tests/test_models.py",
    llm_provider="openai",
    llm_model="gpt-4-turbo-preview",
)

# Check results
print(f"Phase: {final_state.phase}")
print(f"Rounds: {final_state.budget.round_idx}")
print(f"Success: {final_state.notes.get('stop_reason') == 'finalized'}")
```

### Advanced Usage

```python
from agent.orchestrator import EpisodeOrchestrator
from agent.profiles import load_profile
from agent.types import AgentState, RepoFingerprint, BudgetState, Phase

# Load profile
profile = load_profile("profiles/swebench_lite.yaml")

# Initialize state
repo = RepoFingerprint(
    repo_id="test-001",
    commit_sha="HEAD",
    workdir="/tmp/repo",
    language="python",
)

budget = BudgetState(max_rounds=50)

state = AgentState(
    task_id="test-001",
    repo=repo,
    phase=Phase.INGEST,
    budget=budget,
    notes={"problem_statement": "Fix bug X"},
)

# Create orchestrator
orchestrator = EpisodeOrchestrator(
    profile=profile,
    repo_path="/tmp/repo",
    test_command="pytest",
    llm_provider="openai",
    llm_model="gpt-4-turbo-preview",
)

# Run episode
final_state = orchestrator.run(state)
```

## Configuration

### Environment Variables

```bash
# LLM API Keys
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export DEEPSEEK_API_KEY="sk-..."

# Optional: Custom API endpoints
export OPENAI_BASE_URL="https://api.openai.com/v1"
export ANTHROPIC_BASE_URL="https://api.anthropic.com"
```

### Profiles

Profiles control agent behavior and constraints:

**swebench_lite.yaml**:
```yaml
name: swebench_lite
max_rounds: 50
max_patch_attempts: 20
max_test_runs: 40
max_model_calls: 100
localization:
  use_trace: true
  use_ripgrep: true
  use_symbols: true
  use_embeddings: false
strategies:
  - direct_fix
  - test_driven
```

**swebench_verified.yaml**:
```yaml
name: swebench_verified
max_rounds: 100
max_patch_attempts: 40
max_test_runs: 80
max_model_calls: 200
localization:
  use_trace: true
  use_ripgrep: true
  use_symbols: true
  use_embeddings: true  # More expensive, more accurate
strategies:
  - ensemble  # Use all strategies
```

## Execution Flow

### 1. Episode Start
```
User → run_episode.py → EpisodeOrchestrator.__init__()
```
- Load profile
- Initialize LLM client
- Initialize components (localizer, patch generator, test runner)

### 2. Episode Loop
```
EpisodeOrchestrator.run() → agent.loop.run_episode()
```
- Loop until DONE or budget exhausted
- For each round:
  1. **Propose**: Generate next action based on phase
  2. **Gate**: Validate proposal (phase compatibility, budgets)
  3. **Execute**: Run action (localize, generate, test, etc.)
  4. **Advance**: Transition to next phase

### 3. Episode Complete
```
Final State → Save Results → Exit
```
- Return final `AgentState`
- Optionally save to JSON
- Exit with success/failure code

## Integration Points

### Localization → Patch Generation
```python
# Localization produces hits
hits = localize_issue(problem_statement, repo_path)

# Hits feed patch generation
request = PatchGenerationRequest(
    problem_statement=problem_statement,
    localization_hits=hits,
    ...
)
result = patch_generator.generate(request)
```

### Patch Generation → Scoring
```python
# Generate patches
candidates = patch_generator.generate(request).candidates

# Score patches
scores = score_patches(candidates, repo_path)

# Sort by score
sorted_patches = sorted(
    zip(candidates, scores),
    key=lambda x: x[1].total_score,
    reverse=True,
)
```

### Patch Application → Test Runner
```python
# Apply patch
apply_result = patch_applier.apply(patch)

if apply_result.success:
    # Run staged tests
    test_result = run_staged_tests(config)
    
    if test_result.validation_passed:
        # Patch is good!
        pass
```

### Test Failures → Triage
```python
# Tests failed
if not test_result.validation_passed:
    # Triage failures
    for failure in test_result.new_failures:
        diagnosis = triage_failure(
            test_id=failure.test_id,
            error_message=failure.message,
            traceback=failure.traceback,
        )
        
        # Use diagnosis to guide next attempt
        print(f"Root cause: {diagnosis.root_cause}")
        print(f"Suggested fix: {diagnosis.suggested_fix}")
```

## Metrics & Monitoring

### Episode Metrics
```python
# Budget tracking
state.budget.round_idx          # Rounds executed
state.budget.patch_attempts     # Patches attempted
state.budget.test_runs          # Test runs
state.budget.model_calls        # LLM calls

# Outcomes
state.phase                     # Final phase
state.notes["stop_reason"]      # Why stopped
state.touched_files             # Files modified
```

### LLM Metrics
```python
# From patch generation result
result.tokens_used              # Total tokens
result.generation_time          # Time (seconds)
result.total_generated          # Patches generated
result.errors                   # Generation errors
```

### Test Metrics
```python
# From staged test result
result.baseline_duration        # Baseline time
result.validation_duration      # Validation time
result.fixed_regressions        # Tests fixed
result.new_regressions          # Tests broken
```

## Error Handling

### LLM Failures
```python
try:
    result = llm_client.generate(prompt)
except Exception as e:
    # Fallback to mock generation
    logger.warning(f"LLM failed: {e}, using fallback")
    result = mock_generate(request)
```

### Test Failures
```python
# Captured in test result
test_result = run_staged_tests(config)

if not test_result.success:
    # Diagnose and retry
    diagnose_and_plan_retry(test_result)
```

### Patch Application Failures
```python
apply_result = patch_applier.apply(patch)

if not apply_result.success:
    # Automatic rollback
    logger.error(f"Patch failed: {apply_result.error}")
    # State restored automatically
```

## Performance

### Expected Timings
| Component | Time Range | Notes |
|-----------|-----------|-------|
| Localization | 1-5s | Fast (local search) |
| LLM Generation | 5-30s | Depends on model/load |
| Test Baseline | 10-60s | Depends on test suite |
| Test Validation | 5-30s | Subset of tests |
| Patch Minimization | 30-300s | O(n) test runs |

### Cost Estimates (per episode)
| Provider | Model | Cost per Episode |
|----------|-------|-----------------|
| OpenAI | GPT-4-turbo | $0.05 - $0.20 |
| Anthropic | Claude 3.5 | $0.03 - $0.15 |
| DeepSeek | deepseek-chat | $0.01 - $0.05 |

100 SWE-bench tasks:
- OpenAI: $5 - $20
- Anthropic: $3 - $15
- DeepSeek: $1 - $5

## Troubleshooting

### Problem: LLM API key not set
```bash
# Solution: Set environment variable
export OPENAI_API_KEY="sk-..."
```

### Problem: Tests not found
```bash
# Solution: Check test command
python run_episode.py \
  --test-command "python -m pytest tests/" \
  ...
```

### Problem: Docker permission denied
```bash
# Solution: Add user to docker group
sudo usermod -aG docker $USER
# Log out and back in
```

### Problem: Localization returns no hits
```
# Check problem statement quality
# Add more details: function names, error messages, stack traces
```

## Next Steps

1. **Add Memory/Outcomes DB**: Store episode results for learning
2. **Improve Planner**: Use past outcomes to guide strategy selection
3. **Add UI Backend Integration**: Connect UI to real execution
4. **Implement Role Separation**: Separate proposal generation from execution
5. **Run Full Evaluation**: Test on SWE-bench Lite (300 tasks)

## References

- **Episode Loop**: `agent/loop.py`
- **Orchestrator**: `agent/orchestrator.py`
- **CLI**: `run_episode.py`
- **Localization**: `localize/README.md`
- **LLM Integration**: `llm/README.md`
- **Test Runner**: `runner/tests.py`
- **Failure Triage**: `triage/failures.py`
- **Patch Processing**: `patch/README.md`

---

**Status**: Production Ready  
**Version**: 0.4.3  
**Last Updated**: 2026-01-30
