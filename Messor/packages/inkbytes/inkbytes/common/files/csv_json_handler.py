import shutil
import zipfile
import os
import json
import csv
import tinydb as db
import pandas as pd
from tinydb import TinyDB
from datetime import datetime as _dt_


def validateJSON(filePath):
    try:
        with open(filePath, 'r') as file:
            json.load(file)  # Reading JSON data from a file.
    except ValueError as err:
        return False
    return True


def tinydb_to_csv(tinydb_path, csv_path):
    for filename in os.listdir(tinydb_path):
        if not os.path.isdir(filename) and filename.endswith(".json"):
            file_path = os.path.join(tinydb_path, filename)
            process_file(file_path, csv_path)


def json_to_csv(json_path, csv_path):
    for filename in os.listdir(json_path):
        if not os.path.isdir(filename) and filename.endswith(".json"):
            file_path = os.path.join(json_path, filename)
            process_file(file_path, csv_path)


def convert_csv_to_json(destination_dir, csv_origin_file, json_destination_file, json_format="tinydb"):
    # Replace with your CSV file path
    csv_origin_file = os.path.join(destination_dir, csv_origin_file)
    df = pd.read_csv(csv_origin_file)
    # Convert the DataFrame to JSON format
    json_data = df.to_json(orient='records')
    # Save the JSON data to a file
    json_destination_file = json_destination_file + ".json"  # Replace with the desired output JSON file path
    json_file = os.path.join(destination_dir, json_destination_file)
    if json_format == "tinydb":
        dbjson = TinyDB(json_file)
        data = json.loads(json_data)
        table = dbjson.table('_default')
        table.insert_multiple(data)
    if json_format == "raw":
        with open(json_file, 'w') as f:
            f.write(json_data)
    print(f"CSV data converted and saved to {json_file} in JSON format.")
    return json_file


def move_file_to_folder(source_file, destination_folder):
    # Create the destination folder if it doesn't exist
    os.makedirs(destination_folder, exist_ok=True)

    # Get the filename from the source file path
    filename = os.path.basename(source_file)

    # Construct the destination path
    destination_path = os.path.join(destination_folder, filename)

    # Move the file to the destination folder
    shutil.move(source_file, destination_path)
    print(f"File '{filename}' moved to '{destination_folder}'")
    pass


def filename_watermark():
    watermark = _dt_.strftime(_dt_.now(), '%Y%m%d%H')
    return watermark


def unify_jsondb_files_to_df(input_path: str = "", output_path: str = "",extension="db.json") -> pd.DataFrame:
    if not input_path:  # If the input path is empty, return an empty DataFrame
        print("No input path provided.")
        return pd.DataFrame()
    read_files = []  # List to store all records from all files
    for filename in os.listdir(input_path):
        input_file = os.path.join(input_path, filename)
        if input_file.endswith(extension):
            try:
                if validateJSON(input_file):
                    tinydb = TinyDB(input_file)
                    items = tinydb.all()  # Fetch all records from the TinyDB JSON file
                    read_files.extend(items)  # Extend the list with these records
                else:
                    print(f"Skipping {input_file} as it is not a valid JSON file.")
            except Exception as e:
                print(f"Error reading {input_file}: {e}")

    dfx = pd.DataFrame(read_files)  # Create a DataFrame from aggregated records
    if output_path:  # Optionally, save the DataFrame to a file
        dfx.to_csv(output_path, index=False)
    return dfx


def clean_staging_db_files(input_path: str = "", output_path: str = "",extension=".json"):
    watermark = filename_watermark()
    zip_path = os.path.join(output_path, f"processed_files.{watermark}.hist.zip")
    # Crear un archivo ZIP para almacenar los archivos procesados
    with zipfile.ZipFile(zip_path, 'w') as myzip:
        for filename in os.listdir(input_path):
            input_file = os.path.join(input_path, filename)
            if input_file.endswith(extension):
                try:
                    # Agregar el archivo .json al archivo ZIP
                    myzip.write(input_file, arcname=filename)

                    # Opcional: Eliminar el archivo luego de agregarlo al ZIP
                    # os.remove(input_file)
                except Exception as e:
                    print(e)
    # Opcional: Si quieres eliminar los archivos JSON después de zipearlos todos, descomenta la siguiente sección
    for filename in os.listdir(input_path):
        file_path = os.path.join(input_path, filename)
        if file_path.endswith(".json"):
            os.remove(file_path)


def convert_json_files_to_csv(input_dir, output_dir, tinydb_format=False):
    """
    Converts all JSON files in the input directory to CSV files in the output directory.

    Parameters:
    input_dir (str): The path to the directory containing input JSON files.
    output_dir (str): The path to the directory where output CSV files will be saved.
    tinydb_format (bool): Set to True if the JSON files are in TinyDB format. Default is False.
    """
    # Ensure the output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Iterate over all files in the input directory
    for filename in os.listdir(input_dir):
        if filename.endswith(".json"):
            # Construct full file paths
            input_json_path = os.path.join(input_dir, filename)
            output_csv_path = os.path.join(output_dir, filename.replace('.json', '.csv'))

            # Convert JSON to CSV based on the format
            if tinydb_format:
                tinydb_to_csv(input_json_path, output_csv_path)
            else:
                json_to_csv(input_json_path, output_csv_path)

            print(f"Converted {filename} to CSV.")


def convert_csv_to_json(destination_dir, csv_origin_file_name, json_destination_file_name, json_format="tinydb"):
    """
    Converts a CSV file to a JSON file, supporting 'tinydb' or 'raw' JSON formats.

    Parameters:
    - destination_dir: Directory where the output JSON will be saved.
    - csv_origin_file_name: Name of the input CSV file.
    - json_destination_file_name: Name of the output JSON file without extension.
    - json_format: Format of the output JSON. Supported values are 'tinydb' and 'raw'.
    """
    # Construct file paths
    csv_file_path = os.path.join(destination_dir, csv_origin_file_name)
    json_file_path = os.path.join(destination_dir, f"{json_destination_file_name}.json")

    try:
        # Load the CSV file into a DataFrame
        df = pd.read_csv(csv_file_path)

        # Convert the DataFrame to JSON format
        json_data = df.to_json(orient='records')

        # Process JSON data according to the specified format
        if json_format == "tinydb":
            output_db = db.TinyDB(json_file_path)
            data = json.loads(json_data)
            table = output_db.table('_default')
            table.insert_multiple(data)
        elif json_format == "raw":
            with open(json_file_path, 'w') as f:
                f.write(json_data)
        else:
            raise ValueError(f"Unsupported JSON format: {json_format}")
        print(f"CSV data converted and saved to {json_file_path} in {json_format} format.")
        return json_file_path

    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def load_csv_file_to_dataframe(input_file) -> pd.DataFrame:
    """
    Loads a CSV file into a pandas DataFrame.

    Parameters:
    input_file (str): The path to the input CSV file.

    Returns:
    pandas.DataFrame: The DataFrame containing the CSV data.
    """
    df = pd.read_csv(input_file, dtype={1: str, 2: str, 3: str, 4: str, 5: str})
    return df


def load_json_file_to_dataframe(input_file) -> pd.DataFrame:
    """
    Loads a CSV file into a pandas DataFrame.

    Parameters:
    input_file (str): The path to the input CSV file.

    Returns:
    pandas.DataFrame: The DataFrame containing the CSV data.
    """
    df = pd.read_json(input_file, dtype={1: str, 2: str, 3: str, 4: str, 5: str})
    return df


def load_csv_files_to_dataframes(input_dir) -> [pd.DataFrame]:
    """
    Loads all CSV files from the specified directory into an array of pandas DataFrames.

    Parameters:
    input_dir (str): The path to the directory containing CSV files.

    Returns:
    list of pandas.DataFrame: A list containing a DataFrame for each CSV file in the input directory.
    """
    dataframes: [pd.DataFrame] = []  # Initialize an empty list to store the DataFrames

    # Iterate over all files in the input directory
    for filename in os.listdir(input_dir):
        if filename.endswith(".csv"):
            # Construct the full file path
            file_path = os.path.join(input_dir, filename)

            # Load the CSV file into a DataFrame
            df = pd.read_csv(file_path, dtype={1: str, 2: str, 3: str, 4: str, 5: str})

            # Append the DataFrame to the list
            dataframes.append(df)
            # df.shape
            print(f"Loaded {filename} into a DataFrame.")

    return dataframes


def load_json_files_to_dataframes(input_dir) -> pd.DataFrame:
    dataframes = []  # Initialize an empty list to store the DataFrames

    # Iterate over all files in the input directory
    for filename in os.listdir(input_dir):
        if filename.endswith(".json"):
            # Construct the full file path
            file_path = os.path.join(input_dir, filename)

            # Load the CSV file into a DataFrame
            df = pd.read_json(file_path, dtype={1: str, 2: str, 3: str, 4: str, 5: str})

            # Append the DataFrame to the list
            dataframes.append(df)
            # df.shape
            print(f"Loaded {filename} into a DataFrame.")

    return dataframes

def parse_json(data):
    """Utility function to parse JSON safely."""
    if isinstance(data, str):
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return []
    return data if isinstance(data, list) else []
def process_file(file_path, csv_path):
    ids = []
    with open(csv_path, 'a', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(
            ['id', 'category', 'headline', 'short_description', 'keywords'])
        with open(file_path, 'r') as file:
            if file_path.endswith(".json"):
                try:
                    data = json.load(file)
                    # db = data['_default']
                    tinydb = db.TinyDB(file_path)
                    items = tinydb.all()
                    for record in items:
                        # Directly access 'id', assuming it's always present
                        id = record["id"]
                        # Handle 'category' with a fallback for missing key
                        category = record["category"] if "category" in record else ""
                        # Directly access 'title', assuming it's always present
                        headline = record["title"]
                        # Handle 'text' with a fallback for missing key
                        short_description = record["text"].replace('\n', ' ') if "text" in record else ""
                        # Handle 'summary' with a fallback for missing key
                        # summary = record["summary"].replace('\n', ' ') if "summary" in record else ""
                        # Handle 'section' with a fallback for missing key
                        # section = record["metadata"].find("section") if "metdata" in record else ""
                        # Handle 'keywords' with a fallback for missing key
                        keywords = ';'.join(record["keywords"]) if "keywords" in record else ""

                        # Write the row to the CSV file
                        writer.writerow([id, category, headline, short_description, keywords])
                    print(f"Processed {file_path}. with items {len(items)}")
                except ValueError:
                    print(f"Skipping {file_path} as it is not valid JSON.")
                    # Skip files that are not valid JSON
                return
