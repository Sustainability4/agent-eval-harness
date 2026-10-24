# LLM judge runs through a chat UI

This folder holds everything needed to run the LLM-as-judge by hand in a chat
interface (claude.ai or any other), save the replies, and score them with the
same statistics `agenteval report` uses for API runs.

The judge gets exactly what `judge.py` would send it: the rubric, the optional
reference, and the rendered trajectory. It is **not** told which tools exist or
given any clarification beyond the rubric. That is deliberate, so do not add
explanations when you paste.

## Layout

```
data/LLM/
  README.md            this file
  run_log.csv          one row per run: model, date, settings, notes
  prompts/
    manifest.json      which trajectory ids are in each batch
    ref/batch_01..05   reference-aided: judge sees the gold answer, required sources, minimal call count
    noref/batch_01..05 reference-free: judge sees only the question and the trajectory
    corpus/batch_01..05 corpus-aided: no gold answer; judge checks against an uploaded copy of
                       data/corpus.json, the same raw filings the human scorer used
  responses/
    <model>_<ref|noref>/
      batch_01.txt ... batch_05.txt   the model's replies, pasted verbatim
      (<model>_corpus for corpus runs)
```

Each batch has 10 trajectories in the same shuffled order as the human scoring
sheet, so batch order says nothing about the failure mode. Regenerate the
prompts with `python -m agenteval.cli chat-prompts` (use `--batch-size 5` if a
model truncates its replies). That rewrites only `prompts/`.

## Running one model

1. **Name the run** `<model>_<mode>`, for example `haiku-5.5_ref` or
   `sonnet-4.5_noref`. No spaces; end with `_ref`, `_noref` or `_corpus`.
   **Repeats:** add `_r2`, `_r3` and so on for the second and third run of the
   same model and mode, for example `Haiku-5.5_corpus_r2`. A name with no
   suffix counts as repeat 1. Each repeat uses fresh chats and the same prompts.
   Create `responses/<run>/`. For the setup that matches the human scorer, use
   corpus mode: `haiku-5.5_corpus`.
2. **For each of the 5 batches:**
   - Open a **new chat**. One batch per chat, so earlier batches cannot influence
     later ones. Use incognito or temporary chat, or turn memory off, so nothing
     carries over between chats.
   - Pick the model. Leave other settings (extended thinking, styles) the same
     for every batch in a run, and write them in `run_log.csv`.
   - **Corpus mode only:** attach `data/corpus.json` (the file one level up from
     this folder) to the message. Attach it in every new chat, as files do not
     carry over. Keep the filename `corpus.json`, because the prompt refers to it by name.
   - Paste the whole of `prompts/<mode>/batch_NN.txt` as the only message. Add nothing.
   - Copy the whole reply and save it as `responses/<run>/batch_NN.txt`. Do not
     edit it, even if it is malformed or wrapped in a code fence; the importer
     handles fences and records anything it cannot parse.
   - If the reply is cut off, send `continue` and paste the continuation directly
     after the first part in the same file.
3. **Import:** `python -m agenteval.cli chat-import <run>`. This writes
   `results/judge_simulated_chat-<run>.json` and lists any trajectory ids it
   could not read. Re-run a batch only if its reply is missing or unreadable,
   and note that in `run_log.csv`.
4. **Report:** `python -m agenteval.cli report`. Every judge file in `results/`
   gets its own section in `results/report.md`.
5. Add a row to `run_log.csv`.

For a fair comparison between models, run every model in the same modes on all
5 batches. Corpus mode is the one comparable to the human scores, because the
human scorer checked answers against the corpus rather than the gold answers.

## Running a batch through an API instead of a chat

`python -m agenteval.cli batch-judge <run> --backend gemini --model <model> --rpm 5`
sends the same five batch prompts (plus `corpus.json` in corpus mode) to an API
model, one batch per request with no system prompt, as a fresh chat would. Each
reply is saved verbatim as `responses/<run>/batch_NN.txt`, token counts go to
`responses/<run>/api_meta.json`, and the run is imported automatically. Batches
that already have a reply are skipped, so a run stopped by a rate limit resumes
when the command is run again. `--rpm` caps requests per minute for free tiers.

## What the report measures

For every run, two comparisons, each per criterion (C1 to C7) and pooled:

- **Judge vs gold:** accuracy against the answer key implied by the injected failure mode.
- **Judge vs human:** agreement with your hand scores in `data/scoring_sheet_simulated.csv`.

| Statistic | Meaning | How to read it |
| --- | --- | --- |
| exact | Share of items where the two scores are identical | 1.00 is perfect |
| within 1 | Share of items no more than one point apart | Low values mean 2-vs-0 misses, the serious kind |
| kappa_w | Quadratic-weighted Cohen's kappa: agreement after removing chance, with large gaps penalised more | Above 0.8 strong, 0.6 to 0.8 substantial, below 0.4 weak, 0 is chance |
| mean diff | Average of judge minus the other rater | Positive means the judge is more lenient, negative means harsher |

The report also has:

- **By failure mode:** the same statistics grouped by injected mode. This shows
  which kinds of failure the judge misses. Kappa is meaningless for `clean`,
  where gold is all 2s, so use `exact` there.
- **Mean total score** (0 to 14) per rater: overall leniency.
- **Largest disagreements:** every trajectory and criterion where judge and gold
  differ by 2. These are the cases to read, alongside the rationale in the results file.

## Things to compare across runs

- **corpus vs human:** the like-for-like comparison. Both raters had the same
  information, so differences come from judgment, not access.
- **ref vs corpus vs noref** for the same model: how much the judge depends on
  being handed the answer, on having the raw data, or on neither. Second-line
  validators often have the data but not an answer key.
- **Model vs model** on the same mode, especially C5 (groundedness) and C6
  (error handling), which matter most for risk.
- **Judge vs human against judge vs gold:** if the judge agrees with you more
  than with gold, the gold labels or the rubric wording may be the problem, not
  the judge. See the human-vs-gold section for where you and gold already differ.

## Caveats to record in any write-up

- A chat UI is not the API: temperature and system prompt are not controlled,
  and the product may add its own instructions.
- Ten trajectories per message is not the one-per-call setup in `judge.py`. The
  judge can compare trajectories within a batch.
- One run per model. Re-running a batch can give different scores; if you have
  time, repeat one batch to see how stable a model is.
