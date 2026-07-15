"""
ONE Gemini call generates everything needed for the whole video - avoids
per-round API calls (rate limits, more points of failure). Returns a single
structured JSON covering all rounds, per-word color highlighting, image
search terms, the host's pick + reason per round, the closing loop bumper,
and YouTube metadata (title/description/tags) - all in one response.
"""
import json
import config
from google import genai
from google.genai import types
from retry_utils import retry

PERSONA_PREPROMPT = (
    "You are an unapologetic, highly opinionated internet host. Your sole goal is to spark "
    "outrage, debate, and engagement. Do not use filler or pleasantries. Be absurd and confident."
)

SCHEMA_INSTRUCTIONS = """
Return ONLY valid JSON (no markdown fences, no preamble) matching this exact schema:

{
  "rounds": [
    {
      "option_a": {
        "text": "short punchy phrasing of option A, e.g. 'be a genius and know everything'",
        "image_query": "2-4 word stock photo search term that visually represents this option, e.g. 'einstein portrait'",
        "colored_words": [{"word": "genius", "color": "yellow"}]
      },
      "option_b": {
        "text": "short punchy phrasing of option B",
        "image_query": "2-4 word stock photo search term",
        "colored_words": [{"word": "sports", "color": "cyan"}]
      },
      "my_pick": "a",
      "pick_reason": "an absolutely unhinged, highly controversial, or completely illogical hot take justifying the choice. It must be deliberate engagement bait designed to make viewers angry enough to comment and disagree with you. Maximum one sentence."
    }
  ],
  "closing_bumper": "one short line that flows naturally into the video looping back to the start, e.g. mentions subscribing then asks the viewer what they'd choose",
  "title": "YouTube title under 60 characters, curiosity-driven",
  "description": "2 sentences with a soft follow/comment CTA",
  "tags": ["8 to 10 relevant tags, no # symbol"]
}

Rules for "colored_words": pick 1-2 KEY words per option whose meaning suits a
color (e.g. "hot"->red, "cold"->blue, "money"->green, "danger"->red,
"genius"->yellow, "love"->pink) - only color words where a color genuinely
fits the meaning; use hex-safe simple color names from this set only: red,
blue, green, yellow, cyan, orange, pink, white. If no word has an obvious
color fit, colored_words can be an empty list.
"""


@retry(times=3, delay=5, backoff=3)
def generate_video_script(round_count: int = None, avoid_questions: list = None) -> dict:
    round_count = round_count or config.ROUNDS_PER_VIDEO
    client = genai.Client(api_key=config.GEMINI_API_KEY)

    prompt = f"""
Write {round_count} EXTREME "Would You Rather" rounds for a YouTube Shorts game.
Drop vanilla questions entirely. Focus on high-conflict moral dilemmas, mild
gross-out scenarios, and absurdly controversial choices designed to split an
audience 50/50 and cause intense arguments in the comments. Avoid anything that
could be read as making light of real tragedy, self-harm, or targeting real people.
"""
    if avoid_questions:
        recent = "; ".join(avoid_questions[-15:])  # keep prompt short - recent history is what matters most
        prompt += f"\nDo NOT repeat or closely rephrase any of these recently used question pairs: {recent}\n"

    prompt += SCHEMA_INSTRUCTIONS

    response = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.9,
            system_instruction=f"{PERSONA_PREPROMPT} You write short-form interactive game-show scripts.",
        ),
    )

    text = response.text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.endswith("```"):
        text = text[:-3]

    return json.loads(text.strip())


if __name__ == "__main__":
    data = generate_video_script(2)
    print(json.dumps(data, indent=2))