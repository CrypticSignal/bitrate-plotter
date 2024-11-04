import io

from utils import convert_to_mbits, get_second, process_timestamp_and_size

import numpy as np


def calculate_bitrates(
    process,
    progress_bar,
    task_id,
    number_of_frames,
    framerate,
    is_constant_framerate,
    is_integer_framerate,
    use_dts=False,
):
    """
    Calculate bitrates from video frame data using either PTS or DTS.
    Frame numbers start at 1 for correct second calculation.
    """
    if not process or not hasattr(process, "stdout"):
        raise ValueError("Invalid process object provided")
    if framerate <= 0:
        raise ValueError(f"Invalid framerate: {framerate}")
    if number_of_frames <= 0:
        raise ValueError(f"Invalid number of frames: {number_of_frames}")

    frames = []
    x_axis_values = []
    bitrates_list = []
    seconds_dict = {}
    initial_timestamp = None
    frame_count = 0
    prev_timestamp = float("-inf")
    invalid_lines = []

    time_label = "DTS" if use_dts else "PTS"
    print(f"\nDetailed packet analysis ({time_label}-ordered):")
    print("-" * 80)
    print(
        f"{'Frame':>6} {time_label:>10} {'Size(Mb)':>12} "
        f"{'Pre-Sum':>12} {'Post-Sum':>12}"
    )
    print("-" * 80)

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
        frame_count += 1

        if initial_timestamp is None:
            initial_timestamp = timestamp

        if use_dts:
            if timestamp < prev_timestamp:
                raise ValueError(
                    f"Non-monotonic DTS detected at frame {frame_count}: "
                    f"{prev_timestamp} -> {timestamp}"
                )
            prev_timestamp = timestamp

            current_second = get_second(
                use_dts,
                is_constant_framerate,
                is_integer_framerate,
                timestamp,
                frame_count,
                framerate,
                initial_timestamp,
            )

            if current_second not in seconds_dict:
                if seconds_dict:
                    last_second = np.max(seconds_dict.keys())
                    x_axis_values.append(last_second + 1)
                    bitrates_list.append(seconds_dict[last_second]["total_bits"])
                    print(
                        f"\nSecond {last_second + 1} bitrate: {seconds_dict[last_second]['total_bits']:.6f} Mbps"
                    )
                    print(
                        f"Frames in second: {seconds_dict[last_second]['frame_count']}"
                    )
                    print("-" * 80)

                seconds_dict[current_second] = {"total_bits": 0, "frame_count": 0}

            try:
                packet_size_mbits = convert_to_mbits(packet_size)
            except ValueError as e:
                invalid_lines.append((line_number, str(e)))
                continue

            pre_sum = seconds_dict[current_second]["total_bits"]
            seconds_dict[current_second]["total_bits"] += packet_size_mbits
            seconds_dict[current_second]["frame_count"] += 1

            print(
                f"{frame_count:6d} {timestamp:10.3f} "
                f"{packet_size_mbits:12.6f} {pre_sum:12.6f} "
                f"{seconds_dict[current_second]['total_bits']:12.6f}"
            )

            progress_bar.update(task_id, completed=frame_count)
        else:
            frames.append((timestamp, packet_size, frame_count))

    if frame_count != number_of_frames:
        print("\nWarning: Frame count mismatch")
        print(f"Expected: {number_of_frames}")
        print(f"Processed: {frame_count}")
        if invalid_lines:
            print("\nInvalid lines detected:")
            for line_num, reason in invalid_lines:
                print(f"Line {line_num}: {reason}")

    if use_dts:
        if seconds_dict:
            last_second = np.max(seconds_dict.keys())
            x_axis_values.append(last_second + 1)
            bitrates_list.append(seconds_dict[last_second]["total_bits"])
            print(
                f"\nSecond {last_second + 1} bitrate: {seconds_dict[last_second]['total_bits']:.6f} Mbps"
            )
            print(f"Frames in second: {seconds_dict[last_second]['frame_count']}")
            print("-" * 80)
    else:
        frames.sort()  # Sort by timestamp
        seconds_dict.clear()
        processed_frames = 0

        # First pass: group frames by second and calculate totals
        for frame_number, (timestamp, packet_size, _) in enumerate(frames, start=1):
            current_second = get_second(
                use_dts,
                is_constant_framerate,
                is_integer_framerate,
                timestamp,
                frame_number,
                framerate,
                initial_timestamp,
            )

            if current_second not in seconds_dict:
                seconds_dict[current_second] = {"total_bits": 0, "frame_count": 0}

            packet_size_mbits = convert_to_mbits(packet_size)
            seconds_dict[current_second]["total_bits"] += packet_size_mbits
            seconds_dict[current_second]["frame_count"] += 1
            processed_frames += 1
            progress_bar.update(task_id, completed=processed_frames)

        # Second pass: output ordered frames and running totals
        for second in sorted(seconds_dict.keys()):
            current_total = 0
            frame_in_second = 0

            for frame_number, (timestamp, packet_size, original_frame) in enumerate(
                frames, start=1
            ):
                if (
                    get_second(
                        use_dts,
                        is_constant_framerate,
                        is_integer_framerate,
                        timestamp,
                        frame_number,
                        framerate,
                        initial_timestamp,
                    )
                    == second
                ):
                    packet_size_mbits = convert_to_mbits(packet_size)
                    pre_sum = current_total
                    current_total += packet_size_mbits

                    print(
                        f"{original_frame:6d} {timestamp:10.3f} "
                        f"{packet_size_mbits:12.6f} {pre_sum:12.6f} "
                        f"{current_total:12.6f}"
                    )
                    frame_in_second += 1

            x_axis_values.append(second + 1)
            bitrates_list.append(current_total)
            print(f"\nSecond {second + 1} bitrate: {current_total:.6f} Mbps")
            print(f"Frames in second: {frame_in_second}")
            print("-" * 80)

    return x_axis_values, bitrates_list
