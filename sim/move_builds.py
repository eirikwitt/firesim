import os
import re
from datetime import datetime

VORTEX_CONFIGS=(
    "V1S1C",
    "V2S1C",
    "V4S1C",
    "V8S1C",
    "V16S1C",
    "V32S1C",
    "V1S2C",
    "V2S2C",
    "V4S2C",
    "V8S2C",
    "V16S2C",
    "V1S1C0L3",
    "V2S1C0L3",
    "V4S1C0L3",
    "V8S1C0L3",
    "V16S1C0L3",
    "V32S1C0L3",
    "V1S2C0L3",
    "V2S2C0L3",
    "V4S2C0L3",
    "V8S2C0L3",
    "V16S2C0L3",
)

build_separator = r"^========== Building (.*) config ==========$"
timestamp_re = r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]"

def extract_timestamp(timestamp_str):
    return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")

def move_build_logs():
    logs_dir = 'logs'  # Adjust path if needed
    if not os.path.exists(logs_dir):
        print(f"Logs directory '{logs_dir}' does not exist.")
        return

    for config in VORTEX_CONFIGS:
        config_log_dir = os.path.join(logs_dir, f'build_{config}')
        if not os.path.exists(config_log_dir):
            os.makedirs(config_log_dir)
            print(f"Created directory: {config_log_dir}")

        # Move log files matching the pattern to the config-specific directory
        with open(os.path.join(logs_dir, f"build_{config}.log"), 'r') as f:
            lines = f.readlines()
            new_build = False
            timestamp = None
            for line in lines:
                if match := re.match(timestamp_re, line):
                    if new_build:
                        timestamp = extract_timestamp(match.group(1))
                        new_build = False
                    with open(os.path.join(config_log_dir, f'{int(timestamp.timestamp())}.log'), 'a') as config_log_file:
                        config_log_file.write(line)
                
                if re.match(build_separator, line):
                    print(f"Found build log for config: {config}")
                    new_build = True
                    
        
if __name__ == "__main__":
    move_build_logs()

