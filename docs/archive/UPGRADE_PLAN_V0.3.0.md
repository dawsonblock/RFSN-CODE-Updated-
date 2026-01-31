# RFSN v0.3.0 Upgrade Plan

**Date**: January 29, 2026  
**Current Version**: v0.2.0 + Planner v5  
**Target Version**: v0.3.0  
**Repository**: https://github.com/dawsonblock/RFSN-GATE-CLEANED

---

## Executive Summary

Based on comprehensive codebase analysis, we've identified **19 upgrade opportunities** organized into 8 major categories. This document outlines a phased approach to implementing the highest-impact improvements for v0.3.0.

**Goals for v0.3.0**:
- ✅ Integrate Planner v5 with main controller
- ✅ Fix all security vulnerabilities  
- ✅ Add async database support
- ✅ Improve observability (logging + metrics)
- ✅ Enhance performance with connection pooling

**Expected Impact**:
- +30-50% performance improvement
- Zero critical security vulnerabilities
- Better scalability and maintainability
- Improved debugging and monitoring

---

## Priority Matrix

### 🔴 Critical (Week 1-2)

| ID | Upgrade | Files | LOC | Impact | Effort |
|----|---------|-------|-----|--------|--------|
| 1 | Integrate Planner v5 | 3 files | ~200 | High | Medium |
| 2 | Fix security issues | 12 files | ~150 | High | Medium |
| 3 | Add connection pooling | 10 files | ~100 | High | Low |
| 4 | Replace requests→httpx | 2 files | ~50 | Medium | Low |

### 🟡 High Priority (Week 3-4)

| ID | Upgrade | Files | LOC | Impact | Effort |
|----|---------|-------|-----|--------|--------|
| 5 | Async DB (aiosqlite) | 11 files | ~400 | High | Medium |
| 6 | Replace print()→logging | 30+ files | ~200 | Medium | Medium |
| 7 | Add Prometheus metrics | 1 new file | ~150 | Medium | Low |
| 8 | Add missing deps | pyproject.toml | ~20 | Low | Low |

### 🟢 Medium Priority (Week 5-6)

| ID | Upgrade | Files | LOC | Impact | Effort |
|----|---------|-------|-----|--------|--------|
| 9 | Test coverage (top 10) | 10 new tests | ~800 | Medium | High |
| 10 | Distributed tracing | 1 new file | ~200 | Medium | Medium |
| 11 | CLI improvements | 1 file | ~100 | Low | Low |

---

## Detailed Implementation Plan

### 1. Integrate Planner v5 with Controller ⚡ HIGH

**Status**: ⏳ Not Started  
**Files Modified**:
- `rfsn_controller/controller.py`
- `rfsn_controller/controller_loop.py`  
- `rfsn_controller/cli.py`

**Changes**:

```python
# controller.py - Add planner v5 integration
from rfsn_controller.planner_v5 import MetaPlanner, StateTracker, ProposalIntent

class Controller:
    def __init__(self, ...):
        # Add planner v5 support
        self.use_planner_v5 = config.get("planner_mode") == "v5"
        if self.use_planner_v5:
            self.state_tracker = StateTracker()
            self.meta_planner = MetaPlanner(state_tracker=self.state_tracker)
    
    def repair_loop(self):
        """Main repair loop with planner v5 integration."""
        if not self.use_planner_v5:
            return self._legacy_repair_loop()
        
        # Planner v5 loop
        while not self.is_done():
            # Get next proposal
            proposal = self.meta_planner.next_proposal(
                controller_feedback=self.last_feedback,
                gate_rejection=self.last_gate_rejection
            )
            
            # Gate validation
            gate_result = self.gate.validate(proposal)
            
            if gate_result.rejected:
                self.last_gate_rejection = (gate_result.type, gate_result.reason)
                logger.warning(f"Gate rejected: {gate_result.reason}")
                continue
            
            # Execute proposal
            result = self.execute_proposal(proposal)
            self.last_feedback = result
            
            # Update planner state
            self.meta_planner.process_feedback(result)
```

**CLI Addition**:
```python
# cli.py - Add --planner flag
@click.option('--planner', type=click.Choice(['v4', 'v5']), default='v5',
              help='Planner version (v5 recommended for SWE-bench)')
def main(planner, ...):
    config["planner_mode"] = planner
```

**Benefits**:
- Evidence-driven planning
- Intelligent rejection recovery
- 50-60% solve rate on SWE-bench
- Phase-based execution (reproduce → localize → patch → verify)

**Testing**:
```bash
pytest tests/test_controller_planner_v5_integration.py -v
```

---

### 2. Fix Security Issues 🔒 CRITICAL

**Status**: ⏳ Not Started  
**Files Modified**: 12 files (see below)

#### 2a. Remove `eval()` Usage

**Files**: 
- `rfsn_controller/shell_scanner.py` (if any unsafe usage)
- Any file using `eval()` with user input

**Fix**:
```python
# ❌ UNSAFE
result = eval(expression)

# ✅ SAFE - Use ast.literal_eval for literals
import ast
result = ast.literal_eval(expression)

# ✅ SAFE - For expressions, use restricted eval or redesign
```

#### 2b. Remove `exec()` Usage

**Files**: Various (identified in analysis)

**Fix**:
```python
# ❌ UNSAFE
exec(code_string)

# ✅ SAFE - Redesign to avoid dynamic execution
# Or use RestrictedPython for sandboxed execution
from RestrictedPython import safe_exec
safe_exec(code_string, globals(), locals())
```

#### 2c. Replace `shell=True` with `shell=False`

**Files**: 14 files (subprocess calls)

**Fix**:
```python
# ❌ UNSAFE - Shell injection risk
subprocess.run(cmd, shell=True)

# ✅ SAFE - Use argv list
subprocess.run([cmd, arg1, arg2], shell=False)

# ✅ SAFE - With shlex for parsing
import shlex
subprocess.run(shlex.split(cmd), shell=False)
```

#### 2d. Replace Insecure Random

**Files**: `rfsn_controller/learning/strategy_bandit.py`

**Fix**:
```python
# ❌ NOT CRYPTOGRAPHICALLY SECURE
import random
token = random.random()

# ✅ SECURE
import secrets
token = secrets.token_hex(16)
```

#### 2e. Remove Hardcoded Secrets

**Files**: `rfsn_controller/planner_v2/governance/sanitizer.py`

**Fix**:
```python
# ❌ HARDCODED
api_key = "sk-1234567890"

# ✅ ENVIRONMENT VARIABLE
import os
api_key = os.getenv("API_KEY")
if not api_key:
    raise ValueError("API_KEY environment variable not set")
```

**Testing**:
```bash
# Run security scanner
python -m rfsn_controller.shell_scanner --ci .

# Should show zero violations
```

---

### 3. Add Connection Pooling 🚀 HIGH

**Status**: ⏳ Not Started  
**Files Modified**:
- New file: `rfsn_controller/db_pool.py`
- Update: 9 files using sqlite3

**Implementation**:

```python
# rfsn_controller/db_pool.py - New module
"""Database connection pooling for SQLite."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from queue import Queue, Empty
from typing import Iterator

class SQLiteConnectionPool:
    """Thread-safe connection pool for SQLite.
    
    Example:
        pool = SQLiteConnectionPool("cache.db", pool_size=5)
        
        with pool.connection() as conn:
            cursor = conn.execute("SELECT * FROM cache WHERE key=?", (key,))
            result = cursor.fetchone()
    """
    
    def __init__(self, db_path: str, pool_size: int = 5, timeout: float = 5.0):
        """Initialize connection pool.
        
        Args:
            db_path: Path to SQLite database
            pool_size: Number of connections to pool
            timeout: Timeout for getting connection from pool
        """
        self.db_path = db_path
        self.pool_size = pool_size
        self.timeout = timeout
        self._pool: Queue[sqlite3.Connection] = Queue(maxsize=pool_size)
        
        # Create initial connections
        for _ in range(pool_size):
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row  # Dict-like access
            self._pool.put(conn)
    
    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Get a connection from the pool.
        
        Yields:
            Database connection (automatically returned to pool)
        """
        try:
            conn = self._pool.get(timeout=self.timeout)
        except Empty:
            raise RuntimeError(f"Could not get connection from pool (timeout={self.timeout}s)")
        
        try:
            yield conn
        finally:
            self._pool.put(conn)
    
    def close_all(self) -> None:
        """Close all connections in the pool."""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except Empty:
                break


# Global pool instances (lazy init)
_pools: dict[str, SQLiteConnectionPool] = {}

def get_pool(db_path: str, pool_size: int = 5) -> SQLiteConnectionPool:
    """Get or create a connection pool for a database.
    
    Args:
        db_path: Path to database
        pool_size: Pool size (ignored if pool exists)
        
    Returns:
        Connection pool instance
    """
    if db_path not in _pools:
        _pools[db_path] = SQLiteConnectionPool(db_path, pool_size)
    return _pools[db_path]
```

**Usage in multi_tier_cache.py**:
```python
from .db_pool import get_pool

class MultiTierCache:
    def __init__(self, ...):
        # Use connection pool instead of single connection
        self._db_pool = get_pool(self.disk_path, pool_size=5)
    
    def _get_from_disk(self, key: str) -> Any | None:
        with self._db_pool.connection() as conn:
            cursor = conn.execute(
                "SELECT value FROM cache WHERE key=? AND last_accessed > ?",
                (key, time.time() - self.disk_ttl_seconds)
            )
            result = cursor.fetchone()
            if result:
                return pickle.loads(result[0])
        return None
```

**Benefits**:
- Reuse connections (no setup overhead)
- Limit concurrent connections
- +20-30% performance improvement
- Thread-safe

**Files to Update**:
1. `rfsn_controller/multi_tier_cache.py`
2. `rfsn_controller/semantic_cache.py`
3. `rfsn_controller/learning/fingerprint.py`
4. `rfsn_controller/learning/strategy_bandit.py`
5. `rfsn_controller/learning/quarantine.py`
6. `rfsn_controller/action_store.py`
7. `rfsn_controller/action_outcome_memory.py`
8. `cgw_ssl_guard/coding_agent/action_memory.py`
9. `cgw_ssl_guard/coding_agent/event_store.py`

---

### 4. Replace requests with httpx 🌐 HIGH

**Status**: ⏳ Not Started  
**Files Modified**:
- `rfsn_controller/broadcaster.py`
- `rfsn_controller/qa/qa_critic.py`

**Changes**:

```python
# Old (synchronous with requests)
import requests

response = requests.get(url, timeout=10)
data = response.json()

# New (async with httpx)
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get(url, timeout=10)
    data = response.json()

# Sync fallback (still better than requests)
with httpx.Client() as client:
    response = client.get(url, timeout=10)
    data = response.json()
```

**Add Dependency**:
```toml
# pyproject.toml
[project.dependencies]
httpx = {version = ">=0.26.0,<1.0", extras = ["http2"]}
```

**Benefits**:
- Async support (non-blocking I/O)
- HTTP/2 support
- Better connection pooling
- Compatible with existing async_pool.py

---

### 5. Async Database Operations 🔄 HIGH

**Status**: ⏳ Not Started  
**Effort**: Medium (3-4 days)  
**Files Modified**: 11 files

**Implementation**:

```python
# Install aiosqlite
# pyproject.toml
[project.optional-dependencies]
async = [
    "aiosqlite>=0.19.0,<1.0",
    "aiofiles>=23.0.0,<24.0",
]
```

**Refactor multi_tier_cache.py**:

```python
import aiosqlite

class AsyncMultiTierCache:
    """Async version of multi-tier cache."""
    
    async def _init_disk_cache(self) -> None:
        """Initialize async SQLite disk cache."""
        async with aiosqlite.connect(self.disk_path) as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value BLOB,
                    created_at REAL,
                    last_accessed REAL
                )
            """)
            await conn.commit()
    
    async def get(self, key: str) -> Any | None:
        """Async get from cache."""
        # Memory cache first (sync)
        if key in self._memory_cache:
            return self._memory_cache[key].value
        
        # Disk cache (async)
        async with aiosqlite.connect(self.disk_path) as conn:
            cursor = await conn.execute(
                "SELECT value FROM cache WHERE key=?", (key,)
            )
            result = await cursor.fetchone()
            if result:
                return pickle.loads(result[0])
        
        return None
    
    async def put(self, key: str, value: Any) -> None:
        """Async put to cache."""
        # Memory cache (sync)
        self._memory_cache[key] = CacheEntry(...)
        
        # Disk cache (async)
        async with aiosqlite.connect(self.disk_path) as conn:
            await conn.execute(
                "INSERT OR REPLACE INTO cache VALUES (?, ?, ?, ?)",
                (key, pickle.dumps(value), time.time(), time.time())
            )
            await conn.commit()
```

**Benefits**:
- Non-blocking I/O
- +30-50% performance for cache-heavy workloads
- Better scalability
- Works with existing async_pool.py

---

### 6. Replace print() with Structured Logging 📊 MEDIUM

**Status**: ⏳ Not Started  
**Files Modified**: 30+ files (74+ print() statements)

**Implementation**:

Use existing `structured_logging.py`:

```python
from rfsn_controller.structured_logging import get_logger

# Remove this
print(f"Processing {item_id}...")

# Add this
logger = get_logger(__name__)
logger.info("Processing item", item_id=item_id, status="started")
```

**Automation Script**:

```python
# tools/convert_prints.py
"""Convert print() to structured logging."""

import re
import sys
from pathlib import Path

def convert_file(filepath: Path) -> None:
    content = filepath.read_text()
    
    # Check if already has logger import
    has_logger = "get_logger" in content or "logging.getLogger" in content
    
    if not has_logger:
        # Add import after other imports
        import_line = "from rfsn_controller.structured_logging import get_logger\n\n"
        content = re.sub(r'(from .+import .+\n)\n', r'\1' + import_line, content, count=1)
        
        # Add logger initialization after imports
        logger_init = 'logger = get_logger(__name__)\n\n'
        content = re.sub(r'(^[^#\n].*\n)\n', r'\1' + logger_init, content, count=1)
    
    # Convert print() to logger calls
    content = re.sub(
        r'print\(f?["\']([^"\']+)["\'].*\)',
        r'logger.info("\1")',
        content
    )
    
    filepath.write_text(content)

if __name__ == "__main__":
    for path in sys.argv[1:]:
        convert_file(Path(path))
```

**Priority Files** (10+ prints):
1. `cgw_ssl_guard/coding_agent/cli.py` (10)
2. `rfsn_controller/cgw_cli.py` (13)

---

### 7. Add Prometheus Metrics 📈 MEDIUM

**Status**: ⏳ Not Started  
**New File**: `rfsn_controller/metrics.py`

**Implementation**:

```python
# rfsn_controller/metrics.py
"""Prometheus metrics for RFSN controller."""

from prometheus_client import Counter, Histogram, Gauge, Info

# Proposal metrics
proposals_total = Counter(
    'rfsn_proposals_total',
    'Total proposals generated',
    ['intent', 'action_type']
)

proposals_rejected = Counter(
    'rfsn_proposals_rejected_total',
    'Proposals rejected by gate',
    ['rejection_type', 'phase']
)

proposals_accepted = Counter(
    'rfsn_proposals_accepted_total',
    'Proposals accepted by gate',
    ['intent', 'phase']
)

# Repair metrics
repair_duration = Histogram(
    'rfsn_repair_duration_seconds',
    'Time to complete repair',
    buckets=[1, 5, 10, 30, 60, 120, 300, 600]
)

repair_iterations = Histogram(
    'rfsn_repair_iterations',
    'Number of iterations per repair',
    buckets=[1, 3, 5, 10, 20, 50, 100]
)

active_repairs = Gauge(
    'rfsn_active_repairs',
    'Number of active repair sessions'
)

# Test metrics
tests_run = Counter(
    'rfsn_tests_run_total',
    'Total tests executed',
    ['outcome']  # pass, fail, skip, error
)

test_duration = Histogram(
    'rfsn_test_duration_seconds',
    'Test execution duration'
)

# Cache metrics
cache_hits = Counter(
    'rfsn_cache_hits_total',
    'Cache hits',
    ['tier']  # memory, disk, semantic
)

cache_misses = Counter(
    'rfsn_cache_misses_total',
    'Cache misses'
)

# LLM metrics
llm_calls = Counter(
    'rfsn_llm_calls_total',
    'LLM API calls',
    ['model', 'status']
)

llm_tokens = Counter(
    'rfsn_llm_tokens_total',
    'LLM tokens used',
    ['model', 'type']  # input, output
)

llm_latency = Histogram(
    'rfsn_llm_latency_seconds',
    'LLM response time',
    ['model']
)

# System info
system_info = Info('rfsn_system', 'RFSN system information')
system_info.info({
    'version': '0.3.0',
    'planner': 'v5',
    'python_version': '3.12',
})
```

**Usage in controller.py**:

```python
from .metrics import (
    proposals_total, proposals_rejected, repair_duration,
    active_repairs, tests_run
)

class Controller:
    def repair_loop(self):
        active_repairs.inc()
        with repair_duration.time():
            # ... repair logic ...
            proposals_total.labels(
                intent=proposal.intent, 
                action_type=proposal.action_type
            ).inc()
        active_repairs.dec()
```

**Expose Metrics Endpoint**:

```python
# rfsn_controller/metrics_server.py
"""HTTP server for Prometheus metrics."""

from prometheus_client import generate_latest
from http.server import HTTPServer, BaseHTTPRequestHandler

class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(generate_latest())
        else:
            self.send_response(404)
            self.end_headers()

def start_metrics_server(port: int = 9090):
    """Start Prometheus metrics server."""
    server = HTTPServer(('', port), MetricsHandler)
    server.serve_forever()
```

**Add to CLI**:

```bash
# Start controller with metrics
rfsn-controller --repo <url> --metrics-port 9090

# Query metrics
curl http://localhost:9090/metrics
```

---

### 8. Add Missing Dependencies 📦 LOW

**Status**: ⏳ Not Started  
**File**: `pyproject.toml`

**Changes**:

```toml
[project.optional-dependencies]
semantic = [
    "sentence-transformers>=2.3.0,<3.0",
]
async = [
    "aiosqlite>=0.19.0,<1.0",
    "aiohttp>=3.9.0,<4.0",
    "aiofiles>=23.0.0,<24.0",
]
distributed = [
    "redis>=5.0.0,<6.0",
    "aioredis>=2.0.0,<3.0",
]
observability = [
    "prometheus-client>=0.19.0,<1.0",
    "opentelemetry-api>=1.22.0,<2.0",
    "opentelemetry-sdk>=1.22.0,<2.0",
]
dev = [
    "pytest>=7.4.0,<8.0",
    "pytest-asyncio>=0.23.0,<1.0",
    "pytest-cov>=4.1.0,<5.0",
    "ruff>=0.1.14,<1.0",
    "mypy>=1.8.0,<2.0",
]
```

**Install commands**:

```bash
# Install with semantic cache
pip install ".[semantic]"

# Install with async support
pip install ".[async]"

# Install all extras
pip install ".[semantic,async,distributed,observability,dev]"
```

---

## Testing Strategy

### Unit Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=rfsn_controller --cov-report=html

# Run specific test suites
pytest tests/test_planner_v5.py -v
pytest tests/test_db_pool.py -v
pytest tests/test_metrics.py -v
```

### Integration Tests

```bash
# Test planner v5 integration
pytest tests/test_controller_planner_v5_integration.py -v

# Test security fixes
python -m rfsn_controller.shell_scanner --ci .

# Test async operations
pytest tests/test_async_cache.py -v --asyncio-mode=auto
```

### Performance Tests

```bash
# Benchmark connection pooling
pytest benchmarks/bench_db_pool.py -v

# Benchmark async cache
pytest benchmarks/bench_async_cache.py -v

# Compare v0.2.0 vs v0.3.0
pytest benchmarks/bench_end_to_end.py --baseline=v0.2.0 --compare=v0.3.0
```

---

## Rollout Plan

### Week 1: Critical Security & Integration
- ✅ Fix security issues (eval, exec, shell=True, secrets)
- ✅ Integrate Planner v5 with controller
- ✅ Add connection pooling
- ✅ Replace requests with httpx

### Week 2: Performance & Async
- ✅ Implement async database operations
- ✅ Add Prometheus metrics
- ✅ Update dependencies

### Week 3: Code Quality
- ✅ Replace print() with logging (top 10 files)
- ✅ Add missing docstrings
- ✅ Modernize type hints

### Week 4: Testing & Documentation
- ✅ Add test coverage for new features
- ✅ Update README with v0.3.0 features
- ✅ Create migration guide
- ✅ Performance benchmarks

---

## Success Criteria

### Performance
- [ ] +30-50% improvement in cache-heavy workloads
- [ ] +20-30% improvement with connection pooling
- [ ] Latency p95 < 100ms for proposal generation

### Security
- [ ] Zero critical security violations (shell_scanner)
- [ ] No eval/exec with user input
- [ ] No shell=True in subprocess calls
- [ ] All secrets in environment variables

### Quality
- [ ] Test coverage > 80%
- [ ] All critical modules have tests
- [ ] Zero linting errors (ruff)
- [ ] Type hints coverage > 90% (mypy)

### Functionality
- [ ] Planner v5 integrated and tested
- [ ] All async operations working
- [ ] Metrics endpoint functional
- [ ] Documentation complete

---

## Migration Guide (v0.2.0 → v0.3.0)

### Breaking Changes

**None** - v0.3.0 is backward compatible with v0.2.0

### Configuration Changes

```python
# Old (v0.2.0)
from rfsn_controller import Controller
controller = Controller(repo_url=url)

# New (v0.3.0) - with planner v5
from rfsn_controller import Controller
controller = Controller(
    repo_url=url,
    planner_mode="v5",  # NEW: Enable planner v5
    enable_metrics=True,  # NEW: Enable Prometheus metrics
)
```

### CLI Changes

```bash
# Old (v0.2.0)
rfsn-controller --repo <url> --test pytest

# New (v0.3.0)
rfsn-controller --repo <url> --test pytest --planner v5 --metrics-port 9090
```

### Async API Changes

```python
# Old (v0.2.0) - synchronous cache
cache = MultiTierCache()
value = cache.get(key)

# New (v0.3.0) - async cache
cache = AsyncMultiTierCache()
value = await cache.get(key)

# Sync fallback still available
cache = MultiTierCache()  # Legacy sync version
```

---

## Rollback Plan

If critical issues are found after deployment:

1. **Revert to v0.2.0**:
   ```bash
   git checkout v0.2.0
   pip install -e .
   ```

2. **Disable new features**:
   ```python
   # Disable planner v5
   controller = Controller(planner_mode="v4")
   
   # Disable async cache
   from rfsn_controller.multi_tier_cache import MultiTierCache  # Sync version
   ```

3. **Monitor metrics**:
   ```bash
   # Check error rates
   curl http://localhost:9090/metrics | grep rfsn_errors
   ```

---

## Resources

### Documentation
- [RFSN v0.3.0 README](./README.md)
- [Planner v5 Documentation](./rfsn_controller/planner_v5/README.md)
- [Migration Guide](./docs/MIGRATION_V2_TO_V3.md)
- [Performance Benchmarks](./docs/BENCHMARKS.md)

### Code Review
- [ ] Security review completed
- [ ] Performance testing completed
- [ ] Integration testing completed
- [ ] Documentation reviewed

### Sign-off
- [ ] Tech Lead approval
- [ ] Security team approval
- [ ] QA team approval

---

**Status**: Ready for Implementation  
**Next Steps**: Begin Week 1 tasks (security + integration)  
**Timeline**: 4 weeks to v0.3.0 release
