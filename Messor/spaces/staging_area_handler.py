import logging
import os

from inkbytes.common.system.log_formatters import log_function_activity

from inkbytes.common.system.module_handler import get_module_name

from inkbytes.common.system.digital_ocean_spaces import DigitalOceanSpacesHandler

MODULE_NAME = get_module_name(2)
# Adjust the import path as necessary
logger = logging.getLogger(MODULE_NAME)


# Assuming your DigitalOceanSpacesHandler class is already set up to use environment variables for credentials


@log_function_activity(logger.root)
def upload_directory(local_directory, bucket_name, target_prefix='',
                     spaces_handler: DigitalOceanSpacesHandler = DigitalOceanSpacesHandler()):
    """
    Uploads all files from a local directory to a specified bucket in DigitalOcean Spaces.

    :param local_directory: Path to the local directory to upload files from
    :param bucket_name: The name of the bucket (Space) in DigitalOcean
    :param target_prefix: The target directory path inside the bucket where files will be uploaded
    :parama spaces_handler: The Digitalocean Spaces handler
    """
    for root, _, files in os.walk(local_directory):
        for filename in files:
            local_file_path = os.path.join(root, filename)
            relative_path = os.path.relpath(local_file_path, local_directory)
            space_file_path = os.path.join(target_prefix, relative_path) if target_prefix else relative_path

            logger.info(f"Uploading {local_file_path} to {bucket_name}/{space_file_path}...")
            spaces_handler.upload_file(local_file_path, bucket_name, space_file_path)
