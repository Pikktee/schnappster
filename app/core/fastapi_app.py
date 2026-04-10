"""FastAPI-App-Klasse mit CORS-freundlicher Middleware-Reihenfolge."""

from typing import Any

from fastapi import FastAPI
from fastapi.middleware.asyncexitstack import AsyncExitStackMiddleware
from starlette.middleware import Middleware
from starlette.middleware.errors import ServerErrorMiddleware
from starlette.middleware.exceptions import ExceptionMiddleware
from starlette.types import ASGIApp, ExceptionHandler


class SchnappsterFastAPI(FastAPI):
    """Wie FastAPI, aber:

    1. User-Middleware (z. B. CORS) liegt **ausserhalb** von `ServerErrorMiddleware`.
       Sonst sendet Starlette 500-Fehler mit barem `send` und der Browser sieht kein
       `Access-Control-Allow-Origin` bei Cross-Origin-Requests.

    2. Nur explizit `500` wird an `ServerErrorMiddleware.handler` gebunden — nicht
       `Exception`. So landet `@app.exception_handler(Exception)` bei
       `ExceptionMiddleware` und durchlaeuft die normale Send-Kette (inkl. CORS).
       Unbehandelte Ausnahmen behandelt weiterhin `ServerErrorMiddleware` mit
       Standard-500, jetzt aber **innerhalb** von CORS.
    """

    def build_middleware_stack(self) -> ASGIApp:
        debug = self.debug
        error_handler: ExceptionHandler | None = None
        exception_handlers: dict[Any, ExceptionHandler] = {}

        for key, value in self.exception_handlers.items():
            if key == 500:
                error_handler = value
            else:
                exception_handlers[key] = value

        middleware = (
            self.user_middleware
            + [Middleware(ServerErrorMiddleware, handler=error_handler, debug=debug)]
            + [
                Middleware(ExceptionMiddleware, handlers=exception_handlers, debug=debug),
                Middleware(AsyncExitStackMiddleware),
            ]
        )

        app = self.router
        for cls, args, kwargs in reversed(middleware):
            app = cls(app, *args, **kwargs)
        return app
