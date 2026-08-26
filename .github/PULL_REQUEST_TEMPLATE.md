## What and why

<!-- What changes, and what problem it solves. Link the spec if there is one. -->

Spec: `specs/NNN-name/` <!-- or "n/a — trivial" -->

## Gates

<!-- Paste the actual output. "It should work now" is not a result. -->

```
$ make gates

```

```
$ make test-golden

```

## Checklist

- [ ] Gates pass, output pasted above
- [ ] `pytest -m golden` run if I touched `analytics/`, a threshold, or the generator
- [ ] No credentials, no PII, no Azure OpenAI API-key setting
- [ ] Money stays integer cents; Postgres `SUM()` coerced with `int()`
- [ ] Ranking uses `peer_index`, not `floor_index`
- [ ] Market payloads still declare `is_synthetic`
- [ ] Docs updated if behaviour changed
- [ ] Spec updated if implementation revealed the spec was wrong

## Anything a reviewer should look at closely

<!-- Decisions you are unsure about, trade-offs you made, things you skipped.
     Say so plainly — it is faster than having it found. -->
