import collections
import io
from time import time

from utils import clear_current_line_in_terminal, write_to_txt_file


def get_bitrate_every_second(process, raw_data_filename, file_duration):
    x_axis_values = []
    bitrate_every_second = []
    megabits_this_second = 0
    # Initially, get the bitrate for the first second.
    # After every second, this value is incremented by 1 so we can get the bitrate for the 2nd second, 3rd second, etc.
    time_to_check = 1
    # Initialise a dictionary where the decoding timestamps (DTS) will be the keys and the packet sizes will be the values.
    dts_times_and_packet_sizes = {}

    for line in io.TextIOWrapper(process.stdout, encoding="utf-8"):
        ## ffprobe will return the time in ms and the size in bytes.
        dts_time, packet_size = line.strip().split(",")
        packet_size = int(packet_size)
        # Convert to megabits.
        packet_size = (packet_size * 8) / 1000_000

        try:
            float(dts_time)
        except Exception:
            pass
        else:
            dts_times_and_packet_sizes[float(dts_time)] = packet_size
            percentage_complete = round(((float(dts_time) / file_duration) * 100.0), 1)
            print(f"Progress: {percentage_complete}%", end="\r")

    clear_current_line_in_terminal()  # Clears the progress and ETA.
    print("Done!")
    # Create a new dictionary where the entries are ordered by timestamp value (ascending order).
    ordered_dict = dict(sorted(dts_times_and_packet_sizes.items()))
    print("Calculating the bitrates...")

    for dts_time, packet_size in ordered_dict.items():
        if dts_time >= time_to_check:
            x_axis_values.append(dts_time)
            bitrate_every_second.append(megabits_this_second)

            percentage_complete = round(100.0 * (dts_time / file_duration), 1)
            print(f'Progress: {percentage_complete}%', end='\r')
            write_to_txt_file(
                raw_data_filename, f"Timestamp: {dts_time} --> {round(megabits_this_second)} Mbps\n"
            )

            megabits_this_second = packet_size
            time_to_check += 1
        else:
            megabits_this_second += packet_size

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

        key_frame, pkt_dts_time, pkt_size = line.strip().split(",")
        # Convert from bytes to megabits.
        pkt_size = (int(pkt_size) * 8) / 1000_000

        try:
            float(pkt_dts_time)
        except Exception:
            pass
        else:
            pkt_dts_time = float(pkt_dts_time)
            # key_frame=1 (with H.264, this is an IDR frame).
            if key_frame == "1":
                keyframe_count += 1

                if keyframe_count == 1:
                    gop_length = 1
                    gop_size += pkt_size
                    previous_pkt_dts_time = pkt_dts_time
                else:
                    gop_end_times.append(pkt_dts_time)
                    gop_duration = pkt_dts_time - previous_pkt_dts_time
                    gop_bitrates.append(gop_size / gop_duration)

                    previous_pkt_dts_time = pkt_dts_time
                    gop_size = pkt_size
                    # We've reached a new keyframe, set gop_length to 1.
                    gop_length = 1

            # key_frame=0
            else:
                gop_length += 1
                gop_size += pkt_size

            percentage_progress = round((frame_count / number_of_frames) * 100, 1)
            print(f"Progress: {percentage_progress}%", end="\r")

    return gop_end_times, gop_bitrates
