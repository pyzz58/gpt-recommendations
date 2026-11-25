# Workflow configuration

`catalog.yaml` pins the three W12 domain packages:

- `pet_repurposing.yaml`
- `ivd.yaml`
- `device.yaml`

Each package uses the same strict schema while preserving domain-specific
stages, roles, criteria, outputs and failure routes. The final external stage of
each package contains real-world preconditions that cannot be self-confirmed.
W16 must supply actual provider/authorization/result records before those gates
can be accepted.

Config validation proves structure and role references only. It does not prove
scientific validity, regulatory applicability, provider availability, legal
rights or real-world execution.
