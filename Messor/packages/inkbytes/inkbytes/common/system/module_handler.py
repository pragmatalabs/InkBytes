import os
import inspect

def get_module_name(depth=2):
    """
    Dynamically determines the module name based on the file path from which it is called.
    Assumes a certain depth within the project structure to calculate the root of the project.

    Parameters:
    - depth: int, The number of directory levels up to the project root from the calling file.

    Returns:
    - str, The module name in dot-separated format.
    """
    # Get the file path of the caller
    caller_frame = inspect.stack()[1]
    caller_file_path = caller_frame.filename
    caller_file_path = os.path.abspath(caller_file_path)
    
    # Calculate the project root based on the assumed depth
    project_root = os.path.abspath(os.path.join(caller_file_path, *(['..'] * depth)))
    
    # Calculate the module's name by its path relative to the project root
    module_path_relative = os.path.relpath(os.path.dirname(caller_file_path), project_root)
    module_name = module_path_relative.replace(os.path.sep, '.')
    
    # Append the file name without extension
    file_name = os.path.splitext(os.path.basename(caller_file_path))[0]
    full_module_name = f"{module_name}.{file_name}" if module_name else file_name
    
    return full_module_name
