import json
import os
from pathlib import Path
import subprocess

from args import args
from calculate_bitrates import calculate_bitrates
from calculate_gop_bitrates import calculate_gop_bitrates

from utils import FileInfoProvider, VideoInfoProvider, line

import matplotlib.pyplot as plt
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)

framerate = None
is_constant_framerate = None
is_integer_framerate = None

filename = Path(args.file_path).name

output_dir = Path(f"[{filename}]")
if args.gop:
    output_dir = output_dir.joinpath("gop")

os.makedirs(output_dir, exist_ok=True)

entries = f"packet={"dts_time" if args.dts else "pts_time"},size"

if args.gop:
    entries = f"packet={"dts_time" if args.dts else "pts_time"},size,flags"

line()

file_info = FileInfoProvider(args.file_path)
is_video = file_info.is_video()

if not args.stream_specifier:
    if is_video:
        print("Video file detected. The first video stream will be analysed.")
        stream_specifier = "V:0"
        video_info = VideoInfoProvider(args.file_path)
    else:
        stream_specifier = "a:0"
        print(
            "It seems like you have specified an audio file. The first audio stream will be analysed."
        )
else:
    stream_specifier = args.stream_specifier

number_of_packets = file_info.get_number_of_packets(stream_specifier)

# The FFprobe command that will output the timestamps and packet sizes in CSV format.
cmd = [
    "ffprobe",
    "-v",
    "error",
    "-threads",
    str(os.cpu_count()),
    "-select_streams",
    stream_specifier,
    "-show_entries",
    entries,
    "-of",
    "csv=print_section=0:nk=1",
    args.file_path,
]

line()
file_duration = file_info.get_duration()
print(f"Detected the following info about {args.file_path}:")
line()
print(f"Duration: {file_duration}s")
print(f"Number of Packets: {number_of_packets}")

if is_video:
    is_constant_framerate = video_info.is_constant_framerate()

    if not is_constant_framerate:
        framerate = video_info.get_average_framerate()
        print(
            f"This video has a variable framerate. Average framerate is {framerate} FPS"
        )
    else:
        framerate = video_info.get_framerate_number()
        is_integer_framerate = video_info.is_integer_framerate()
        print(f"Framerate: {framerate} FPS")

line()

if args.gop:
    data_file = Path(output_dir).joinpath("gop_statistics.txt")

    with open(data_file, "w") as f:
        pass

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
    ) as progress_bar:
        task_1 = progress_bar.add_task(
            description="Retrieving packet data...",
            total=number_of_packets,
        )
        task_2 = progress_bar.add_task(
            description="Retrieving GOPs...",
            total=number_of_packets,
        )

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)

        gop_end_times, gop_bitrates, data = calculate_gop_bitrates(
            process,
            progress_bar,
            task_1,
            task_2,
            framerate,
            data_file,
            args.dts,
        )

    plt.figure(figsize=(15, 8))
    plt.suptitle(f"{filename} - Full Video")
    plt.xlabel("GOP end time (s)")
    plt.ylabel("GOP bitrate (Mbps)")

    if args.graph_type == "filled":
        plt.fill_between(gop_end_times, gop_bitrates, step="post", alpha=0.3)

    plt.step(gop_end_times, gop_bitrates, where="post", linestyle="-", linewidth=2)
    plt.scatter(gop_end_times, gop_bitrates, marker=".", color="red", s=20, alpha=0.5)
    plt.grid(True, alpha=0.3)
    plt.ylim(bottom=0)
    plt.savefig(Path(output_dir).joinpath("GOP_bitrates_graph.png"))
    plt.close()

else:
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
    ) as progress_bar:
        task_1 = progress_bar.add_task(
            description="Retrieving packet data...",
            total=number_of_packets,
        )
        task_2 = progress_bar.add_task(
            description="Summing packet sizes...",
            total=number_of_packets,
        )

        x_axis_values, bitrate_every_second, data = calculate_bitrates(
            process,
            progress_bar,
            task_1,
            task_2,
            args.dts,
            output_unit="mbps" if is_video else "kbps",
        )

    average_bitrate = round(sum(bitrate_every_second) / len(bitrate_every_second), 3)
    min_bitrate = round(min(bitrate_every_second), 3)
    max_bitrate = round(max(bitrate_every_second), 3)

    data_file = Path(output_dir).joinpath("bitrates.txt")

    print("Creating a graph...")
    plt.suptitle(
        f"{filename}\nMin: {min_bitrate} | Max: {max_bitrate} | Avg: {average_bitrate} {"Mbps" if is_video else "Kbps"}"
    )
    plt.xlabel("Time (s)")
    plt.ylabel(f"Bitrate ({"Mbps" if is_video else "Kbps"})")
    if args.graph_type == "filled":
        plt.fill_between(x_axis_values, bitrate_every_second)
    plt.plot(x_axis_values, bitrate_every_second)
    plt.savefig(Path(output_dir).joinpath("bitrates_graph.png"))

with open(output_dir.joinpath("data.json"), "w") as f:
    json.dump(data, f, indent=4)

print(f"Done! Check out the '{output_dir}' folder.")
