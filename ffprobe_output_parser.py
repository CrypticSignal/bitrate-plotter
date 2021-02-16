from time import time
import io
from utils import write_to_txt_file


def parse_ffprobe_output(process, filename_without_ext, file_duration):
    time_last_eta_update = time()
    time_data = []
    size_data = []
    sum_pkt_size = 0
    one_second_passed = False
    # Get the total number of bits after 1 second. 
    # After every second, this value is incremented by 1 so we can get the bitrate for the 2nd second, 3rd second, etc.
    time_to_check = 1
    
    for line in io.TextIOWrapper(process.stdout, encoding="utf-8"):
        if 'pkt_pts_time' in line:
            timestamp = float(line[13:])

            if timestamp >= time_to_check:
                write_to_txt_file(filename_without_ext, f'Time: {timestamp} --> ')
                time_data.append(timestamp)

                percentage_complete = round(100.0 * (timestamp / file_duration), 1)

                eta = (time() - time_last_eta_update) * (file_duration - timestamp)
                time_last_eta_update = time()
                minutes = round(eta / 60)
                seconds = f'{round(eta % 60):02d}'

                eta_string = ''
                if minutes >= 2:
                    eta_string = f'| ETA: ~{minutes} minutes'

                print(f'Progress: {percentage_complete}% {eta_string}', end='\r')

                time_to_check += 1 
                one_second_passed = True
            else:
                one_second_passed = False
                
        elif 'pkt_size' in line:
            if one_second_passed:
                write_to_txt_file(filename_without_ext, f'{round(sum_pkt_size)} kbps\n')
                size_data.append(sum_pkt_size)
                sum_pkt_size = 0
            else:
                sum_pkt_size += (int(line[9:]) * 8) / 1000
                # Multiplied by 8 to convert bytes to bits, then divided by 1000 to convert to kbps

    return time_data, size_data
