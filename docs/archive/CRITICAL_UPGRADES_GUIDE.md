# RFSN Controller v0.3.0 - Critical Upgrades Implementation Guide

**Date:** January 29, 2026  
**Status:** 🚧 IN PROGRESS  
**Priority:** 🔴 HIGH PRIORITY ITEMS

---

## 🎯 Overview

This document provides detailed implementation plans for the remaining critical upgrades identified in the deep analysis. These upgrades will deliver significant improvements in solve rate, performance, and maintainability.

---

## 🔴 HIGH PRIORITY UPGRADES

### 1. Planner v5 Integration ⚠️ CRITICAL

**Status:** Code exists but NOT wired to main controller  
**Impact:** Missing ~5-10% solve rate improvement  
**Effort:** 2-3 days  

#### Current State
- ✅ Planner v5 code exists in `rfsn_controller/planner_v5/`
- ✅ MetaPlanner, StateTracker, Scoring implemented
- ✅ Adapter created in `rfsn_controller/planner_v5_adapter.py`
- ❌ NOT connected to main controller
- ❌ CLI flag missing (`--planner v5`)

#### Files to Modify

**1. `rfsn_controller/cli.py`**
```python
# Add to argument parser (line ~343)
"--planner-mode",
choices=["off", "v2", "dag", "v5"],  # ADD v5
help="Planner mode: off|v2|dag|v5 (v5 is latest with state tracking)"
```

**2. `rfsn_controller/controller.py`** (2,634 lines - needs careful integration)

Add imports:
```python
from .planner_v5_adapter import PlannerV5Adapter
from .planner_v5.meta_planner import MetaPlanner, PlanningPhase
```

Add to controller initialization:
```python
def __init__(self, ...):
    # ... existing code ...
    
    # Initialize Planner v5 if requested
    if planner_mode == "v5":
        self.planner_v5 = PlannerV5Adapter(
            enable_learning=True,
            enable_state_tracking=True
        )
        self.use_planner_v5 = True
    else:
        self.planner_v5 = None
        self.use_planner_v5 = False
```

Add planning method:
```python
async def _plan_with_v5(self, issue_text: str, failing_tests: list[str]) -> dict:
    """Use Planner v5 for intelligent planning."""
    if not self.planner_v5:
        raise ValueError("Planner v5 not initialized")
    
    plan = await self.planner_v5.create_plan(
        repo_url=self.repo_url,
        issue_text=issue_text,
        failing_tests=failing_tests,
        traceback=self._get_traceback()
    )
    
    return plan
```

Add feedback loop:
```python
async def _record_outcome_v5(self, patch_result: PatchResult):
    """Record patch outcome for Planner v5 learning."""
    if not self.planner_v5:
        return
    
    await self.planner_v5.record_outcome(
        patch_id=patch_result.patch_id,
        success=patch_result.tests_passed,
        test_output=patch_result.test_output
    )
```

**3. `rfsn_controller/controller_loop.py`**

Update main loop to use v5:
```python
async def run_controller_loop(controller):
    """Main controller loop with Planner v5 support."""
    
    if controller.use_planner_v5:
        # Use v5 planning
        plan = await controller._plan_with_v5(
            issue_text=controller.issue_text,
            failing_tests=controller.failing_tests
        )
        
        # Execute plan phases
        for phase in plan.phases:
            result = await controller._execute_phase(phase)
            await controller._record_outcome_v5(result)
    else:
        # Fall back to v2/dag planning
        # ... existing code ...
```

#### Testing Checklist
- [ ] Unit tests for v5 adapter integration
- [ ] Integration test: v5 vs v2 solve rate comparison
- [ ] Regression test: Ensure v2 still works
- [ ] Performance test: v5 planning overhead
- [ ] End-to-end test: Full repair cycle with v5

#### Expected Outcome
- +5-10% solve rate improvement
- Better state tracking across attempts
- Adaptive strategy selection
- Hypothesis-driven debugging

---

### 2. Async Database Operations ⚠️ PERFORMANCE BLOCKER

**Status:** Still using synchronous sqlite3  
**Impact:** I/O blocking reduces throughput  
**Effort:** 3-4 days  
**Expected Gain:** +15-25% performance  

#### Current State
- ✅ aiosqlite already in dependencies
- ✅ AsyncConnectionPool created in `rfsn_controller/async_db.py`
- ✅ AsyncCache wrapper created
- ❌ multi_tier_cache.py still using sqlite3
- ❌ connection_pool.py is synchronous
- ❌ No async context managers

#### Files to Modify

**1. `rfsn_controller/multi_tier_cache.py`**

Current (synchronous):
```python
import sqlite3

class DiskCache:
    def get(self, key):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM cache WHERE key = ?", (key,))
        result = cursor.fetchone()
        conn.close()
        return result
```

New (async):
```python
from .async_db import AsyncConnectionPool

class DiskCache:
    def __init__(self, db_path, pool: AsyncConnectionPool):
        self.pool = pool
    
    async def get(self, key):
        results = await self.pool.execute(
            "SELECT value FROM cache WHERE key = ?",
            (key,)
        )
        return results[0] if results else None
```

**2. Update all cache callers to use async/await**

Example conversion:
```python
# Before
value = cache.get(key)
if value is None:
    value = expensive_operation()
    cache.set(key, value)

# After
value = await cache.get(key)
if value is None:
    value = await expensive_operation()
    await cache.set(key, value)
```

**3. Create async context manager for transactions**
```python
@asynccontextmanager
async def transaction(pool: AsyncConnectionPool):
    """Async transaction context manager."""
    async with pool.acquire() as conn:
        try:
            yield conn
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise
```

#### Migration Strategy

**Phase 1: Create async versions alongside sync**
- Keep existing sync code working
- Add new async methods with `_async` suffix
- Test async methods in isolation

**Phase 2: Convert callers one by one**
- Start with non-critical paths
- Add async/await to controller methods
- Update tests to use pytest-asyncio

**Phase 3: Remove sync code**
- Once all callers converted, remove sync methods
- Update connection_pool.py to AsyncConnectionPool
- Final performance benchmarks

#### Testing Checklist
- [ ] Async connection pool stress test (1000+ concurrent ops)
- [ ] Cache hit/miss rates unchanged
- [ ] Performance benchmark: Before vs after
- [ ] Memory usage: Check for connection leaks
- [ ] Error handling: Timeout, deadlock scenarios

#### Expected Outcome
- +15-25% throughput on cache-heavy workloads
- No I/O blocking in event loop
- Better concurrency under load
- Cleaner async/await code

---

### 3. Controller Decomposition ⚠️ TECHNICAL DEBT

**Status:** controller.py is 2,634 lines (monolithic)  
**Impact:** Hard to maintain, test, and extend  
**Effort:** 5-7 days  
**Target:** Reduce to <1,500 lines  

#### Current State
- ✅ PatchManager extracted to `rfsn_controller/patch_manager.py`
- ❌ VerificationManager not extracted
- ❌ StrategyExecutor not extracted
- ❌ Controller still monolithic

#### Decomposition Plan

**Extract 1: VerificationManager**
```python
class VerificationManager:
    """
    Manages test execution and verification workflow.
    
    Responsibilities:
    - Running tests in isolation
    - Collecting test output
    - Determining pass/fail
    - Tracking test execution metrics
    """
    
    async def verify_patch(
        self,
        patch: Patch,
        test_command: list[str],
        worktree: str
    ) -> VerificationResult:
        """Run tests and verify patch correctness."""
        pass
```

**Extract 2: StrategyExecutor**
```python
class StrategyExecutor:
    """
    Executes repair strategies based on planner decisions.
    
    Responsibilities:
    - Strategy selection
    - Step execution
    - Progress tracking
    - Rollback on failure
    """
    
    async def execute_strategy(
        self,
        strategy: RepairStrategy,
        context: ExecutionContext
    ) -> StrategyResult:
        """Execute a repair strategy."""
        pass
```

**Extract 3: FeedbackCollector**
```python
class FeedbackCollector:
    """
    Collects and processes feedback from repair attempts.
    
    Responsibilities:
    - Outcome recording
    - Learning data collection
    - Metrics aggregation
    - Evidence management
    """
    
    async def record_outcome(
        self,
        attempt: RepairAttempt,
        result: RepairResult
    ):
        """Record repair attempt outcome."""
        pass
```

**New Controller Structure** (<1,500 lines):
```python
class Controller:
    """
    Orchestrates the repair process.
    
    Delegates to:
    - PatchManager: Patch application
    - VerificationManager: Test execution
    - StrategyExecutor: Strategy execution
    - FeedbackCollector: Outcome tracking
    - Planner v5: Planning decisions
    """
    
    def __init__(self, ...):
        self.patch_manager = PatchManager(...)
        self.verifier = VerificationManager(...)
        self.executor = StrategyExecutor(...)
        self.feedback = FeedbackCollector(...)
        self.planner = PlannerV5Adapter(...)
    
    async def repair(self, repo_url: str, issue_text: str):
        """High-level repair orchestration."""
        # 1. Plan
        plan = await self.planner.create_plan(repo_url, issue_text)
        
        # 2. Execute
        for strategy in plan.strategies:
            result = await self.executor.execute_strategy(strategy)
            
            if result.patches:
                # 3. Apply patches
                for patch in result.patches:
                    patch_result = await self.patch_manager.apply_and_test(patch)
                    
                    # 4. Verify
                    if patch_result.applied:
                        verify_result = await self.verifier.verify_patch(patch_result)
                        
                        # 5. Record
                        await self.feedback.record_outcome(patch, verify_result)
                        
                        if verify_result.success:
                            return verify_result
        
        return FailureResult("No successful patches found")
```

#### Refactoring Steps

1. **Week 1: Extract PatchManager** ✅ DONE
2. **Week 2: Extract VerificationManager**
   - Move test execution logic
   - Add comprehensive tests
   - Update controller to use it
3. **Week 3: Extract StrategyExecutor**
   - Move strategy execution logic
   - Add strategy registry
   - Update controller to use it
4. **Week 4: Extract FeedbackCollector**
   - Move outcome recording
   - Integrate with evidence manager
   - Final controller simplification

#### Testing Checklist
- [ ] Each extracted component has 90%+ test coverage
- [ ] Integration tests for component interactions
- [ ] Performance unchanged (or improved)
- [ ] All existing tests still pass
- [ ] Controller.py < 1,500 lines

#### Expected Outcome
- Reduced complexity (easier to understand)
- Better testability (isolated components)
- Improved maintainability (clear boundaries)
- Faster development (parallel work possible)
- Lower bug rate (smaller surface area)

---

## 🟡 MEDIUM PRIORITY UPGRADES

### 4. Semantic Search / RAG Implementation

**Status:** Not implemented  
**Impact:** Missing +10-15% solve rate  
**Effort:** 1-2 weeks  

#### Implementation Plan

**File: `rfsn_controller/semantic_search.py`**
```python
from sentence_transformers import SentenceTransformer
import faiss

class SemanticCodeSearch:
    """
    Vector-based semantic search for code.
    
    Uses sentence-transformers for embeddings and FAISS for
    fast similarity search across large codebases.
    """
    
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.code_chunks = []
    
    async def index_codebase(self, repo_path: str):
        """Build vector index of codebase."""
        # Extract code chunks
        chunks = await self._extract_chunks(repo_path)
        
        # Generate embeddings
        embeddings = self.model.encode([c.text for c in chunks])
        
        # Build FAISS index
        self.index = faiss.IndexFlatL2(embeddings.shape[1])
        self.index.add(embeddings)
        self.code_chunks = chunks
    
    async def search(self, query: str, top_k: int = 5) -> list[CodeChunk]:
        """Find most relevant code chunks for query."""
        query_embedding = self.model.encode([query])
        distances, indices = self.index.search(query_embedding, top_k)
        return [self.code_chunks[i] for i in indices[0]]
```

**RAG Integration:**
```python
async def generate_patch_with_rag(
    issue_text: str,
    semantic_search: SemanticCodeSearch
) -> str:
    """Generate patch using RAG (Retrieval-Augmented Generation)."""
    
    # 1. Find relevant code
    relevant_code = await semantic_search.search(issue_text, top_k=5)
    
    # 2. Build context
    context = "\\n\\n".join([c.text for c in relevant_code])
    
    # 3. Generate patch with LLM
    prompt = f"""
    Issue: {issue_text}
    
    Relevant Code:
    {context}
    
    Generate a patch to fix this issue:
    """
    
    patch = await llm.generate(prompt)
    return patch
```

#### Expected Outcome
- +10-15% solve rate on large codebases
- Better context awareness
- More targeted patches
- Reduced LLM token usage (focused context)

---

### 5. Enhanced Buildpacks

**Status:** Missing modern Python tools, mobile frameworks  
**Effort:** 3-5 days per buildpack  

#### Poetry Buildpack

**File: `rfsn_controller/buildpacks/poetry_pack.py`**
```python
class PoetryBuildpack(Buildpack):
    """Support for Python projects using Poetry."""
    
    def detect(self, ctx: BuildpackContext) -> Optional[DetectResult]:
        if "pyproject.toml" in ctx.repo_tree:
            # Check if using Poetry
            pyproject = self._read_file(ctx, "pyproject.toml")
            if "[tool.poetry]" in pyproject:
                return DetectResult(
                    buildpack_type="poetry",
                    confidence=0.95
                )
        return None
    
    def install_plan(self, ctx) -> list[Step]:
        return [
            Step(argv=["poetry", "install"], description="Install dependencies")
        ]
    
    def test_plan(self, ctx) -> TestPlan:
        return TestPlan(
            argv=["poetry", "run", "pytest"],
            description="Run tests with Poetry"
        )
```

#### React Native Buildpack

**File: `rfsn_controller/buildpacks/react_native_pack.py`**
```python
class ReactNativeBuildpack(Buildpack):
    """Support for React Native mobile apps."""
    
    def detect(self, ctx) -> Optional[DetectResult]:
        if "package.json" in ctx.repo_tree:
            pkg = json.loads(self._read_file(ctx, "package.json"))
            deps = pkg.get("dependencies", {})
            if "react-native" in deps:
                return DetectResult(
                    buildpack_type="react-native",
                    confidence=0.9
                )
        return None
    
    def install_plan(self, ctx) -> list[Step]:
        return [
            Step(argv=["npm", "install"], description="Install dependencies"),
            Step(argv=["npx", "pod-install"], description="Install iOS pods")
        ]
    
    def test_plan(self, ctx) -> TestPlan:
        return TestPlan(
            argv=["npm", "test"],
            description="Run React Native tests"
        )
```

---

## 📋 Implementation Checklist

### This Week
- [x] Create PatchManager module
- [x] Create AsyncConnectionPool
- [ ] Wire Planner v5 to controller
- [ ] Add --planner v5 CLI flag
- [ ] Integration tests for v5

### Next Week
- [ ] Migrate multi_tier_cache to async
- [ ] Update connection_pool to async
- [ ] Add async context managers
- [ ] Performance benchmarks

### This Month
- [ ] Extract VerificationManager
- [ ] Extract StrategyExecutor
- [ ] Extract FeedbackCollector
- [ ] Controller < 1,500 lines

### This Quarter
- [ ] Implement semantic search
- [ ] Add Poetry buildpack
- [ ] Add React Native buildpack
- [ ] Add Flutter buildpack
- [ ] Replay debugging tool

---

## 🎯 Success Metrics

| Upgrade | Metric | Target | Current |
|---------|--------|--------|---------|
| Planner v5 | Solve Rate | +5-10% | Baseline |
| Async DB | Throughput | +15-25% | Baseline |
| Decomposition | Lines of Code | <1,500 | 2,634 |
| Semantic Search | Solve Rate | +10-15% | N/A |
| Test Coverage | Coverage | 90%+ | 90% |

---

## ⚠️ Risk Mitigation

1. **Planner v5 Integration**
   - Risk: Breaking existing v2 functionality
   - Mitigation: Keep v2 as fallback, extensive regression testing

2. **Async Migration**
   - Risk: Subtle concurrency bugs
   - Mitigation: Gradual migration, stress testing, monitoring

3. **Controller Decomposition**
   - Risk: Breaking complex interactions
   - Mitigation: Extract one component at a time, comprehensive tests

---

**Status:** 🚧 Implementation in progress  
**Next Update:** Weekly progress reports  
**Contact:** See repository for issues/discussions
