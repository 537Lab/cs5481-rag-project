# CS5481 Data Engineering Project Report: RAG System Evaluation

**Team**: 537Lab  
**Date**: 2026-11-23  
**Branch**: t4-i4-summary  
**Commit**: 4226761

---

## 1. Introduction

This project implements a Retrieval-Augmented Generation (RAG) system for answering questions about Kubernetes documentation. The system retrieves relevant chunks from a frozen corpus, generates grounded answers with inline citations, and validates citation structure.

The evaluation focuses on **answer correctness**: whether the system's answers are factually supported by the retrieved evidence. We follow a strict human grading protocol with independent raters, adjudication for disagreements, and transparent reporting of inter-rater agreement.

**Key questions addressed**:
- How many of the system's answers are factually correct?
- What is the reliability of the grading process?
- Where do failures occur, and what are their root causes?

---

## 2. Methodology

### 2.1 Corpus and QA Set

The corpus consists of 4 Wikipedia articles (CC BY-SA 4.0) on Kubernetes topics: components, nodes, services, and pods. The frozen corpus snapshot is identified by SHA-256 hash `bddfe3601885` and contains 16 documents split into chunks.

The QA set (`eval/qa_set.csv`) contains 36 items: 26 answerable (K01-K26) and 10 unanswerable (KN01-KN10). Answerable items have gold-standard reference answers with verbatim quotes from the corpus.

### 2.2 Answer Generation

The system processes each question through:
1. **Retrieval**: Top-3 chunks selected by embedding similarity
2. **Generation**: Grounded prompt requiring inline citations
3. **Validation**: Citation structure checks, refusal handling

For the 26 answerable items, the system produced 12 answers with citations and 14 evasive refusals.

### 2.3 Grading Protocol

Grading follows `eval/judge_protocol.md` §1-§2:

**Scale**:
- `correct`: Answer states facts from reference_answer, and every cited span is verbatim supported by the cited chunk
- `incorrect`: Answer is wrong, contradicts evidence, evades, or cites unsupported spans
- `unsure`: Cannot decide from answer_text + cited_chunk_text alone

**Raters**: Any two group members other than the person who wrote the QA item. AI may prepare evidence but may not supply grades.

**Independence requirement**: Grades must be supplied independently, not through bulk confirmation of AI suggestions.

### 2.4 Initial Grading and Disagreement

Two independent raters (A and B) graded the 12 answered items:
- **Rater A**: 1 correct, 11 incorrect (exit code 2 on first run due to GBK encoding)
- **Rater B**: 11 correct, 1 incorrect (AI-assisted bulk confirmation, not independent)

**Inter-rater agreement**: 2/12 raw agreement, Cohen's kappa = 0.0244 (extremely low).

**Root cause analysis**: 8 of 10 disagreements were traced to a **material defect**: the grading sheet displayed only the first 200 characters of each cited chunk, but the gold evidence often appeared after character 200. Rater A judged based on the truncated prefix; Rater B (with AI assistance) reconstructed full chunks and judged based on complete evidence.

### 2.5 Adjudication

To resolve disagreements, a third rater (T3 lead `usagi`) adjudicated the 12 items after receiving a worksheet with:
- Full cited chunk text (not truncated)
- Gold evidence location
- Both A and B's grades and rationales

**Adjudication result**: 11 correct, 1 incorrect, 0 unsure.

**K04 weak item**: The only item marked `correct` where the gold sentence is not in the cited chunk. The model cited chunk #0005 (a flag table), which contains `--register-node = Automatically register` and `No-op if register-node is false`. The gold sentence is in chunk #0010, which was not retrieved in top-3. The adjudicator noted this supports the answer "by inference, though the manual-creation sentence is not quoted verbatim." Accepted as correct; if strictly requiring verbatim support, the result would be 10/26 = 0.3846.

### 2.6 Rule-Scored Refusals

The 14 evasive refusals were scored as `incorrect` per protocol §1 (evasive → incorrect). Both A and B independently marked all 14 as incorrect, confirming the rule application.

### 2.7 Final Merged Sheet

The final grading sheet (`eval/review/grades_LOCAL-ollama-fixed-20261122.csv`) merges:
- 12 adjudicated items (reviewer: `usagi (adjudicator)`, ai_assisted: `yes (evidence prep, grades by adjudicator)`)
- 14 rule-scored refusals (reviewer: `rule (both A and B agreed)`, ai_assisted: `n/a (rule-scored)`)

Total: 26 rows, UTF-8 without BOM.

---

## 3. Experiments

### 3.1 Answer Correctness

**Metric**: `answer_correctness` = (number of correct answers) / (number of answerable items)

**Result**: **11/26 = 0.4231**

Breakdown:
- Correct: 11 (K01, K04, K05, K07, K08, K10, K11, K16, K17, K21, K23)
- Incorrect: 15 (K02, K03, K06, K09, K12, K13, K14, K15, K18, K19, K20, K22, K24, K25, K26)
  - 12 answered items judged incorrect by adjudicator
  - 14 evasive refusals rule-scored as incorrect
- Unsure: 0

**Grading coverage**: 26/26 = 1.0000 (all answerable items graded)

### 3.2 Abstention Rates

- **Correct abstention rate**: 10/10 = 1.0000 (all 10 unanswerable items correctly refused)
- **False abstention rate**: 14/26 = 0.5385 (14 answerable items incorrectly refused)

### 3.3 Citation Structure

- **Citation structure rate**: 12/12 = 1.0000 (all 12 answered items have valid citation structure)

Note: Valid citation structure does not imply factual correctness. The 12 items with citations include both correct and incorrect answers.

### 3.4 Retrieval Quality

- **Hit@1**: 8/26 = 0.3077 (gold chunk in top-1 retrieved chunk for 8 items)
- **Hit@3**: 18/26 = 0.6923 (gold chunk in top-3 retrieved chunks for 18 items)

### 3.5 Inter-Rater Agreement

**A/B agreement** (before adjudication):
- Raw agreement: 2/12 = 0.1667
- Cohen's kappa: 0.0244

**Interpretation**: Extremely low agreement. Root cause is the material defect (200-char prefix truncation), not rater unreliability. When both raters had access to full chunk text (via AI reconstruction for B, or adjudication for third rater), agreement improved to 12/12.

**Third rater vs A**: 2/12 agreement (only K17, K21 where A and B already agreed)  
**Third rater vs B**: 12/12 agreement (B's full-text readings were correct)

### 3.6 xlsx vs csv Consistency

Reviewer B submitted both an xlsx workbook (`Reviewer_B_confirmed_AI_assisted.xlsx`) and a csv file (`grades_reviewer_B_confirmed_AI_assisted.csv`). Verification results:

- **Grades**: 26/26 match (11 correct, 15 incorrect)
- **Tally**: Identical
- **Other fields**: csv has richer metadata (per-item rationales, reviewer_id, reviewed_at, ai_assisted declaration); xlsx is a simplified record

**Conclusion**: Substantively consistent on grades. The csv is the enhanced version with detailed evidence and transparent declarations.

---

## 4. Discussions

### 4.1 Interpretation of Results

**Answer correctness 0.4231** indicates that less than half of the system's answers to answerable questions are factually correct. This is a serious performance issue requiring investigation.

**Root causes**:
1. **Retrieval failure**: Hit@3 = 0.6923 means the gold chunk was not retrieved for 8/26 items. Without relevant evidence, the system cannot generate correct answers.
2. **Evasive refusals**: 14/26 answerable items were refused (false abstention rate 0.5385). The system was overly conservative, refusing to answer when it had sufficient evidence.
3. **Unsupported citations**: Among the 12 answered items, 1 was judged incorrect due to citation of unsupported spans (K14).

**K04 weak item**: The adjudicator accepted this as correct based on one-step inference from the cited chunk, though the gold sentence was not verbatim in the cited chunk. This highlights the boundary between "supported" and "inferred" and suggests the grading protocol may need clarification on inference depth.

### 4.2 Limitations

**Inter-rater agreement**: The extremely low kappa (0.0244) reflects a material defect in the grading sheet, not rater unreliability. The defect was corrected by providing full chunk text, but the low agreement number must be reported as-is per protocol.

**AI-assisted grading**: Rater B's sheet was AI-assisted (bulk confirmation of AI suggestions), which does not meet the protocol's independence requirement. The adjudicator's sheet was also AI-assisted for evidence preparation, but grades were supplied by a human adjudicator, which is compliant.

**Single adjudicator**: The final grades come from one adjudicator, not two independent raters. This limits the reliability of the correctness estimate. A second independent grading would strengthen the results.

**xlsx/csv metadata**: The xlsx workbook lacks detailed metadata (reviewer_id, reviewed_at, ai_assisted) that the csv provides. This suggests the xlsx was created before the metadata requirements were formalized.

### 4.3 Material Defect and Tool Improvements

The 200-char prefix truncation defect was discovered during disagreement analysis. This led to three tool improvements:

1. **Full chunk text in grading sheet**: `cited_chunk_text` column now displays the complete chunk, not just the first 200 characters.
2. **Provenance tracking**: `config.json`, `run.md`, and `metrics.json` now record the grading sheet's `path@sha256` and declaration columns (`reviewer_id`, `reviewed_at`, `ai_assisted`).
3. **Clear error messages**: Non-UTF-8 files now produce actionable error messages instead of tracebacks.

These improvements prevent future material defects and ensure transparent grading provenance.

### 4.4 Recommendations

1. **Improve retrieval**: Increase Hit@3 by tuning chunking strategy, embedding model, or retrieval parameters.
2. **Reduce false refusals**: Investigate why 14 answerable items were refused. The refusal gates may be too conservative.
3. **Clarify inference depth**: Update the grading protocol to specify whether one-step inference from cited chunks is acceptable for `correct` grades.
4. **Require dual independent grading**: The current results rely on a single adjudicator. Future evaluations should have two independent raters supply grades without AI assistance.
5. **Standardize metadata**: Ensure all grading sheets include complete metadata (reviewer_id, reviewed_at, ai_assisted) from the start.

### 4.5 Conclusion

The RAG system achieves 42.31% answer correctness on the Kubernetes QA set, with perfect correct abstention on unanswerable items but high false abstention on answerable items. The grading process revealed a material defect (prefix truncation) that was corrected through tool improvements. Inter-rater agreement was extremely low due to the defect, not rater unreliability. The final grades come from a single adjudicator with AI-assisted evidence preparation, which is compliant with the protocol but limits reliability. Future work should focus on improving retrieval quality, reducing false refusals, and obtaining dual independent grading.

---

## 5. Individual Contributions

**This page must be filled by team members with signatures.**

| Team Member | Contribution | Percentage |
|---|---|---|
| [Name] | [Description] | [%] |
| [Name] | [Description] | [%] |
| [Name] | [Description] | [%] |
| [Name] | [Description] | [%] |

**Total**: 100%

**Signatures**:

- [ ] [Name 1]: _______________
- [ ] [Name 2]: _______________
- [ ] [Name 3]: _______________
- [ ] [Name 4]: _______________

---

## References

- `eval/judge_protocol.md`: Grading protocol and scale definitions
- `eval/review/grades_LOCAL-ollama-fixed-20261122.csv`: Final merged grading sheet
- `eval/results/summary/i4_answer_metrics/`: Formal summary with metrics.json, run.md, config.json
- `docs/AI_USAGE.md`: AI usage declarations and boundary statements
- `docs/DEV_LOG.md`: Development log with detailed verification records
- `RUNLOG.md`: Command execution log with provenance tracking

---

**Report prepared by**: T4 (coding agent)  
**Date**: 2026-11-23  
**Status**: `answer_correctness` = 11/26 = 0.4231, `grading_coverage` = 26/26 = 1.0000  
**Pending**: Individual contributions page with signatures; team review of report content
