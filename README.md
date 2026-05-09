# Interview Transcript Summarizer

A command-line tool that takes an interview transcript and produces a structured summary with topics covered, candidate profile assessment, and an overall candidate summary with a hiring recommendation.

Built as a take-home assignment for Intervue.io — AI Systems Intern role.

## Setup

### 1. Install dependencies

```bash
pip install requests python-dotenv
```

### 2. Get a Groq API key

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up and create an API key
3. Create a `.env` file in the project root:

```
GROQ_API_KEY=your-key-here
```

> **Note:** The `.env` file is gitignored. Never commit your API key.

### 3. Run

```bash
python summarizer.py sample_transcript_assignment_1.txt
python summarizer.py sample_transcript_assignment_2.txt
```

For raw JSON output:

```bash
python summarizer.py sample_transcript_assignment_1.txt --json
```

The summary is printed to the console and also saved to `<transcript_name>_summary.txt` (or `.json` with the `--json` flag).

## LLM Provider & Model

- **Provider:** Groq (free tier, no credit card required)
- **Model:** `llama-3.3-70b-versatile`
- **Temperature:** 0.3 (low for consistent, factual output)
- **JSON mode:** Enabled via `response_format={"type": "json_object"}`

Chose Groq + Llama 3.3 70B for strong instruction-following at zero cost, fast inference (~2s per call), and native JSON mode support which eliminates parsing failures.

## Project Structure

```
├── summarizer.py              # Main script — single API call with structured prompt
├── prompt_iterations.md       # Log of prompt evolution with real outputs
├── README.md                  # This file
├── .env                       # API key (gitignored)
├── .gitignore                 # Excludes .env and generated output files
└── sample_transcript_*.txt    # Test transcripts (from assignment)
```

## Reflection

**What surprised me:** The biggest improvement didn't come from adding more detail to the prompt — it came from being explicit about behavioral rules. Early versions produced LinkedIn-style endorsements even for candidates who clearly struggled during the interview. The model has a strong default "be nice" bias. Adding rules like "do not hedge" and "if the interviewer gives feedback, incorporate it" transformed the output from generic praise into actionable assessments. A single rule — making the hiring signal mandatory — forced the model to actually synthesize its observations into a decision rather than sitting on the fence.

I also didn't expect JSON formatting to be a problem. The model returned `candidate_summary` as `{ "paragraph" }` (a set-like invalid structure) on the first run. Explicitly stating "a single STRING (not an object)" fixed it immediately. Small type hints in prompts prevent entire classes of parsing errors.

**What I'd improve with another day:**

- **Two-step pipeline:** A first pass to extract raw facts, quotes, and key moments from the transcript, followed by a second pass to synthesize the assessment. This would reduce the risk of the model skipping important moments in longer transcripts and would make the grounding more verifiable.
- **Confidence scoring:** Add a confidence field per topic and per assessment dimension, so readers know where the model is working from strong evidence vs. thin signal.
- **Transcript preprocessing:** Normalize speaker labels, handle edge cases like timestamps and overlapping speech, and chunk very long transcripts to stay within token limits gracefully.
- **Broader testing:** Test on more diverse transcript types — group interviews, panel interviews, non-tech roles like sales or design — to find where the prompt breaks down.

**Limitations of the final prompt:**

- Very short or vague transcripts produce somewhat generic output — there's a floor on quality when input signal is weak.
- The model occasionally over-indexes on a single strong/weak answer when assessing overall level, rather than weighing the full conversation proportionally.
- Both test transcripts received "lean hire" — the model may still carry a slight positive bias even with honesty constraints.
- Role detection works well for common roles (engineer, PM, program manager) but may struggle with niche or hybrid titles (e.g., "ML Platform Engineer" vs. "MLOps Engineer").
- No handling for non-English transcripts or heavily informal/abbreviated speech patterns.