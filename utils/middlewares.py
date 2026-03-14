from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware


class ServicesMiddleware(BaseMiddleware):
    def __init__(self, **services: Any):
        self.services = services

    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any],
    ) -> Any:
        data.update(self.services)
        return await handler(event, data)
