#!/usr/bin/env python3
"""
Redis Connection Diagnostic Tool

Tests different Redis connection methods to diagnose connection issues.
"""

import asyncio
import os
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
import redis.asyncio as redis


async def test_redis_connection_methods():
    """Test different Redis connection approaches."""
    print("🔍 Redis Connection Diagnostics")
    print("=" * 50)

    # Load environment variables
    load_dotenv()

    # Get Redis configuration
    host = os.getenv("UPSTASH_REDIS_HOST", "")
    port = int(os.getenv("UPSTASH_REDIS_PORT", "6379"))
    password = os.getenv("UPSTASH_REDIS_PASSWORD", "")
    username = os.getenv("UPSTASH_REDIS_USERNAME", "default")

    print("🔧 Configuration:")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Username: {username}")
    print("   Password: [CONFIGURED SECURELY]")
    print()

    # Test 1: Basic connection without authentication
    print("🧪 Test 1: Basic connection (no auth)")
    try:
        client = redis.Redis(host=host, port=port, decode_responses=True)
        await client.ping()
        print("   ✅ SUCCESS: Connected without authentication")
        await client.close()
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
    print()

    # Test 2: Password-only authentication
    print("🧪 Test 2: Password-only authentication")
    try:
        client = redis.Redis(
            host=host,
            port=port,
            password=password,
            decode_responses=True,
            socket_connect_timeout=10,
            socket_timeout=10,
        )
        await client.ping()
        print("   ✅ SUCCESS: Connected with password only")
        await client.close()
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
    print()

    # Test 3: Username + password authentication
    print("🧪 Test 3: Username + password authentication")
    try:
        client = redis.Redis(
            host=host,
            port=port,
            username=username,
            password=password,
            decode_responses=True,
            socket_connect_timeout=10,
            socket_timeout=10,
        )
        await client.ping()
        print("   ✅ SUCCESS: Connected with username + password")
        await client.close()
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
    print()

    # Test 4: URL-based connection (current approach)
    print("🧪 Test 4: URL-based connection (current method)")
    try:
        redis_url = f"redis://{username}:{password}@{host}:{port}"
        client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=10,
            socket_timeout=10,
        )
        await client.ping()
        print("   ✅ SUCCESS: Connected with URL method")
        await client.close()
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
    print()

    # Test 5: SSL/TLS connection
    print("🧪 Test 5: SSL/TLS connection")
    try:
        client = redis.Redis(
            host=host,
            port=port,
            username=username,
            password=password,
            ssl=True,
            ssl_cert_reqs=None,
            decode_responses=True,
            socket_connect_timeout=10,
            socket_timeout=10,
        )
        await client.ping()
        print("   ✅ SUCCESS: Connected with SSL/TLS")
        await client.close()
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
    print()

    # Test 6: URL with SSL
    print("🧪 Test 6: URL-based SSL connection")
    try:
        redis_url = f"rediss://{username}:{password}@{host}:{port}"  # rediss for SSL
        client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=10,
            socket_timeout=10,
            ssl_cert_reqs=None,
        )
        await client.ping()
        print("   ✅ SUCCESS: Connected with SSL URL")
        await client.close()
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
    print()

    print("🏁 Diagnostic Complete")
    print("\n💡 Recommendations:")
    print("   • If SSL tests succeed, use rediss:// URL format")
    print("   • If password-only succeeds, remove username from config")
    print("   • If no tests succeed, check Upstash dashboard for connection limits")
    print("   • Verify credentials in Upstash console")


if __name__ == "__main__":
    asyncio.run(test_redis_connection_methods())
