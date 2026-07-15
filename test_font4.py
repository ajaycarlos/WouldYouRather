import subprocess
p = subprocess.run(["ffmpeg", "-y", "-v", "debug", "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=1", "-vf", "ass=test_font2.ass:fontsdir='.'", "test_font4.mp4"], capture_output=True, text=True)
for line in p.stderr.splitlines():
    if "font" in line.lower(): print(line)
