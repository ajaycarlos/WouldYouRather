# Would You Rather - Automated Shorts Pipeline

Generates split-screen "Would You Rather" game videos: plain-background intro
per round → split-screen question with images → timer tick sound → percentage
reveal → host's pick + reason → loops through 2-3 rounds → closing bumper
that flows into the video looping.

## How it works

1. **One Gemini call per video** generates everything: all rounds' question
   text, per-word color highlighting, image search terms, the host's pick +
   reason, the closing bumper, and YouTube title/description/tags - all in a
   single structured JSON response.
2. **Images** come from Pexels (free, no commercial restriction) using
   Gemini's suggested search term per option.
3. **Voiceover** uses Edge-TTS (free) - and its word-boundary timing events
   are captured directly, giving exact caption timing without needing Whisper.
4. **Percentages are NOT real poll data** - `percentage_gen.py` generates a
   plausible skewed split (never 50/50, never a total blowout). This is a
   transparent, standard convention of this content genre.
5. **Captions** are built with three modes: centered (plain background beats),
   anchored to the top half (option A), or bottom half (option B) - with
   specific words colored based on Gemini's semantic color mapping.
6. **Timer sound** is procedurally synthesized via ffmpeg (no external sound
   library, zero licensing question).

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:
- `GEMINI_API_KEY` - aistudio.google.com
- `PEXELS_API_KEY` - pexels.com/api, free signup
- YouTube OAuth: same process as the other channels - Google Cloud Console →
  enable YouTube Data API v3 + YouTube Analytics API → OAuth Client ID →
  Desktop App → save as `client_secret.json`. **This needs to be a separate
  OAuth setup from channels 1 and 2** if this is going to a different YouTube
  channel.

You also need the Poppins font installed (same as the other channels):
```bash
mkdir -p ~/.fonts
wget https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Bold.ttf -P ~/.fonts
fc-cache -f
```

And ffmpeg installed and on PATH.

## Run

```bash
python main.py
```

First run opens a browser once for YouTube OAuth, then runs fully automated
from there.

## Content note

The reveal percentages are a well-understood convention in this content genre,
not real audience polling - this pipeline doesn't collect or claim to collect
real votes. Gemini is instructed to avoid questions that trivialize real
tragedy, self-harm, or target real people - worth spot-checking output
periodically since this runs unattended.

## Not yet built

- GitHub Actions workflow (same pattern as channels 1 & 2 - add when ready)
