# RFSN-CODE-GATE File Inventory

## Extracted Files Location

**Base Directory:** `/home/user/webapp/RFSN-CODE-GATE-main/`

## Analysis Documents (Created)

1. **RFSN_CODE_GATE_ANALYSIS.md** (988 lines, 25KB)
   - Comprehensive deep analysis report
   - Component breakdown
   - Architecture details
   - Security analysis
   - Usage patterns

2. **QUICK_SUMMARY.md**
   - Quick reference guide
   - Key statistics
   - Usage examples
   - Performance metrics

3. **FILE_INVENTORY.md** (this file)
   - File structure overview
   - Module counts
   - Key file locations

## Project Structure Summary

### Root Level (11 items)
```
RFSN-CODE-GATE-main/
├── rfsn_controller/      (Main controller - 70+ files)
├── cgw_ssl_guard/        (CGW system - 24 files)
├── tests/                (Test suite - 41 files)
├── docs/                 (Documentation - 7 files)
├── examples/             (Demo code - 3 Python files + 3 repos)
├── scripts/              (Utility scripts)
├── .github/              (CI/CD workflows - 3 YAML files)
├── bugsinpy_demo/        (BugsinPy integration)
├── quickbugs_demo/       (QuickBugs integration)
├── README.md             (421 lines)
├── SECURITY.md           (138 lines)
├── CHANGELOG.md          (Production upgrade notes)
├── LICENSE               (MIT)
├── pyproject.toml        (Project metadata)
├── requirements.txt      (Core dependencies)
├── uv.lock               (UV lockfile - 288KB)
├── Dockerfile            (Container definition)
└── docker-compose.yml    (Docker orchestration)
```

### Core Modules (`rfsn_controller/`) - 70+ Files

**Key Files:**
- `controller.py` (2,634 lines) - Main repair loop
- `controller_loop.py` (244 lines) - Serial execution
- `cli.py` - CLI entry point
- `config.py` - Configuration management
- `sandbox.py` - Sandbox operations

**Subdirectories:**
- `gates/` - Safety gates (1 module)
- `learning/` - Learning system (4 modules)
- `llm/` - LLM integration (4 modules)
- `buildpacks/` - Language support (9 modules)
- `planner_v2/` - Hierarchical planner (25+ modules)
- `qa/` - QA system

**Optimization Modules:**
- `docker_pool.py` - Container warm pool
- `semantic_cache.py` - Embedding cache
- `prompt_compression.py` - Token reduction
- `streaming_validator.py` - Early exit
- `action_store.py` - Outcome memory
- `speculative_exec.py` - Precomputation
- `incremental_testing.py` - Test selection
- `parallel.py` - Parallel evaluation

**Security Modules:**
- `shell_scanner.py` - Static analysis
- `command_allowlist.py` - Command validation
- `apt_whitelist.py` - Package validation
- `security_hardening.py` - Hardening
- `url_validation.py` - URL safety
- `signing.py` - Artifact signing
- `patch_hygiene.py` - Patch validation

### CGW System (`cgw_ssl_guard/`) - 24 Files

**Core:**
- `thalamic_gate.py` (135 lines) - Gate arbitration
- `event_bus.py` - Event system
- `monitors.py` - Monitoring
- `runtime.py` - Runtime management
- `types.py` - Type definitions
- `cgw_state.py` - State management

**Coding Agent (`coding_agent/`):**
- `coding_agent_runtime.py` - Agent runtime
- `executor.py` - Execution engine
- `llm_integration.py` - LLM interface
- `llm_adapter.py` - LLM adapters
- `streaming_llm.py` - Streaming support
- `docker_sandbox.py` - Sandbox integration
- `action_memory.py` - Action tracking
- `action_types.py` - Action definitions
- `cgw_bandit.py` - Bandit algorithm
- `event_store.py` - Event persistence
- `proposal_generators.py` - Proposal generation
- `config.py` - Configuration
- `cli.py` - CLI interface
- `integrated_runtime.py` - Integrated runtime

**Simulation (`coding_agent/sim/`):**
- `simulation_gate.py` - Simulation mode

### Hierarchical Planner v2 (`rfsn_controller/planner_v2/`) - 25+ Files

**Core Planning:**
- `planner.py` (29,177 lines) - Main planner
- `schema.py` (15,965 lines) - Data schemas
- `lifecycle.py` (4,846 lines) - State machine
- `controller_adapter.py` (19,915 lines) - Controller interface
- `llm_decomposer.py` (15,946 lines) - AI decomposition
- `revision_strategies.py` (12,534 lines) - Failure handling
- `tool_registry.py` (14,378 lines) - Tool catalog

**Governance (`governance/`):**
- `validator.py` - Plan validation
- `budget.py` - Resource limits
- `halt_conditions.py` - Halt logic
- `sanitizer.py` - Input sanitization
- `risk_routing.py` - Risk assessment

**Supporting:**
- `memory_adapter.py` - Memory integration
- `parallel_executor.py` - Parallel execution
- `plan_cache.py` - Caching
- `metrics.py` - Metrics tracking
- `artifact_log.py` - Audit trail
- `replay.py` - Deterministic replay
- `verification_hooks.py` - Verification
- `fingerprint.py` - Fingerprinting
- `failure_classifier.py` - Classification
- `model_selector.py` - Model selection
- `qa_integration.py` - QA system
- `regression_firewall.py` - Anti-regression
- `semantic_guardrails.py` - Guardrails
- `overrides.py` - Configuration overrides
- `cli.py` - CLI interface

**Documentation:**
- `ARCHITECTURE.md` (327 lines) - Architecture spec
- `plan.schema.json` (12,340 lines) - JSON schema

### Learning System (`rfsn_controller/learning/`) - 4 Files

- `learned_strategy_selector.py` (8,053 lines) - Main selector
- `strategy_bandit.py` (9,271 lines) - Thompson Sampling
- `fingerprint.py` (7,379 lines) - Failure classification
- `quarantine.py` (8,734 lines) - Anti-regression

### LLM Integration (`rfsn_controller/llm/`) - 4 Files

- `ensemble.py` (11,180 lines) - Multi-model coordination
- `deepseek.py` (18,293 lines) - DeepSeek client
- `gemini.py` (17,821 lines) - Gemini client
- `async_client.py` (16,949 lines) - Async operations

### Buildpacks (`rfsn_controller/buildpacks/`) - 9 Files

- `base.py` (6,873 lines) - Base buildpack
- `python_pack.py` (13,126 lines) - Python
- `node_pack.py` (5,865 lines) - Node.js
- `java_pack.py` (5,876 lines) - Java
- `go_pack.py` (4,464 lines) - Go
- `rust_pack.py` (4,452 lines) - Rust
- `cpp_pack.py` (4,927 lines) - C/C++
- `dotnet_pack.py` (4,621 lines) - .NET
- `polyrepo_pack.py` (5,702 lines) - Multi-language

### Safety Gates (`rfsn_controller/gates/`) - 1 File

- `plan_gate.py` (14,783 lines) - Hard safety gate

### Test Suite (`tests/`) - 41 Files

**Structure:**
```
tests/
├── cgw/                        (CGW tests)
├── rfsn_controller/            (Controller tests)
├── security/                   (Security tests)
├── unit/                       (Unit tests)
├── fixtures/                   (Test data)
│   └── tiny_repo/
├── golden_plans/               (Reference plans - JSON)
│   ├── repair_single_test.json
│   ├── refactor_module.json
│   └── add_feature.json
└── test_*.py                   (41 test files)
```

**Major Test Files:**
- `test_no_shell.py` (13,038 lines) - Shell security
- `test_events.py` (34,126 lines) - Event system
- `test_budget_gates.py` (36,740 lines) - Budget
- `test_contracts.py` (35,171 lines) - Contracts
- `test_shell_scanner.py` (18,788 lines) - Scanner
- `test_planner_v2.py` (18,361 lines) - Planner
- `test_planner_v2_governance.py` (17,527 lines) - Governance
- `conftest.py` (8,319 lines) - Pytest config

### Documentation (`docs/`) - 7 Files

- `USAGE_GUIDE.md` (804 lines) - Usage documentation
- `CGW_CODING_AGENT.md` - CGW architecture
- `SECURITY.md` - Security model
- `VALIDATION_REPORT.md` - Validation results
- `ARCHITECTURE.md` - Architecture overview
- `E2B_USE_CASES.md` - E2B integration
- `FEATURE_MODE.md` - Feature mode docs
- `DOCKER_SANDBOX.md` - Docker sandbox
- `ARTIFACTS_AND_SIGNING.md` - Artifact signing

### Examples (`examples/`) - 6 Items

**Python Scripts:**
- `demo_bugsinpy.py` (8,868 lines) - BugsinPy demo
- `demo_quixbugs.py` (7,028 lines) - QuixBugs demo
- `run_fix_demo.py` (7,943 lines) - Fix demo

**Test Repositories:**
- `simple_bugs_repo/` - Simple test cases
- `hard_bugs_repo/` - Complex test cases
- `test_fix_repo/` - Fix validation

**Documentation:**
- `README.md` (963 lines) - Examples guide

### CI/CD (`.github/workflows/`) - 3 Files

- `ci.yml` - Continuous integration
- `rfsn_autofix.yml` - Auto-fix workflow
- `rfsn_open_pr.yml` - PR creation workflow

## File Type Distribution

- **Python files:** 206 files (59,648 lines total)
- **Markdown docs:** 15+ files
- **YAML configs:** 4 files (workflows + docker-compose)
- **JSON schemas:** 4 files (golden plans + schemas)
- **Configuration:** pyproject.toml, requirements.txt, Dockerfile

## Key Configuration Files

1. **pyproject.toml** - Project metadata, dependencies, build config
2. **requirements.txt** - Core dependencies (minimal)
3. **Dockerfile** - Container definition
4. **docker-compose.yml** - Service orchestration
5. **profiles.default.yaml** - Default profiles
6. **profiles.schema.json** - Profile JSON schema
7. **plan.schema.json** - Plan JSON schema (12KB+)
8. **uv.lock** - UV lockfile (288KB)

## Notable Large Files

1. `uv.lock` - 288KB (lockfile)
2. `planner.py` - 29,177 lines
3. `controller_adapter.py` - 19,915 lines
4. `deepseek.py` - 18,293 lines
5. `gemini.py` - 17,821 lines
6. `async_client.py` - 16,949 lines
7. `llm_decomposer.py` - 15,946 lines
8. `schema.py` - 15,965 lines
9. `plan_gate.py` - 14,783 lines
10. `tool_registry.py` - 14,378 lines

## Access Paths

All files are accessible under:
```
/home/user/webapp/RFSN-CODE-GATE-main/
```

Examples:
- Main controller: `/home/user/webapp/RFSN-CODE-GATE-main/rfsn_controller/controller.py`
- CGW gate: `/home/user/webapp/RFSN-CODE-GATE-main/cgw_ssl_guard/thalamic_gate.py`
- Plan gate: `/home/user/webapp/RFSN-CODE-GATE-main/rfsn_controller/gates/plan_gate.py`
- Planner: `/home/user/webapp/RFSN-CODE-GATE-main/rfsn_controller/planner_v2/planner.py`

## Total Project Size

- **Python code:** 59,648 lines
- **Total files:** 206 Python + 30+ docs/configs
- **Documentation:** 7 comprehensive guides
- **Tests:** 102+ passing tests
- **Disk usage:** ~1MB Python code + 288KB lockfile

---

*Inventory generated: 2026-01-29*
