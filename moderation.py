from dataclasses import dataclass
import re


@dataclass
class Decision:
    score: int = 0
    category: str = ""
    reason: str = ""
    target: bool = False
    escalation: bool = False

    @property
    def alert(self):
        return self.score >= 3


class ModerationEngine:
    """
    Contextual triage, deliberately conservative.
    Ordinary profanity is not treated as a punishable violation by itself.
    """

    targeted = [
        r"\b(?:kill|hurt|attack|rape|dox|destroy)\s+(?:you|u|him|her|them)\b",
        r"\b(?:te|tum|aap|usko|isko)\s+(?:maar|marunga|marunga|nuksan)\b",
        r"\b(?:te voy a matar|te mataré|voy a matarte)\b",
        r"\b(?:je vais te tuer|ich werde dich töten)\b",
        r"\b(?:죽여|죽인다|죽일)\b",
        r"\b(?:殺す|死ね)\b",
    ]

    insults = [
        r"\b(?:idiot|moron|loser|stupid|shut up)\b",
        r"\b(?:gadha|bewakoof|chutiya|mc|bc)\b",
        r"\b(?:imbecile|idiota)\b",
        r"\b(?:idiot|connard|putain)\b",
    ]

    threats = [
        r"\b(?:i will|i am going to|i'll)\s+(?:kill|hurt|attack)\b",
        r"\b(?:kill you|hurt you|find you)\b",
        r"\b(?:mar dunga|maar dunga|jaan se maar)\b",
        r"\b(?:te voy a matar)\b",
    ]

    def inspect(self, text: str, history=None):
        normalized = re.sub(r"\s+", " ", text.lower()).strip()
        score = 0
        reasons = []
        target = False

        if any(re.search(pattern, normalized) for pattern in self.targeted):
            score += 4
            target = True
            reasons.append("targeted threat/harassment")

        if any(re.search(pattern, normalized) for pattern in self.threats):
            score += 4
            target = True
            reasons.append("threat")

        insult_count = sum(
            bool(re.search(pattern, normalized))
            for pattern in self.insults
        )
        if insult_count:
            score += min(2, insult_count)
            reasons.append("insult indicator")

        if history:
            recent = [item.lower() for item in history[-5:]]
            hits = sum(
                any(
                    re.search(pattern, item)
                    for pattern in self.insults + self.threats + self.targeted
                )
                for item in recent
            )
            if hits >= 2:
                score += 2
                reasons.append("escalation")

        letters = sum(c.isalpha() for c in text)
        if (
            len(normalized) > 30
            and letters
            and sum(c.isupper() for c in text) / letters > 0.7
        ):
            score += 1
            reasons.append("aggressive formatting")

        escalation = "escalation" in reasons

        return Decision(
            score=score,
            category="harassment" if target else "language",
            reason="; ".join(dict.fromkeys(reasons)),
            target=target,
            escalation=escalation,
        )
