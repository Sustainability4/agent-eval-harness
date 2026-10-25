# Known conflicts between the gold scores and the rubric

The ground-truth scores for the simulated set are not assigned one trajectory
at a time. Each injected failure mode carries one fixed gold vector
(`FAILURE_MODES` in `src/agenteval/rubric.py`), and every trajectory with that
mode inherits it. In four places that vector contradicts the rubric's own
anchors (`RUBRIC.md`).

**The gold vectors have been left unchanged.** Changing the answer key after
seeing the judges' scores would make the judge-vs-gold results partly circular.
This file records the conflicts so the results can be read with them in mind.
All judge-vs-gold figures in `results/report.md` use the original key.

## How they were found

Six raters scored the 50 simulated trajectories: one human and five LLM
judges. Four are Claude models (Haiku 5.5, Sonnet 5.5, Opus 5.5 and Fable 5.1),
run in claude.ai chat with the corpus prompts in `data/LLM/prompts/corpus/`.
The fifth, Gemini 3 Flash, comes from a different model family; it received
the same prompts and `corpus.json` through the Gemini API (`batch-judge`).
Each judge was run three times, in fresh chats or requests. The raters did not
see each other's scores, and the judges saw neither the gold scores nor the
human's. In each cell below, the human and most of the judges departed from
gold in the direction the rubric's wording indicates. The rubric text, not the
agreement, is the reason each cell is listed: agreement only flagged where to
look.

Counts below are cells: 6 trajectories × 3 runs = 18 per judge (15 for
conflict 3, which covers 5 trajectories).

## The four conflicts

### 1. `wrong_tool`, C6 Error handling: gold 1, rubric indicates 0

- **Anchors:** 1 = "Error noticed but recovery was partial or clumsy."
  0 = "Error ignored and the agent proceeded as if the call had succeeded."
- **Example, S05:** `calculate` is called on the string `"What was Meridian
  Logistics figure"` and returns `calc_error`. The agent's next and only action
  is the final answer, `16,497 employees`, an invented number. Nothing in the
  trajectory shows the error was noticed.
- **Raters:** the human gave 0 on 6 of 6; every judge gave 0 on 18 of 18.
- **Cells:** S05, S19, S21, S29, S38, S41.

### 2. `wrong_tool`, C7 Efficiency: gold 1, rubric indicates 2

- **Anchors:** 2 = "At or near the minimal step count for the task."
  1 = "One or two unnecessary steps."
- **Example, S05:** one tool call in total. The trajectory is too short, not
  too long. Missing steps are already penalised under C2 (a necessary tool never
  called) and C4. C7 has no anchor for too few steps.
- **Raters:** the human gave 2 on 6 of 6; Haiku, Opus and Fable on 18 of 18,
  Gemini on 17 of 18. Sonnet agreed with gold on all 18, calling the single
  call "wasted".
- **Cells:** S05, S19, S21, S29, S38, S41.

### 3. `tool_error_ignored`, C3 Tool arguments: gold 2, rubric indicates 0 when a calculation follows

- **Anchors:** 2 = "All arguments correct."
  0 = "An argument error that fed a wrong input into the answer."
  The C3 question lists "expression" as an argument.
- **Example, S26:** `get_section` for the LMS FY2024 balance sheet returns a
  transient error. The agent then calls `calculate("279.0 / 1300.0")`. Neither
  number appears in any tool result (the filing has 300.0 and 1,250.0), and the
  answer 0.21x follows from them.
- **Scope:** the conflict exists only for the five trajectories in this mode
  with a calculation (yoy_change, ratio, margin): S13, S18, S26, S30, S50. In
  S32, a comparison question, no invented values are passed to a tool, so
  gold 2 is consistent with the rubric there.
- **Raters:** Haiku, Opus, Fable and Gemini gave 0 on 15 of 15; the human on
  4 of 5 (not S18). Sonnet gave 2 on 13 of 15, treating the `calculate`
  expression as reasoning rather than a tool argument. That reading conflicts
  with the C3 question, which names the expression explicitly.

### 4. `arithmetic_error`, C5 Groundedness: gold 1, rubric indicates 2

- **Anchors:** 2 = "All claims traceable to retrieved text or a calculation over it."
  1 = "A minor embellishment not supported by retrieval but not affecting the core answer."
- **Example, S20:** both cash figures are retrieved correctly; the `calculate`
  expression uses the wrong base, giving +19.0% instead of +23.4%. Every number
  in the answer is a calculation over retrieved text, which is anchor 2. There
  is no embellishment, so anchor 1 does not describe it. The mistake is already
  penalised under C1 (wrong answer) and C3 (wrong expression).
- **Raters:** the human gave 2 on 6 of 6; Sonnet and Gemini on 18 of 18;
  Haiku, Opus and Fable on 12 of 18.
- **Cells:** S20, S23, S45, S47, S48, S49.

## Effect on the results

The four conflicts cover 23 of the 350 scored cells per run (50 trajectories ×
7 criteria). Each rater's agreement with gold, pooled over all runs, with and
without those cells (a sensitivity check, not a corrected key):

| Rater | All cells: exact / kappa_w | Excluding the 23: exact / kappa_w |
| --- | --- | --- |
| Human | 0.80 / 0.80 | 0.86 / 0.85 |
| Haiku 5.5 | 0.86 / 0.88 | 0.92 / 0.94 |
| Sonnet 5.5 | 0.88 / 0.90 | 0.91 / 0.92 |
| Opus 5.5 | 0.84 / 0.88 | 0.90 / 0.93 |
| Fable 5.1 | 0.85 / 0.88 | 0.90 / 0.94 |
| Gemini 3 Flash | 0.87 / 0.89 | 0.93 / 0.95 |

- Every rater's accuracy is understated, Sonnet's least: on conflicts 2 and 3
  Sonnet sided with gold.
- The ranking of judges against gold depends on whether these cells are counted.
  Sonnet leads on all cells; Gemini leads without the 23. Do not read the
  ranking without this caveat, and note that the 95% intervals in the report
  overlap for every judge.
- The by-failure-mode rows most affected are `wrong_tool` (kappa_w against gold
  0.34 to 0.43 for every judge) and `tool_error_ignored`.

## Related findings that are not gold conflicts

**Unanimous, but the rubric is not clear-cut.** For `wrong_tool` C3 (gold 1),
the human gave 0 on 6 of 6 and every judge on 18 of 18. The calculator was
handed a nonsense string. Whether that is "harmless" (1) or "fed a wrong input
into the answer" (0) is arguable, because the answer was invented rather than
computed from the call. It is not listed above, since the rubric does not
clearly contradict gold.

**The rubric is ambiguous, and raters split.** These are wording problems in
the rubric, not errors in the key. Fixing them would mean new rubric text and
new judge runs:

- **C1 "wrong magnitude":** anchor 1 includes "wrong magnitude". On trajectories
  where gold gives C1 = 0, Opus gave 1 on 34 of 90 cells and Fable on 33 of 90;
  Haiku, Sonnet and Gemini on 3 to 6 of 90, and the human on 1 of 30.
- **C5 "material" vs "minor":** for the invented extra facts in
  `unsupported_claim` (for example a share buyback or revenue guidance), the
  human scored 1 (minor) on 6 of 6, Gemini on 17 of 18, Haiku on 14, Opus and
  Fable on 12. Gold and Sonnet (16 of 18) scored 0 (material). The rubric does
  not define "material".
- **C1 with an unsupported extra claim:** gold gives 1 when the core answer is
  right but an invented fact is added. Four judges gave 2 on 18 of 18, Sonnet
  on 11 of 18, and the human on 4 of 6, keeping correctness separate from
  groundedness.
- **C3 scope:** whether a wrong `calculate` expression is an argument error
  (see conflict 3; Sonnet alone said no).
- **C7 with too few steps:** see conflict 2.

Run-to-run changes point the same way: within each judge's three runs, C4 and
C6 scores almost never changed, while C5 changed on 14% to 36% of trajectories
for the four Claude judges.

## Caveats

- One human rater, who had seen the generator code before scoring.
- Claude judges were run by hand in claude.ai chat rather than through the
  API, mainly because of API cost, with temperature and the product's system
  prompt not controlled, and 10 trajectories per message.
- Four of the five judges come from one model family and may share blind spots,
  which is why agreement alone is not treated as grounds for a conflict. The
  one judge from another family, Gemini 3 Flash, departed from gold in the
  rubric's direction on 68 of 69 cells across its three runs.
