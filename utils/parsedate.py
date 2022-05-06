import sys
import re
from datetime import datetime

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise TypeError("Must pass file to parse as an argument")

    file_to_parse = sys.argv[1]
    max_timestamp = None

    with open(file_to_parse, "r") as f:
        for line in f:
            # split line with whitespace, '=', and '>' deliminators
            split_line = re.split("[\s=>]", line)
            # timestamp will be at index next to 'timestamp' string
            if "timestamp" in split_line:
                timestamp_idx = split_line.index("timestamp") + 1
                timestamp_str = split_line[timestamp_idx]
                # create timestamp object from string
                timestamp = datetime.strptime(timestamp_str, "\"%Y-%m-%dT%H:%M:%SZ\"")
                if max_timestamp is None:
                    max_timestamp = timestamp
                elif timestamp > max_timestamp:
                    max_timestamp = timestamp

        if max_timestamp is None:
            raise ValueError("A timestamp was not found in the inputted lines")
        
    print(max_timestamp)
