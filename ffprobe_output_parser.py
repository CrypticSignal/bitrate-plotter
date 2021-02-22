import collections
import io
from time import time

from utils import clear_current_line_in_terminal, write_to_txt_file


def get_bitrate_every_second(process, raw_data_filename, file_duration):
    x_axis_values = []
    bitrate_every_second = []
    kilobits_this_second = 0
    # Initially, get the bitrate for the first second.
    # After every second, this value is incremented by 1 so we can get the bitrate for the 2nd second, 3rd second, etc.
    time_to_check = 1
    # We will create a dictionary where the pts_time is the value and the frame size is the value.
    pts_time_and_size = {}

    for line in io.TextIOWrapper(process.stdout, encoding="utf-8"):
        pts_time, size = line.strip().split(',')
        pts_time = float(pts_time[9:])
        frame_size = (int(size[5:]) * 8) / 1000

        pts_time_and_size[pts_time] = frame_size

        percentage_complete = round(((pts_time / file_duration) * 100.0), 1)
        print(f'Progress: {percentage_complete}%', end='\r')
    
    clear_current_line_in_terminal() # Clears the progress and ETA.
    print('Done!')
    # Create a new dictionary where the entries are ordered by timestamp value (ascending order).
    ordered_dict = dict(sorted(pts_time_and_size.items()))
    print('Calculating the bitrates...')

    for pts_time, frame_size in ordered_dict.items():
        if pts_time >= time_to_check:
            x_axis_values.append(pts_time)
            bitrate_every_second.append(kilobits_this_second)

            percentage_complete = round(100.0 * (pts_time / file_duration), 1)
            #print(f'Progress: {percentage_complete}%', end='\r')
            write_to_txt_file(raw_data_filename, f'Timestamp: {pts_time} --> {round(kilobits_this_second)} kbps\n')
        
            kilobits_this_second = frame_size
            time_to_check += 1
        else:
            kilobits_this_second += frame_size

    clear_current_line_in_terminal()
    return x_axis_values, bitrate_every_second


def get_gop_bitrates(process, number_of_frames, data_output_path):
    frame_count = 0
    keyframe_count = 0
    gop_length = 0
    gop_size = 0
    gop_end_times = []
    gop_bitrates = []

    for line in io.TextIOWrapper(process.stdout):
        frame_count += 1
        write_to_txt_file(data_output_path, line)
      
        key_frame, pkt_pts_time, pkt_size = line.strip().split(',')
        pkt_size = (int(pkt_size[9:]) * 8) / 1000

        if key_frame[10:] == '1':
            keyframe_count += 1
            pkt_pts_time = float(pkt_pts_time[13:])

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
                # We've reached a new keyframe, set gop_length to 1.
                gop_length = 1      
        else:
            gop_length += 1
            gop_size += pkt_size

        percentage_progress = round((frame_count / number_of_frames) * 100, 1)
        print(f'Progress: {percentage_progress}%', end='\r')
            
    return gop_end_times, gop_bitrates
