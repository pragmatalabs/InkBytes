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
import sys
from datetime import datetime
from typing import List
import pytz
import requests
import Logger
import SysDictionary
from Outlets import OutletsSource, OutletsHandler
from Rest import RestClient
from NewsScraper import ScrapperPool
from Articles import ArticleCollection

logger = Logger.get_logger(__name__)


def do_exit():
    """
    This method is used to exit the program gracefully.

    :return: None
    """
    sys.exit()


"""Create an instance of the RestClient"""
restclient = RestClient(SysDictionary.BACKOFFICE_API_URL)


def extract_articles_from_outlet(outlet: OutletsSource) -> ArticleCollection:
    """
    Extract articles from a given outlet.

    :param outlet: The outlet from which to extract articles.
    :return: An ArticleCollection object containing the scraped articles.
    """
    try:
        scraper = ScrapperPool(outlet, num_workers=4)
        session = scraper.session
        save_scrapping_session(session)
    except ValueError as e:
        logger.error(f"Error scraping articles from '{outlet}': {e}")
        return None


def get_outlets() -> List[OutletsSource]:
    """
    Retrieves the list of news outlets from the server.
    :return: The list of news outlets.
    :rtype: List[SourceOutlet]
    :raises RuntimeError: If there is an error getting the outlets endpoint.
    """
    outlets_handler = OutletsHandler()
    try:
        response = restclient.send_api_request("GET", "outletssources?filters[active]=true")
        if response:
            payload = response['data']
            for outlet in payload:
                outlet_source = OutletsSource(**outlet)
                outlets_handler.add(outlet_source)
            return outlets_handler.news_outlets
    except ValueError as error:
        raise RuntimeError(f"Error getting outlets endpoint, reason: {error}") from error


def save_scrapping_session(scrapping_session):
    """
    :param scrapping_session: The scrapping session to be saved.
    :return: The response from the API call.
    """
    try:
        session_dict = scrapping_session.to_json()
        response = restclient.send_api_request("POST", "scrapesessions/",
                                               data=session_dict,
                                               headers=SysDictionary.STRAPI_API_POST_HEADER)
        return response
    except requests.exceptions.RequestException as e:
        logger.error(f"Error saving session: {e}")


def execute_scrape() -> List[ArticleCollection]:
    """
    Executes the scrape process to extract articles from outlets.

    :return: A list of ArticleCollection objects containing the extracted articles.
    :rtype: List[ArticleCollection]
    """
    try:
        outlets = get_outlets()
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
                break
            args = parser.parse_args([choice])
            mode = args.mode
            return mode
        except KeyboardInterrupt:
            logger.exception("Bye!!! Hasta La Vista \n Inkpills Grabit v1c\n system exited by keyboard interrupt")
            raise SystemExit


def perform_action(mode):
    """
    Perform an action based on the given mode.

    :param mode: The mode for the action to perform. Valid values are "SCRAPE" or "EXIT".
    :type mode: str

    :return: None
    """
    if mode == "SCRAPE":
        execute_scrape()
    elif mode == "EXIT":
        do_exit()
    else:
        print("Invalid mode!")


def log_execution_time():
    """
    Logs the start and end time of code execution.

    :return: None
    """
    start_time = datetime.now(pytz.timezone(SysDictionary.TIME_ZONE))
    logger.info(f"Start time: {start_time}")
    end_time = datetime.now(pytz.timezone(SysDictionary.TIME_ZONE))
    logger.info(f"End time: {end_time}")


def main():
    """
    Run the project in the specified mode.

    :return: None
    """

    parser = argparse.ArgumentParser(description="Choose the mode to run the project.")
    parser.add_argument("mode", type=str.upper, choices=["SCRAPE", "DETOX", "EXIT"], help="Mode: SCRAPE, EXIT, DETOX")

    mode = await_command(parser)

    log_execution_time()  # logging start_time
    perform_action(mode)
    log_execution_time()  # logging end_time


def run():
    """
    Run method to execute the main function.

    :return: None
    """
    main()


if __name__ == "__main__":
    run()
