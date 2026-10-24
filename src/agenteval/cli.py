"""Command-line entry point.

  agenteval generate                      build corpus, questions, simulated trajectories, scoring sheet
  agenteval llm-agent --backend gemini    run a real LLM agent on the questions (optional --limit N)
  agenteval judge --backend anthropic     score trajectories with an LLM judge (--mode ref|noref|corpus, --repeats N, --effort)
  agenteval chat-prompts                  write batched judge prompts to data/LLM/prompts/ for pasting into a chat UI
  agenteval chat-import <run>             convert saved chat replies in data/LLM/responses/<run>/ into a judge results file
  agenteval batch-judge <run> --backend gemini --model M   send the same batch prompts to an API model, then import
  agenteval score                         hand-score a sheet in the terminal (--set simulated|llm, --redo, --start TID)
  agenteval report                        compute agreement tables from human sheet + judge files
  agenteval rubric                        print the rubric as markdown
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

from . import __version__
from .backends import Throttled, anthropic_cost, make_backend
from .chat_judge import import_chat_run, parse_run_name, run_batches_via_api, write_chat_prompts
from .corpus import save_corpus
from .interactive import interactive_score
from .judge import MODES, judge_all
from .llm_agent import build_llm_trajectories
from .questions import build_questions, save_questions
from .report import build_report
from .rubric import rubric_markdown
from .scoring_sheet import export_sheet, import_sheet, write_renders
from .simulated_agent import build_simulated_trajectories
from .trajectory import load_trajectories, save_trajectories

ROOT = pathlib.Path.cwd()
DATA = ROOT / "data"
RESULTS = ROOT / "results"
LLM_DIR = DATA / "LLM"


def cmd_generate(args):
    save_corpus(DATA / "corpus.json")
    save_questions(DATA / "questions.json")
    trajs = build_simulated_trajectories(seed=args.seed)
    save_trajectories(trajs, DATA / "trajectories_simulated.json")
    write_renders(trajs, DATA / "render" / "simulated")
    export_sheet(trajs, DATA / "scoring_sheet_simulated.csv")
    counts = {}
    for t in trajs:
        counts[t.injected_failure] = counts.get(t.injected_failure, 0) + 1
    print(f"wrote {len(trajs)} simulated trajectories; failure-mode counts: {json.dumps(counts, sort_keys=True)}")
    print(f"hand-score them in {DATA / 'scoring_sheet_simulated.csv'} (rendered text in {DATA / 'render' / 'simulated'})")


def cmd_llm_agent(args):
    backend = make_backend(args.backend, args.model)
    trajs = build_llm_trajectories(backend, limit=args.limit)
    save_trajectories(trajs, DATA / "trajectories_llm.json")
    write_renders(trajs, DATA / "render" / "llm")
    export_sheet(trajs, DATA / "scoring_sheet_llm.csv")
    print(f"wrote {len(trajs)} LLM-agent trajectories from {backend.name}")


def load_dotenv(path: pathlib.Path) -> None:
    """Sets KEY=VALUE lines from a .env file as environment variables, without overriding ones already set."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        key, sep, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if sep and key and not key.startswith("#"):
            os.environ.setdefault(key, value)


def _cost_line(rows: list, n_total: int) -> str:
    calls = [r.get("meta") or {} for r in rows]
    tin = sum(m.get("input_tokens", 0) + m.get("cache_creation_input_tokens", 0) + m.get("cache_read_input_tokens", 0) for m in calls)
    tout = sum(m.get("output_tokens", 0) for m in calls)
    costs = [anthropic_cost(m) for m in calls if m]
    line = f"tokens in {tin:,}, out {tout:,}"
    if costs and None not in costs:
        spent = sum(costs)
        line += f"; cost ${spent:.2f} at list prices"
        if len(rows) < n_total:
            line += f", about ${spent / len(rows) * n_total:.2f} for all {n_total}"
    return line


def cmd_judge(args):
    mode = "noref" if args.no_reference else args.mode
    backend = make_backend(args.backend, args.model, effort=args.effort)
    if args.rpm:
        backend = Throttled(backend, args.rpm)
    path = DATA / ("trajectories_simulated.json" if args.set == "simulated" else "trajectories_llm.json")
    trajs = load_trajectories(path)
    n_all = len(trajs)
    if args.limit:
        trajs = trajs[: args.limit]
    qs = {q.qid: q for q in build_questions()}
    corpus_json = (DATA / "corpus.json").read_text(encoding="utf-8") if mode == "corpus" else None  # the file uploaded in chat runs
    RESULTS.mkdir(exist_ok=True)
    name = backend.name.replace(":", "-").replace("/", "-")
    for k in range(1, args.repeats + 1):
        out = RESULTS / f"judge_{args.set}_{name}_{mode}_r{k}.json"
        rows = json.loads(out.read_text()) if out.exists() else []
        done = {r["tid"] for r in rows}
        todo = [t for t in trajs if t.tid not in done]
        print(f"repeat {k}/{args.repeats}: {out.name} ({len(done)} already judged, {len(todo)} to go)")

        def save(r, rows=rows, out=out):
            rows.append(r.to_dict())
            out.write_text(json.dumps(rows, indent=2))

        try:
            judge_all(backend, todo, qs, mode=mode, corpus_json=corpus_json, on_result=save,
                      progress=lambda i, n: print(f"  judged {i}/{n}", end="\r", file=sys.stderr))
        except Exception as e:  # noqa: BLE001 - API failures after the SDK's retries; progress is already saved
            print(f"\nstopped: {type(e).__name__}: {e}\nrerun the same command to resume from where it stopped")
            return
        bad = [r["tid"] for r in rows if not r["parse_ok"]]
        refused = [r["tid"] for r in rows if (r.get("meta") or {}).get("stop_reason") == "refusal"]
        print(f"\n  {len(rows)} judged, {len(bad)} unparsed{': ' + ', '.join(bad) if bad else ''}"
              f"{f', {len(refused)} refusals' if refused else ''}; {_cost_line(rows, n_all)}")
    if backend.name == "mock":
        print("NOTE: mock backend scores are hash noise, for pipeline testing only.")


def cmd_chat_prompts(args):
    trajs = load_trajectories(DATA / "trajectories_simulated.json")
    manifest = write_chat_prompts(trajs, {q.qid: q for q in build_questions()}, LLM_DIR, batch_size=args.batch_size)
    (LLM_DIR / "responses").mkdir(parents=True, exist_ok=True)
    print(f"wrote {len(manifest['ref'])} batches x 3 modes to {LLM_DIR / 'prompts'} "
          "(ref = gold answer, noref = nothing, corpus = upload data/corpus.json with each batch)")


RUN_NAME_HELP = "<model>_<ref|noref|corpus>, plus _r2, _r3 ... for repeats, e.g. Haiku-5.5_corpus_r2"


def cmd_chat_import(args):
    run_dir = LLM_DIR / "responses" / args.run
    parsed = parse_run_name(args.run)
    if parsed is None or not run_dir.is_dir():
        print(f"expected a folder {LLM_DIR / 'responses'} / {RUN_NAME_HELP}, with batch_NN.txt replies")
        return
    model, mode, _ = parsed
    tids = [t.tid for t in load_trajectories(DATA / "trajectories_simulated.json")]
    results = import_chat_run(run_dir, tids, f"chat:{model}", mode == "ref")
    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / f"judge_simulated_chat-{args.run}.json"
    out.write_text(json.dumps([r.to_dict() for r in results], indent=2))
    bad = [r.tid for r in results if not r.parse_ok]
    print(f"wrote {out} ({len(results) - len(bad)} parsed, {len(bad)} missing or invalid{': ' + ', '.join(bad) if bad else ''})")


def cmd_batch_judge(args):
    parsed = parse_run_name(args.run)
    if parsed is None:
        print(f"run name must be {RUN_NAME_HELP}")
        return
    _, mode, _ = parsed
    backend = make_backend(args.backend, args.model)
    if args.rpm:
        backend = Throttled(backend, args.rpm)
    corpus_json = (DATA / "corpus.json").read_text(encoding="utf-8") if mode == "corpus" else None
    out_dir = LLM_DIR / "responses" / args.run
    print(f"{backend.name}: sending {LLM_DIR / 'prompts' / mode} batches to {out_dir}")
    try:
        sent = run_batches_via_api(backend, LLM_DIR / "prompts" / mode, out_dir, corpus_json,
                                   progress=lambda i, n: print(f"  batch {i}/{n} saved", file=sys.stderr))
    except Exception as e:  # noqa: BLE001 - API failures after retries; finished batches are already saved
        print(f"stopped: {type(e).__name__}: {e}\nrerun the same command to resume from where it stopped")
        return
    print(f"sent {len(sent)} batches")
    cmd_chat_import(args)


def cmd_score(args):
    sheet = DATA / f"scoring_sheet_{args.set}.csv"
    if not sheet.exists():
        print(f"no sheet at {sheet}; run `agenteval generate` (or `llm-agent`) first")
        return
    interactive_score(sheet, DATA / "render" / args.set, redo=args.redo, start=args.start, clear=not args.no_clear)


def cmd_report(args):
    RESULTS.mkdir(exist_ok=True)
    sim_path = DATA / "trajectories_simulated.json"
    sim = {t.tid: t for t in load_trajectories(sim_path)} if sim_path.exists() else {}
    gold = {t.tid: t.gold_scores for t in sim.values()}
    modes = {t.tid: t.injected_failure for t in sim.values()}
    human_sim = import_sheet(DATA / "scoring_sheet_simulated.csv") if (DATA / "scoring_sheet_simulated.csv").exists() else {}
    human_llm = import_sheet(DATA / "scoring_sheet_llm.csv") if (DATA / "scoring_sheet_llm.csv").exists() else {}
    text = build_report(RESULTS, gold, modes, human_sim, human_llm, __version__, n_boot=args.boot)
    if text is None:
        print("nothing to report: no human sheet and no judge files found")
        return
    (RESULTS / "report.md").write_text(text, encoding="utf-8")
    print(text)


def cmd_rubric(args):
    print(rubric_markdown())


def main(argv=None):
    p = argparse.ArgumentParser(prog="agenteval", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate"); g.add_argument("--seed", type=int, default=11); g.set_defaults(fn=cmd_generate)

    a = sub.add_parser("llm-agent"); a.add_argument("--backend", default="anthropic"); a.add_argument("--model")
    a.add_argument("--limit", type=int); a.set_defaults(fn=cmd_llm_agent)

    j = sub.add_parser("judge"); j.add_argument("--backend", default="anthropic"); j.add_argument("--model")
    j.add_argument("--set", choices=["simulated", "llm"], default="simulated")
    j.add_argument("--mode", choices=MODES, default="ref", help="what the judge is given besides the trajectory")
    j.add_argument("--no-reference", action="store_true", help="same as --mode noref")
    j.add_argument("--repeats", type=int, default=1, help="independent runs, saved as _r1, _r2, ...")
    j.add_argument("--effort", default="medium", help="Claude thinking effort; ignored by models without it")
    j.add_argument("--rpm", type=float, help="max calls per minute, for rate-limited free tiers")
    j.add_argument("--limit", type=int); j.set_defaults(fn=cmd_judge)

    cp = sub.add_parser("chat-prompts"); cp.add_argument("--batch-size", type=int, default=10); cp.set_defaults(fn=cmd_chat_prompts)
    ci = sub.add_parser("chat-import"); ci.add_argument("run", help=RUN_NAME_HELP); ci.set_defaults(fn=cmd_chat_import)
    bj = sub.add_parser("batch-judge"); bj.add_argument("run", help=RUN_NAME_HELP)
    bj.add_argument("--backend", default="gemini"); bj.add_argument("--model")
    bj.add_argument("--rpm", type=float, help="max calls per minute, for rate-limited free tiers")
    bj.set_defaults(fn=cmd_batch_judge)

    s = sub.add_parser("score"); s.add_argument("--set", choices=["simulated", "llm"], default="simulated")
    s.add_argument("--redo", action="store_true"); s.add_argument("--start"); s.add_argument("--no-clear", action="store_true")
    s.set_defaults(fn=cmd_score)

    r = sub.add_parser("report"); r.add_argument("--boot", type=int, default=2000, help="bootstrap resamples")
    r.set_defaults(fn=cmd_report)
    ru = sub.add_parser("rubric"); ru.set_defaults(fn=cmd_rubric)

    args = p.parse_args(argv)
    load_dotenv(ROOT / ".env")
    args.fn(args)


if __name__ == "__main__":
    main()
