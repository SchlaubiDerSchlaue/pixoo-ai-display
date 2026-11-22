from typing import Annotated, Literal

from a2wsgi import WSGIMiddleware
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import Field, StrictBool
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import Headers
from starlette.responses import JSONResponse

from . import main


mcp = FastMCP(
    'Pixoo AI Display',
    stateless_http=True,
    json_response=True,
    # The ASGI entry point validates Origin against the incoming LAN or proxy address.
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


@mcp.tool()
async def show_message(
    text: Annotated[str, Field(min_length=1, max_length=main.MAX_CHARS)],
    theme: Literal['night', 'green', 'warm', 'red'] = 'night',
) -> dict[str, bool]:
    """Zeigt eine kurze Nachricht auf dem Pixoo 64 an."""
    await run_in_threadpool(main.show_message, text, theme)
    return {'ok': True}


@mcp.tool()
async def set_brightness(brightness: Annotated[int, Field(strict=True, ge=0, le=100)]) -> dict[str, int | bool]:
    """Setzt die Helligkeit des Pixoo auf einen Wert von 0 bis 100."""
    return await run_in_threadpool(main.set_brightness, brightness)


@mcp.tool()
async def set_power(on: StrictBool) -> dict[str, bool]:
    """Schaltet das Pixoo-Display mit true ein oder mit false aus."""
    return await run_in_threadpool(main.set_power, on)


mcp_app = mcp.streamable_http_app()
flask_app = WSGIMiddleware(main.app, workers=4)


async def app(scope, receive, send):
    if scope['type'] == 'lifespan':
        await mcp_app(scope, receive, send)
        return
    if scope['type'] != 'http' or scope['path'] != '/mcp':
        await flask_app(scope, receive, send)
        return

    headers = Headers(scope=scope)
    origin = headers.get('origin')
    if origin is not None and origin != f"{scope['scheme']}://{headers.get('host', '')}":
        response = JSONResponse({'error': 'Ungültiger Origin'}, status_code=403)
        await response(scope, receive, send)
        return
    if not main.authorized(headers.get('authorization', '')):
        response = JSONResponse(
            {'error': 'Ungültiger oder fehlender Bearer-Token'},
            status_code=401,
            headers={'WWW-Authenticate': 'Bearer'},
        )
        await response(scope, receive, send)
        return
    await mcp_app(scope, receive, send)
