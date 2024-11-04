# Bitrate Plotter
A command line program that plots one of the following graphs:

**[1]** A graph showing the bitrate every second. The graph can be "filled" or "unfilled".

**[2]** A graph showing bitrate of every Group of Pictures (GOP). You must use the `-gop` argument if this is what you are looking for. Only applicable if analysing a video file.

You can find an example of each graph type below:

**Graph type [1] (unfilled):**
![Graph type [1] (unfilled)](<https://github.com/CrypticSignal/bitrate-variation-plotter/blob/main/Example%20Graphs/Bitrate%20every%20second%20(unfilled).png>)

_Image 1: a graph showing the bitrate every second. To see an example of a filled graph, check out the "Example Graphs" folder._

**Graph type [2]:**

![Graph type [2]](https://github.com/CrypticSignal/bitrate-plotter/blob/main/Example%20Graphs/Closed%20GOP%20bitrates.png)

_Image 2: a graph showing the bitrate of every GOP. The distances between the lines show the length (in seconds) of each GOP._

# Requirements
- Python 3.6+
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
  -gop                  Instead of plotting the bitrate of every second, plot the bitrate of every GOP.
                        Only applicable if analysing a video file.
                        This plots GOP end time (x-axis, in seconds) against GOP bitrate (y-axis, Mbps).
  -g, --graph-type {filled,unfilled}
                        Specify the type of graph that should be created. The default graph type is "unfilled".
                        To see the difference between a filled and unfilled graph, check out the example graph files.
  -s, --stream-specifier STREAM_SPECIFIER
                        Use FFmpeg stream specifier syntax to specify the audio/video stream that you want to analyse.
                        The defaults for audio and video files are a:0 and V:0, respectively.
                        Note that stream index starts at 0.
                        As an example, to target the 2nd audio stream: --stream-specifier a:1
```