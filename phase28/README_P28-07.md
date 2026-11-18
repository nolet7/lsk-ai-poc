# P28-07 — Governed service and source-ID grounding (offline lab)

Copy `phase28/service.py` and `phase28/grounding.py` into the repository, and replace `phase28/tests/test_service.py` and `phase28/tests/test_grounding.py` with the supplied tests. Preserve your existing `phase28/authorization.py` and `phase28/audit.py` from P28-06.

Run from repo root:

```bash
python -m py_compile phase28/service.py phase28/grounding.py
python -m unittest discover -s phase28/tests -p 'test_service.py' -v
python -m unittest discover -s phase28/tests -p 'test_grounding.py' -v
python -m unittest discover -s phase28/tests -v
```

The new service function retains the original `actor/domain/question/record_id/use_model` parameters and adds explicit dependencies. Caller MUST provide trusted `Principal` constructed from verified gateway claims. No gateway OIDC/JWT validation, business API integration, durable audit sink, or real inference is included. `retrieve(scope)` MUST apply tenant/domain restrictions at the data layer. `generate(question, evidence)` is injected, and any production implementation must route through approved budget enforcement.

A cited ID belonging to authorized sources is not proof that generated statements are true. Full semantic grounding and operational integration are outstanding.
