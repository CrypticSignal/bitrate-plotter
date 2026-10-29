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
- Python 3.7+ (and Matplotlib 3.4+ for interval plots)
- FFprobe executable in your PATH.
- `pip install -r requirements.txt`

# Usage
You can find the output of `python main.py -h` below:
```
usage: main.py [-h] -f FILE_PATH [-dts] [-gop] [-g {filled,unfilled}] [-s STREAM_SPECIFIER] [--include-partial]

options:
  --include-partial     Include partial edge buckets (still divided by one second).
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

## Calculation rules

Per-second rates sum selected-stream packet bytes in fixed `[second, second + 1)` buckets, using `floor(PTS)` or `floor(DTS)`, then multiply by 8 and convert to decimal kbps/Mbps. Negative timestamps are supported. Full intervals inside the packet timeline are included, even at low frame rates or with no packets (zero bitrate); packet density is not a completeness test. The timeline ends at the latest packet timestamp plus duration. Missing video packet durations fall back to average frame rate, then nominal frame rate; otherwise unknown durations count as zero.

Partial edge intervals are excluded by default and their actual ranges are reported. Use `--include-partial` to keep them; their values still divide by one second rather than extrapolating. The chart mean covers displayed intervals. JSON also reports a whole-stream mean using all valid selected packet bits divided by the full packet timeline (unavailable for zero duration). Container duration and bitrate are not used as calculation denominators. `-dts` works for audio and video; the default remains PTS.

GOPs start at keyframes in the selected timestamp order. Each ends at the next keyframe; the final GOP ends at its latest packet end. Packets before the first keyframe are excluded from GOP rates. The overall GOP mean is duration-weighted. These are packet-based groups, not decoded dependency graphs; reordered video can differ between PTS and DTS. Graph steps now cover the actual analyzed interval/GOP boundaries.

Stream specifiers must select exactly one audio/video stream. Units, metadata, and frame-rate fallback follow that stream, including when selecting audio inside a video file. FFprobe failures and missing keyframes/timestamps produce errors instead of partial successful results. Packet bitrates exclude container and transport overhead.

## Tests

With dependencies installed and native FFmpeg/FFprobe available:

```bash
python -m unittest discover -s tests -v
```

Tests cover exact-second endings, negative/nonzero timestamps, low-rate and sparse streams, partial intervals, invalid packets, variable GOP durations, weighted means, and independent native packet sums. CLI checks verify audio/video selection, GOP output, and generated graphs/JSON. No `ffmpeg-python` package is needed; FFprobe is called directly.
