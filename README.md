# Bitrate Plotter
A command line program that outputs one of the following:

**[1]** A graph showing the bitrate every second. The graph can be "filled" or "unfilled".

Unfilled graph example:

![Unfilled graph example](<https://github.com/CrypticSignal/bitrate-variation-plotter/blob/main/Example%20Graphs/Bitrate%20every%20second%20(unfilled).png>)

Filled graph example:

![Filled graph example](<https://github.com/CrypticSignal/bitrate-variation-plotter/blob/main/Example%20Graphs/Bitrate%20every%20second%20(filled).png>)


**[2]** Information about every Group of Pictures (GOP). You must use the `-gop` argument if this is what you are looking for. Only applicable if analysing a video file. Here's an example of the output:
```
Detected the following info about BigBuckBunny.mp4:
----------------------------------------------------
Duration: 596.474195s
Number of Frames: 14315
Framerate: 24.0 FPS
----------------------------------------------------
GOP Statistics:

GOP count: 266
Average number of packets per GOP: 53.8
GOP duration range: 0.500s to 2.500s
Average GOP duration: 2.242s
GOP size range: 0.54 to 9.09 Megabits
GOP bitrate range: 0.51 to 4.07 Mbps
Average GOP bitrate: 2.00 Mbps

✓ Average PTS interval matches expected frame rate
✓ PTS intervals are consistent
[Info] GOP durations are inconsistent:
Min GOP Duration: 0.5000006666665892
Max GOP Duration: 2.5000006666667027
```

# Requirements
- Python 3.7+
- FFprobe executable in your PATH.
- `pip install -r requirements.txt`

# Usage
You can find the output of `python main.py -h` below:
```
usage: main.py [-h] -f FILE_PATH [-dts] [-gop] [-g {filled,unfilled}] [-s STREAM_SPECIFIER]

options:
  -h, --help            show this help message and exit
  -f, --file-path FILE_PATH
                        Enter the path of the file that you want to analyse.
                        If the path contains a space, it must be surrounded in double quotes.
                        Example: -f "C:/Users/H/Desktop/my file.mp4"
  -dts                  Use DTS instead of PTS when calculating bitrates.
                        Only applicable if analysing a video file.
  -gop                  Output information about every Group Of Pictures (GOP).
                        Only applicable if analysing a video file.
  -g, --graph-type {filled,unfilled}
                        Specify the type of graph that should be created. The default graph type is "unfilled".
                        To see the difference between a filled and unfilled graph, check out the example graph files.
  -s, --stream-specifier STREAM_SPECIFIER
                        Use FFmpeg stream specifier syntax to specify the audio/video stream that you want to analyse.
                        The defaults for audio and video files are a:0 and V:0, respectively.
                        Note that stream index starts at 0.
                        As an example, to target the 2nd audio stream: --stream-specifier a:1
```