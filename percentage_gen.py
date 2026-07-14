"""
Generates the on-screen percentage split. This is NOT real poll data - there's
no actual audience vote happening. It's a deliberate, transparent convention
of this content genre (viewers understand these aren't scientifically polled
numbers). Always skewed, never a coin-flip 50/50, never a total blowout -
keeps the reveal satisfying without being meaningless.

Cross-round deduplication: generate_split() accepts an optional `used_splits`
list and retries until the result is unique. Prevents the same 31/69 appearing
in consecutive rounds.
"""
import random
import config


def generate_split(used_splits: list = None, max_retries: int = 20) -> dict:
    """
    Returns {"a": int, "b": int} summing to 100, with the winner randomised
    between PERCENT_SPLIT_MIN and PERCENT_SPLIT_MAX.

    used_splits: list of previously-generated (a, b) tuples for this video.
    Retries until a fresh split is found, up to max_retries times.
    """
    used_splits = used_splits or []
    used_set = {(s["a"], s["b"]) for s in used_splits}

    for _ in range(max_retries):
        winner_pct = random.randint(config.PERCENT_SPLIT_MIN, config.PERCENT_SPLIT_MAX)
        loser_pct  = 100 - winner_pct
        a_wins     = random.choice([True, False])
        result     = {"a": winner_pct if a_wins else loser_pct,
                      "b": loser_pct  if a_wins else winner_pct}
        if (result["a"], result["b"]) not in used_set:
            return result

    # Fallback: return a valid split even if it's not perfectly unique
    # (only possible if range is extremely narrow, e.g. MIN==MAX)
    winner_pct = random.randint(config.PERCENT_SPLIT_MIN, config.PERCENT_SPLIT_MAX)
    loser_pct  = 100 - winner_pct
    a_wins     = random.choice([True, False])
    return {"a": winner_pct if a_wins else loser_pct,
            "b": loser_pct  if a_wins else winner_pct}


if __name__ == "__main__":
    used = []
    for _ in range(5):
        s = generate_split(used)
        used.append(s)
        print(s)
