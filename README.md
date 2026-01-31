<div align="center">

# 🔐 RFSN Controller

### Serial Authority Gate for Autonomous Code Repair

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-1000%20passing-brightgreen.svg?style=for-the-badge)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.4.3-success.svg?style=for-the-badge)](CHANGELOG.md)

**A production-ready safety kernel + intelligent planner for autonomous code repair**

[Quick Start](#-quick-start) • [Architecture](#-architecture) • [Features](#-features) • [Documentation](#-documentation)

</div>

---

## 🎯 What is RFSN?

RFSN is a **two-layer autonomous repair system**:

1. **Safety Kernel** (Gate) - A deterministic, non-learning safety boundary
2. **Intelligent Planner** - A learning-enabled proposal generator subordinate to the gate

```
┌─────────────────────────────────────────────────────────────┐
│                     RFSN Controller                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Planner    │───>│   PlanGate   │───>│  Executor    │  │
│  │  (learning)  │    │ (no learning)│    │ (sandboxed)  │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│        ↑                    │                    │          │
│        └────────────────────┴────────────────────┘          │
│                    Outcome Feedback                          │
└─────────────────────────────────────────────────────────────┘
```

### Why This Architecture?

| Challenge | RFSN Solution |
|-----------|---------------|
| AI makes unsafe changes | **Hard safety gate** - blocks dangerous operations |
| Learning corrupts safety | **Gate never learns** - only proposals learn |
| Unpredictable execution | **Serial authority** - one action at a time |
| Low success rate | **Beam search** - explore multiple fixes in parallel |
| No memory of past fixes | **Outcome learning** - bias toward successful patterns |

---

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/dawsonblock/RFSN-GATE-CLEANED.git
cd RFSN-GATE-CLEANED/RFSN-CODE-GATE-main

# Install with all features
pip install -e '.[llm,dev]'

# Set API keys
export DEEPSEEK_API_KEY="sk-..."
export GEMINI_API_KEY="..."  # optional fallback
```

### Basic Usage

```bash
# Fix bugs in a repository
python -m rfsn_controller.cli \
    --repo https://github.com/user/repo \
    --test "pytest"

# With beam search (NEW!)
python -m rfsn_controller.cli \
    --repo ./my-project \
    --test "pytest" \
    --beam-search \
    --beam-width 3
```

### Python API

```python
from rfsn_controller.controller import run_repair
from rfsn_controller.config import ControllerConfig

config = ControllerConfig(
    repo_url="https://github.com/user/repo",
    test_cmd="pytest",
    beam_search_enabled=True,
    beam_width=3,
)

result = run_repair(config)
print(f"Fixed: {result.success}")
```

---

## 🏗️ Architecture

### Core Components

| Component | Purpose | Learning? |
|-----------|---------|-----------|
| **PlanGate** | Block unsafe operations | ❌ No |
| **PlannerV2** | Goal decomposition | ✅ Yes |
| **BeamSearcher** | Parallel hypothesis testing | ✅ Yes |
| **ActionOutcomeStore** | Remember what works | ✅ Yes |
| **GitRollbackManager** | Safe state restoration | ❌ No |

### Project Structure

```
rfsn_controller/
├── controller.py          # Main orchestration
├── config.py              # Configuration dataclasses
├── git_rollback.py        # Snapshot/restore for beam search
├── action_outcome_memory.py  # Outcome learning
├── gates/
│   └── plan_gate.py       # Safety enforcement (non-learning)
├── planner_v2/
│   ├── planner.py         # Goal decomposition
│   ├── beam_search.py     # Multi-step patch exploration
│   ├── memory_adapter.py  # Historical pattern retrieval
│   └── ...
├── llm/
│   ├── deepseek.py        # DeepSeek integration
│   ├── gemini.py          # Gemini integration
│   └── async_pool.py      # Parallel LLM calls
└── buildpacks/            # Multi-language support
```

---

## ✨ Features

### 🔐 Safety Kernel (Gate)

The gate is **deterministic, non-learning, and non-bypassable**:

```python
from rfsn_controller.gates import PlanGate

gate = PlanGate(config)
result = gate.validate_plan(plan)

# ✓ Allows: safe file edits, approved commands
# ✗ Blocks: shell injection, path traversal, dangerous ops
```

**Guarantees:**

- Command allowlists
- Path scope restrictions  
- Budget enforcement
- No side effects

### 🧠 Intelligent Planner

The planner **learns from outcomes** but is always subordinate to the gate:

```python
from rfsn_controller.planner_v2 import PlannerV2

planner = PlannerV2(memory_adapter=memory)
plan = planner.propose_plan(
    goal="Fix failing test_authentication",
    context={"language": "python", "test_cmd": "pytest"}
)
```

**Capabilities:**

- Goal decomposition into atomic steps
- Thompson Sampling for strategy selection
- Historical memory bias
- Failure fingerprinting

### 🔍 Beam Search (NEW!)

Explore multiple repair hypotheses in parallel:

```python
from rfsn_controller.planner_v2.beam_search import create_beam_searcher

searcher = create_beam_searcher(beam_width=3, max_depth=5)
result = searcher.search(
    repo_path="/path/to/repo",
    goal="Fix failing tests",
    generate_fn=my_patch_generator,
    evaluate_fn=my_test_runner,
)
```

**Features:**

- Git-based rollback for safe exploration
- Score-based candidate ranking
- Early termination on success
- Parallel candidate evaluation

### 📚 Outcome Learning

Remember what works and bias toward successful patterns:

```python
from rfsn_controller.action_outcome_memory import ActionOutcomeStore

store = ActionOutcomeStore("outcomes.db")

# Record outcome
store.record(
    context=context,
    action_type="patch",
    outcome="success",
    score=0.95,
)

# Query priors for similar context
priors = store.query_action_priors(context)
```

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [PRODUCTION_GUIDE.md](docs/PRODUCTION_GUIDE.md) | Deployment and configuration |
| [ARCHITECTURE.md](rfsn_controller/planner_v2/ARCHITECTURE.md) | Planner architecture |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [SECURITY.md](SECURITY.md) | Security policy |

### Tests

```bash
# Run all tests (1000 tests)
pytest tests/ -q

# Run specific module
pytest tests/test_beam_search.py -v

# With coverage
pytest tests/ --cov=rfsn_controller
```

---

## 🔧 Configuration

### CLI Options

```bash
--repo URL              # Repository to repair
--test CMD              # Test command
--beam-search           # Enable beam search
--beam-width N          # Candidates per step (default: 3)
--beam-depth N          # Max search depth (default: 5)
--planner-mode v5       # Planner version
--model deepseek-chat   # LLM model
```

### Environment Variables

```bash
export DEEPSEEK_API_KEY="sk-..."
export GEMINI_API_KEY="..."
export RFSN_CACHE_DIR="~/.rfsn/cache"
export RFSN_LOG_LEVEL="INFO"
```

---

## 📊 Stats

- **1000 tests** passing
- **8 languages** supported via buildpacks
- **2 LLM providers** (DeepSeek, Gemini)
- **3-tier caching** (memory, disk, semantic)

---

## 📄 License

MIT License - see [LICENSE](LICENSE)

---

<div align="center">

**Built for safety. Designed to learn.**

</div>
