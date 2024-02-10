import os
import sys
from fastapi import  APIRouter, WebSocket
import asyncio
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))
from __main__ import scrape as scrape
from log_readers import file_log_reader

router = APIRouter()

@router.websocket_route("/ws/scrape")
async def websocket_scrape(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("Welcome to the scraping websocket!")
    try:
        data = await websocket.receive_text()
        if data == "start_scrape":
            scrape_task = asyncio.create_task(scrape())
            async for message in file_log_reader(10):
                await websocket.send_text(message)
                if scrape_task.done():
                        break
            await scrape_task
            await websocket.send_text("Scraping completed successfully.")
        else:
            await websocket.send_text("Unknown command. Send 'start_scrape' to initiate scraping.")
    except Exception as e:
        # Consider using logging.error(e) after importing logging
        print(f"Error: {e}")
    finally:
        await websocket.send_text("Closing websocket connection.")
        await websocket.close()
    