import json
from typing import List
from inkbytes.common.api.rest import RestClient
from inkbytes.models.outlets import OutletsDataSource


# API Class to manage outlets
class OutletsManagerAPI:
    def __init__(self, api_url, endpoint, local_file=""):

        self.endpoint = endpoint
        self.api_url = api_url

    def get_outlets(self, source=OutletsDataSource.REST_API) -> List[OutletsDataSource]:
        """
        Retrieves the list of news outlets from the server or a .json file.
        :param source: The source of the outlets (REST API or .json file).
        :type source: OutletsSource, optional
        :return: The list of news outlets.
        :rtype: List[OutletsSource]
        :raises RuntimeError: If there is an error getting the outlets.
        """
        try:
            outlets_payload = self.get_outlets_payload(source)
            #outlets = self.create_outlets_from_payload(outlets_payload)
            return outlets_payload[0:2]
        except ValueError as error:
            raise RuntimeError(f"Error getting outlets, reason: {error}") from error

    def get_outlets_payload(self, source):
        if source == OutletsDataSource.REST_API:
            return self.get_rest_api_payload()
        elif source == OutletsDataSource.JSON_FILE:
            return self.get_json_file_payload()
        else:
            raise ValueError("Invalid source specified")

    def get_json_file_payload(self):
        with open(self.local_file, 'r') as json_file:
            return json.load(json_file)

    def get_rest_api_payload(self):
        restclient = RestClient(self.api_url)
        endpoint = self.endpoint
        response = restclient.send_api_request("GET", f"{endpoint}?filters[active]=true")
        if response:
            print(response)
            return response['data']
        else:
            return []
