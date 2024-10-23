import os
import subprocess


def calc_number_of_frames(file_path, stream_specifier, file_duration):
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-threads",
        str(os.cpu_count()),
        "-select_streams",
        stream_specifier,
        "-show_entries",
        "stream=r_frame_rate",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        file_path,
    ]
    process = subprocess.run(cmd, capture_output=True)
    output = process.stdout.decode("utf-8")
    numerator, denominator = output.split("/")
    framerate = int(numerator) / int(denominator)
    number_of_frames = framerate * file_duration
    return number_of_frames


def get_file_duration(file_path, stream_specifier):
    duration_cmd = [
        "ffprobe",
        "-v",
        "error",
        "-threads",
        str(os.cpu_count()),
        "-select_streams",
        stream_specifier,
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        file_path,
    ]
    process = subprocess.run(duration_cmd, capture_output=True)

    return float(process.stdout.decode("utf-8"))


def write_to_txt_file(filename, data, mode="a"):
    with open(filename, mode) as f:
        f.write(data)
