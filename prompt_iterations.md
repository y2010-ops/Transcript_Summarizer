# Prompt Iterations: Interview Transcript Summarizer

Documenting how I evolved the system prompt across three versions. Each change was driven by a specific failure I hit while testing against both sample transcripts.

---

## Iteration 1: Getting the basics right

I started with a straightforward approach — give the model a persona ("expert interview analyst"), define the three output fields, and add some ground rules about being specific and grounded in the transcript.

**Prompt (relevant section):**
```text
...
3. "candidate_summary": A single paragraph of 3-6 sentences covering:
   - Their professional background (briefly)
   - Key strengths demonstrated in the interview
   - Any concerns or red flags (be honest but fair)
   - Overall impression and hiring signal (lean hire / lean no-hire / strong hire / strong no-hire)

Rules:
- Base everything strictly on what is in the transcript. Do not infer skills or experience not discussed.
- If the transcript is short, vague, or lacks detail in some areas, say so explicitly.
- Be specific: reference actual topics, answers, or moments from the interview.
- If the candidate contradicts themselves or gives notably weak/strong answers, mention it.
- Return ONLY valid JSON. No markdown, no backticks, no extra text.
```

**What happened:**

It actually worked on the first couple of runs — topics were reasonable, role detection was correct for both transcripts. But then I got a `400 json_validate_failed` error. Looking at the `failed_generation` in the error response, the model had wrapped the candidate summary in curly braces like `{"The candidate has..."}` instead of just returning it as a string. Basically it treated "paragraph" as "object."

When it did work, the outputs were... fine but not great. The frontend engineer transcript candidate got called a "strong candidate" even though he literally said "I cannot use this" when asked about Zustand and got cut off by the interviewer during the Redux slice question. The program manager transcript output used a lot of hedge language — "shows promise", "could be a strong fit" — without ever committing to an actual recommendation.

<details>
<summary>Output — Transcript 1 (Frontend Engineer)</summary>

```text
TOPICS COVERED
----------------------------------------
  1. AI-powered coding assistance and integration
  2. Ionic Framework for mobile app development
  3. Capacitor and plugin ecosystem for native functionalities
  4. CSS framework utility classes for responsive design
  5. Angular Framework for scalable application structure
  6. State management in React for large-scale applications

CANDIDATE PROFILE
----------------------------------------
  Role:  Senior Frontend Engineer
  Level: senior

  Justification: The candidate demonstrated extensive experience in software development, particularly with Angular, React, and Ionic Framework. They showed a deep understanding of AI-powered coding assistance, state management, and responsive design principles. Their ability to design scalable application structures and implement complex data flows also suggests a senior-level expertise.

CANDIDATE SUMMARY
----------------------------------------
  The candidate, Prasanna Kumar, has around 9 years of experience in software development with a strong focus on frontend technologies. They demonstrated a good understanding of various frameworks and libraries, including Angular, React, and Ionic. The candidate showed strengths in designing scalable application structures, implementing state management, and using AI-powered coding assistance. However, there were moments where they seemed uncertain or lacked specific knowledge, such as with Zustand. Overall, the candidate presented themselves as a strong candidate for a senior frontend engineer role, but may require some additional learning or experience in certain areas.
```
</details>

<details>
<summary>Output — Transcript 2 (Program Manager)</summary>

```text
TOPICS COVERED
----------------------------------------
  1. program and project management experience
  2. vendor management and stakeholder engagement
  3. operations management and process improvement
  4. fraud detection and prevention
  5. leadership and team management
  6. data analysis and presentation

CANDIDATE PROFILE
----------------------------------------
  Role:  Program Manager
  Level: mid-level

  Justification: The candidate has demonstrated experience in program and project management, vendor management, and stakeholder engagement. They have shown ability to lead teams, manage operations, and analyze data. However, they sometimes use jargon and lack confidence in communication, which is a concern for a mid-level role. Overall, their experience and skills align with a mid-level program manager position.

CANDIDATE SUMMARY
----------------------------------------
  Krishna has a background in mechanical engineering and has worked in operations and program management roles in ed-tech companies. They have demonstrated strengths in process improvement, vendor management, and data analysis. However, they sometimes struggle with communication and confidence, using jargon and lacking assertiveness in their responses. Overall, Krishna shows promise as a program manager, but needs to work on their communication skills to succeed in a leadership role. With some development, they could be a strong fit for a mid-level program management position.
```
</details>

**Two problems to fix:** the JSON crash, and the model being way too nice.

---

## Iteration 2: Fixing the JSON crash

This was a quick one. The crash happened because I described `candidate_summary` as "a single paragraph" and the model interpreted that as a JSON object instead of a string. I just made the type explicit:

```diff
- 3. "candidate_summary": A single paragraph of 3-6 sentences covering:
+ 3. "candidate_summary": A single string (NOT an object or array) containing a paragraph of 3-6 sentences covering:
```

This fixed the 400 errors completely — no more crashes after this change. But the actual content of the summaries was still the same problem: too generic, too positive, no real hiring signal. So I moved on to fixing that.

---

## Iteration 3: Making the model actually honest

This was the big one. I had two specific frustrations with the output:

1. The frontend engineer candidate couldn't write Zustand or Redux slice code during the interview, and the interviewer literally cut him off ("Let's not waste time") — but the summary barely mentioned it and still called him a "strong candidate." That's not useful to anyone reading this summary.

2. The program manager candidate got direct feedback from the interviewer about using too much Hindi jargon and lacking confidence — but the summary treated this as a minor note instead of a key concern.

So I made several changes at once:

```diff
2. "profile": An object with:
-   - "role": The most fitting role title (e.g., "Backend Engineer", "Data Scientist", "Product Manager")
+   - "role": The most fitting role title (e.g., "Backend Engineer", "Data Scientist", "Product Manager", "Program Manager", "Operations Manager")

-3. "candidate_summary": A single string (NOT an object or array) containing a paragraph of 3-6 sentences covering:
-   - Their professional background (briefly)
-   - Key strengths demonstrated in the interview
-   - Any concerns or red flags (be honest but fair)
-   - Overall impression and hiring signal (lean hire / lean no-hire / strong hire / strong no-hire)
+3. "candidate_summary": A single STRING (not an object) containing one paragraph of 3-6 sentences covering:
+   - Their professional background in one sentence
+   - Key strengths with specific examples from the interview (cite actual moments, not generic praise)
+   - Any concerns or red flags including: inability to answer questions, vague responses, interviewer feedback, or gaps in expected knowledge
+   - A clear hiring signal: one of "strong hire", "lean hire", "lean no-hire", or "strong no-hire" with a one-sentence reason

Rules:
...
-- If the candidate contradicts themselves or gives notably weak/strong answers, mention it.
+- If the candidate struggles to answer, avoids a question, or the interviewer cuts them off, treat these as significant signals and mention them.
+- If the interviewer gives explicit feedback about the candidate, incorporate it into your assessment.
+- The hiring signal is MANDATORY. Do not hedge with "could be" or "shows promise" — commit to a signal and justify it.
+- All values must be valid JSON types: "topics_covered" is an array of strings, "profile" is an object with string values, "candidate_summary" is a plain string.
```

The thinking behind each change:

- **Added more role examples** — the first transcript is a frontend engineer, the second is a program manager. Without "Program Manager" in the examples, I worried the model might force-fit non-engineering candidates into engineering roles.
- **"cite actual moments, not generic praise"** — this was the key phrase. In iteration 1, the model would say things like "demonstrated strengths in process improvement" without pointing to anything specific. Now it references the fraud scoring system, the Zustand failure, etc.
- **"the interviewer cuts them off"** — I added this specifically because of the Redux slice moment. The interviewer saying "let's not waste time" is a pretty clear negative signal that the model was ignoring.
- **"as noted by the interviewer"** — for the program manager transcript, the interviewer gave explicit feedback about jargon and confidence. I wanted the model to treat interviewer feedback as authoritative, not optional.
- **Mandatory hiring signal** — "do not hedge with 'could be' or 'shows promise'" was me directly targeting the exact phrases from iteration 1's output. If you're assessing a candidate, you need to commit to a recommendation.

**Results after these changes:**

<details>
<summary>Output — Transcript 1 (Frontend Engineer)</summary>

```text
TOPICS COVERED
----------------------------------------
  1. AI-powered coding assistance
  2. Ionic Framework and mobile app development
  3. State management in Angular and React
  4. CSS framework utility classes
  5. Capacitor and plugin ecosystem

CANDIDATE PROFILE
----------------------------------------
  Role:  Senior Frontend Engineer
  Level: senior

  Justification: The candidate has around nine years of experience in software development, with core technical expertise in Angular, React, and Ionic framework. They demonstrated a good understanding of AI-powered coding assistance, state management, and CSS framework utility classes. Their ability to design scalable application structures and implement state management strategies also suggests a senior level of experience.

CANDIDATE SUMMARY
----------------------------------------
  The candidate has around nine years of experience in software development, with a strong background in frontend technologies. They demonstrated key strengths in designing scalable application structures, implementing state management strategies, and using AI-powered coding assistance. However, they struggled to write code for specific topics like Redux slice and Zustand, which raises some concerns about their ability to implement certain technologies. Overall, I would give a 'lean hire' signal, as the candidate's experience and strengths outweigh their weaknesses, but they may require additional training or support in certain areas.
```
</details>

<details>
<summary>Output — Transcript 2 (Program Manager)</summary>

```text
TOPICS COVERED
----------------------------------------
  1. program and project management experience
  2. vendor management and stakeholder engagement
  3. operations management and process improvement
  4. leadership and communication skills
  5. data analysis and KPI tracking
  6. conflict resolution and prioritization

CANDIDATE PROFILE
----------------------------------------
  Role:  Program Manager
  Level: mid-level

  Justification: The candidate has around 3-4 years of experience in operations and project management, with a background in mechanical engineering. They have demonstrated experience in managing vendors, stakeholders, and teams, and have shown ability to analyze data and track KPIs. However, they sometimes use jargon and lack confidence in their communication, which may be a concern for a leadership role.

CANDIDATE SUMMARY
----------------------------------------
  Krishna has a professional background in operations and project management, with experience in managing vendors, stakeholders, and teams. One of their key strengths is their ability to analyze data and track KPIs, as seen in their explanation of how they built a score to identify potential fraud. However, a concern is their tendency to use jargon and lack confidence in their communication, as noted by the interviewer. Overall, I would give a 'lean hire' signal, as Krishna has shown potential but needs to work on their communication skills to succeed in a leadership role.
```
</details>

Much better. The frontend engineer went from "strong candidate" to "lean hire" with explicit mention of the coding struggles. The program manager summary now cites the fraud scoring system as a specific strength and references the interviewer's feedback directly. Both summaries commit to a hiring signal instead of hedging.

**One thing I'd still improve:** both candidates got "lean hire" — the model might still be slightly biased toward positive outcomes. The frontend engineer arguably deserves a "lean no-hire" given that coding is literally the job and he couldn't do it live. But at least the evidence is surfaced now and a human reader can make their own call, which is probably the right behavior for a summarization tool.
