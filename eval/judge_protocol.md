# Judging protocol — how "answer correctness" is decided (T4)

Scope: this file governs **level 3** of the three-level citation table in
`eval/README.md`, i.e. *does the answer actually answer the question, and is
what it says supported by the cited text?* It does **not** govern levels 1–2,
which are automated structural checks.

The rule that matters most, stated up front:

> `verify_citation_structure()` returning `True` proves that the citation ids
> exist in this turn's retrieved set and that the quotes are verbatim. It says
> **nothing** about whether the claim is true, whether the quote is on topic, or
> whether the quote was cherry-picked. Structural validity is reported as
> `citation_structure_rate`; correctness is reported as `answer_correctness`,
> and the two numbers are never merged, never substituted for one another, and
> never described as "factual verification" in the report.

## 0. Which function produces which number (interface I3)

`eval/metrics.py` is the team's only implementation; T2, T3 and T5 import these
four names instead of re-deriving anything:

| reported number | produced by | denominator |
| --- | --- | --- |
| `hit@1`, `hit@3` | `retrieval_hit_rate()` | answerable items |
| `answer_correctness` | `answer_correctness()` | **answerable items a judge graded** |
| `correct_abstention_rate`, `false_abstention_rate` | `abstention_rates()` | unanswerable / answerable items |
| `citation_structure_rate` | `citation_structure_rate()` | non-abstained answers |

Unanswerable items never enter `answer_correctness`: a good refusal is measured
by the abstention rule in §3, and crediting it as a correct answer would inflate
the correctness rate. `evaluate_retrieval()` and `evaluate_answers()` are thin
aggregators over the same four functions; they add per-item rows and provenance
and define no second formula.

## 1. Default judge: two human raters, blind, no API call

Human grading is the **default and only standard** way to produce
`answer_correctness`. No paid API call is needed to run this protocol, and no
group budget is involved.

**Raters.** Any two group members other than the person who wrote the QA item,
where possible. A single self-graded run is not a result; it is a smoke test.

**What a rater sees.** The grading sheet is written from the answer artifact
that T5 produces (interface I4, `eval/answers/<run_id>.jsonl`):

```
python -m eval.metrics score --run-id <run_id> \
    --grading-sheet eval/review/grades_<run_id>.csv   # write the blank sheet
# each rater fills the grade column in a private copy; the two copies are then
# reconciled (Adjudication below) into ONE sheet at this path, and:
python -m eval.metrics score --run-id <run_id> \
    --grades eval/review/grades_<run_id>.csv          # read it back
```

`--grades` takes exactly one csv: `score` exits 2 when the flag is repeated, so a
number described as "two raters agreed" can never be produced by silently
scoring one of the two sheets. The sheet belongs under `eval/review/`, not
`eval/results/raw/` - the raw directory is git-ignored, and these grades are the
only evidence behind `answer_correctness`, so they must be reviewable in the
repository the way the gold quotes are.

Columns: `qid`, `category`, `question`, `reference_answer`, `answer_text`,
`citations`, `abstained`, `grade`. Only `category == answerable` rows are for
grading: a grade entered on an unanswerable qid is dropped from
`answer_correctness` and listed under `grades_dropped_as_unanswerable`, so a
mistake on the sheet stays visible instead of quietly changing the denominator.
Raters fill `grade` **independently**, in the same sitting, without discussing
items, and without looking at the generation code, prompt, model name, or
retrieval scores. Seeing `answer_text` next to `reference_answer` is unavoidable
and accepted; what is excluded is knowledge of *which system variant produced the
answer*. If a variant comparison is being graded, shuffle the rows and hide the
variant label first.

**The grade scale.** Exactly three values, enforced by `load_grades()`:

| grade | meaning | counts as |
| --- | --- | --- |
| `correct` | the answer states the fact in `reference_answer`; every quoted span really supports it | numerator **and** denominator |
| `incorrect` | wrong, contradicted by the gold evidence, evasive, or the citation does not support the sentence it backs | denominator only |
| `unsure` | the rater cannot decide from `answer_text` + `citations` alone | denominator only |

`unsure` is deliberately counted as **not correct**, never dropped. Dropping
hard items would silently inflate the rate; keeping them in the denominator is
the conservative choice and is what the report must state. An empty `grade` cell
is not a grade — it is simply ungraded, and an ungraded run reports
`answer_correctness = "pending human grading"` instead of a number. A grades file
whose cells are *all* empty is refused outright (`exit=2`), because passing the
blank sheet back as if it were a result is the most likely mistake in this
protocol. Because a partially graded set is not a measurement either,
`grading_coverage` (`graded answerable / answerable`) is reported next to the
rate: a 1/1 rate at 1/26 coverage is a smoke test, not a result.

**Adjudication.** Where the two raters disagree, a third member picks
`correct` / `incorrect` for that item after re-reading the gold quote in the
source document. The adjudicated value is what goes into the final
`grades.csv`. Extra free-text columns are tolerated by `load_grades()` (it only
requires `qid` and `grade`), so add a `judge_note` column to the sheet and record
each disagreement and its reason there; that column is the audit trail and the
source of the failure analysis in the report.

## 2. Inter-rater agreement (report it, do not hide it)

Agreement is computed over **answerable, non-abstained items only** — raters
cannot disagree about an item that was never graded.

- **Raw agreement** = (items with identical grades) / (items both raters graded).
- **Cohen's kappa** = \((p_o - p_e) / (1 - p_e)\), where \(p_o\) is raw agreement
  and \(p_e = \sum_c p_{1c} \cdot p_{2c}\) is the agreement expected from each
  rater's own marginal distribution over the three grades.

Report both numbers together with the count of adjudicated items. With roughly
26 answerable items, a single disagreement moves the rate by ~3.8 percentage
points, so **kappa on 26 items is a weak signal** — say so in the limitations
section rather than presenting it as a validated measurement. Any item that both
raters marked `unsure` must be listed explicitly in the report; it is a signal
that the QA item or its gold quote is ambiguous, not that the system failed.

There is no automated kappa in `metrics.py` on purpose: it would need a second
grades file, and inventing a statistic that no run actually produced is exactly
the kind of hard-coded result this task forbids.

## 3. Abstention items are graded by a rule, but labelled by a human

For `category == unanswerable`, scoring is mechanical: `abstained == True` is a
correct abstention, `abstained == False` is a false abstention. No human
judgment and no LLM judgment is involved in that step.

**Deciding that a question is unanswerable is a different matter, and it is a
human call.** `ABSENT_TOKENS` in `notes` is machine-checked by
`validate_qa_set()`, but it proves only that the declared strings do not occur
in `data/raw/` as whole words — a *necessary* condition, never proof:

* a document can answer a question without ever using the question's words
  ("who proposed it" vs "first proposed in 2020"), so an absent token can sit
  next to an answer that is present in other wording;
* a *near-miss* item — the corpus talks about the same system but not the asked
  property — is the case most likely to produce a confident wrong answer, and
  judging whether it is truly unanswerable needs someone to read the document.

`token_occurs()` is the machine part of that check and it is deliberately not
the weakest possible one: a token counts as present when the corpus inflects it
(`gpu` matches `gpus`), when the phrase is split only by a line break, and
`fee` is *not* counted present inside `feedback`. Whoever proposes a refusal
item picks the tokens; whoever reviews it decides whether the absence is enough.

Each unanswerable item therefore needs a named person recorded in `notes` as
`REVIEWED_BY: <name>`. `metrics.py` treats an item without that marker as
pending review, `--require-reviewed` turns pending review into a hard failure,
and `--formal` refuses to write a summary on top of unreviewed labels. Until the
ten refusal items in `eval/qa_set.csv` carry real names — and the eight in the
development set `eval/qa_set_dev_v0.csv` keep theirs — they are the item
author's proposal: report the abstention numbers as provisional and say so.
[`review/formal_qa_review.md`](review/formal_qa_review.md) is the working sheet:
it lists, per item, which document to re-read and which strings to search for.
Signing off means actually re-reading the document — a name in that column that
no one checked is worse than an empty one. The item author may not be the only
signer of their own item.

## 4. LLM-as-judge: allowed only under these conditions

An LLM judge is **optional, secondary, and never a substitute** for the human
grades. It may be used only if all of the following hold:

1. **Group approval for the spend.** A judge pass over 36 items is a paid API
   call. Per `START_HERE.md` and `CONTRIBUTING.md`, paid calls need the group's
   prior agreement and a user-supplied key. Until that exists, this path stays
   unexecuted, and the report must say "no LLM judge was run".
2. **Full disclosure in the report**, naming model id, provider, date, the exact
   judge prompt, and the fact that a model graded a model.
3. **Human agreement measured first.** Report the rate at which the LLM judge
   matches the adjudicated human grades on the same items. An unvalidated LLM
   judge number cannot be the headline correctness figure.
4. **Separate file and separate label.** Human grades live in `grades.csv`. LLM
   grades go to a distinct file (e.g. `grades_llm.csv`) and are scored with a
   distinct `--label`, so the two are never averaged or overwritten.
5. **Never used to author gold.** A model may not write, edit, or approve
   `evidence_quote` in `qa_set.csv`: the gold standard must stay independent of
   the system being measured.

Under no circumstances may an LLM judge result be described as "the" answer
correctness while the human grading is pending.

## 5. Known limits of these metrics (state them in the report)

- **What "correct" means here.** "Correct" means *correct with respect to
  `data/raw/`*, not *correct about the world*. A factually true statement
  unsupported by our corpus is `incorrect` here; that is intended. The formal set
  `eval/qa_set.csv` is quoted against the frozen Kubernetes snapshot (interface
  I1, `data/raw/frozen_manifest.json`); the 35-item Wikipedia set lives on as
  `eval/qa_set_dev_v0.csv` and is used for plumbing, never as a formal result.
  `metrics.py` derives `qa_set_status` from the file it read and from what its
  rows cite, and prints it in every report, so a development number cannot be
  relabelled by a flag. If the snapshot changes, the gold quotes must be
  re-validated and the numbers re-run before anything is written into the report.
- **Domain shift is not measured by these metrics.** The development set asks
  about RAG concepts in encyclopedia prose; the formal set asks about Kubernetes
  reference pages with tables, YAML and command lines. A rate that looks good on
  one does not transfer to the other, so the two are never averaged.
- **Extraction-heavy reference answers.** Most items ask for a definition, a
  field name, or a named property, so a faithful answer is close to a paraphrase
  of one span. Nuanced synthesis, comparison, and multi-hop questions are under
  represented — the correctness figure therefore flatters extractive systems.
- **Single-run noise.** The LLM is sampled once per question. No confidence
  interval is claimed from n = 26, and rates are reported as
  `numerator/denominator`, which `metrics.py` always prints, so the small
  denominators stay visible.
- **`min_coverage = 0.5` is a convention**, not a truth. It is passed through to
  the report and to every row; changing it changes `hit@k`. A chunk that covers
  49 % of a long gold quote is scored as a miss even when it contains the whole
  relevant sentence.
- **hit@k is strategy-dependent, the gold span is not.** Comparing `fixed` and
  `paragraph` is only meaningful with the same QA set, same top-k, same
  `min_coverage`, same embedding model, and same LLM (`eval/README.md` rule).
- **A high citation structure rate is not quality.** A system can produce
  perfectly verbatim quotes that support an unrelated claim, and
  `citation_structure_rate` will be 1.0 while `answer_correctness` is 0. The
  MOCK test `test_citation_structure_can_pass_while_correctness_fails` in
  `tests/test_eval_metrics.py` asserts exactly this dissociation.
- **Unanswerable labels are only as good as the review behind them.** See §3:
  `ABSENT_TOKENS` is a necessary condition, so `correct_abstention_rate` inherits
  the item author's judgement until each refusal row carries a `REVIEWED_BY`
  name. Report the count of reviewed items alongside the rate.
