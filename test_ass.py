import subprocess

ass = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,100,&HFFFFFF&,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,4,0,5,40,40,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:03.00,Default,,0,0,0,,{\\c&HFFFFFF&\\t(0,100,\\c&H00FFFF&)\\t(1000,1010,\\c&HFFFFFF&)}Hello {\\c&HFFFFFF&\\t(1000,1010,\\c&H00FFFF&)\\t(2000,2010,\\c&HFFFFFF&)}World
"""
with open("test.ass", "w") as f:
    f.write(ass)

subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=3", "-vf", "ass=test.ass", "test.mp4"])
