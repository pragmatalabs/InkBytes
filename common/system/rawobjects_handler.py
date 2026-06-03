import copy
import logging
import os
import dill


class ObjectHandler:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)

    def save_pickled_object(self, obj, filename):
        try:
            with open(filename, "wb") as output_file:
                dill.dump(obj, output_file)
            print(f"Object pickled and saved to '{filename}'.")
        except Exception as e:
            print(f"Error saving object to '{filename}': {e}")

    def load_pickled_object(self, filename):
        try:
            with open(filename, "rb") as input_file:
                unpickler = dill.Unpickler(input_file)
                raw_object = unpickler.load()
                loaded_object = raw_object
                print(loaded_object)
                return loaded_object
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found.")
        except EOFError:
            print(f"Error: End of file reached while unpickling. The file might be empty or corrupted.")
        except Exception as e:
            print(f"An error occurred: {e}")

    def check_pickled_object_exists_and_non_empty(self, filename):
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            return True
        else:
            return False

    def extract_info_or_create_new(self, object_store, reference_class=None) -> object:
        if self.check_pickled_object_exists_and_non_empty(object_store):
            raw_object = self.load_pickled_object(object_store)
            print(type(raw_object))
        else:
            raw_object = reference_class()
        return raw_object
