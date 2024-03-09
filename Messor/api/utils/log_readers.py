import asyncio
import os


async def file_log_reader(duration, file_name="logs/messor.log", n=100):
    log_file_path = file_name  # Path to your log file
    last_position = 0

    for _ in range(duration):
        log_lines = []
        try:
            with open(log_file_path, 'r') as log_file:
                # Move to the last known position
                log_file.seek(last_position)
                # Read new lines since last check
                lines = log_file.readlines()
                last_position = log_file.tell()

            # If you only want the last 'n' lines of new data, uncomment the following line:
            # lines = lines[-n:]

            for line in lines:
                # Apply formatting based on log level
                """if "ERROR" in line:
                    log_lines.append(f'<span class="text-red-200">{line.strip()}</span><br/>')
                elif "WARNING" in line:
                    log_lines.append(f'<span class="text-orange-300">{line.strip()}</span><br/>')
                elif "CRITICAL" in line:
                    log_lines.append(f'<span class="text-orange-500">{line.strip()}</span><br/>')
                else:
                    log_lines.append(f'<span class="text-black-300">{line.strip()}</span><br/>')"""
                log_lines.append(f'{line.strip()}<br/>')
                yield ''.join(log_lines)
        except FileNotFoundError:
            yield f'<span class="text-red-500">File not found: {os.path.abspath(log_file_path)}</span><br/>'
        except Exception as e:
            yield f'<span class="text-red-500">Error reading file: {str(e)}</span><br/>'

        await asyncio.sleep(1)  # Check for new log messages every second
