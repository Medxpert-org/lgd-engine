# Red-team probes — four defects this gate found in itself

Every row below is a **case file that ships in this repository**. Run the command, read
the exit code, read the reason chain. Nothing here needs a network call, a model, or a
credential.

The four defects share one shape, which is the reason they are published together:

> **A rule that waits on an intermediate artefact inherits the artefact's absence as
> permission.** The artefact can be a boolean flag, a vocabulary entry, a downstream
> classification, or a field nobody filled in.

| # | Domain | Case file | Command |
|---|---|---|---|
| 1 | EU MDR | `demo1/cases_mdr/mdr08_red_team_acceptance_scope_expansion.json` | `python -m lgd_engine.cli --case … --domain mdr` |
| 2 | 510(k) | `demo1/cases/510k_red_team_label_expansion.json` | `python -m lgd_engine.cli --case … --domain 510k` |
| 3 | Postmarket | `demo1/cases_postmarket/pm04_red_team_death_without_recall.json` | `python -m lgd_engine.cli --case … --domain postmarket` |
| 4 | PCCP | `demo1/cases_pccp/pccp08_red_team_absent_special_controls.json` | `python -m lgd_engine.cli --case … --domain pccp` |

Each file declares `"expected_verdict": "hold"`, so `--all` over the directory fails the
build if the fix is ever reverted.

---

## 1. EU MDR — the accepted corrective action

**What used to happen.** `corrective_action_accepted_by_authority: true` skipped *every*
major rule. An expansion of indication, a change affecting safety or performance, and a
change of risk class all returned **go**.

**Why it is wrong.** CAMD FAQ 17 exempts *the change that implements* the accepted
corrective action. The code read "an accepted action exists" as "this change is
accepted" — the exemption was never scoped to the change itself.

**What settles it now.** `M-MAJ-13-acceptance-not-scoped-to-the-change` requires both
markers: the authority acceptance **and** a declaration that this change implements it.

---

## 2. 510(k) — a value the vocabulary knew

**What used to happen.** `change_type: "label_expansion"` is in `KNOWN_CHANGE_TYPES`,
matched no rule, and returned **go with an empty reason chain**.

**Why it is wrong.** A labelling change that adds a patient population changes the
intended use — 21 CFR 807.81(a)(3)(i) puts it on the new-510(k) side, not on the
label-correction side.

**What settles it now.** `R-MAJ-09-label-expansion-new-claim`, plus
`R-MAJ-10-no-rule-claims-this-change` for the general case: a verdict that cannot name
its rule is not a verdict. `TestEnumCoverage` walks every known change type and fails if
any arrives unplaced — which is how four *more* conditionally-claimed types were found
(`design_defect`, `material_nonconforming`, `process_change_control`,
`maintenance_execution`).

---

## 3. Postmarket — a death with no recall class

**What used to happen.** `harm_severity: "death"` with `recall_class: "none"` returned
**go with an empty reason chain**.

**Why it is wrong.** The table only asked "is there a recall?". 21 CFR 803.50 does not
wait for a recall class: a device-related death or serious injury is reportable within
30 days.

**What settles it now.** `PM-MAJ-04-reportable-event-without-recall` keys on the harm
severity itself. `PM-MIN-02-no-recall-recorded` makes the green path name its rule too,
so silence is no longer indistinguishable from "the table has nothing for this field".

---

## 4. PCCP — a field nobody filled in

**What used to happen.** Delete a field from an otherwise compliant PCCP record and it
returned **go**.

**Why it is wrong.** Four special controls — the modification class description, the
validation record, the labeling version history, the new UDI — were tested with
`is False`. An absent field is not `False`. 21 CFR 892.2055 lists these among the
controls every update must carry.

**What settles it now.** All four test `is not True`, so `False` and absent get the same
verdict. `P-MAJ-04` had already stated the doctrine — *unproven is not met* — for the
acceptance criteria alone; it is now applied to all five.

---

## How to attack this gate

The probes above were found by changing the *input shape*, not by reading the code:

- **delete a field** rather than set it to a negative value (probe 4);
- **use a value the vocabulary knows** rather than a value it rejects (probe 2);
- **supply the artefact the rule keys on** rather than the fact it is meant to prove
  (probes 1 and 3).

Each of those is a different question about the same table, and each found something the
previous probes could not. If you have a fifth, the form is in
[`Challenge.md`](Challenge.md): the rule id, the clause quoted verbatim, and a case
file. A challenge that only says "the regulation does not say that", without quoting
the text, will be declined — not because the objection is unwelcome, but because it
cannot be checked.

**What is *not* claimed here.** These four fixes make the gate stricter in one direction:
they refuse to let an unclassified or unstated change out as go. They do not establish
that the remaining rules are right, and they do not establish that the verdicts match a
regulator's judgement. The published list of what is deliberately not encoded is
[`coverage_gaps.json`](coverage_gaps.json).
