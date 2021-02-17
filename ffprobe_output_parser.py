import collections
import io
from time import time

from utils import clear_current_line_in_terminal, write_to_txt_file


def parse_ffprobe_output(process, raw_data_filename, file_duration):
    time_data = []
    size_data = []
    sum_pkt_size = 0
    # Initially, get the bitrate for the first second.
    # After every second, this value is incremented by 1 so we can get the bitrate for the 2nd second, 3rd second, etc.
    time_to_check = 1

    timestamp_to_size = {}
    print('Linking the timestamps to their associated packet sizes...')

    for line in io.TextIOWrapper(process.stdout, encoding="utf-8"):
        data_array = line.split(',')
        timestamp_to_size[float(data_array[1])] = int(data_array[2][:-1])

        percentage_complete = round(((float(data_array[1]) / file_duration) * 100.0), 1)
        print(f'Progress: {percentage_complete}%', end='\r')
    
    clear_current_line_in_terminal() # Clears the progress and ETA.
    print('Done!')

    ordered_dict = collections.OrderedDict(sorted(timestamp_to_size.items()))
    print('Calculating the bitrates...')

    for timestamp, pkt_size in ordered_dict.items():
        if timestamp >= time_to_check:
            time_data.append(timestamp)
            size_data.append(sum_pkt_size)

            percentage_complete = round(100.0 * (timestamp / file_duration), 1)
            print(f'Progress: {percentage_complete}%', end='\r')
            write_to_txt_file(raw_data_filename, f'Timestamp: {timestamp} --> {round(sum_pkt_size)} kbps\n')
        
            sum_pkt_size = 0
            time_to_check += 1 
        else:
            sum_pkt_size += (pkt_size * 8) / 1000
            # Multiplied by 8 to convert bytes to bits, then divided by 1000 to convert to kbps

    clear_current_line_in_terminal()
    return time_data, size_data
