from argparse import ArgumentParser, RawTextHelpFormatter

parser = ArgumentParser(formatter_class=RawTextHelpFormatter)

parser.add_argument(
    "-f",
    "--file-path",
    type=str,
    required=True,
    help="Enter the path of the file that you want to analyse.\n"
    "If the path contains a space, it must be surrounded in double quotes.\n"
    'Example: -f "C:/Users/H/Desktop/my file.mp4"',
)

parser.add_argument(
    "-dts",
    action="store_true",
    help="Use DTS instead of PTS when calculating bitrates.\nOnly applicable if analysing a video file.",
)

parser.add_argument(
    "-gop",
    action="store_true",
    help="Output information about every Group Of Pictures (GOP).\nOnly applicable if analysing a video file.",
)

parser.add_argument(
    "-g",
    "--graph-type",
    choices=["filled", "unfilled"],
    default="unfilled",
    help='Specify the type of graph that should be created. The default graph type is "unfilled".\n'
    "To see the difference between a filled and unfilled graph, check out the example graph files.",
)

parser.add_argument(
    "-s",
    "--stream-specifier",
    type=str,
    help="Use FFmpeg stream specifier syntax to specify the audio/video stream that you want to analyse.\n"
    "The defaults for audio and video files are a:0 and V:0, respectively.\n"
    "Note that stream index starts at 0.\n"
    "As an example, to target the 2nd audio stream: --stream-specifier a:1",
)

args = parser.parse_args()
