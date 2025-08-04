#!/usr/bin/env python3
"""
API Endpoint Validation Script
Tests all OurTube API endpoints for proper functionality
"""

import asyncio
import aiohttp
import json
from typing import Dict, List, Tuple

# Configuration
BASE_URL = "http://localhost:8000"
TEST_VIDEO_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Define all endpoints to test
ENDPOINTS = [
    # Health & Config
    ("GET", "/api/health", None, 200),
    ("GET", "/api/config", None, 200),
    
    # Video Info & Formats
    ("GET", f"/api/info?url={TEST_VIDEO_URL}", None, 200),
    ("GET", f"/api/formats?url={TEST_VIDEO_URL}", None, 200),
    
    # Downloads
    ("GET", "/api/downloads", None, 200),
    ("POST", "/api/download", {"url": TEST_VIDEO_URL, "audio_only": True}, 200),
    
    # Directory Operations
    ("POST", "/api/set-download-dir", {"directory": "./downloads"}, 200),
    ("POST", "/api/open-download-dir", None, 200),
    
    # Updates
    ("POST", "/api/update-ytdlp", None, 200),
    ("POST", "/api/restart", None, 200),
]

async def test_endpoint(session: aiohttp.ClientSession, method: str, path: str, data: Dict = None) -> Tuple[int, Dict]:
    """Test a single endpoint"""
    url = f"{BASE_URL}{path}"
    
    try:
        if method == "GET":
            async with session.get(url) as response:
                return response.status, await response.json()
        elif method == "POST":
            async with session.post(url, json=data) as response:
                return response.status, await response.json()
        elif method == "DELETE":
            async with session.delete(url) as response:
                return response.status, await response.json()
    except Exception as e:
        return 0, {"error": str(e)}

async def main():
    """Run all endpoint tests"""
    print("🔍 OurTube API Endpoint Validation")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        results = []
        
        for method, path, data, expected_status in ENDPOINTS:
            status, response = await test_endpoint(session, method, path, data)
            success = status == expected_status
            
            results.append({
                "endpoint": f"{method} {path}",
                "status": status,
                "expected": expected_status,
                "success": success,
                "response": response if not success else "OK"
            })
            
            print(f"{'✅' if success else '❌'} {method} {path} - Status: {status}")
            if not success:
                print(f"   Expected: {expected_status}, Response: {response}")
        
        # Summary
        print("\n" + "=" * 50)
        successful = sum(1 for r in results if r["success"])
        total = len(results)
        print(f"Summary: {successful}/{total} endpoints passed")
        
        # WebSocket test
        print("\n🔌 Testing WebSocket connection...")
        try:
            ws_url = f"{BASE_URL.replace('http', 'ws')}/ws"
            async with session.ws_connect(ws_url) as ws:
                print("✅ WebSocket connection successful")
                await ws.close()
        except Exception as e:
            print(f"❌ WebSocket connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())