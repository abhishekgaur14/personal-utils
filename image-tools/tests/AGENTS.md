# Image Tools test guidance

- Prefer small generated synthetic images for operation tests.
- Assert resulting pixel dimensions and relevant pixel properties, not encoded-file byte equality.
- Do not use private files from `test_assets/` as test fixtures.
