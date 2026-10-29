# Sample documents

Six documents from Blue Defence, a fictional Singapore defence company with a coastal test facility
(Kestrel Point) and an electric unmanned surface vessel (Sentinel-7). Every document carries a
"fictional sample" banner. [`../scripts/build-sample-docs.py`](../scripts/build-sample-docs.py) writes
them all from the content in that script; [`../answer-key.yaml`](../answer-key.yaml) holds the
questions they answer.

```bash
scripts/build-sample-docs.py        # rebuild this folder
```

## blue-defence-knowledge-base/

Upload this folder in Lab 1. Each file exercises one part of OpenRAG ingestion.

| File | Format | Content | What it shows |
|---|---|---|---|
| `policies/security-clearance-policy-2026.docx` | Word | Revision 2 (1 July 2026): SECRET clearance valid 5 years, security incidents reported within 24 hours, overseas travel declared on form SEC-T3 | The current revision of a policy |
| `archive/security-clearance-policy-2024.docx` | Word | Revision 1 (1 January 2024): SECRET clearance valid 7 years, security incidents reported within 72 hours | A superseded revision that still answers the same questions |
| `engineering/sentinel-7-maintenance-manual.pdf` | PDF, 2 pages | Maintenance intervals, torques (pod mounting bolts 85 N·m), fault codes (E-104 overtemperature) | A table in a PDF is kept as a table, so a value is read from the right row |
| `reports/project-status-q3-2026.pptx` | PowerPoint | HALCYON amber (battery modules from Volta Marine Energy late), LANTERN go-live 15 January 2027, ORCHID red | A file type the 2.4.x ingestion page does not list |
| `registers/approved-suppliers.csv` | CSV | Eight suppliers with contract numbers and expiry dates (Volta Marine Energy, 2027-06-30) | Tabular data; joins with the status deck |

## scanned/

| File | Format | Content | What it shows |
|---|---|---|---|
| `site-inspection-memo-2026-08-14.pdf` | PDF, one page image, no text layer | Inspection INS-2026-031 at Kestrel Point: replace the Hangar 2 fire extinguishers by 31 August 2026 | Ingestion fails with OCR off and succeeds with OCR on |
