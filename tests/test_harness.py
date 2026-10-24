import json

from agenteval.agreement import compare, weighted_kappa
from agenteval.backends import MockBackend
from agenteval.corpus import build_corpus
from agenteval.judge import judge_trajectory
from agenteval.llm_agent import run_llm_agent
from agenteval.questions import build_questions
from agenteval.rubric import CRITERION_IDS, FAILURE_MODES
from agenteval.simulated_agent import build_simulated_trajectories
from agenteval.tools import Environment


def test_corpus_shape():
    c = build_corpus()
    assert len(c) == 16
    assert {f.fiscal_year for f in c} == {"FY2024", "FY2025"}


def test_questions_gold_plans_execute_and_match_gold():
    env_filings = build_corpus()
    for q in build_questions():
        env = Environment(env_filings)
        last_calc = None
        for p in q.gold_plan:
            res = env.call(p["tool"], p["args"])
            assert "error" not in res, (q.qid, p, res)
            if p["tool"] == "calculate":
                last_calc = res["result"]
        if q.gold_value is not None and last_calc is not None:
            assert abs(last_calc - q.gold_value) <= max(abs(q.gold_value) * q.tolerance, 0.01), (q.qid, last_calc, q.gold_value)


def test_simulated_set_counts_and_gold_scores():
    trajs = build_simulated_trajectories()
    assert len(trajs) == 50
    counts = {}
    for t in trajs:
        counts[t.injected_failure] = counts.get(t.injected_failure, 0) + 1
        assert set(t.gold_scores) == set(CRITERION_IDS)
        assert t.steps[-1].kind == "final_answer"
        assert t.final_answer
    assert counts["clean"] == 8
    for m in FAILURE_MODES:
        if m != "clean":
            assert counts[m] == 6, counts


def test_failure_modes_have_their_signature():
    trajs = {t.injected_failure: t for t in build_simulated_trajectories()}
    loop = trajs["loop"]
    calls = [json.dumps(s.content, sort_keys=True) for s in loop.steps if s.kind == "tool_call"]
    assert max(calls.count(c) for c in calls) >= 4
    err = trajs["tool_error_ignored"]
    assert any(s.kind == "tool_result" and "error" in s.content for s in err.steps)
    prem = trajs["premature_termination"]
    assert all(s.content["tool"] == "search_filings" for s in prem.steps if s.kind == "tool_call")
    qs = {q.qid: q for q in build_questions()}
    for t in build_simulated_trajectories():
        if t.injected_failure in ("clean", "loop"):
            assert t.final_answer == qs[t.qid].gold_answer
        if t.injected_failure in ("stale_context", "arithmetic_error", "wrong_tool", "premature_termination", "tool_error_ignored"):
            assert t.final_answer != qs[t.qid].gold_answer, (t.tid, t.injected_failure)


def test_mock_llm_agent_follows_gold_plan():
    q = build_questions()[0]
    tr = run_llm_agent(MockBackend(), q)
    assert tr.final_answer == q.gold_answer
    assert tr.n_tool_calls() == len(q.gold_plan)


def test_mock_judge_parses():
    q = build_questions()[0]
    tr = build_simulated_trajectories()[0]
    r = judge_trajectory(MockBackend(), tr, q)
    assert r.parse_ok and set(r.scores) == set(CRITERION_IDS)


def test_kappa_edges():
    assert weighted_kappa([0, 1, 2, 2], [0, 1, 2, 2]) == 1.0
    assert weighted_kappa([0, 0, 2, 2], [2, 2, 0, 0]) < 0
    rep = compare({"a": {c: 2 for c in CRITERION_IDS}}, {"a": {c: 2 for c in CRITERION_IDS}})
    assert rep["pooled"]["exact"] == 1.0


def test_interactive_score_saves_and_resumes(tmp_path):
    from agenteval.interactive import interactive_score
    from agenteval.scoring_sheet import export_sheet, import_sheet, write_renders

    trajs = build_simulated_trajectories()[:2]
    sheet, renders = tmp_path / "sheet.csv", tmp_path / "render"
    export_sheet(trajs, sheet)
    write_renders(trajs, renders)
    # Row 1: C1=1, back, C1=2, C2..C7, a note. Row 2: two scores then quit (discarded).
    keys = iter(["1", "b", "2", "2", "1", "x", "2", "0", "2", "2", "looked fine", "2", "2", "q"])
    interactive_score(sheet, renders, clear=False, ask=lambda _: next(keys))
    scored = import_sheet(sheet)
    assert len(scored) == 1
    assert list(scored.values())[0] == {"C1": 2, "C2": 2, "C3": 1, "C4": 2, "C5": 0, "C6": 2, "C7": 2}
    keys = iter(["2"] * 7 + [""])
    interactive_score(sheet, renders, clear=False, ask=lambda _: next(keys))
    assert len(import_sheet(sheet)) == 2


def test_chat_prompts_and_import_round_trip(tmp_path):
    from agenteval.chat_judge import import_chat_run, write_chat_prompts

    trajs = build_simulated_trajectories()
    qs = {q.qid: q for q in build_questions()}
    manifest = write_chat_prompts(trajs, qs, tmp_path, batch_size=10)
    assert len(manifest["ref"]) == 5 and sorted(sum(manifest["ref"].values(), [])) == sorted(t.tid for t in trajs)
    first = manifest["ref"]["batch_01"]
    assert "Gold answer" in (tmp_path / "prompts/ref/batch_01.txt").read_text(encoding="utf-8")
    assert "Gold answer" not in (tmp_path / "prompts/noref/batch_01.txt").read_text(encoding="utf-8")
    corpus_prompt = (tmp_path / "prompts/corpus/batch_01.txt").read_text(encoding="utf-8")
    assert "corpus.json" in corpus_prompt and "Gold answer" not in corpus_prompt
    # A fenced reply covering all but the last trajectory of batch 1.
    reply = [{"tid": t, "scores": {c: 2 for c in CRITERION_IDS}, "rationale": {c: "ok" for c in CRITERION_IDS}} for t in first[:-1]]
    run = tmp_path / "responses/test_ref"
    run.mkdir(parents=True)
    (run / "batch_01.txt").write_text("```json\n" + json.dumps(reply) + "\n```", encoding="utf-8")
    res = {r.tid: r for r in import_chat_run(run, [t.tid for t in trajs], "chat:test", True)}
    assert len(res) == 50 and sum(r.parse_ok for r in res.values()) == 9
    assert not res[first[-1]].parse_ok and res[first[0]].scores["C1"] == 2


def test_corpus_mode_sends_corpus_as_prefix():
    from agenteval.judge import CORPUS_REFERENCE

    class Capture(MockBackend):
        def complete(self, system, user, prefix=None):
            self.seen = (user, prefix)
            return super().complete(system, user, prefix)

    b = Capture()
    tr = build_simulated_trajectories()[0]
    r = judge_trajectory(b, tr, None, mode="corpus", corpus_json='[{"ticker": "X"}]')
    user, prefix = b.seen
    assert r.parse_ok and r.mode == "corpus" and not r.reference_aided
    assert prefix.startswith("Attached file corpus.json:") and '"ticker"' in prefix
    assert CORPUS_REFERENCE in user and "Gold answer" not in user


def test_judge_command_saves_progress_and_resumes(tmp_path, monkeypatch):
    from agenteval import cli
    from agenteval.corpus import save_corpus
    from agenteval.trajectory import save_trajectories

    monkeypatch.setattr(cli, "DATA", tmp_path / "data")
    monkeypatch.setattr(cli, "RESULTS", tmp_path / "results")
    save_trajectories(build_simulated_trajectories(), tmp_path / "data" / "trajectories_simulated.json")
    save_corpus(tmp_path / "data" / "corpus.json")
    calls = []
    real = MockBackend.complete

    def flaky(self, system, user, prefix=None):
        calls.append(1)
        if len(calls) == 4:
            raise RuntimeError("simulated outage")
        return real(self, system, user, prefix)

    monkeypatch.setattr(MockBackend, "complete", flaky)
    args = ["judge", "--backend", "mock", "--mode", "corpus", "--limit", "5", "--repeats", "2"]
    cli.main(args)  # fails on the 4th call: 3 saved
    out = tmp_path / "results" / "judge_simulated_mock_corpus_r1.json"
    assert len(json.loads(out.read_text())) == 3
    cli.main(args)  # resumes: 2 more for r1, then 5 for r2
    assert len(json.loads(out.read_text())) == 5
    assert len(json.loads((tmp_path / "results" / "judge_simulated_mock_corpus_r2.json").read_text())) == 5
    assert len(calls) == 4 + 2 + 5


def test_throttled_spaces_calls(monkeypatch):
    import time
    from agenteval.backends import Throttled

    clock = {"t": 0.0}
    slept = []
    monkeypatch.setattr(time, "monotonic", lambda: clock["t"])
    monkeypatch.setattr(time, "sleep", lambda s: (slept.append(s), clock.__setitem__("t", clock["t"] + s)))
    b = Throttled(MockBackend(), rpm=5)
    for _ in range(3):
        b.complete("s", "u")
    assert slept == [12.0, 12.0] and b.name == "mock"


def test_run_names_with_repeats():
    from agenteval.chat_judge import parse_run_name

    assert parse_run_name("Haiku-5.5_corpus") == ("Haiku-5.5", "corpus", 1)
    assert parse_run_name("Haiku-5.5_corpus_r2") == ("Haiku-5.5", "corpus", 2)
    assert parse_run_name("gemini-3-flash_noref_r3") == ("gemini-3-flash", "noref", 3)
    assert parse_run_name("Haiku-5.5") is None and parse_run_name("x_corpus_r0") is None


def test_batch_judge_sends_prompts_and_resumes(tmp_path):
    from agenteval.chat_judge import import_chat_run, run_batches_via_api, write_chat_prompts

    trajs = build_simulated_trajectories()
    manifest = write_chat_prompts(trajs, {q.qid: q for q in build_questions()}, tmp_path)

    class BatchMock(MockBackend):
        name = "batchmock"

        def complete(self, system, user, prefix=None):
            assert system == "" and prefix.startswith("Attached file corpus.json:")
            tids = next(v for v in manifest["corpus"].values() if f"({', '.join(v)})" in user)
            self.last_meta = {"input_tokens": 1}
            return json.dumps([{"tid": t, "scores": {c: 2 for c in CRITERION_IDS}, "rationale": {}} for t in tids])

    out = tmp_path / "responses" / "m_corpus"
    (out).mkdir(parents=True)
    (out / "batch_01.txt").write_text("already saved by an earlier run", encoding="utf-8")
    sent = run_batches_via_api(BatchMock(), tmp_path / "prompts" / "corpus", out, corpus_json="[]")
    assert sent == ["batch_02", "batch_03", "batch_04", "batch_05"]
    assert json.loads((out / "api_meta.json").read_text())["batch_02"]["judge"] == "batchmock"
    res = import_chat_run(out, [t.tid for t in trajs], "chat:m", False)
    assert sum(r.parse_ok for r in res) == 40  # batch_01's placeholder reply parses to nothing


def test_repeat_grouping_ci_and_stability(tmp_path):
    from agenteval.agreement import bootstrap_ci, self_agreement, stack_runs
    from agenteval.report import build_report, display_name, group_result_files

    gold = {t.tid: t.gold_scores for t in build_simulated_trajectories()}
    flipped = {t: {**s, "C1": 2 - s["C1"]} for t, s in gold.items()}
    # Two identical runs and one with C1 flipped everywhere.
    runs = [gold, dict(gold), flipped]
    sa = self_agreement(runs)
    changed = sum(s["C1"] != 1 for s in gold.values())  # flipping leaves C1 = 1 unchanged
    assert sa["runs"] == 3 and abs(sa["all_runs_identical"] - (1 - changed / 350)) < 1e-3
    a, b, _ = stack_runs(runs, gold)
    assert len(a) == 150 and all(k.split("#")[0] in gold for k in a)
    ci = bootstrap_ci([gold], gold, n_boot=50)
    assert ci["exact"] == (1.0, 1.0)
    lo, hi = bootstrap_ci(runs, gold, n_boot=200)["exact"]
    assert lo <= 1 - (sum(s["C1"] != 1 for s in gold.values()) / 50) / 21 <= hi  # point estimate inside the interval

    for name, run in (("Haiku-5.5_corpus", gold), ("Haiku-5.5_corpus_r2", flipped), ("Opus-5.5_corpus", gold)):
        rows = [{"tid": t, "scores": s, "parse_ok": True} for t, s in run.items()]
        (tmp_path / f"judge_simulated_chat-{name}.json").write_text(json.dumps(rows))
    groups = group_result_files(tmp_path)
    assert [(k, [r for r, _ in v]) for k, v in groups.items()] == [
        (("simulated", "chat-Haiku-5.5_corpus"), [1, 2]), (("simulated", "chat-Opus-5.5_corpus"), [1])]
    assert display_name("chat-Haiku-5.5_corpus") == "Haiku-5.5 (corpus)"
    text = build_report(tmp_path, gold, {}, {}, {}, "test", n_boot=50)
    assert "| Haiku-5.5 (corpus) | 2 |" in text and "## Run-to-run stability" in text and "50 trajectories x 2 runs" in text
