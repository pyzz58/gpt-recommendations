# CRA-W07 dependency and licence record

Date: 2026-10-31. Engineering record only.

| Component | Locked version | Licence | Role |
| --- | --- | --- | --- |
| openpyxl | 3.1.5 | MIT | Formula/cache-aware XLSX parsing and synthetic fixture generation |
| AG Grid Community (`ag-grid-community`) | 36.2.0 | MIT | Import preview grid sorting, filtering and virtual scrolling |
| AG Grid React (`ag-grid-react`) | 36.2.0 | MIT | React adapter for Community grid only |
| React | 19.3.1 | MIT | Existing application frontend |
| PostgreSQL | 18.6 | PostgreSQL License | Real snapshot/mapping/test database |

`uv.lock` and `web/package-lock.json` pin the installed versions. Only the MIT
AG Grid Community and React packages are installed; no Enterprise package,
Excel Export, charting or other commercially licensed module is included.

The import grid uses AG Grid's explicit `legacy` CSS theme with its matching
Community CSS file. Sorting/filtering only changes the browser view; persisted
rows, mappings and snapshots remain server-authoritative.

No OCR/model package, model credential, paid service or real clinical file was
added for W07.
