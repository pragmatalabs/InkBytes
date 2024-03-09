"""
Author: Julian Delarosa (juliandelarosa@icloud.com)
Date: 2023-07-14
Version: 1.0
Description:
    This is the main file of the URI Harvest program. It is used to scrape news from various sources, including local files,
    shared files, URIs, URLs, and Agent Mode.
System: Messor URI Harvest v1.0
Language: Python 3.10
License: MIT License
"""
import argparse
import concurrent
import json
import logging
import os
import threading
import time
from contextlib import contextmanager
from datetime import datetime, date
from typing import List
import pytz
import sys
import nltk
from dotenv import load_dotenv

from inkbytes.common.system.digital_ocean_spaces import DigitalOceanSpacesHandler
from inkbytes.common.system.log_formatters import (log_function_activity,
                                                   CEFLogFormatter,
                                                   EnhancedSyslogFormatter)
from inkbytes.common.system.rabbit_log_handler import RabbitMQLoggingHandler
from inkbytes.common import sysdictionary
from inkbytes.common.api.rest import RestClient
from inkbytes.common.api.ampq_mq import RabbitMQHandler
from inkbytes.models.articles import ArticleCollection
from inkbytes.models.outlets import (OutletsSource,
                                     OutletsHandler,
                                     OutletsDataSource)
from inkbytes.common.system.module_handler import get_module_name
from inkbytes.common.system.config_loader import ConfigLoader
from scraping.newsscraper import ScraperPool
from scraping.scraper import SessionSavingMode
from collections import deque
from spaces.staging_area_handler import upload_directory
from uvicorn import run as uvicornRun

# Load environment variables from .env file
load_dotenv()
nltk.download('punkt')
sysdictionary = ConfigLoader('./env.yaml')

# Access the environment variables
LOG_LEVEL = sysdictionary.__('logging.level')
logging.basicConfig(level=LOG_LEVEL)

# LOG_LEVEL = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
API_URL = sysdictionary.__('strapi_cms.base_url')
LOCAL_QUEUE_FILE_NAME = sysdictionary.__('storage.offline.local.queue.file')
LOGS_FOLDER = sysdictionary.__('logging.folder')
LOG_FILE_NAME = os.path.join(LOGS_FOLDER, sysdictionary.__('logging.file_name'))
RABBIT_HOST_NAME = sysdictionary.__('rabbitmq.host')
RABBIT_HOST_PORT = int(sysdictionary.__('rabbitmq.port'))
RABBIT_USERNAME = sysdictionary.__('rabbitmq.username')
RABBIT_PASSWORD = sysdictionary.__('rabbitmq.password')
SCRAPE_QUEUE_NAME = sysdictionary.__('rabbitmq.queues.scraping.name')
LOG_EXCHANGE_NAME = sysdictionary.__('rabbitmq.exchanges.logging.name')
LOG_QUEUE_NAME = sysdictionary.__('rabbitmq.queues.logging.name')
SCRAPE_AGENT = sysdictionary.__('scraping.agent.default')
SCRAPE_HEADERS = sysdictionary.__('scraping.headers.default')
MODULE_NAME = get_module_name(2)
root_logger = logging.getLogger()
# This will be our local queue to store messages when RabbitMQ is not connected
local_message_queue = deque()
exit_event = threading.Event()


@log_function_activity(root_logger)
def initialize_backoffice_client():
    backoffice_client = RestClient(API_URL)
    rabbitmq_client = RabbitMQHandler(local_queue_filename=LOCAL_QUEUE_FILE_NAME,
                                      exchange_name='inkbytes@',
                                      host=RABBIT_HOST_NAME,
                                      queue_name=SCRAPE_QUEUE_NAME + str(date.today().strftime('%Y%m%d')))
    syslogger = logging.getLogger(MODULE_NAME)
    return backoffice_client, syslogger, rabbitmq_client


if __name__ == "__main__":
    restclient, logger, rabbitmq_handler = initialize_backoffice_client()
    file_handler = logging.FileHandler(LOG_FILE_NAME)
    # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    formatter = CEFLogFormatter(vendor="InkBytes", product="Messor", version="1.0", signature="EventID",
                                name="EventName", severity="5")
    file_handler.setFormatter(formatter)

    # Create and configure RabbitMQ handler
    rabbit_handler = RabbitMQLoggingHandler(host=RABBIT_HOST_NAME,
                                            local_queue_filename=LOCAL_QUEUE_FILE_NAME,
                                            queue_name=LOG_QUEUE_NAME,
                                            exchange_name=LOG_EXCHANGE_NAME,
                                            routing_key="logs",
                                            port=RABBIT_HOST_PORT,
                                            user_name=RABBIT_USERNAME,
                                            password=RABBIT_PASSWORD
                                            )
    rabbit_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    syslog_formatter = EnhancedSyslogFormatter(app_name="Messor")
    rabbit_handler.setFormatter(syslog_formatter)
    # Add the handler to the logger
    logger.root.addHandler(file_handler)
    root_logger.root.addHandler(rabbit_handler)
    # logger.addHandler(rabbit_handler)
    # logger.addHandler(file_handler)


def do_exit():
    """
    This method is used to exit the program gracefully.
    :return: None
    """
    sys.exit()


@log_function_activity(root_logger)
def extract_articles_from_outlet(outlet: OutletsSource) -> ArticleCollection:
    """
    Extract articles from a given outlet.
    :param outlet: The outlet from which to extract articles.
    :return: An ArticleCollection object containing the scraped articles.
    """
    try:
        scraper = ScraperPool(outlet, agent=SCRAPE_AGENT, headers=SCRAPE_HEADERS, num_workers=2)
        session = scraper.session.to_json()
        logger.info(f"Scraping articles from '{outlet}'")
        save_scraping_session(session)
        # rabbitmq_handler.connect_to_rabbitmq()
        rabbitmq_handler.publish_message_to_exchange(exchange='inkbytes@', routing_key='hello',
                                                     message=json.dumps(session))

    except ValueError as e:
        logger.error(f"Error scraping articles from '{outlet}': {e}")
        return None


@log_function_activity(root_logger)
def get_outlets(source=OutletsDataSource.REST_API) -> List[OutletsSource]:
    """
    Retrieves the list of news outlets from the server or a .json file.
    :param source: The source of the outlets (REST API or .json file).
    :type source: OutletsSource, optional
    :return: The list of news outlets.
    :rtype: List[OutletsSource]
    :raises RuntimeError: If there is an error getting the outlets.
    """
    outlets_handler = OutletsHandler()

    try:
        if source == OutletsDataSource.REST_API:
            response = (
                restclient.
                send_api_request
                ("GET", f"{sysdictionary.__('strapi_cms.endpoints.outlets')}"f"?filters[active]=true"))

            if response:
                payload = response['data']
        elif source == OutletsDataSource.JSON_FILE:
            with open('outlets.json', 'r') as json_file:
                payload = json.load(json_file)
        else:
            raise ValueError("Invalid source specified")
        outlets_handler.add_outlets_from_payload(payload)
        return outlets_handler.news_outlets

    except ValueError as error:
        raise RuntimeError(f"Error getting outlets, reason: {error}") from error


@log_function_activity(root_logger)
def move_scrapes_to_digitalocean(space: str = ''):
    # Specify your local directory, Space name, and optional target prefix
    LOCAL_DIRECTORY = sysdictionary.__('storage.staging.local.scraping')
    SPACE_NAME = sysdictionary.__('digitalocean.spaces.buckets.' + space)
    TARGET_PREFIX = str(date.today().strftime('%Y%m%d'))
    # Execute the upload
    spaces_handler = DigitalOceanSpacesHandler(
        access_id=sysdictionary.__('digitalocean.access_id'),
        secret_key=sysdictionary.__('digitalocean.secret_key'),
        region_name=sysdictionary.__('digitalocean.region'),
        endpoint_url=sysdictionary.__('digitalocean.endpoint_url'))

    upload_directory(LOCAL_DIRECTORY, SPACE_NAME, TARGET_PREFIX, spaces_handler)


@log_function_activity(root_logger)
def save_scraping_session(scraping_session):
    """
    :param scraping_session: The scraping session to be saved.
    :return: True if the session is successfully saved or sent to API, False otherwise.
    """
    try:

        # Check the value of the SESSION_SAVING_MODE in your .env file
        session_saving_mode = sysdictionary.__('scraping.save_mode')

        if session_saving_mode == SessionSavingMode.SAVE_TO_FILE.value:
            file_path = "path/to/your/scraping_session.json"

            with open(file_path, 'w') as file:
                json.dump(scraping_session, file)
            return True
        elif session_saving_mode == SessionSavingMode.SEND_TO_API.value:
            post_headers = {
                "Authorization": 'Bearer ' + sysdictionary.__('strapi_cms.token'),
                'Content-Type': sysdictionary.__('strapi_cms.post_headers.content_type'), }
            response = restclient.send_api_request("POST", f"{sysdictionary.__('strapi_cms.endpoints.session')}/",
                                                   data=scraping_session,
                                                   headers=post_headers)
            return response is not None
        else:
            logger.error("Invalid value for SESSION_SAVING_MODE in .env file.")
            return False

    except Exception as e:
        logger.error(f"Error processing session: {e}")
        return False


@log_function_activity(root_logger)
def execute_scraping_process() -> List[ArticleCollection]:
    """
    Executes the scrape process to extract articles from outlets.
    
    :return: A list of ArticleCollection objects containing the extracted articles.
    :rtype: List[ArticleCollection]
    """
    try:
        outlets = get_outlets(OutletsDataSource.REST_API)
    except ValueError as e:
        logger.error(f"Error executing scrape: {e}")
        return []

    if not outlets:
        logger.warning("No outlets found")
        return []

    articles_collections = []

    # Check the number of outlets
    if len(outlets) > 1:
        # Use multithreading only if there are more than 1 outlets
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {executor.submit(extract_articles_from_outlet, outlet): outlet for outlet in outlets}
            for future in concurrent.futures.as_completed(futures):
                articles_collection = future.result()
                if articles_collection is not None:
                    articles_collections.append(articles_collection)
    else:
        # If there is only one outlet, don't use multithreading
        for outlet in outlets:
            articles_collection = extract_articles_from_outlet(outlet)
            if articles_collection is not None:
                articles_collections.append(articles_collection)

    return articles_collections


def await_command(parser):
    """
    :param parser: The argument parser object used to parse the command entered by the user.
    :return: The mode specified by the user's command.
    """
    while True:
        try:
            choice = input("Insert command to run: ")
            if choice.upper() == 'EXIT':
                return None  # Return None to indicate that the exit command was received
            args = parser.parse_args([choice])
            mode = args.mode
            return mode
        except KeyboardInterrupt:
            logger.exception("Bye!!! Hasta La Vista \n Inkpills Grabit v1c\n system exited by keyboard interrupt")
            return None


@log_function_activity(root_logger)
def perform_action(mode):
    """
    Perform an action based on the given mode.

    :param mode: The mode for the action to perform. Valid values are "SCRAPE" or "EXIT".
    :type mode: str

    :return: None
    """
    if mode == "SCRAPE":
        execute_scraping_process()
    elif mode == "MOVE":
        move_scrapes_to_digitalocean('scraping')
    elif mode == "EXIT":
        do_exit()
    else:
        print("Invalid mode!")


@contextmanager
def log_execution_time():
    """
    Logs the start and end time of code execution.
    :return: None
    """
    time_zone = sysdictionary.__('application.time_zone')
    start_time = datetime.now(pytz.timezone(time_zone))
    logger.info(f"Start time: {start_time}")
    yield
    end_time = datetime.now(pytz.timezone(time_zone))
    logger.info(f"End time: {end_time}")


# Event to signal the threads to exit


def command_input_thread(parser, exit_event):
    while not exit_event.is_set():  # Continue until the event is set
        mode = await_command(parser)
        if mode is None:
            print("Exiting the program.")
            exit_event.set()  # Signal all threads to exit
            break
        with log_execution_time():
            perform_action(mode)


@log_function_activity(root_logger)
async def scrape():
    perform_action('SCRAPE')


@log_function_activity(root_logger)
async def move():
    perform_action('MOVE')


def main():
    """
    Run the project in the specified mode.

    :return: None
    """
    parser = argparse.ArgumentParser(description="Choose the mode to run the project.")
    parser.add_argument("mode", type=str.upper, choices=["SCRAPE", "MOVE", "DETOX", "EXIT"],
                        help="Mode: SCRAPE, EXIT, DETOX")

    # Start the command input thread
    command_thread = threading.Thread(target=command_input_thread, args=(parser, exit_event))
    command_thread.start()
    uvicornRun("api.main:app", host="0.0.0.0", port=8585, log_level="info")

    # The main thread continues to run the connection monitoring loop
    try:
        while not exit_event.is_set():
            if not rabbitmq_handler.connected:
                rabbitmq_handler.connect_to_rabbitmq()
            time.sleep(100)  # Check connection status every 10 seconds
    finally:
        # When exiting, make sure to join the thread and clean up resources
        exit_event.set()  # Ensure the event is set to stop the thread
        command_thread.join()  # Wait for the command thread to finish
        print("Program exited cleanly.")


def run():
    """
    Run method to execute the main function.
    """
    main()


if __name__ == "__main__":
    run()
