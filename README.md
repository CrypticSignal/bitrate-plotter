# Bitrate Plotter
A command line program that plots one of the following graphs:

**[1]** A graph showing the bitrate every second. The graph can be "filled" or "unfilled".

**[2]** A graph showing bitrate of every closed GOP (you must specify the `-gop` argument). Applicable to video files only.

You can find an example of each graph type below:

**Graph type [1] (unfilled):**

![Graph type [1] (unfilled)](https://github.com/CrypticSignal/bitrate-variation-plotter/blob/main/Example%20Graphs/Bitrate%20every%20second%20(unfilled).png)

*Image 1: a graph showing the bitrate every second. To see an example of a filled graph, check out the "Example Graphs" folder.* 

**Graph type [2]:**

![Graph type [2]](https://github.com/CrypticSignal/bitrate-plotter/blob/main/Example%20Graphs/Closed%20GOP%20bitrates.png)

*Image 2: a graph showing the bitrate of every closed GOP. The distances between the lines show the length (in seconds) of each closed GOP.*

When opting for graph type **[1]**, the data used to plot the graph is saved in a filed named `BitrateEverySecond.txt`. The data is in the format `timestamp --> bitrate`. Here is a sample:
```
1.008 --> 223 kbps
2.016 --> 257 kbps
3.0 --> 239 kbps
4.008 --> 250 kbps
5.016 --> 263 kbps
6.0 --> 253 kbps
7.008 --> 264 kbps
8.016 --> 267 kbps
9.0 --> 260 kbps
10.008 --> 266 kbps
```
When opting for graph type **[2]**, the raw FFprobe output is saved in a file named `Keyframes & GOPs.txt`. Each line in this file represents a frame, and you can see the following data:
1. Whether the frame is a keyframe (if you see `key_frame=1`, that frame is a keyframe).
2. The timestamp of the frame (`pts_pkt_time`).
3. The size of the frame in bytes (`pkt_size`).

You can find an example line below:

`key_frame=1,pkt_pts_time=0.000000,pkt_size=250439`

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