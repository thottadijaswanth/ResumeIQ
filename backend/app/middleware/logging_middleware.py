import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from backend.app.utils.logger import logger


class LoggingAndContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        start_time = time.time()

        # Log incoming request
        logger.info(f"[{request_id}] START {request.method} {request.url.path}")

        try:
            response: Response = await call_next(request)
            process_time = (time.time() - start_time) * 1000
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.2f}ms"

            logger.info(
                f"[{request_id}] END {request.method} {request.url.path} "
                f"Status: {response.status_code} in {process_time:.2f}ms"
            )
            return response
        except Exception as e:
            process_time = (time.time() - start_time) * 1000
            logger.error(
                f"[{request_id}] FAILED {request.method} {request.url.path} "
                f"in {process_time:.2f}ms - Error: {str(e)}"
            )
            raise e

