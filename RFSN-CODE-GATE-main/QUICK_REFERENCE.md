# 🚀 RFSN v0.4.0 Quick Reference

## Installation

```bash
# Core dependencies
pip install aiosqlite pytest-asyncio

# Optional (semantic localization)
pip install sentence-transformers faiss-cpu

# External tools (optional, for better performance)
# macOS: brew install ripgrep universal-ctags
# Ubuntu: apt-get install ripgrep universal-ctags
```

## Quick Start

### 1. Run Evaluation on SWE-bench

```python
import asyncio
from eval.run import EvalConfig, run_eval

async def main():
    config = EvalConfig(
        dataset="swebench_lite",
        max_tasks=5,
        profile_name="swebench_lite",
        max_time_per_task=1800,
    )
    results = await run_eval(config)

asyncio.run(main())
```

### 2. Localize a Bug

```python
from pathlib import Path
from localize import localize_issue

hits = localize_issue(
    problem_statement="Function returns None instead of expected value",
    repo_dir=Path("/path/to/repo"),
    traceback="File 'src/module.py', line 42...",
)

for hit in hits[:5]:
    print(f"{hit.file_path}:{hit.line_start} (score: {hit.score:.2f})")
```

### 3. Generate Patches

```python
from patch.gen import generate_patches
from patch.types import PatchStrategy

patches = generate_patches(
    problem_statement="Fix the bug...",
    repo_dir=Path("/path/to/repo"),
    localization_hits=hits,
    strategy=PatchStrategy.ENSEMBLE,
    max_patches=5,
)
```

## Module Structure

```
eval/
├── __init__.py
├── run.py           # Main eval loop, EvalRunner, EvalConfig
└── swebench.py      # Dataset loading, SWEBenchTask

localize/
├── __init__.py      # Multi-layer localization API
├── types.py         # LocalizationHit
├── trace.py         # Layer 1: Stack trace parsing
├── ripgrep.py       # Layer 2a: Lexical search
├── symbol_index.py  # Layer 2b: Symbol/import graph
└── embeddings.py    # Layer 3: Semantic search (optional)

patch/
├── __init__.py
├── types.py         # Patch, PatchCandidate, strategies
└── gen.py           # Patch generation with multiple strategies

gate_ext/
├── __init__.py      # gate_with_profile()
├── policy_phase.py  # Phase validation
├── policy_files.py  # File limits
├── policy_tests.py  # Test coverage
└── policy_diff.py   # Diff size

memory/
└── log.py          # append_event() for outcome logging

agent/
├── types.py        # AgentState, Phase, Proposal
├── profiles.py     # load_profile()
└── loop.py         # run_episode() [needs integration]

rfsn_controller/
├── async_multi_tier_cache.py  # Async DB
├── file_cache.py              # LRU file cache
├── early_stop_optimizer.py    # Fast-fail
└── batch_file_ops.py          # Batched I/O
```

## Key APIs

### Evaluation
- `EvalRunner.run_task(task)`: Run single SWE-bench task
- `EvalRunner.run_batch(tasks)`: Run multiple tasks
- `run_eval(config)`: High-level evaluation API

### Localization
- `localize_issue(problem, repo_dir, traceback)`: Multi-layer localization
- `MultiLayerLocalizer`: Full control over layers
- `RipgrepConfig`, `EmbeddingConfig`: Layer-specific configuration

### Patch Generation
- `generate_patches(problem, repo_dir, hits)`: Generate patches
- `PatchGenerator`: Full control over generation
- Strategies: DIRECT_FIX, TEST_DRIVEN, HYPOTHESIS, INCREMENTAL, ENSEMBLE

### Gate System
- `gate_with_profile(profile, state, proposal)`: Validate proposal
- Returns: `GateDecision(accept, reason, constraints)`

### Memory
- `append_event(state, event)`: Log outcome event

## Testing

```bash
# Run all tests
pytest tests/

# Run specific test suite
pytest tests/test_async_multi_tier_cache.py -v
pytest tests/test_integration.py -v
pytest tests/test_optimizations.py -v

# Run with coverage
pytest tests/ --cov=rfsn_controller --cov=eval --cov=localize --cov=patch
```

## Configuration Files

### Profile (e.g., profiles/swebench_lite.yaml)
```yaml
name: swebench_lite
max_steps: 50
max_time: 1800
max_patches: 20
strategies:
  - DIRECT_FIX
  - TEST_DRIVEN
  - ENSEMBLE
```

### Localization Config
```python
LocalizationConfig(
    use_trace=True,
    use_ripgrep=True,
    use_embeddings=False,  # Optional
    use_symbols=True,
    max_results=50,
    score_weights={
        "trace": 1.0,
        "symbol": 0.9,
        "ripgrep": 0.7,
        "embedding": 0.8,
    }
)
```

## Architecture Flow

```
eval/run.py
    ↓
┌─────────────────────┐
│ Load SWE-bench task │
└─────────────────────┘
    ↓
┌─────────────────────┐
│ agent/loop.py       │
│ run_episode()       │
└─────────────────────┘
    ↓
┌─────────────────────┐
│ LOCALIZE            │
│ localize_issue()    │
└─────────────────────┘
    ↓
┌─────────────────────┐
│ PATCH               │
│ generate_patches()  │
└─────────────────────┘
    ↓
┌─────────────────────┐
│ GATE                │
│ gate_with_profile() │
└─────────────────────┘
    ↓
┌─────────────────────┐
│ TEST [pending]      │
│ runner/stages.py    │
└─────────────────────┘
    ↓
┌─────────────────────┐
│ STORE               │
│ append_event()      │
└─────────────────────┘
```

## Performance Tips

1. **Use file cache**: Automatically enabled in `file_cache.py`
2. **Enable early stop**: Use `early_stop_optimizer.py` for fast-fail
3. **Batch operations**: Use `batch_file_ops.py` for multiple files
4. **Cache embeddings**: Provide `cache_path` to `EmbeddingLocalizer`
5. **Limit results**: Set `max_results` in `LocalizationConfig`

## Troubleshooting

### "Module not found" errors
```bash
# Ensure you're in the right directory
cd /home/user/webapp/RFSN-CODE-GATE-main

# Run with module syntax
python -m eval.run
```

### Localization returns no results
- Check ripgrep is installed: `rg --version`
- Enable more layers: `use_embeddings=True`
- Lower `min_similarity` threshold

### Patch generation returns empty
- Verify localization found hits
- Check LLM integration (currently placeholder)
- Ensure files exist and are readable

## Next Steps (Priority Order)

1. **Wire episode loop** (2-3 days)
   - Connect localize → patch → test cycle
   - Implement phase transitions

2. **Implement staged test runner** (2 days)
   - Fast-fail pipeline
   - Artifact capture

3. **Add LLM integration** (1-2 days)
   - Real patch generation
   - Prompt engineering

4. **Patch scoring** (1 day)
   - Static analysis
   - Test delta
   - Diff risk

5. **Memory layer** (1 day)
   - SQLite outcomes DB
   - Event logging

## Success Metrics

- ✅ MVP: Components working independently
- 🎯 Production: 10% pass rate on SWE-bench Lite
- 🚀 Killer: 50% pass rate on SWE-bench Lite

## Resources

- **Documentation**: `SWE_BENCH_IMPLEMENTATION_STATUS.md`
- **Summary**: `COMPLETE_V04_SUMMARY.md`
- **Tests**: `tests/test_*.py`
- **Commit History**: `git log --oneline`

---

**Version**: v0.4.0-dev  
**Status**: Foundation complete ✅  
**Next**: LLM integration + episode loop wiring
