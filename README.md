# agent-eval-harness

Rubric-based evaluation of tool-use agent trajectories, with hand scores, LLM judges, and agreement statistics between them. Built to answer one question a model-risk validator actually has: **can an LLM judge be trusted to score an agent's trajectory the way a careful human would, and where does it fail?**

The task domain is financial research over a small synthetic corpus of company filings (every company and number is invented). The agent has three tools: `search_filings`, `get_section` and `calculate`.

## Results

50 trajectories with planted, known mistakes. One human rater (me) and five LLM judges, each judge run three times. All raters got the rubric, the trajectory and the raw filings (`corpus.json`); none got the answer key. Full tables: [`results/report.md`](results/report.md).

| Rater | Runs | vs answer key, kappa_w [95% CI] | vs human, kappa_w [95% CI] | Run-to-run kappa_w |
| --- | --- | --- | --- | --- |
| Human (hand scored) | 1 | 0.80 [0.75, 0.85] | — | — |
| Claude Sonnet 5.5 | 3 | 0.90 [0.87, 0.93] | 0.79 [0.73, 0.83] | 0.95 |
| Gemini 3 Flash | 3 | 0.89 [0.86, 0.93] | 0.86 [0.80, 0.92] | 0.98 |
| Claude Fable 5.1 | 3 | 0.88 [0.85, 0.92] | 0.85 [0.80, 0.90] | 0.97 |
| Claude Haiku 5.5 | 3 | 0.88 [0.83, 0.92] | 0.85 [0.78, 0.90] | 0.96 |
| Claude Opus 5.5 | 3 | 0.88 [0.84, 0.91] | 0.83 [0.78, 0.88] | 0.93 |

What the data shows:

1. **Every judge matched the answer key more closely than the human did.** The judges' intervals overlap, so this data cannot rank them.
2. **The answer key was wrong in four places.** The human and most judges departed from it in the same direction, and each time the key contradicted the rubric's own wording. Gemini, from a different model family, did so on 68 of 69 of those cells. The key is left unchanged and the conflicts are documented in [`GOLD_CONFLICTS.md`](GOLD_CONFLICTS.md); without those 23 cells, judges reach kappa 0.92 to 0.95.
3. **Judges wobble where the rubric is vague.** Across a judge's three runs, sourcing (C4) and error-handling (C6) scores almost never changed; groundedness (C5) changed on 14% to 36% of trajectories for the Claude judges.
4. **Judges have styles.** Sonnet reads a wrong `calculate` expression as reasoning rather than a tool argument; Opus and Fable give partial correctness credit for wrong numbers; Gemini is the most consistent run to run.

This is a method demonstration, not a benchmark. See [Limitations](#limitations).

## What is in the box

| Piece | Where | What it does |
| --- | --- | --- |
| Corpus | `src/agenteval/corpus.py` | 8 fictional companies × 2 fiscal years, 4 sections each |
| Questions | `src/agenteval/questions.py` | 50 questions in 6 types, each with a gold answer and a minimal gold tool plan |
| Rubric | `src/agenteval/rubric.py` | 7 criteria scored 0/1/2 with written anchors; 8 failure modes with implied gold scores |
| Simulated agent | `src/agenteval/simulated_agent.py` | Executes the gold plan, then injects one known failure mode per trajectory |
| LLM agent | `src/agenteval/llm_agent.py` | ReAct-style agent driven by a real model; failures occur naturally |
| Judge | `src/agenteval/judge.py` | LLM-as-judge prompt in three modes: gold answer (`ref`), raw filings (`corpus`), nothing (`noref`) |
| Chat and batch judging | `src/agenteval/chat_judge.py` | Batched prompts for chat UIs, import of pasted replies, and the same prompts sent through an API |
| Hand scoring | `src/agenteval/interactive.py` | Terminal scorer that shows each trajectory with the rubric anchors |
| Agreement | `src/agenteval/agreement.py` | Exact and within-one agreement, quadratic-weighted kappa, bootstrap intervals, run-to-run stability |
| Report | `src/agenteval/report.py` | Groups repeat runs per judge and writes `results/report.md` |
| Backends | `src/agenteval/backends.py` | Anthropic, Gemini, OpenAI and a mock backend; rate limiting for free tiers |

## The rubric

| ID | Criterion | 2 | 1 | 0 |
| --- | --- | --- | --- | --- |
| C1 | Final answer correctness | Correct value, unit and entity | Partially correct | Wrong or missing |
| C2 | Tool selection | Every call is the right tool | One unnecessary or mis-chosen call | Wrong tool for a necessary step, or a necessary tool never called |
| C3 | Tool arguments | All arguments correct | One error, later corrected or harmless | An argument error fed a wrong input into the answer |
| C4 | Context freshness and sourcing | Required sources retrieved and used | Stale or extra source also influenced the answer | Rests on wrong year, company or section |
| C5 | Groundedness | Every claim traceable to a tool result | Minor unsupported embellishment | A material unsupported number or fact |
| C6 | Error handling | No errors, or every error handled | Error noticed, recovery partial | Error ignored |
| C7 | Efficiency | Near-minimal steps | One or two unnecessary steps | Repeated calls, loops, or >2× necessary steps |

Full anchors: [`RUBRIC.md`](RUBRIC.md) or `python -m agenteval.cli rubric`.

Failure modes in the simulated set: `clean` (8 trajectories) and six each of `wrong_tool`, `stale_context`, `unsupported_claim`, `tool_error_ignored`, `loop`, `premature_termination` and `arithmetic_error`. Each mode maps to a fixed gold score vector, which is what lets a judge's *accuracy* be measured, not just its agreement with a human.

## Quick start

```bash
pip install -e ".[dev]"            # core has no dependencies; add [anthropic], [gemini] or [openai] for API backends
pytest                             # 15 tests
python -m agenteval.cli report     # rebuild results/report.md from the saved scores
```

Everything also runs with `--backend mock` (no key), so the plumbing can be tested; mock scores are hash noise and the output says so.

## How the results were produced

1. **Generate** the corpus, questions, 50 simulated trajectories, readable renders and a blank, shuffled scoring sheet: `python -m agenteval.cli generate`. This overwrites `data/scoring_sheet_simulated.csv`.
2. **Hand-score** in the terminal, with the rubric anchors on screen: `python -m agenteval.cli score`. It saves after every trajectory and resumes where you stopped. Do not open `data/trajectories_simulated.json` while scoring: it holds the answer key.
3. **Write the judge prompts** (10 trajectories per batch, in the sheet's order): `python -m agenteval.cli chat-prompts`.
4. **Judge in a chat UI.** For each batch, open a fresh chat, paste the contents of `data/corpus.json` followed by `data/LLM/prompts/corpus/batch_NN.txt` as one message, and save the reply verbatim as `data/LLM/responses/<Model>_corpus[_r2|_r3]/batch_NN.txt`. Then `python -m agenteval.cli chat-import <Model>_corpus`. Details: [`data/LLM/README.md`](data/LLM/README.md).
5. **Or judge through an API** with the same prompts: `python -m agenteval.cli batch-judge Gemini-3-Flash_corpus --backend gemini --model gemini-3-flash-preview --rpm 5`. Keys come from the environment or a `.env` file (`ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`).
6. **One trajectory per call** instead: `python -m agenteval.cli judge --backend anthropic --mode corpus --repeats 3`. It resumes after interruptions and prints token use and cost.
7. **Report:** `python -m agenteval.cli report`.

Run logs: [`data/LLM/run_log.csv`](data/LLM/run_log.csv).

## Why this design

* **Known ground truth.** Injected failures give an answer key for the judge's accuracy. Naturally occurring failures (the LLM-agent set) show whether the result holds when failures are messier.
* **Raw data, not the answer.** A second-line validator rarely has an answer key but usually has the underlying data. The `corpus` mode gives judges the filings, the same information the human had.
* **Per-criterion statistics.** "The judge agrees 89% of the time" hides that one judge's C3 agreement is 0.64 while every judge's C4 is 1.00.
* **Repeats.** Three runs per judge separate a judge's style from run-to-run noise, and show where the rubric is unclear.

## Limitations

* One human rater, who had seen the generator code before scoring.
* 50 short synthetic trajectories; the planted mistakes are fairly easy to spot.
* The LLM-agent set (natural failures) has not been scored yet.
* Some parts of the rubric were never exercised by the data; see [Known gaps and next steps](#known-gaps-and-next-steps).
* Claude judges were run by hand in claude.ai chat rather than through the API, mainly because of API cost: temperature and the product's system prompt were not controlled, and each message held 10 trajectories.
* Four judges from Anthropic and one from Google; OpenAI models could not be run on the free tier.
* The answer key has four known errors, documented in [`GOLD_CONFLICTS.md`](GOLD_CONFLICTS.md) and left unchanged.

## Known gaps and next steps

The current study's data stays as it is, so its results remain comparable. These changes are for the next version.

| Gap | Why it matters | Next step |
| --- | --- | --- |
| Section choice not tested | No planted mistake reads the wrong section, so that part of C3 and C4 was never exercised | Add a `wrong_section` failure mode to the simulated agent |
| Judge corpus has no sections | `data/corpus.json` holds raw fields; a judge must infer which section holds which figure | Give judges a corpus laid out by section, exactly as `get_section` returns it, as a new file |
| No ties or close comparisons | The eight comparison questions differ by 30% to 88%, no values are equal, and the code always names the second company on a tie | Handle ties explicitly (gold answer "Both reported …"), and add one tie and one near-tie question |
| Real-agent failures not scored | Planted failures are cleaner than natural ones | Generate the LLM-agent set with `llm-agent`, hand-score it, and judge it |
| Rubric wording | "Material", "wrong magnitude" and the scope of C3 are read differently by raters ([`GOLD_CONFLICTS.md`](GOLD_CONFLICTS.md)) | Write a clarified rubric v2 and test whether agreement and run-to-run stability improve |
| One human rater | No human-to-human agreement baseline | Add a blind second rater, or re-score after a gap to measure self-consistency |

## Licence

MIT.
