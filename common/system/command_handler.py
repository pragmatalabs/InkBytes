import yaml
import argparse
import sys
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Command interface
class Command:
    def execute(self):
        raise NotImplementedError("Subclasses must implement this method")

class ExitCommand(Command):
    def execute(self):
        print("Exiting program.")
        sys.exit()

# Command factory to create command instances
class CommandFactory:
    def __init__(self, command_map):
        self.commands = command_map

    def get_command(self, action):
        command_class = self.commands.get(action.upper(), None)
        if command_class:
            return command_class()
        else:
            logger.warning(f"No command found for action: {action}")
            return None

# Helper function to read command line configuration from a YAML file
def load_config(file_path):
    try:
        with open(file_path, 'r') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        logger.error(f"Config file not found: {file_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML file: {e}")
        sys.exit(1)

# Main application class
class CommandLineAppHandler:
    def __init__(self, config_path, command_factory):
        self.config = load_config(config_path)
        self.parser = self.setup_parser()
        self.command_factory = command_factory

    def setup_parser(self):
        parser = argparse.ArgumentParser(description=self.config['help'])
        parser.add_argument("mode", type=str.upper, choices=self.config['mode_arguments'],
                            help="Specify the mode of operation.")
        return parser

    def await_command(self):
        while True:
            try:
                user_input = input("Insert command to run: ")
                args = self.parser.parse_args(user_input.split())
                command = self.command_factory.get_command(args.mode)
                if command:
                    command.execute()
                else:
                    logger.warning("Invalid command. Please try again.")
            except KeyboardInterrupt:
                print("\nProgram interrupted by user.")
                sys.exit()
            except argparse.ArgumentError as e:
                logger.error(f"Argument error: {e}")
            except SystemExit:
                # This is raised by argparse when --help is called
                continue

# Example usage
'''if __name__ == "__main__":
    config_path = "config.yaml"  # Replace with your actual config file path
    command_map = {
        "EXIT": ExitCommand,
        # Add other commands here
    }
    command_factory = CommandFactory(command_map)
    app = CommandLineAppHandler(config_path, command_factory)
    app.await_command()'''