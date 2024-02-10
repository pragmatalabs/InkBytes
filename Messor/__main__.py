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
import asyncio
import concurrent
import json
import logging
import sys
import threading
import time
import nltk


nltk.download('punkt')
from contextlib import contextmanager
from datetime import datetime, date
from typing import List
import pytz
import sys
sys.path.append('/Users/juliandelarosa/Projects/InkBytes/src')
from inkbytes.common import sysdictionary
from inkbytes.common.rest import RestClient
from inkbytes.common.mq import RabbitMQHandler
from inkbytes.models.articles import ArticleCollection
from inkbytes.models.outlets import OutletsSource, OutletsHandler, OutletsDataSource
from scraping.newsscraper import ScraperPool
from scraping.scraper import SessionSavingMode
from collections import deque
from uvicorn import run as uvicornRun

# This will be our local queue to store messages when RabbitMQ is not connected
local_message_queue = deque()
#log_queue = asyncio.Queue()
#queue_handler = AsyncioQueueHandler(log_queue)
LOG_LEVEL = sysdictionary.LOGGING_CONF.get("LOG_LEVEL", logging.INFO)
API_URL = sysdictionary.BACKOFFICE_API_URL
MODULE_NAME = "InkBytes Messor"
logging.basicConfig(level=LOG_LEVEL)


def initialize_backoffice_client():
    backoffice_client = RestClient(API_URL)
    rabbitmq_client = RabbitMQHandler(local_queue_filename="./data/local_queue.json", host="kloudsix.io",
                                      queue_name="messor@scrapes@" + str(date.today().strftime('%Y%m%d')))
    syslogger = logging.getLogger(MODULE_NAME)
    return backoffice_client, syslogger, rabbitmq_client


        

if __name__ == "__main__":
    restclient, logger, rabbitmq_handler = initialize_backoffice_client()
    file_handler = logging.FileHandler("messor.log")
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    #logger.addHandler(file_handler) 
    logger.addHandler(file_handler)
    

def do_exit():
    """
    This method is used to exit the program gracefully.

    :return: None
    """
    sys.exit()


def extract_articles_from_outlet(outlet: OutletsSource) -> ArticleCollection:
    """
    Extract articles from a given outlet.
    :param outlet: The outlet from which to extract articles.
    :return: An ArticleCollection object containing the scraped articles.
    """
    try:
        scraper = ScraperPool(outlet, num_workers=2)
        session = scraper.session.to_json()
        logger.info(f"Scraping articles from '{outlet}'")
        save_scraping_session(session)
        rabbitmq_handler.try_reconnect()
        rabbitmq_handler.publish_message_to_exchange(exchange='inkbytes@', routing_key='hello',
                                                     message=json.dumps(session))

    except ValueError as e:
        logger.error(f"Error scraping articles from '{outlet}': {e}")
        return None


            
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
            response = restclient.send_api_request("GET", f"{sysdictionary.STRAPI_API_ENDPOINTS.get('OUTLETS')}"
                                                          f"?filters[active]=true")
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


def save_scraping_session(scraping_session):
    """
    :param scraping_session: The scraping session to be saved.
    :return: True if the session is successfully saved or sent to API, False otherwise.
    """
    try:

        # Check the value of the SESSION_SAVING_MODE in your .env file
        session_saving_mode = sysdictionary.SCRAPE_SESSION_SAVE_MODE

        if session_saving_mode == SessionSavingMode.SAVE_TO_FILE.value:
            file_path = "path/to/your/scraping_session.json"

            with open(file_path, 'w') as file:
                json.dump(scraping_session, file)
            return True
        elif session_saving_mode == SessionSavingMode.SEND_TO_API.value:

            response = restclient.send_api_request("POST", f"{sysdictionary.STRAPI_API_ENDPOINTS.get('SESSIONS')}/",
                                                   data=scraping_session,
                                                   headers=sysdictionary.STRAPI_API_POST_HEADER)
            return response is not None
        else:
            logger.error("Invalid value for SESSION_SAVING_MODE in .env file.")
            return False

    except Exception as e:
        logger.error(f"Error processing session: {e}")
        return False


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


def perform_action(mode):
    """
    Perform an action based on the given mode.

    :param mode: The mode for the action to perform. Valid values are "SCRAPE" or "EXIT".
    :type mode: str

    :return: None
    """
    if mode == "SCRAPE":
        execute_scraping_process()
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
    start_time = datetime.now(pytz.timezone(sysdictionary.TIME_ZONE))
    logger.info(f"Start time: {start_time}")
    yield
    end_time = datetime.now(pytz.timezone(sysdictionary.TIME_ZONE))
    logger.info(f"End time: {end_time}")


'''def main():


    parser = argparse.ArgumentParser(description="Choose the mode to run the project.")
    parser.add_argument("mode", type=str.upper, choices=["SCRAPE", "DETOX", "EXIT"], help="Mode: SCRAPE, EXIT, DETOX")
    mode = await_command(parser)
    with log_execution_time():  # logging start_time
        perform_action(mode)'''

exit_event = threading.Event()  # Event to signal the threads to exit


def command_input_thread(parser, exit_event):
    while not exit_event.is_set():  # Continue until the event is set
        mode = await_command(parser)
        if mode is None:
            print("Exiting the program.")
            exit_event.set()  # Signal all threads to exit
            break
        with log_execution_time():
            perform_action(mode)

@asyncio.coroutine
def scrape():
    perform_action('SCRAPE')


def main():
    """
    Run the project in the specified mode.

    :return: None
    """
    parser = argparse.ArgumentParser(description="Choose the mode to run the project.")
    parser.add_argument("mode", type=str.upper, choices=["SCRAPE", "DETOX", "EXIT"], help="Mode: SCRAPE, EXIT, DETOX")

    # Start the command input thread
    command_thread = threading.Thread(target=command_input_thread, args=(parser, exit_event))
    command_thread.start()
    uvicornRun("api.main:app", host="0.0.0.0", port=8580)
    # The main thread continues to run the connection monitoring loop
    try:
        while not exit_event.is_set():
            if not rabbitmq_handler.connected:
                rabbitmq_handler.try_reconnect()
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