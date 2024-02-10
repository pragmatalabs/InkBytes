import os
from dotenv import load_dotenv


class SysDictionary():
    pass


def config(storage_type="local"):
    load_dotenv(os.path.join(os.curdir, ".env"))
    base_system_folder = os.path.join(os.pardir)
    app_folder = base_system_folder
    mode = os.getenv("MODE", "development")
    outlets_folder = os.path.join(base_system_folder, os.getenv("OUTLETS_FOLDER"))

    if storage_type == "local":
        storage_path = os.path.join(base_system_folder, os.getenv("STAGING_STORAGE_LOCAL"))
        storage_file = storage_path + os.getenv("STORAGE_FILE")
        storage_clusters_path = storage_path + os.getenv("STORAGE_CLUSTERS_PATH")
    elif storage_type == "bucket":
        storage_path = os.path.join(base_system_folder, os.getenv("STAGING_STORAGE_BUCKET"))
        storage_file = os.getenv("STORAGE_FILE_BUCKET")
        storage_clusters_path = os.getenv("STORAGE_CLUSTERS_PATH_BUCKET")
    else:
        raise ValueError("Invalid storage_type. Use 'local' or 'bucket'.")

    return (
        mode,
        storage_file,
        storage_path,
        storage_clusters_path,
        storage_file,
        app_folder,
        outlets_folder,
    )


# Retrieve configuration values using the config() function
(
    inkpill_mode,
    inkpills_storage_file,
    storage_path,
    storage_clusters_path,
    storage_file,
    app_folder,
    outlets_folder,
) = config()
LOGGING_CONF = {
    "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
}
APP_GLOBAL_CONF = {
    "APP_NAME": os.getenv("APP_NAME", "URIHarvest"),
    "APP_VERSION": os.getenv("APP_VERSION", "1.0"),
}
THREADING_CONF = {"MAX_THREADS": int(os.getenv("MAX_THREADS", 5))}
TIME_ZONE = os.getenv("TIME_ZONE", "UTC")

MODE_CONFIG = {
    "development": {
        "data_slicing_size": int(os.getenv("DEVELOPMENT_DATA_SLICING_SIZE", 100)),
        "database_slicing_size": int(
            os.getenv("DEVELOPMENT_DATABASE_SLICING_SIZE", 1000)
        ),
    },
    "production": {
        "data_slicing_size": int(os.getenv("PRODUCTION_DATA_SLICING_SIZE", -1)),
        "database_slicing_size": int(os.getenv("PRODUCTION_DATABASE_SLICING_SIZE", -1)),
    },
}

UUID_PREFIX = os.getenv("UUID_PREFIX", "IKPGRB")
BACKOFFICE_API_URL = os.getenv("BIFROST_API_BASE_URL", "")
API_CONTENT_TYPE = "application/json"
API_TOKEN = os.getenv("STRAPI_API_TOKEN", )
OPEN_AI = {
    "api-key": os.getenv("OPEN_AI_API_KEY", ""),
}

OUTLETS = {
    "file": os.path.join(outlets_folder, "models.json"),
}

LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "pt": "Portuguese",
    "ru": "Russian",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "ar": "Arabic",
}

PGSQL_CONNECTION_PARAMS = {
    "dbname": os.getenv("PGSQL_DBNAME", "inkpills"),
    "user": os.getenv("PGSQL_USER", ""),
    "password": os.getenv("PGSQL_PASSWORD", ""),
    "host": os.getenv("PGSQL_HOST", ""),
    "port": os.getenv("PGSQL_PORT", ""),
}

# ... continue using the loaded variables in your code
DEFAULT_AGENT = (
    "InkPill Mozilla/9.0 (PointLobos 10.0; OsX64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/79.0.3945.88 Safari/537.36",
)
DEFAULT_HEADER = {
    "Connection": "close",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/53.0.2785.143 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}
STRAPI_API_CONTENT_TYPE = "application/json"
STRAPI_API_TOKEN = os.getenv("STRAPI_API_TOKEN", )
STRAPI_API_POST_HEADER = {
    'Authorization': 'Bearer ' + STRAPI_API_TOKEN,
    'Content-Type': STRAPI_API_CONTENT_TYPE
}
STRAPI_API_ENDPOINTS = {
    'SESSIONS': os.getenv('STRAPI_API_SESSION_ENDPOINT'),
    'OUTLETS': os.getenv('STRAPI_API_OUTLETS_ENDPOINT'),
}
NER_TYPES = {
    'PERSON': 'Refers to people, including fictional characters or groups of people such as teams or organizations.',
    'ORG': 'Refers to organizations or institutions, such as companies or governmental bodies.',
    'GPE': 'Refers to geopolitical entities such as countries, cities, or regions.',
    'LOC': 'Refers to non-geopolitical locations such as bodies of water or mountains.',
    'EVENT': 'Refers to real-world events, such as natural disasters or sports matches.',
    'LAW': 'Refers to legal document or terms.',
    'PRODUCT': 'Refers to products, including physical goods or software.',
    'LANGUAGE': 'Refers to languages.',
    'WORK_OF_ART': 'Titles of books, songs, movies, or other artistic creations.',
    'NORP': 'Refers to nationalities or religious or political groups.',
    'FAC': 'Refers to buildings, airports, highways, bridges, etc.',
    'DATE': 'Absolute or relative dates or periods.',
    'MONEY': 'Monetary values, including unit.',
}
