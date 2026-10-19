import json
import base64
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from app.core.redis import redis_client

class IdempotencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Look for the idempotency header
        idempotency_key = request.headers.get("x-idempotency-key")
        
        if not idempotency_key:
            return await call_next(request)

        redis_key = f"idemp:{idempotency_key}"

        # 2. Check if key exists in Redis
        cached_state = await redis_client.get(redis_key)
        
        if cached_state == "IN_FLIGHT":
            return JSONResponse(
                status_code=409,
                content={"detail": "Operation is currently processing. Please wait."}
            )
        
        if cached_state:
            # 3. Request is already resolved. Return cached HTTP response.
            cached_data = json.loads(cached_state)
            
            # Remove content-length as it will be recalculated by Starlette
            headers = cached_data["headers"]
            headers.pop("content-length", None)
            
            return Response(
                content=base64.b64decode(cached_data["body"]),
                status_code=cached_data["status_code"],
                headers=headers,
                media_type=cached_data["media_type"],
            )

        # 4. Not present: Set IN_FLIGHT lock (TTL: 5 minutes / 300s)
        # nx=True ensures this fails if another request sets it milliseconds prior
        set_success = await redis_client.set(redis_key, "IN_FLIGHT", ex=300, nx=True)
        if not set_success:
            return JSONResponse(
                status_code=409,
                content={"detail": "Operation is currently processing. Please wait."}
            )

        try:
            # 5. Execute the actual request
            response = await call_next(request)
            
            # Extract body from the StreamingResponse
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            
            # Serialize the response state. 
            # We base64 encode the body to safely store JSON, HTML, or raw PDFs.
            cache_data = {
                "status_code": response.status_code,
                "media_type": response.media_type,
                "headers": dict(response.headers),
                "body": base64.b64encode(body).decode("utf-8")
            }

            # 6. Cache final response (TTL: 24 hours / 86400s)
            await redis_client.set(redis_key, json.dumps(cache_data), ex=86400)

            # Reconstruct and return the response
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
            
        except Exception as e:
            # On failure, clear the lock so the user can safely retry
            await redis_client.delete(redis_key)
            raise e