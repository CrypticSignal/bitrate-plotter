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
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    SpinnerColumn,
    MofNCompleteColumn,
)

filename = Path(args.file_path).name
output_dir = f"[{filename}]"
os.makedirs(output_dir, exist_ok=True)

entries = f"packet={"dts_time" if args.dts else "pts_time"},size"

if args.gop:
    entries = f"packet={"dts_time" if args.dts else "pts_time"},size,flags"

line()

file_info = FileInfoProvider(args.file_path)
first_stream = file_info.first_stream_info()

if not args.stream_specifier:
    if "codec_type=video" in first_stream:
        print("Video file detected. The first video stream will be analysed.")
        stream_specifier = "V:0"
        video_info = VideoInfoProvider(args.file_path)
        is_video = True
    elif "codec_type=subtitle" in first_stream:
        print(
            "It seems like you have specified a video file. The first video stream will be analysed.\n"
            "If this is not what you want, re-run this program using the -s argument "
            "to manually specify the stream to analyse."
        )
        stream_specifier = "V:0"
        video_info = VideoInfoProvider(args.file_path)
        is_video = True
    else:
        stream_specifier = "a:0"
        print(
            "It seems like you have specified an audio file. The first audio stream will be analysed."
        )
        is_video = False
else:
    stream_specifier = args.stream_specifier

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

if is_video:
    number_of_frames = video_info.get_number_of_frames()
    print(f"Number of Frames: {number_of_frames}")

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
        MofNCompleteColumn(),
    ) as progress_bar:
        task_1 = progress_bar.add_task(
            description="Collecting frames...",
            total=number_of_frames,
        )

        task_2 = progress_bar.add_task(
            description="Processing frames...",
            total=number_of_frames,
        )

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)

        gop_end_times, gop_bitrates = calculate_gop_bitrates(
            process,
            progress_bar,
            task_1,
            task_2,
            framerate,
            number_of_frames,
            data_file,
            args.dts,
        )

    plt.suptitle(filename)
    plt.xlabel("GOP end time (s)")
    plt.ylabel("GOP bitrate (Mbps)")

    if args.graph_type == "filled":
        plt.fill_between(gop_end_times, gop_bitrates)

    plt.stem(gop_end_times, gop_bitrates)
    plt.savefig(Path(output_dir).joinpath("GOP_bitrates_graph.png"))

else:
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
    ) as progress_bar:
        task_id = progress_bar.add_task(
            description="Calculating bitrates...",
            total=number_of_frames if is_video else file_duration,
        )
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)

        x_axis_values, bitrate_every_second = calculate_bitrates(
            process,
            progress_bar,
            task_id,
            number_of_frames,
            framerate,
            is_constant_framerate,
            is_integer_framerate,
            args.dts,
        )

    average_bitrate = round(sum(bitrate_every_second) / len(bitrate_every_second), 3)
    min_bitrate = round(min(bitrate_every_second), 3)
    max_bitrate = round(max(bitrate_every_second), 3)

    data_file = Path(output_dir).joinpath("bitrates.txt")

    print("Creating a graph...")
    plt.suptitle(
        f"{filename}\nMin: {min_bitrate} | Max: {max_bitrate} | Avg: {average_bitrate} Mbps"
    )
    plt.xlabel("Time (s)")
    plt.ylabel("Bitrate (Mbps)")
    if args.graph_type == "filled":
        plt.fill_between(x_axis_values, bitrate_every_second)
    plt.plot(x_axis_values, bitrate_every_second)
    plt.savefig(Path(output_dir).joinpath("bitrates_graph.png"))

    print(f"Done! Check out the '{output_dir}' folder.")
