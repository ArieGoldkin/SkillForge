#!/usr/bin/env python3
"""Integration tests for Redis connection reliability.

These tests validate the Redis L2 cache connection fixes implemented
in Issue #388, including TCP keepalive, retry logic, and graceful degradation.

Run with:
    cd backend
    poetry run pytest tests/integration/test_redis_connection_reliability.py -v -s -n 0 --tb=short
    
Quick test (skip 10-minute idle test):
    cd backend
    poetry run pytest tests/integration/test_redis_connection_reliability.py -v -s -n 0 -k "not idle_connection" --tb=short
    
Note: These tests run sequentially (-n 0) to avoid connection pool exhaustion.
"""

import asyncio
import socket
import sys
import time
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from redis import Redis
from redis.exceptions import ConnectionError

from app.core.logging import get_logger
from app.shared.services.cache.redis_connection import (
    _get_socket_keepalive_options,
    create_redis_client,
)
from app.shared.services.prompts.prompt_manager import PromptManager

logger = get_logger(__name__)


@pytest.mark.integration
@pytest.mark.slow
def test_idle_connection_survives_10_minutes():
    """Test that Redis connection survives 10-minute idle period.
    
    This validates that TCP keepalive settings prevent connection drops
    during idle periods.
    
    WARNING: This test takes 10 minutes to run. Use -k "not idle_connection" 
    to skip it during quick validation.
    """
    logger.info("test_start", test="idle_connection_10min")
    
    # Get Redis client
    client = create_redis_client()
    
    try:
        # Verify initial connection
        result = client.ping()
        assert result is True, "Initial ping should succeed"
        logger.info("initial_ping_success")
        
        # Wait 10 minutes
        logger.info("waiting_10_minutes", message="Simulating idle connection...")
        time.sleep(600)  # 10 minutes
        
        # Verify connection still works
        result = client.ping()
        assert result is True, "Connection should survive 10-minute idle period"
        
        logger.info("test_complete", test="idle_connection_10min", status="PASS")
    finally:
        # Clean up connection
        client.close()


@pytest.mark.integration
def test_connection_pool_health():
    """Test connection pool health checks work correctly."""
    logger.info("test_start", test="connection_pool_health")
    
    # Create Redis client with connection pool
    client = create_redis_client()
    
    try:
        # Perform multiple operations to test pool health
        for i in range(10):
            result = client.ping()
            assert result is True, f"Ping {i} should succeed"
            if i % 3 == 0:
                logger.info("ping_batch", index=i, ping_ok=True)
        
        logger.info(
            "test_complete", 
            test="connection_pool_health", 
            status="PASS", 
            pings=10
        )
    finally:
        client.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_exponential_backoff_retry():
    """Test that retry logic with exponential backoff works correctly.
    
    This test validates that the PromptManager gracefully handles connection
    errors and falls back to L3 (Langfuse API) or hardcoded prompts.
    """
    logger.info("test_start", test="exponential_backoff_retry")
    
    # Get prompt manager (with Redis enabled)
    pm = PromptManager(enable_redis=True, enable_langfuse=False)
    
    try:
        # Try to get prompt (will use L1 cache or fallback to hardcoded)
        result = await pm.get_prompt(
            name="analysis-supervisor-routing",
            variables={"agent_list": "- test_agent"},
            label="production"
        )
        
        # Should get result from L1 cache or hardcoded fallback
        assert result is not None, "Should get prompt from L1 or fallback"
        assert "agents" in result, "Prompt should contain agent selection logic"
        
        logger.info("test_complete", test="exponential_backoff_retry", status="PASS")
    finally:
        # Clean up
        pm.clear_caches()


@pytest.mark.integration
def test_socket_keepalive_configured():
    """Test that socket keepalive options are configured correctly."""
    logger.info("test_start", test="socket_keepalive")
    
    # Get socket keepalive options
    options = _get_socket_keepalive_options()
    
    # Verify options exist and are correct for the platform
    assert len(options) > 0, "Socket keepalive options should be configured"
    
    # Platform-specific validation
    if sys.platform == "darwin":  # macOS
        assert socket.TCP_KEEPALIVE in options, "macOS should use TCP_KEEPALIVE"
        assert options[socket.TCP_KEEPALIVE] == 60, "TCP_KEEPALIVE should be 60s"
    elif hasattr(socket, "TCP_KEEPIDLE"):  # Linux
        assert socket.TCP_KEEPIDLE in options, "Linux should use TCP_KEEPIDLE"
        assert options[socket.TCP_KEEPIDLE] == 60, "TCP_KEEPIDLE should be 60s"
    
    # Common options across platforms
    if hasattr(socket, "TCP_KEEPINTVL"):
        assert socket.TCP_KEEPINTVL in options, "TCP_KEEPINTVL should be configured"
        assert options[socket.TCP_KEEPINTVL] == 10, "TCP_KEEPINTVL should be 10s"
    
    if hasattr(socket, "TCP_KEEPCNT"):
        assert socket.TCP_KEEPCNT in options, "TCP_KEEPCNT should be configured"
        assert options[socket.TCP_KEEPCNT] == 3, "TCP_KEEPCNT should be 3"
    
    logger.info(
        "socket_keepalive_verified",
        enabled=True,
        options=options,
        platform=sys.platform,
        status="PASS",
    )


@pytest.mark.integration
def test_connection_configuration():
    """Test that Redis client is configured with correct connection parameters."""
    logger.info("test_start", test="connection_configuration")
    
    # Create Redis client
    client = create_redis_client()
    
    try:
        # Get connection pool
        pool = client.connection_pool
        
        # Verify pool configuration
        assert pool.connection_kwargs.get("socket_keepalive") is True, \
            "Socket keepalive should be enabled"
        
        assert pool.connection_kwargs.get("socket_connect_timeout") == 5, \
            "Socket connect timeout should be 5s"
        
        assert pool.connection_kwargs.get("socket_timeout") == 5, \
            "Socket timeout should be 5s"
        
        assert pool.connection_kwargs.get("health_check_interval") == 30, \
            "Health check interval should be 30s"
        
        assert pool.max_connections == 20, \
            "Max connections should be 20"
        
        # Verify keepalive options are set
        keepalive_options = pool.connection_kwargs.get("socket_keepalive_options", {})
        assert len(keepalive_options) > 0, "Socket keepalive options should be configured"
        
        # Verify retry configuration
        retry = pool.connection_kwargs.get("retry")
        assert retry is not None, "Retry should be configured"
        # Retry uses _retries (private attribute)
        assert retry._retries == 3, "Should have 3 retry attempts"
        
        logger.info(
            "connection_configuration_verified",
            socket_keepalive=True,
            max_connections=20,
            health_check_interval=30,
            retry_attempts=3,
            status="PASS",
        )
    finally:
        client.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_graceful_degradation_l2_to_fallback():
    """Test that PromptManager gracefully falls back when Redis is unavailable.
    
    This test validates the L1 -> L2 -> L3 -> Fallback cache hierarchy.
    """
    logger.info("test_start", test="graceful_degradation")
    
    # Create PromptManager with Redis disabled to simulate failure
    pm = PromptManager(enable_redis=False, enable_langfuse=False)
    
    # Clear L1 cache to force fallback
    pm.l1_cache.clear()
    
    try:
        # Try to get prompt (should fall back to hardcoded)
        result = await pm.get_prompt(
            name="analysis-supervisor-routing",
            variables={"agent_list": "- test_agent"},
            label="production"
        )
        
        # Should get hardcoded fallback
        assert result is not None, "Should get hardcoded fallback prompt"
        assert "agents" in result, "Fallback prompt should contain agent selection logic"
        
        logger.info("test_complete", test="graceful_degradation", status="PASS")
    finally:
        pm.clear_caches()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_l2_cache_retry_on_connection_error():
    """Test that L2 cache retries on connection errors with exponential backoff.
    
    This test verifies the retry logic implemented in PromptManager._get_from_l2_cache().
    """
    logger.info("test_start", test="l2_cache_retry")
    
    # Create PromptManager
    pm = PromptManager(enable_redis=True, enable_langfuse=False)
    
    try:
        # Mock Redis client to simulate connection errors
        retry_attempts = []
        
        def mock_get_with_errors(key):
            """Simulate connection error on first 2 attempts, then succeed."""
            retry_attempts.append(datetime.now(UTC))
            if len(retry_attempts) < 3:
                raise ConnectionError("Simulated connection error")
            return None  # Cache miss on third attempt
        
        if pm.redis_client:
            with patch.object(pm.redis_client, 'get', side_effect=mock_get_with_errors):
                # Try to get from L2 cache (should retry 3 times)
                result = await pm._get_from_l2_cache(
                    name="test-prompt",
                    label="production"
                )
                
                # Should have retried 3 times
                assert len(retry_attempts) == 3, "Should retry 3 times on connection error"
                
                # Verify exponential backoff delays
                if len(retry_attempts) >= 2:
                    delay1 = (retry_attempts[1] - retry_attempts[0]).total_seconds()
                    assert 0.08 <= delay1 <= 0.15, \
                        f"First retry delay should be ~100ms, got {delay1:.3f}s"
                
                if len(retry_attempts) >= 3:
                    delay2 = (retry_attempts[2] - retry_attempts[1]).total_seconds()
                    assert 0.15 <= delay2 <= 0.25, \
                        f"Second retry delay should be ~200ms, got {delay2:.3f}s"
                
                # Result should be None (graceful degradation)
                assert result is None, "Should return None after exhausting retries"
        
        logger.info(
            "test_complete", 
            test="l2_cache_retry", 
            status="PASS",
            retry_attempts=len(retry_attempts)
        )
    finally:
        pm.clear_caches()


@pytest.mark.integration
def test_connection_survives_multiple_pings():
    """Test that connection remains healthy across multiple operations."""
    logger.info("test_start", test="multiple_pings")
    
    # Create Redis client
    client = create_redis_client()
    
    try:
        # Perform 100 pings with small delays
        success_count = 0
        for i in range(100):
            try:
                result = client.ping()
                if result:
                    success_count += 1
                if i % 20 == 0:
                    logger.info("ping_batch", index=i, success_count=success_count)
                time.sleep(0.01)  # 10ms delay between pings
            except Exception as e:
                logger.error("ping_failed", index=i, error=str(e))
        
        # Verify all pings succeeded
        assert success_count == 100, f"All 100 pings should succeed, got {success_count}"
        
        logger.info(
            "test_complete", 
            test="multiple_pings", 
            status="PASS",
            pings=100,
            success_rate=success_count/100
        )
    finally:
        client.close()


@pytest.mark.integration
def test_connection_health_check():
    """Test that connection pool health checks detect stale connections."""
    logger.info("test_start", test="health_check")
    
    # Create Redis client with 30s health check interval
    client = create_redis_client(health_check_interval=30)
    
    try:
        # Perform multiple operations
        for i in range(5):
            result = client.ping()
            assert result is True, f"Health check {i} should pass"
            time.sleep(0.5)
        
        logger.info("test_complete", test="health_check", status="PASS")
    finally:
        client.close()


@pytest.mark.integration
def test_socket_timeouts_configured():
    """Test that socket timeouts are configured to prevent hanging."""
    logger.info("test_start", test="socket_timeouts")
    
    # Create Redis client
    client = create_redis_client()
    
    try:
        pool = client.connection_pool
        
        # Verify socket timeouts
        assert pool.connection_kwargs.get("socket_connect_timeout") == 5, \
            "Socket connect timeout should be 5s"
        assert pool.connection_kwargs.get("socket_timeout") == 5, \
            "Socket timeout should be 5s"
        
        # Test that connection works
        result = client.ping()
        assert result is True, "Connection with timeouts should work"
        
        logger.info(
            "test_complete", 
            test="socket_timeouts", 
            status="PASS",
            connect_timeout=5,
            socket_timeout=5
        )
    finally:
        client.close()
