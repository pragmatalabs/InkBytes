import os
import sys
import asyncio
from typing import List
from fastapi import APIRouter, WebSocket

from api.utils.api_security import _handle_invalid_api_key, _api_key_is_valid

sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))
from __main__ import scrape as scrape
from api.utils.log_readers import file_log_reader

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket, api_key: str) -> bool:
        if _api_key_is_valid(api_key):
            await websocket.send_text(f'Accepted api key: {api_key}')
            self.active_connections.append(websocket)
            return True
        else:
            await _handle_invalid_api_key(websocket)
            return False

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)


@router.websocket_route(f"/ws/scrape")
async def websocket_scrape(websocket: WebSocket):
    manager = ConnectionManager()
    await websocket.accept()
    api_key = websocket.query_params.get("api_key")
    valid_connection = await manager.connect(websocket, api_key)
    if valid_connection:
        await websocket.send_text(f"Api Key: {api_key} valid")
        await websocket.send_text("Welcome to the scraping websocket!")
        try:
            if await websocket.receive_text() == "start_scrape":
                await websocket.send_text("Scrape initiated.")
                await manage_scrape(websocket)
            else:
                await websocket.send_text("Unknown command. Send 'start_scrape' to start scraping.")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await websocket.send_text("Closing websocket connection.")
            await websocket.close()


async def manage_scrape(websocket: WebSocket):
    scrape_task = asyncio.create_task(scrape())
    async for message in file_log_reader(60):
        await websocket.send_text(message)
        if scrape_task.done():
            break
    await scrape_task
    await websocket.send_text("Scraping completed successfully.")
