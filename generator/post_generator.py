import os
import json
import re
from anthropic import Anthropic


SYSTEM_PROMPT = (
    "You are a cybersecurity content writer helping a graduate security engineer "
    "build their LinkedIn presence. Write like a thoughtful human security practitioner, "
    "not a corporate blog or vulnerability database. Be clear, specific, and approachable. "
    "No clickbait, no fearmongering, no hype. Focus on what's genuinely interesting or important."
)


def generate_post(findings, tone="professional"):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "Error: ANTHROPIC_API_KEY not set."

    client = Anthropic(api_key=api_key)

    tone_instruction = {
        "professional": "Use a professional but human tone suitable for LinkedIn. Sound like a real security practitioner sharing a useful observation.",
        "conversational": "Use a conversational, approachable tone — like talking to a peer over coffee.",
        "technical": "Use a technical but readable tone with specific details, for a security-savvy audience.",
    }.get(tone, "Use a professional, polished tone suitable for LinkedIn.")

    findings_text = json.dumps(findings, indent=2)

    user_prompt = f"""Here are this week's cybersecurity findings from three sources:

{findings_text}

Based on these findings, identify the 2-3 most interesting or important items across all three sources, then write the final LinkedIn post.

{tone_instruction}

Strict output rules:
- Return only the final LinkedIn post.
- Do not include analysis, headings like "Top Findings Analysis", explanations, or labels like "LinkedIn Post".
- Start with a strong human hook in the first 1-2 lines that makes a reader want to click "see more".
- The hook should feel natural, specific, and relevant to the findings. Avoid generic hooks like "Cybersecurity is important".
- Write in first person if it helps the post feel more human, e.g. "One thing that stood out to me...".
- Keep the post between 120 and 180 words.
- Use short paragraphs with line breaks so it reads well on LinkedIn.
- Do not use semicolons.
- Do not use dashes as punctuation. CVE identifiers like CVE-2026-12345 are the only exception.
- Include relevant hashtags at the end.
- Do not use emojis.
- Focus on genuine insight or awareness, not just listing CVEs."""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return clean_post_text(message.content[0].text)
    except Exception as e:
        print(f"Claude API error: {e}")
        return f"Error generating post: {e}"


def clean_post_text(text):
    """Remove punctuation habits that make posts sound too AI-written."""
    text = text.replace(";", ",")
    text = text.replace("—", ",")
    text = text.replace("–", ",")
    text = re.sub(r"\s+-\s+", ", ", text)
    return text
