| ID | Criterion | 2 | 1 | 0 |
| --- | --- | --- | --- | --- |
| C1 | Final answer correctness | Correct value, unit and entity; within tolerance for numeric answers. | Partially correct: right direction or entity but wrong magnitude, missing unit, or incomplete comparison. | Wrong, missing, or answers a different question. |
| C2 | Tool selection | Every tool call is the appropriate tool for what the step needed. | One unnecessary or mis-chosen tool call that did not derail the task. | Wrong tool for a necessary step, or a necessary tool never called. |
| C3 | Tool arguments | All arguments correct. | One argument error that was later corrected, or a harmless one. | An argument error that fed a wrong input into the answer. |
| C4 | Context freshness and sourcing | All required sources retrieved and used; no stale or wrong-year context. | Required source retrieved but a stale or extra source also influenced the answer. | Answer rests on the wrong year, wrong company or wrong section. |
| C5 | Groundedness | All claims traceable to retrieved text or a calculation over it. | A minor embellishment not supported by retrieval but not affecting the core answer. | A material number or fact appears that no tool result supports. |
| C6 | Error handling | No errors occurred, or every error was detected and handled (retry, alternative, or honest abstention). | Error noticed but recovery was partial or clumsy. | Error ignored and the agent proceeded as if the call had succeeded. |
| C7 | Efficiency | At or near the minimal step count for the task. | One or two unnecessary steps. | Repeated identical calls, loops, or more than double the necessary steps. |
