# How to falsify a claim in this repository

Every claim here is meant to be breakable by someone who does not trust us. This page lists
the claims, the cheapest way to break each one, and what we promise to do when you do.

| Claim | How to break it | Where |
|---|---|---|
| "Every rule either cites a clause or declares itself doctrine" | Find a rule whose `LAW` label points to text that does not say what the rule assumes | [`Clause_Matrix.md`](Clause_Matrix.md), [`basis.py`](../../lgd_engine/judges/basis.py) |
| "67/67 rules have a basis, 12 are DOCTRINE" | Show a shipped rule missing from the matrix, or a DOCTRINE count above the cap | `python benchmarks/clause_matrix.py` |
| "The verdict is deterministic and calls no model" | Produce two runs with different output on the same input, or find a network call | `python benchmarks/verdict_cost.py` |
| "The evaluation report is generated, not written" | Make the report's `<!-- eval-report ... -->` marker disagree with the repository and see whether `C12` catches it | `python benchmarks/eval_method_note.py` |
| "Every field any rule reads is classified, and the weak ones are capped" | Find a field classified `claim` that is really evidence — deleting it should have been a `hold`, not a `go` | [`absence_taxonomy.json`](absence_taxonomy.json), `python benchmarks/absence_taxonomy.py` |
| "Weak fields are a fact about the corpus, not an excuse" | Pick a field marked `weak_evidence` and show that every shipped case supplies it — that would make the label false | `python benchmarks/absence_taxonomy.py` |
| "An incomplete record cannot soften a veto" | Delete a required field from a record that violates a critical rule -- the answer must stay `reject`, and the veto must stay named | `python -m unittest tests.test_contract.TestVetoPrecedence` |
| "A verdict needs a usable record, not a present key" | Delete a required field, or set it to `null` / `""` / `[]` / `0`, and see whether a `go` comes back | `python benchmarks/absence_sweep.py` |
| "Coverage gaps are published, not hidden" | Find a law we silently fail to encode and that is absent from the list | [`coverage_gaps.json`](coverage_gaps.json) |
| "Competitive claims are labelled by evidence strength" | Find an `observed` row without a source, or a claim that should be `inferred` but says `observed` | [`competitive_edges.json`](competitive_edges.json) |

## The strongest form of challenge

A single case that the engine gets wrong, with the operative clause quoted. File it through
the **Challenge a rule** issue form. You do not need to install anything: paste the case as
JSON and we will run it.

## What we promise

1. **Negative results are published as negative results.** A confirmed wrong verdict goes into
   the evaluation report and the clause matrix as a defect, with the rule ID.
2. **We do not pick the challenger.** We will not ask for a "friendly" reviewer or edit a case
   to make it pass.
3. **We do not argue from authority.** If the clause text contradicts the rule, the rule is
   wrong, whoever wrote it.
4. **Silence is not agreement.** If we cannot resolve a challenge within two weeks, we say so in
   the issue rather than letting it sit.

## What a challenge does not get you

A challenge that asserts "the regulation says otherwise" without quoting the text will be
answered with a request for the quote, not with a change. Authority-only claims are how this
repository's own errors survived as long as they did.
