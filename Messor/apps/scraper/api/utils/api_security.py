from starlette.websockets import WebSocket


def _api_key_is_valid(api_key: str) -> bool:
    valid_api_keys = ['ghyuhjbjhjhhjhjhj']  # Make sure this includes your actual API key
    return api_key in valid_api_keys


async def _handle_invalid_api_key(websocket: WebSocket):
    await websocket.send_text('Invalid API key')
    await websocket.close(code=4001)  # Custom close code
