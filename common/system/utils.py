from datetime import datetime, timedelta
from typing import List, Any
import numpy as np


def generate_threshold_timestamp(n_minutes):
    current_GMT = datetime.utcnow()
    last_n_minutes = current_GMT - timedelta(minutes=n_minutes)
    last_n_minutes_start = datetime(
        last_n_minutes.year, last_n_minutes.month, last_n_minutes.day,
        last_n_minutes.hour
    )
    timestamp = int(last_n_minutes_start.timestamp())
    return timestamp
def generate_today_timestamp():
    current_GMT = datetime.utcnow()
    today_start = datetime(
        current_GMT.year, current_GMT.month, current_GMT.day, 0, 0, 0
    )
    timestamp = int(today_start.timestamp())
    return timestamp

# Convert numpy to list
def convert_numpy_to_list(data):
    if isinstance(data, np.ndarray):
        return data.tolist()
    return data

def create_object_list_chunks(objects: List[Any], chunk_size: int) -> List[List[Any]]:
    """Divide a list of objects into specified chunks.

    Args:
        objects (List[Any]): The list of objects to be chunked.
        chunk_size (int): The desired number of objects in each chunk.

    Returns:
        List[List[Any]]: A list of lists, where each sublist is a chunk of the original list.
    """
    # Create chunks from the list
    return [objects[i:i + chunk_size] for i in range(0, len(objects), chunk_size)]
