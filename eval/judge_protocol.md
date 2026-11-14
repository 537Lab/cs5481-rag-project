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

## 1. Default judge: two human raters, blind, no API call

Human grading is the **default and only standard** way to produce
`answer_correctness`. No paid API call is needed to run this protocol, and no
group budget is involved.

**Raters.** Any two group members other than the person who wrote the QA item,
where possible. A single self-graded run is not a result; it is a smoke test.

**What a rater sees.** The grading sheet produced by:

```
python -m eval.metrics score --outputs eval/results/run.json \
    --grading-sheet eval/results/grades.csv
```

Columns: `qid`, `question`, `reference_answer`, `answer_text`, `citations`,
`grade`. Raters fill `grade` **independently**, in the same sitting, without
discussing items, and without looking at the generation code, prompt, model
name, or retrieval scores. Seeing `answer_text` next to `reference_answer` is
unavoidable and accepted; what is excluded is knowledge of *which system variant
produced the answer*. If a variant comparison is being graded, shuffle the rows
and hide the variant label first.

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
`answer_correctness = "pending human grading"` instead of a number.

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
27 answerable items, a single disagreement moves the rate by ~3.7 percentage
points, so **kappa on 27 items is a weak signal** — say so in the limitations
section rather than presenting it as a validated measurement. Any item that both
raters marked `unsure` must be listed explicitly in the report; it is a signal
that the QA item or its gold quote is ambiguous, not that the system failed.

There is no automated kappa in `metrics.py` on purpose: it would need a second
grades file, and inventing a statistic that no run actually produced is exactly
the kind of hard-coded result this task forbids.

## 3. Abstention items are graded by a rule, not by a judge

For `category == unanswerable`, correctness is mechanical: `abstained == True` is
a correct abstention. No human judgment, no LLM judgment. The one judgement call
is whether an `unanswerable` question is genuinely unanswerable from
`data/raw/`; that is checked when the set is written (each such item declares
`ABSENT_TOKENS` in `notes`, verified by `validate_qa_set()` against the real
corpus), not when it is scored.

## 4. LLM-as-judge: allowed only under these conditions

An LLM judge is **optional, secondary, and never a substitute** for the human
grades. It may be used only if all of the following hold:

1. **Group approval for the spend.** A judge pass over 35 items is a paid API
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

- **The corpus is four Wikipedia excerpts.** "Correct" means *correct with
  respect to `data/raw/`*, not *correct about the world*. A factually true
  statement unsupported by our corpus is `incorrect` here; that is intended.
- **Extraction-heavy reference answers.** Most items ask for a definition, a
  date, or a named property, so a faithful answer is close to a paraphrase of
  one span. Nuanced synthesis, comparison, and multi-hop questions are under
  represented — the correctness figure therefore flatters extractive systems.
- **Single-run noise.** The LLM is sampled once per question. No confidence
  interval is claimed from n = 27, and rates are reported as
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
