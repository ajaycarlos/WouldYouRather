"""
Generates the on-screen percentage split. This is NOT real poll data - there's
no actual audience vote happening. It's a deliberate, transparent convention
of this content genre (viewers understand these aren't scientifically polled
numbers). Always skewed, never a coin-flip 50/50, never a total blowout -
keeps the reveal satisfying without being meaningless.
"""
import random
import config


def generate_split() -> dict:
    """Returns {"a": int, "b": int} summing to 100, with a's/b's split randomized
    on which side wins."""
    winner_pct = random.randint(config.PERCENT_SPLIT_MIN, config.PERCENT_SPLIT_MAX)
    loser_pct = 100 - winner_pct
    a_wins = random.choice([True, False])
    return {"a": winner_pct if a_wins else loser_pct, "b": loser_pct if a_wins else winner_pct}


if __name__ == "__main__":
    for _ in range(5):
        print(generate_split())
