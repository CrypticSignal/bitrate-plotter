import io

from utils import write_to_txt_file


def get_bitrate_every_second(
    process,
    raw_data_filename,
    progress_bar,
    task_id_1,
    task_id_2,
):
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
        if line.strip():
            dts_time, packet_size = line.strip().split(",", 2)[:2]
            packet_size = int(packet_size)
            # Convert to megabits.
            packet_size = (packet_size * 8) / 1000_000

        try:
            dts_time = float(dts_time)
        except Exception:
            pass
        else:
            dts_times_and_packet_sizes[dts_time] = packet_size
            progress_bar.update(task_id_1, completed=dts_time)

    # Create a new dictionary where the entries are ordered by timestamp value (ascending order).
    ordered_dict = dict(sorted(dts_times_and_packet_sizes.items()))
    print("Calculating the bitrates...")

    for dts_time, packet_size in ordered_dict.items():
        if dts_time >= time_to_check:
            x_axis_values.append(dts_time)
            bitrate_every_second.append(megabits_this_second)

            progress_bar.update(task_id_2, completed=dts_time)
            write_to_txt_file(
                raw_data_filename,
                f"Timestamp: {dts_time} --> {round(megabits_this_second, 3)} Mbps\n",
            )

            megabits_this_second = packet_size
            time_to_check += 1
        else:
            megabits_this_second += packet_size

    return x_axis_values, bitrate_every_second


def get_gop_bitrates(process, progress_bar, task_id, number_of_frames):
    keyframe_count = 0
    gop_size = 0
    gop_end_times = []
    gop_bitrates = []

    print(f"Processing ~{number_of_frames} frames...")

    frame_number = 0

    for line in io.TextIOWrapper(process.stdout):
        frame_number += 1
        progress_bar.update(task_id, completed=frame_number)
        key_frame, pkt_dts_time, pkt_size = line.strip().split(",")
        # Convert from bytes to megabits.
        pkt_size = (int(pkt_size) * 8) / 1000_000

        try:
            float(pkt_dts_time)
        except Exception:
            pass
        else:
            pkt_dts_time = float(pkt_dts_time)
            # IDR frame
            if key_frame == "1":
                keyframe_count += 1

                if keyframe_count == 1:
                    gop_size += pkt_size
                    previous_pkt_dts_time = pkt_dts_time
                else:
                    gop_end_times.append(pkt_dts_time)
                    gop_duration = pkt_dts_time - previous_pkt_dts_time
                    gop_bitrates.append(gop_size / gop_duration)

                    previous_pkt_dts_time = pkt_dts_time
                    gop_size = pkt_size

            # Not an IDR frame.
            else:
                gop_size += pkt_size

    return gop_end_times, gop_bitrates
