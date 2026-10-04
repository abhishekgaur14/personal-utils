# Source tree guidance

- Production code belongs under `pdf_tools/` in this `src/` tree.
- Keep imports and module initialization side-effect free: do not read local documents, start processes, or access the network at import time.
- Keep CLI presentation concerns out of core operations so operations remain reusable and directly testable.
