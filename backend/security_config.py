"""
Security configuration and middleware for OurTube
"""

from fastapi import Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time
from collections import defaultdict
from datetime import datetime, timedelta
import re
import os
from urllib.parse import urlparse

# Security Headers
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self'",
}

# Rate limiting configuration
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value
        
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware"""

    def __init__(self, app):
        super().__init__(app)
        self.requests = defaultdict(list)
        self.last_cleanup = datetime.now()
        self.cleanup_interval = timedelta(minutes=5)  # Cleanup every 5 minutes

    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        now = datetime.now()
        cutoff = now - timedelta(seconds=RATE_LIMIT_WINDOW)

        # Clean old requests for this IP
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if req_time > cutoff
        ]

        # Periodic cleanup of stale IPs to prevent memory leak
        if now - self.last_cleanup > self.cleanup_interval:
            stale_ips = [
                ip for ip, times in self.requests.items()
                if not times or all(t <= cutoff for t in times)
            ]
            for ip in stale_ips:
                del self.requests[ip]
            self.last_cleanup = now

        # Check rate limit
        if len(self.requests[client_ip]) >= RATE_LIMIT_REQUESTS:
            return Response(
                content="Rate limit exceeded. Please try again later.",
                status_code=429,
                headers={"Retry-After": str(RATE_LIMIT_WINDOW)}
            )

        # Record request
        self.requests[client_ip].append(now)

        # Process request
        return await call_next(request)

def validate_url(url: str) -> bool:
    """Validate URL for security"""
    try:
        parsed = urlparse(url)
        
        # Check for valid scheme
        if parsed.scheme not in ['http', 'https']:
            return False
        
        # Check for local/private IPs
        hostname = parsed.hostname
        if not hostname:
            return False
        
        # Block localhost and private IPs
        blocked_hosts = [
            'localhost', '127.0.0.1', '0.0.0.0',
            '10.', '172.16.', '192.168.'
        ]
        
        for blocked in blocked_hosts:
            if hostname.startswith(blocked):
                return False
        
        return True
    except:
        return False

def validate_path(path: str) -> bool:
    """Validate file paths for security"""
    # Prevent path traversal
    if '..' in path or path.startswith('/'):
        return False
    
    # Only allow specific characters
    if not re.match(r'^[a-zA-Z0-9_\-./]+$', path):
        return False
    
    return True

def setup_security(app):
    """Setup all security middleware"""
    
    # CORS - Configure for production
    origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
    )
    
    # Trusted Host
    allowed_hosts = os.getenv("ALLOWED_HOSTS", "*").split(",")
    if allowed_hosts != ["*"]:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=allowed_hosts
        )
    
    # Security Headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Rate Limiting
    app.add_middleware(RateLimitMiddleware)
    
    return app