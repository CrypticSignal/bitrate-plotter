# Bitrate Plotter

A command line program that plots one of the following graphs:

**[1]** A graph showing the bitrate every second. The graph can be "filled" or "unfilled".

**[2]** A graph showing bitrate of every closed GOP (you must specify the `-gop` argument). Applicable to video files only.

You can find an example of each graph type below:

**Graph type [1] (unfilled):**

![Graph type [1] (unfilled)](<https://github.com/CrypticSignal/bitrate-variation-plotter/blob/main/Example%20Graphs/Bitrate%20every%20second%20(unfilled).png>)

_Image 1: a graph showing the bitrate every second. To see an example of a filled graph, check out the "Example Graphs" folder._

**Graph type [2]:**

![Graph type [2]](https://github.com/CrypticSignal/bitrate-plotter/blob/main/Example%20Graphs/Closed%20GOP%20bitrates.png)

_Image 2: a graph showing the bitrate of every closed GOP. The distances between the lines show the length (in seconds) of each closed GOP._

When opting for graph type **[1]**, the data used to plot the graph is saved in a file named `BitrateEverySecond.txt`. The data is in the format `timestamp --> bitrate`. Here's an example:

```
Timestamp: 1.001 --> 9.201 Mbps
Timestamp: 2.002 --> 9.256 Mbps
Timestamp: 3.003 --> 8.46 Mbps
Timestamp: 4.004 --> 8.898 Mbps
Timestamp: 5.005 --> 9.429 Mbps
Timestamp: 6.006 --> 8.784 Mbps
Timestamp: 7.007 --> 8.522 Mbps
Timestamp: 8.008 --> 8.276 Mbps
Timestamp: 9.009 --> 10.259 Mbps
Timestamp: 10.01 --> 9.958 Mbps
```

# Requirements

- Python 3.6+
- FFprobe executable in your PATH.
- `pip install -r requirements.txt`

# Usage

You can find the output of `python main.py -h` below:

```
usage: main.py [-h] -f FILE_PATH [-g {filled,unfilled}] [-gop] [-se SHOW_ENTRIES] [-ngm] [-s STREAM_SPECIFIER]

optional arguments:
  -h, --help            show this help message and exit
  -f FILE_PATH, --file-path FILE_PATH
                        Enter the path of the file that you want to analyse. If the path contains a space, it must be
                        surrounded in double quotes. Example: -f "C:/Users/H/Desktop/my file.mp4"
  -g {filled,unfilled}, --graph-type {filled,unfilled}
                        Specify the type of graph that should be created. The default graph type is "unfilled". To see
                        the difference between a filled and unfilled graph, check out the example graph files.
  -gop                  Instead of plotting the bitrate every second, plot the bitrate of each GOP. This plots GOP end
                        time (x-axis, in seconds) against GOP bitrate (y-axis, kbps).
  -se SHOW_ENTRIES, --show-entries SHOW_ENTRIES
                        Only applicable if --no-graph-mode is specified. Use FFprobe's -show_entries option to specify
                        what to output. Example: -se frame=key_frame,pkt_pts_time
  -ngm, --no-graph-mode
                        Enable "no graph mode" which simply writes the output of ffprobe to a .txt file. You should
                        also use the --show-entries argument to specify what information you want ffprobe to output.
  -s STREAM_SPECIFIER, --stream-specifier STREAM_SPECIFIER
                        Use FFmpeg stream specifier syntax to specify the audio/video stream that you want to analyse.
                        The defaults for audio and video files are a:0 and V:0, respectively. Note that stream index
                        starts at 0. As an example, to target the 2nd audio stream, enter: --stream-specifier a:1
```
