# Bitrate Variation Plotter
A command line program that plots a graph showing the variation of the bitrate throughout the specified audio/video file. The graph can be "filled" or "unfilled":

**Unfilled:**

![Unfilled Graph](https://github.com/CrypticSignal/bitrate-variation-plotter/blob/main/Unfilled%20Graph%20Example.png)

**Filled:**

![Filled Graph](https://github.com/CrypticSignal/bitrate-variation-plotter/blob/main/Filled%20Graph%20Example.png)

In addition to this, the data used to plot the graph is saved in a .txt file. The data is in the format `timestamp --> bitrate`. Here is a sample:
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

# Requirements 
- Python 3.6+
- FFprobe executable in your PATH.
- `pip install -r requirements.txt`

# Usage
Simply specify the path of the file you wish to analyse, as well as your desired graph type. Here's an example:

`python main.py -f video.mp4 --graph-type filled`

To analyse a specific stream, use the `-s`/`--stream-specifier` argument:

`python main.py -f video.mp4 -s a:0 --graph-type filled`

You can find the output of `python main.py -h` below:
```
usage: main.py [-h] -f FILE_PATH [-g {filled,unfilled}] [-gop] [-se SHOW_ENTRIES] [-ngm] [-s STREAM_SPECIFIER]

optional arguments:
  -h, --help            show this help message and exit
  -f FILE_PATH, --file-path FILE_PATH
                        Enter the path of the file that you want to analyse. If the path contains a space, it must be
                        surrounded in double quotes. Example: -f "C:/Users/H/Desktop/my file.mp4" (default: None)
  -g {filled,unfilled}, --graph-type {filled,unfilled}
                        Specify the type of graph that should be created. To see the difference between a filled and
                        unfilled graph, check out the example graph files. (default: unfilled)
  -gop                  Instead of plotting the bitrate every second, plot the bitrate of each GOP. This plots GOP end
                        time (x-axis, in seconds) against GOP bitrate (y-axis, kbps). (default: False)
  -se SHOW_ENTRIES, --show-entries SHOW_ENTRIES
                        Use FFprobe's -show_entries option to specify what to output. Example: -se
                        frame=key_frame,pkt_pts_time (default: packet=pts_time,size)
  -ngm, --no-graph-mode
                        Enable "no graph mode" which simply writes the output of ffprobe to a .txt file. You should
                        also use the --show-entries argument to specify what information you want ffprobe to output.
                        (default: False)
  -s STREAM_SPECIFIER, --stream-specifier STREAM_SPECIFIER
                        Use FFmpeg stream specifier syntax to specify the audio/video stream that you want to analyse.
                        The defaults for audio and video files are a:0 and V:0, respectively. Stream index starts at
                        0, therefore, as an example, to target the 2nd audio stream, enter -s a:1 (default: None)
```