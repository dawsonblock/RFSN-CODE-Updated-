"""Central configuration for RFSN Controller.

Provides type-safe configuration using Pydantic with environment variable support.

Usage:
    from rfsn_controller.config import RFSNConfig, get_config
    
    # Load from environment
    config = get_config()
    
    # Or create manually
    config = RFSNConfig(
        llm_primary="deepseek-chat",
        planner_mode="v5",
        cache_enabled=True
    )
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class LLMConfig(BaseModel):
    """LLM configuration settings."""
    
    primary: str = Field(
        "deepseek-chat",
        description="Primary LLM model for planning and generation"
    )
    fallback: str = Field(
        "gemini-2.0-flash",
        description="Fallback LLM model when primary fails"
    )
    temperature: float = Field(
        0.2,
        ge=0.0,
        le=2.0,
        description="Temperature for LLM sampling"
    )
    max_tokens: int = Field(
        4096,
        ge=1,
        le=32000,
        description="Maximum tokens per LLM response"
    )
    timeout: float = Field(
        60.0,
        ge=1.0,
        description="LLM API timeout in seconds"
    )
    max_retries: int = Field(
        3,
        ge=0,
        le=10,
        description="Maximum API retry attempts"
    )


class PlannerConfig(BaseModel):
    """Planner configuration settings."""
    
    mode: Literal["v4", "v5"] = Field(
        "v5",
        description="Planner version to use"
    )
    max_plan_steps: int = Field(
        12,
        ge=1,
        le=50,
        description="Maximum steps in a single plan"
    )
    max_iterations: int = Field(
        50,
        ge=1,
        le=200,
        description="Maximum repair iterations"
    )
    max_stuck_iterations: int = Field(
        3,
        ge=1,
        le=10,
        description="Iterations before considering stuck"
    )
    risk_budget: int = Field(
        3,
        ge=0,
        le=10,
        description="Maximum allowed risk level"
    )


class CacheConfig(BaseModel):
    """Cache configuration settings."""
    
    enabled: bool = Field(
        True,
        description="Enable caching system"
    )
    ttl_hours: int = Field(
        72,
        ge=1,
        le=8760,  # 1 year
        description="Cache TTL in hours"
    )
    dir: Path = Field(
        Path.home() / ".cache" / "rfsn",
        description="Cache directory path"
    )
    max_size_mb: int = Field(
        1024,
        ge=10,
        description="Maximum cache size in MB"
    )
    memory_enabled: bool = Field(
        True,
        description="Enable in-memory cache tier"
    )
    disk_enabled: bool = Field(
        True,
        description="Enable disk cache tier"
    )
    semantic_enabled: bool = Field(
        False,
        description="Enable semantic cache tier (requires sentence-transformers)"
    )


class SafetyConfig(BaseModel):
    """Safety and security configuration."""
    
    docker_enabled: bool = Field(
        True,
        description="Use Docker sandboxing for code execution"
    )
    max_risk_budget: int = Field(
        3,
        ge=0,
        le=10,
        description="Maximum cumulative risk budget"
    )
    shell_allowed: bool = Field(
        False,
        description="Allow shell=True in subprocess (NOT RECOMMENDED)"
    )
    eval_allowed: bool = Field(
        False,
        description="Allow eval() and exec() (NOT RECOMMENDED)"
    )
    gate_strict_mode: bool = Field(
        True,
        description="Enable strict gate validation"
    )


class ObservabilityConfig(BaseModel):
    """Observability and monitoring configuration."""
    
    metrics_enabled: bool = Field(
        True,
        description="Enable Prometheus metrics"
    )
    metrics_port: int = Field(
        9090,
        ge=1024,
        le=65535,
        description="Prometheus metrics port"
    )
    tracing_enabled: bool = Field(
        False,
        description="Enable distributed tracing"
    )
    jaeger_host: str = Field(
        "localhost",
        description="Jaeger agent hostname"
    )
    jaeger_port: int = Field(
        6831,
        ge=1,
        le=65535,
        description="Jaeger agent port"
    )
    structured_logging: bool = Field(
        True,
        description="Use structured JSON logging"
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        "INFO",
        description="Logging level"
    )


class RFSNConfig(BaseSettings):
    """Central RFSN Controller configuration.
    
    Loads from environment variables with RFSN_ prefix.
    
    Example:
        # Set via environment
        export RFSN_LLM__PRIMARY="gpt-4"
        export RFSN_PLANNER__MODE="v5"
        export RFSN_CACHE__ENABLED="true"
        
        # Load config
        config = RFSNConfig()
        print(config.llm.primary)  # "gpt-4"
    """
    
    model_config = SettingsConfigDict(
        env_prefix="RFSN_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )
    
    # Component configurations
    llm: LLMConfig = Field(
        default_factory=LLMConfig,
        description="LLM configuration"
    )
    planner: PlannerConfig = Field(
        default_factory=PlannerConfig,
        description="Planner configuration"
    )
    cache: CacheConfig = Field(
        default_factory=CacheConfig,
        description="Cache configuration"
    )
    safety: SafetyConfig = Field(
        default_factory=SafetyConfig,
        description="Safety configuration"
    )
    observability: ObservabilityConfig = Field(
        default_factory=ObservabilityConfig,
        description="Observability configuration"
    )
    
    # Global settings
    version: str = Field(
        "0.2.0",
        description="RFSN Controller version"
    )
    debug: bool = Field(
        False,
        description="Enable debug mode"
    )
    dry_run: bool = Field(
        False,
        description="Dry run mode (no actual changes)"
    )
    
    def validate_environment(self) -> list[str]:
        """Validate required environment variables and dependencies.
        
        Returns:
            List of warnings/errors
        """
        issues = []
        
        # Check cache directory
        if self.cache.enabled and not self.cache.dir.exists():
            try:
                self.cache.dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                issues.append(f"Failed to create cache dir: {e}")
        
        # Check semantic cache dependencies
        if self.cache.semantic_enabled:
            try:
                import sentence_transformers
            except ImportError:
                issues.append(
                    "Semantic cache enabled but sentence-transformers not installed. "
                    "Install with: pip install 'rfsn-controller[semantic]'"
                )
        
        # Check tracing dependencies
        if self.observability.tracing_enabled:
            try:
                import opentelemetry
            except ImportError:
                issues.append(
                    "Tracing enabled but opentelemetry not installed. "
                    "Install with: pip install 'rfsn-controller[observability]'"
                )
        
        # Security warnings
        if self.safety.shell_allowed:
            issues.append(
                "WARNING: shell=True is enabled. This is a security risk!"
            )
        
        if self.safety.eval_allowed:
            issues.append(
                "WARNING: eval/exec is enabled. This is a security risk!"
            )
        
        return issues


# Global configuration instance
_config: RFSNConfig | None = None


def get_config(reload: bool = False) -> RFSNConfig:
    """Get global configuration instance.
    
    Args:
        reload: Force reload configuration from environment
        
    Returns:
        Global RFSNConfig instance
    """
    global _config
    
    if _config is None or reload:
        _config = RFSNConfig()
        
        # Validate and print warnings
        issues = _config.validate_environment()
        if issues:
            import sys
            for issue in issues:
                print(f"Config warning: {issue}", file=sys.stderr)
    
    return _config


def reset_config() -> None:
    """Reset global configuration (useful for testing)."""
    global _config
    _config = None
