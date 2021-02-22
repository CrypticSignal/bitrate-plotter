import collections
import io
from time import time

from utils import clear_current_line_in_terminal, write_to_txt_file


def parse_ffprobe_output(process, raw_data_filename, file_duration):
    time_data = []
    size_data = []
    gop_size = 0
    # Initially, get the bitrate for the first second.
    # After every second, this value is incremented by 1 so we can get the bitrate for the 2nd second, 3rd second, etc.
    time_to_check = 1

    timestamp_to_size = {}
    print('Creating a dictionary where the timestamps are the keys and the packet sizes are the values...')

    for line in io.TextIOWrapper(process.stdout, encoding="utf-8"):
        timestamp = float(line.split(',')[1])
        packet_size = line.split(',')[2]
        timestamp_to_size[timestamp] = packet_size

        percentage_complete = round(((timestamp / file_duration) * 100.0), 1)
        print(f'Progress: {percentage_complete}%', end='\r')
    
    clear_current_line_in_terminal() # Clears the progress and ETA.
    print('Done!')
    # Create a new dictionary where the entries are ordered by timestamp value (ascending order).
    ordered_dict = dict(sorted(timestamp_to_size.items()))
    print('Calculating the bitrates...')

    for timestamp, pkt_size in ordered_dict.items():
        if timestamp >= time_to_check:
            time_data.append(timestamp)
            size_data.append(gop_size)

            percentage_complete = round(100.0 * (timestamp / file_duration), 1)
            print(f'Progress: {percentage_complete}%', end='\r')
            write_to_txt_file(raw_data_filename, f'Timestamp: {timestamp} --> {round(gop_size)} kbps\n')
        
            gop_size = 0
            time_to_check += 1 
        else:
            gop_size += (int(pkt_size) * 8) / 1000
            # Multiplied by 8 to convert bytes to bits, then divided by 1000 to convert to kbps.

    clear_current_line_in_terminal()
    return time_data, size_data

def get_gop_bitrates(process, number_of_frames, data_output_path):
    frame_count = 0
    keyframe_count = 0
    gop_length = 0
    gop_size = 0
    gop_end_times = []
    gop_bitrates = []

    for line in io.TextIOWrapper(process.stdout):
        frame_count += 1
        write_to_txt_file(data_output_path, f'Frame {frame_count} | {line}')
      
        key_frame, pkt_pts_time, pkt_size = line.strip().split(',')

        percentage_progress = round((frame_count / number_of_frames) * 100, 1)
        print(f'Progress: {percentage_progress}%', end='\r')

        if key_frame[10:] == '1':
            keyframe_count += 1
            pkt_pts_time = float(pkt_pts_time[13:])
            pkt_size = (int(pkt_size[9:]) * 8) / 1000
            write_to_txt_file(data_output_path, f'Frame {frame_count} is a keyframe\n')

            if keyframe_count == 1:
                gop_length = 1
                gop_size += pkt_size
                previous_pkt_pts_time = pkt_pts_time
            else:
                gop_end_times.append(pkt_pts_time)
                gop_duration = pkt_pts_time - previous_pkt_pts_time
                gop_bitrates.append(gop_size / gop_duration)

                previous_pkt_pts_time = pkt_pts_time
                gop_size = pkt_size
    
                write_to_txt_file(data_output_path, f'GOP length was {gop_length} frames\n')
                # We've reached a new keyframe, set gop_length to 1.
                gop_length = 1      
        else:
            gop_length += 1
            gop_size += (int(pkt_size[9:]) * 8) / 1000
            
    return gop_end_times, gop_bitrates
