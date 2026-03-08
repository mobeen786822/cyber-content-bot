import os
import json
from anthropic import Anthropic


SYSTEM_PROMPT = (
    "You are a cybersecurity content writer helping a graduate security engineer "
    "build their LinkedIn presence. Write in a direct, technical but accessible tone. "
    "No fluff, no hype. Focus on what's genuinely interesting or important."
)


def generate_post(findings, tone="professional"):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "Error: ANTHROPIC_API_KEY not set."

    client = Anthropic(api_key=api_key)

    tone_instruction = {
        "professional": "Use a professional, polished tone suitable for LinkedIn.",
        "conversational": "Use a conversational, approachable tone — like talking to a peer over coffee.",
        "technical": "Use a deeply technical tone with specific details, for a security-savvy audience.",
    }.get(tone, "Use a professional, polished tone suitable for LinkedIn.")

    findings_text = json.dumps(findings, indent=2)

    user_prompt = f"""Here are this week's cybersecurity findings from three sources:

{findings_text}

Based on these findings, identify the 2-3 most interesting or important items across all three sources. Then draft a LinkedIn post of 150-250 words.

{tone_instruction}

Include relevant hashtags at the end. Do not use emojis. Focus on providing genuine insight or awareness, not just listing CVEs."""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text
    except Exception as e:
        print(f"Claude API error: {e}")
        return f"Error generating post: {e}"
