# Horizon RPG v17 — AI Sense & Conversation Cleanup

## Purpose
This patch fixes Horizon's conversational behavior without changing the RPG systems.

## Changes
- Replaced the overly performative AI personality instructions.
- Added intent-first response behavior.
- Added tone switching for casual, joking, serious, frustrated, technical, RPG, and conflict contexts.
- Humor is now optional and restrained.
- Prevents constant sarcasm, roasting, metaphors, dramatic monologues, and AI/server jokes.
- Prevents invented relationships, motives, history, and facts.
- Keeps casual replies short unless detail is useful.
- Prevents server-specific personality text from overriding core conversational behavior.
- Adds explicit behavior for uncertainty and correcting mistakes.
- Keeps privacy and moderation guidance intact.

## RPG scope
No removed v15 systems were reintroduced. No new RPG gameplay systems were added in this pass.
