import os
import logging
from concurrent.futures import ThreadPoolExecutor
from botocore.exceptions import NoCredentialsError, ClientError
from boto3 import session
from boto3.s3.transfer import TransferConfig
from botocore.config import Config
import glob
import concurrent.futures
from tqdm import tqdm

class DigitalOceanSpacesHandler:
    """Handler for Digital Ocean Spaces operations."""
    
    def __init__(self, access_id, secret_key, region_name, endpoint_url):
        """Initialize the Digital Ocean Spaces handler."""
        self.logger = logging.getLogger(__name__)
        self.access_id = access_id
        self.secret_key = secret_key
        self.region_name = region_name or 'nyc3'
        self.endpoint_url = endpoint_url or 'https://nyc3.digitaloceanspaces.com'
        
        # Create session and client
        self.session = session.Session()
        self.s3_client = self.session.client(
            's3',
            region_name=self.region_name,
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_id,
            aws_secret_access_key=self.secret_key,
            use_ssl=True,
            config=Config(signature_version='s3v4', s3={'addressing_style': 'virtual'})
        )
    
    def upload_file(self, file_path, bucket, s3_file_path=None, folder_path=""):
        """
        Upload a single file to Digital Ocean Spaces.
        
        Args:
            file_path (str): Path to the local file
            bucket (str): DO Spaces bucket name
            s3_file_path (str, optional): Path where the file should be stored in DO Spaces
            folder_path (str, optional): Folder path in the bucket
            
        Returns:
            bool: True if upload was successful, False otherwise
        """
        try:
            if not os.path.exists(file_path):
                self.logger.error(f"File not found: {file_path}")
                return False
            
            # If a folder path is provided, prepend it to the object name
            if folder_path:
                object_name = os.path.join(folder_path, s3_file_path or os.path.basename(file_path))
            else:
                object_name = s3_file_path or os.path.basename(file_path)
                
            self.logger.info(f"Uploading {file_path} to {bucket}/{object_name}")
            
            # Upload the file
            self.s3_client.upload_file(
                file_path,
                bucket,
                object_name,
                ExtraArgs={'ACL': 'public-read'},
                Config=TransferConfig(use_threads=False)
            )
            
            self.logger.info(f"Successfully uploaded {file_path} to {bucket}/{object_name}")
            return True
        except NoCredentialsError as e:
            self.logger.error(f"Credentials error during file upload: {e}")
            return False
        except ClientError as e:
            self.logger.error(f"Client error uploading file to Digital Ocean Spaces: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during file upload: {e}")
            return False
    
    def upload_directory(self, local_dir, bucket, s3_prefix="", extension='.db.json', num_of_threads=4):
        """
        Upload an entire directory to Digital Ocean Spaces.
        
        Args:
            local_dir (str): Local directory to upload
            bucket (str): DO Spaces bucket name
            s3_prefix (str): Prefix in DO Spaces
            extension (str): File extension filter
            num_of_threads (int): Number of concurrent uploads
            
        Returns:
            bool: True if all uploads were successful, False otherwise
        """
        try:
            if not os.path.isdir(local_dir):
                self.logger.error(f"Directory not found: {local_dir}")
                return False
                
            # Find files with the specified extension
            search_pattern = os.path.join(local_dir, f'*{extension}')
            files_to_upload = glob.glob(search_pattern)
            
            # Sort files by size (smaller files first)
            files_to_upload.sort(key=os.path.getsize)
            
            if not files_to_upload:
                self.logger.warning(f"No files with extension '{extension}' found in {local_dir}")
                return True
                
            self.logger.info(f"Found {len(files_to_upload)} files to upload from {local_dir}")
            
            def upload_task(file_path):
                # Calculate relative path for object name, preserving subdirectory structure
                relative_path = os.path.relpath(file_path, start=local_dir)
                # If s3_prefix is provided, it's prepended to the relative path
                object_name = os.path.join(s3_prefix, relative_path) if s3_prefix else relative_path
                return self.upload_file(file_path, bucket, object_name)
            
            success = True
            # Use ThreadPoolExecutor with tqdm progress bar
            with ThreadPoolExecutor(max_workers=num_of_threads) as executor:
                results = list(tqdm(
                    executor.map(upload_task, files_to_upload), 
                    total=len(files_to_upload), 
                    desc="Uploading files"
                ))
                
                # Check if any upload failed
                if not all(results):
                    success = False
                    self.logger.warning("Some files failed to upload")
            
            return success
        except Exception as e:
            self.logger.error(f"Error in upload_directory: {e}")
            return False
    
    def read_file(self, bucket_name, object_name):
        """Read a file from Digital Ocean Spaces."""
        try:
            response = self.s3_client.get_object(Bucket=bucket_name, Key=object_name)
            return response['Body'].read().decode('utf-8')
        except Exception as e:
            self.logger.error(f"Failed to read file '{object_name}' from bucket '{bucket_name}': {e}")
            return None
    
    def list_files_with_extension(self, bucket_name, extension, sub_folder=None):
        """List files in the bucket that end with the given extension, optionally within a sub-folder."""
        prefix = f"{sub_folder}/" if sub_folder else ""
        object_names = []

        # Use the S3 client to list objects in the bucket
        response = self.s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)

        if 'Contents' in response:
            for obj in response['Contents']:
                if obj['Key'].endswith(extension):
                    object_names.append(obj['Key'])

        return object_names
    
    def read_directory(self, local_directory_path, bucket_name, remote_directory_name="", extension='.db.json',
                     num_of_threads=5):
        """Reads all files with a given extension within a bucket directory and saves them locally using multithreading."""
        object_names = self.list_files_with_extension(bucket_name, extension, sub_folder=remote_directory_name)

        def read_task(object_name):
            local_path = os.path.join(local_directory_path, os.path.basename(object_name))
            print(local_path)
            if not os.path.exists(local_path):
                file = self.read_file(bucket_name, object_name)
                with open(local_path, 'w') as f:
                    f.write(file)

        # Use ThreadPoolExecutor to download files in parallel
        with ThreadPoolExecutor(max_workers=num_of_threads) as executor:
            results = list(
                tqdm(executor.map(read_task, object_names), total=len(object_names), desc="Downloading files"))

        return results
    
    def append_to_file(self, bucket_name, object_name, content):
        """Append content to a file in the bucket."""
        temp_file_path = os.path.join("./data", "temp_download_file")
        try:
            self.s3_client.download_file(bucket_name, object_name, temp_file_path)
            with open(temp_file_path, "a") as f:
                f.write(content)
            self.upload_file(temp_file_path, bucket_name, object_name)
        except self.s3_client.exceptions.NoSuchKey:
            self.logger.info("File does not exist, creating a new one.")
            with open(temp_file_path, "w") as f:
                f.write(content)
            self.upload_file(temp_file_path, bucket_name, object_name)
        except Exception as e:
            self.logger.error(f"Failed to append to file: {e}")
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
    
    def delete_file(self, bucket_name, object_name):
        """Delete a file from the bucket."""
        try:
            self.s3_client.delete_object(Bucket=bucket_name, Key=object_name)
            self.logger.info(f"File {object_name} deleted from {bucket_name}")
        except Exception as e:
            self.logger.error(f"Failed to delete file: {e}")
    
    def move_files_in_remote(self, bucket_name, source_folder, destination_folder, extension='.db.json',
                           num_of_threads=5):
        """
        Moves files with a given extension from one folder to another within the same bucket.
        """
        # List files to move
        files_to_move = self.list_files_with_extension(bucket_name, extension, sub_folder=source_folder)

        if not files_to_move:
            self.logger.info(f"No files with extension '{extension}' found in '{source_folder}' to move.")
            return

        def move_task(object_name):
            # Construct the new object key by replacing the source folder with the destination folder
            if source_folder:
                relative_path = os.path.relpath(object_name, source_folder)
            else:
                relative_path = object_name

            new_key = os.path.join(destination_folder, relative_path)

            # Copy the object to the new key
            copy_source = {'Bucket': bucket_name, 'Key': object_name}
            try:
                self.s3_client.copy(copy_source, bucket_name, new_key)
                self.logger.info(f"Copied {object_name} to {new_key}")

                # Delete the original object
                self.s3_client.delete_object(Bucket=bucket_name, Key=object_name)
                self.logger.info(f"Deleted original object {object_name}")
            except Exception as e:
                self.logger.error(f"Failed to move {object_name} to {new_key}: {e}")

        # Use ThreadPoolExecutor to move files in parallel
        with ThreadPoolExecutor(max_workers=num_of_threads) as executor:
            list(tqdm(executor.map(move_task, files_to_move), total=len(files_to_move), desc="Moving files"))