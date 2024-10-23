from argparse import ArgumentParser
import io
import os
from pathlib import Path
import subprocess

import matplotlib.pyplot as plt
import mplcursors
from rich.progress import (
    Progress,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    SpinnerColumn,
    MofNCompleteColumn,
)

from ffprobe_output_parser import get_bitrate_every_second, get_gop_bitrates
from utils import calc_number_of_frames, get_file_duration, write_to_txt_file

parser = ArgumentParser()
parser.add_argument(
    "-f",
    "--file-path",
    type=str,
    required=True,
    help="Enter the path of the file that you want to analyse. "
    "If the path contains a space, it must be surrounded in double quotes. "
    'Example: -f "C:/Users/H/Desktop/my file.mp4"',
)
parser.add_argument(
    "-g",
    "--graph-type",
    choices=["filled", "unfilled"],
    default="unfilled",
    help='Specify the type of graph that should be created. The default graph type is "unfilled". '
    "To see the difference between a filled and unfilled graph, check out the example graph files.",
)
parser.add_argument(
    "-gop",
    action="store_true",
    help="Instead of plotting the bitrate every second, plot the bitrate of each GOP. "
    "This plots GOP end time (x-axis, in seconds) against GOP bitrate (y-axis, Mbps).",
)
parser.add_argument(
    "-se",
    "--show-entries",
    type=str,
    default="packet=dts_time,size",
    help="Only applicable if --no-graph-mode is specified. "
    "Use FFprobe's -show_entries option to specify what to output. Example: -se frame=key_frame,pkt_pts_time",
)
parser.add_argument(
    "-ngm",
    "--no-graph-mode",
    action="store_true",
    help='Enable "no graph mode" which simply writes the output of ffprobe to a .txt file. '
    "You should also use the --show-entries argument to specify what information you want ffprobe to output.",
)
parser.add_argument(
    "-s",
    "--stream-specifier",
    type=str,
    help="Use FFmpeg stream specifier syntax to specify the audio/video stream that you want to analyse. "
    "The defaults for audio and video files are a:0 and V:0, respectively. "
    "Note that stream index starts at 0. "
    "As an example, to target the 2nd audio stream, enter: --stream-specifier a:1",
)

args = parser.parse_args()
filename = Path(args.file_path).name
filename_without_ext = Path(args.file_path).stem

output_dir = f"{filename}_bitrate_analysis"
os.makedirs(output_dir, exist_ok=True)

# This command will information about file's first stream.
cmd = [
    "ffprobe",
    "-v",
    "error",
    "-threads",
    str(os.cpu_count()),
    "-show_streams",
    "-select_streams",
    "0",
    args.file_path,
]

process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
first_stream = process.stdout.read().decode("utf-8")

if not args.stream_specifier:
    if "codec_type=video" in first_stream:
        print("Video file detected. The video stream will be analysed.")
        stream_specifier = "V:0"
    elif "codec_type=subtitle" in first_stream:
        print(
            "It seems like you have specified a video file. The video stream will be analysed.\n"
            "If this is not what you want, re-run this program using the -s argument "
            "to manually specify the stream to analyse."
        )
        stream_specifier = "V:0"
    else:
        stream_specifier = "a:0"
        print(
            "It seems like you have specified an audio file. The first audio stream will be analysed."
        )
else:
    stream_specifier = args.stream_specifier
    print(f"The bitrate of stream {args.stream_specifier} will be analysed.")

file_duration = get_file_duration(args.file_path, stream_specifier)

if "V" in stream_specifier or "v" in stream_specifier:
    number_of_frames = calc_number_of_frames(
        args.file_path, stream_specifier, file_duration
    )

# To calculate the bitrate every second, FFprobe needs to output the following entries.
entries = "packet=dts_time,size"

if args.no_graph_mode:
    entries = args.show_entries
elif args.gop:
    entries = "frame=key_frame,pkt_dts_time,pkt_size"

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
process = subprocess.Popen(cmd, stdout=subprocess.PIPE)

if args.gop:
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        MofNCompleteColumn(),
    ) as progress_bar:
        task_id = progress_bar.add_task(
            description="Processing frames...",
            total=number_of_frames,
        )

        gop_end_times, gop_bitrates = get_gop_bitrates(
            process, progress_bar, task_id, number_of_frames
        )

    plt.suptitle(filename)
    plt.xlabel("GOP end time (s)")
    plt.ylabel("GOP bitrate (Mbps)")

    if args.graph_type == "filled":
        plt.fill_between(gop_end_times, gop_bitrates)

    plt.stem(gop_end_times, gop_bitrates)
    # Use mplcursors to show the X and Y value when hovering over a point on the line.
    cursor = mplcursors.cursor(hover=True)
    cursor.connect(
        "add",
        lambda sel: sel.annotation.set_text(
            f"{round(sel.target[0], 1)}, {round(sel.target[1], 1)}"
        ),
    )

    plt.savefig(Path(output_dir).joinpath("GOP bitrates graph.png"))

else:
    if args.no_graph_mode:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            MofNCompleteColumn(),
        ) as progress_bar:
            task_id = progress_bar.add_task(
                description="Processing frames...",
                total=number_of_frames,
            )

            frame_number = 0
            # GOP length in terms of number of frames.
            gop_length = 0

            if "key_frame" in args.show_entries:
                for line in io.TextIOWrapper(process.stdout):
                    frame_number += 1
                    gop_length += 1
                    progress_bar.update(task_id, completed=frame_number)

                    if line.strip() == "1":
                        write_to_txt_file(
                            Path(output_dir).joinpath(
                                f"{args.show_entries.split("=")[1]}.txt"
                            ),
                            f"Frame {frame_number} is an I-frame\n{'GOP length was ' + str(gop_length) + ' frames\n\n' if gop_length != 1 else '\n'}",
                        )

                        print(
                            "-----------------------------------------------------------------------"
                        )
                        print(f"Frame {frame_number} is an I-frame")

                        if gop_length != 1:
                            print(f"GOP length was {gop_length} frames")

                        # We have reached the next I-frame, set gop_length to 0 to calculate the next GOP length.
                        gop_length = 0

            elif "pict_type" in args.show_entries:
                for line in io.TextIOWrapper(process.stdout):
                    frame_number += 1
                    gop_length += 1

                    progress_bar.update(task_id, completed=frame_number)

                    pict_type = line.strip()

                    write_to_txt_file(
                        Path(output_dir).joinpath(
                            f"{args.show_entries.split("=")[1]}.txt"
                        ),
                        f"{'\n' if pict_type == 'I' and frame_number > 1 else ''}Frame {frame_number} is {'an' if pict_type == 'I' else 'a'} {pict_type}-frame\n{'GOP length was ' + str(gop_length) + ' frames\n\n' if pict_type == "I" and gop_length != 1 else ''}",
                    )

                    if pict_type == "I":
                        # We have reached the next keyframe, set gop_length to 0 to calculate the next GOP length.
                        gop_length = 0

            else:
                for line in io.TextIOWrapper(process.stdout, encoding="utf-8"):
                    frame_number += 1
                    progress_bar.update(task_id, completed=frame_number)

                    write_to_txt_file(
                        Path(output_dir).joinpath(
                            f"{args.show_entries.split("=")[1]}.txt"
                        ),
                        line,
                    )

        print(f"Done! Check out {output_dir}/{args.show_entries.split("=")[1]}.txt")

    else:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
        ) as progress_bar:
            task_id_1 = progress_bar.add_task(
                description=f"Retrieving {"video" if stream_specifier == "V:0" else "audio"} stream data...",
                total=file_duration,
            )
            task_id_2 = progress_bar.add_task(
                description="Calculating bitrates...",
                total=file_duration,
            )

            # Parse the ffprobe output save the timestamps and bitrates in the time_data and size_data lists, respectively.
            x_axis_values, bitrate_every_second = get_bitrate_every_second(
                process,
                Path(output_dir).joinpath("bitrates.txt"),
                progress_bar,
                task_id_1,
                task_id_2,
            )

        average_bitrate = round(
            sum(bitrate_every_second) / len(bitrate_every_second), 3
        )
        min_bitrate = round(min(bitrate_every_second), 3)
        max_bitrate = round(max(bitrate_every_second), 3)

        raw_data_file = Path(output_dir).joinpath("bitrates.txt")

        write_to_txt_file(
            raw_data_file,
            f"\nMin Bitrate: {min_bitrate} Mbps\nAverage Bitrate: {average_bitrate} Mbps\nMax Bitrate: {max_bitrate} Mbps",
        )

        print("Creating a graph...")
        plt.suptitle(
            f"{filename}\nMin: {min_bitrate} | Max: {max_bitrate} | Avg: {average_bitrate} Mbps"
        )
        plt.xlabel("Time (s)")
        plt.ylabel("Bitrate (Mbps)")
        if args.graph_type == "filled":
            plt.fill_between(x_axis_values, bitrate_every_second)
        plt.plot(x_axis_values, bitrate_every_second)
        plt.savefig(Path(output_dir).joinpath("graph.png"))

        print(f"Done! Check out the {output_dir} folder.")
