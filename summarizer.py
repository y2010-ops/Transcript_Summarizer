"""
Interview Transcript Summarizer
Processes interview transcripts and produces structured summaries using Groq's Llama 3.3 70B.
"""

import os
import sys
import json
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You are an expert interview analyst at a tech recruiting firm. Your job is to read interview transcripts and produce structured, honest assessments of candidates.

Analyze the provided interview transcript and return a JSON object with exactly three keys:

1. "topics_covered": An array of 3-7 topic strings. Each topic should be a specific, descriptive phrase (e.g., "distributed systems design experience" not just "technical skills"). Order them from most to least discussed. Only include topics that were meaningfully discussed, not just briefly mentioned.

2. "profile": An object with:
   - "role": The most fitting role title (e.g., "Backend Engineer", "Data Scientist", "Product Manager", "Program Manager", "Operations Manager")
   - "level": One of "intern", "junior", "mid-level", "senior", "lead" based on demonstrated experience, depth of answers, and years of relevant work
   - "justification": 2-3 sentences explaining WHY this role and level fit, citing specific moments or statements from the transcript

3. "candidate_summary": A single STRING (not an object) containing one paragraph of 3-6 sentences covering:
   - Their professional background in one sentence
   - Key strengths with specific examples from the interview (cite actual moments, not generic praise)
   - Any concerns or red flags including: inability to answer questions, vague responses, interviewer feedback, or gaps in expected knowledge
   - A clear hiring signal: one of "strong hire", "lean hire", "lean no-hire", or "strong no-hire" with a one-sentence reason

Rules:
- Base everything strictly on what is in the transcript. Do not infer skills or experience not discussed.
- If the transcript is short, vague, or lacks detail in some areas, say so explicitly.
- Be specific: reference actual topics, answers, or moments from the interview.
- If the candidate struggles to answer, avoids a question, or the interviewer cuts them off, treat these as significant signals and mention them.
- If the interviewer gives explicit feedback about the candidate, incorporate it into your assessment.
- The hiring signal is MANDATORY. Do not hedge with "could be" or "shows promise" — commit to a signal and justify it.
- All values must be valid JSON types: "topics_covered" is an array of strings, "profile" is an object with string values, "candidate_summary" is a plain string.
- Return ONLY valid JSON. No markdown, no backticks, no extra text."""

USER_PROMPT_TEMPLATE = """Here is the interview transcript to analyze:

---TRANSCRIPT START---
{transcript}
---TRANSCRIPT END---

Produce the structured JSON summary now."""

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


def load_transcript(filepath: str) -> str:
    path = Path(filepath)
    if not path.exists():
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    text = path.read_text(encoding="utf-8").strip()
    if len(text) < 100:
        print(f"Warning: Transcript is very short ({len(text)} chars). Output quality may be limited.")
    return text


def summarize_transcript(transcript: str) -> dict:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY not found.")
        print("Create a .env file with: GROQ_API_KEY=your-key-here")
        sys.exit(1)

    response = requests.post(
        GROQ_API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT_TEMPLATE.format(transcript=transcript)},
            ],
            "temperature": 0.3,
            "max_tokens": 2048,
            "response_format": {"type": "json_object"},
        },
    )

    if response.status_code != 200:
        print(f"API Error ({response.status_code}): {response.text}")
        sys.exit(1)

    data = response.json()

    try:
        return json.loads(data["choices"][0]["message"]["content"])
    except (KeyError, json.JSONDecodeError) as e:
        print(f"Failed to parse response: {e}")
        print(f"Raw response: {json.dumps(data, indent=2)}")
        sys.exit(1)


def format_output(summary: dict) -> str:
    lines = []
    lines.append("=" * 60)
    lines.append("INTERVIEW TRANSCRIPT SUMMARY")
    lines.append("=" * 60)

    lines.append("\nTOPICS COVERED")
    lines.append("-" * 40)
    for i, topic in enumerate(summary.get("topics_covered", []), 1):
        lines.append(f"  {i}. {topic}")

    lines.append("\nCANDIDATE PROFILE")
    lines.append("-" * 40)
    profile = summary.get("profile", {})
    lines.append(f"  Role:  {profile.get('role', 'N/A')}")
    lines.append(f"  Level: {profile.get('level', 'N/A')}")
    lines.append(f"\n  Justification: {profile.get('justification', 'N/A')}")

    lines.append("\nCANDIDATE SUMMARY")
    lines.append("-" * 40)
    lines.append(f"  {summary.get('candidate_summary', 'N/A')}")

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python summarizer.py <transcript_file> [--json]")
        print("\nOptions:")
        print("  --json    Output raw JSON instead of formatted text")
        print("\nExample:")
        print("  python summarizer.py sample_transcript_assignment_1.txt")
        sys.exit(1)

    filepath = sys.argv[1]
    output_json = "--json" in sys.argv

    print(f"Loading transcript: {filepath}")
    transcript = load_transcript(filepath)
    print(f"Transcript loaded ({len(transcript)} characters). Sending to LLM...")

    summary = summarize_transcript(transcript)

    if output_json:
        print(json.dumps(summary, indent=2))
    else:
        print(format_output(summary))

    # Save to file
    out_name = Path(filepath).stem + "_summary"
    out_ext = ".json" if output_json else ".txt"
    out_path = out_name + out_ext

    with open(out_path, "w", encoding="utf-8") as f:
        if output_json:
            json.dump(summary, f, indent=2)
        else:
            f.write(format_output(summary))

    print(f"\nSummary saved to: {out_path}")


if __name__ == "__main__":
    main()