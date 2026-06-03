import os


def read_data_files(directory, extension: str = '.db.json') -> [str]:
    list_of_files = filter(lambda x: os.path.isfile(os.path.join(directory, x)),
                           os.listdir(directory))
    list_of_files = sorted(list_of_files,
                           key=lambda x: os.stat(os.path.join(directory, x)).st_size)

    return [file for file in list_of_files if file.endswith(extension)]
