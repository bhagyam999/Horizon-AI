# Horizon RPG v18 — AI Tone Balance

## Purpose

v18 refines Horizon's conversational personality after the v17 sense cleanup.
The goal is to keep Horizon sensible and useful while allowing occasional light
humor or sarcasm when the user is clearly in a playful/bored mood.

## Tone behavior

- Normal requests stay normal: no deliberate sarcasm or banter.
- Explicit boredom/joke/roast/banter requests can trigger a light playful moment.
- Playful mode is **request-local** and is not stored as a personality state.
- When the user changes subject or asks a normal/serious/technical question, the
  next response automatically returns to the normal tone.
- Humor is optional even during a playful moment.
- Sarcasm should be mild, short, and natural rather than a long roast or monologue.
- Horizon should not repeatedly joke about being an AI, rebooting, hardware,
  shutdowns, server stability, or personality settings unless that is actually the topic.
- Server personality settings remain additional guidance and cannot force constant
  sarcasm, verbosity, or theatrical behavior.

## Explicit playful cues

Examples include: "I'm bored", "make me laugh", "tell me a joke", "roast me",
"mess around", "let's banter", "be a little sarcastic", and similar direct requests.

The cue expires after the current response.

## Validation

- `bot.py` compile: passed
- Existing v17 RPG systems and removals unchanged
- No new RPG gameplay systems introduced
