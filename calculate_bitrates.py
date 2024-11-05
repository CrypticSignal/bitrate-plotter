import io

from utils import (
    convert_to_kbits,
    convert_to_mbits,
    get_second,
    process_timestamp_and_size,
)

import numpy as np


def calculate_bitrates(
    process,
    is_video,
    number_of_frames,
    framerate,
    is_constant_framerate,
    is_integer_framerate,
    use_dts=False,
):
    if not process or not hasattr(process, "stdout"):
        raise ValueError("Invalid process object provided")
    if is_video and framerate <= 0:
        raise ValueError(f"Invalid framerate: {framerate}")
    if is_video and number_of_frames <= 0:
        raise ValueError(f"Invalid number of frames: {number_of_frames}")

    packets = []
    x_axis_values = []
    bitrates_list = []
    seconds_dict = {}
    initial_timestamp = None
    packet_count = 0
    prev_timestamp = float("-inf")
    invalid_lines = []

    for line_number, line in enumerate(
        io.TextIOWrapper(process.stdout, encoding="utf-8"), 1
    ):
        if not line.strip():
            invalid_lines.append((line_number, "Empty line"))
            continue

        result = process_timestamp_and_size(line.strip().split(",", 2))
        if not result:
            invalid_lines.append((line_number, f"Invalid format: {line.strip()}"))
            continue

        timestamp, packet_size = result
        packet_count += 1

        if initial_timestamp is None:
            initial_timestamp = timestamp

        if is_video and use_dts:
            if timestamp < prev_timestamp:
                raise ValueError(
                    f"Non-monotonic DTS detected at packet {packet_count}: "
                    f"{prev_timestamp} -> {timestamp}"
                )
            prev_timestamp = timestamp

            current_second = get_second(
                use_dts,
                is_constant_framerate,
                is_integer_framerate,
                timestamp,
                packet_count,
                framerate,
                initial_timestamp,
            )

            if current_second not in seconds_dict:
                if seconds_dict:
                    last_second = np.max(seconds_dict.keys())
                    x_axis_values.append(last_second + 1)
                    bitrates_list.append(seconds_dict[last_second]["total_bits"])

                seconds_dict[current_second] = {"total_bits": 0, "packet_count": 0}

            try:
                packet_size_mbits = (
                    convert_to_mbits(packet_size)
                    if is_video
                    else convert_to_kbits(packet_size)
                )
            except ValueError as e:
                invalid_lines.append((line_number, str(e)))
                continue

            seconds_dict[current_second]["total_bits"] += packet_size_mbits
            seconds_dict[current_second]["packet_count"] += 1

        else:
            packets.append((timestamp, packet_size, packet_count))

    if invalid_lines:
        print("\nInvalid lines detected:")
        for line_num, reason in invalid_lines:
            print(f"Line {line_num}: {reason}")

    if use_dts:
        if seconds_dict:
            last_second = np.max(seconds_dict.keys())
            x_axis_values.append(last_second + 1)
            bitrates_list.append(seconds_dict[last_second]["total_bits"])
    else:
        packets.sort()  # Sort by timestamp
        seconds_dict.clear()
        packets_processed = 0

        # First pass: group packets by second and calculate totals
        for packet_number, (timestamp, packet_size, _) in enumerate(packets, start=1):
            current_second = get_second(
                use_dts,
                is_constant_framerate,
                is_integer_framerate,
                timestamp,
                packet_number,
                framerate,
                initial_timestamp,
            )

            if current_second not in seconds_dict:
                seconds_dict[current_second] = {"total_bits": 0, "packet_count": 0}

            packet_size_mbits = (
                convert_to_mbits(packet_size)
                if is_video
                else convert_to_kbits(packet_size)
            )
            seconds_dict[current_second]["total_bits"] += packet_size_mbits
            seconds_dict[current_second]["packet_count"] += 1
            packets_processed += 1

        # Second pass: output ordered packets and running totals
        for second in sorted(seconds_dict.keys()):
            current_total = 0
            packets_in_second = 0

            for packet_number, (timestamp, packet_size, original_packet) in enumerate(
                packets, start=1
            ):
                if (
                    get_second(
                        use_dts,
                        is_constant_framerate,
                        is_integer_framerate,
                        timestamp,
                        packet_number,
                        framerate,
                        initial_timestamp,
                    )
                    == second
                ):
                    packet_size_mbits = (
                        convert_to_mbits(packet_size)
                        if is_video
                        else convert_to_kbits(packet_size)
                    )

                    current_total += packet_size_mbits
                    packets_in_second += 1

            x_axis_values.append(second + 1)
            bitrates_list.append(current_total)

    return x_axis_values, bitrates_list
