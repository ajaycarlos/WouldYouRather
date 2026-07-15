import subprocess
ass = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Fredoka Bold,110,&HFFFFFF&,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,0,5,40,40,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:03.00,Default,,0,0,0,,Hello World
"""
with open("test_font3.ass", "w") as f: f.write(ass)
p = subprocess.run(["ffmpeg", "-y", "-v", "debug", "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=1", "-vf", "ass=test_font3.ass:fontsdir='.'", "test_font3.mp4"], capture_output=True, text=True)
for line in p.stderr.splitlines():
    if "fontselect" in line: print(line)
