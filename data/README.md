# data/ — Agricultural knowledge base

## Layout

```
data/
├── raw/          # Source documents as downloaded (PDF/HTML/TXT). Gitignored.
│   └── sources.jsonl   # Provenance registry — COMMITTED (see below)
├── processed/    # Derived artifacts: cleaned text, chunks, FAISS index. Gitignored.
└── README.md     # This file — committed.
```

## Provenance policy (required by project spec)

Every document placed in `data/raw/` **must** have one entry in
`data/raw/sources.jsonl` with these fields:

| Field | Description |
|---|---|
| `doc_id` | Stable identifier (e.g. `uas_dharwad_wheat_package_2024`) |
| `title` | Document title as published |
| `organization` | Issuing organization (e.g. "ICAR — Krishi Vigyan Kendra") |
| `url` | Source URL (or `local_scan` + description if from a scan) |
| `published_date` | Publication date if available, else `null` |
| `retrieved_date` | Date we downloaded it (ISO 8601) |
| `license_notes` | License / permitted-use notes, or `unknown — academic fair use` |
| `language` | Language of the document (e.g. `en`, `hi`, `kn`) |
| `topics` | e.g. `["irrigation", "fertilizer", "wheat"]` |

Rules:

- **Only credible sources**: ICAR institutes, KVKs, state agriculture
  universities, state/central agriculture departments, and similar.
- **Never fabricate** a document, URL, or recommendation. If a URL cannot be
  retrieved, record the failure; do not invent a replacement.
- **Respect copyright**: store documents locally for the academic evaluation;
  do not redistribute copyrighted PDFs in the public GitHub repo (raw files
  are gitignored; the provenance registry is committed).

## Source candidates (STATUS: planned — NOT yet downloaded or verified)

> Every URL below must be verified live at download time. Unreachable or
> unsuitable sources get removed here with a note in the commit message.

| Candidate | Organization | Topics | Why |
|---|---|---|---|
| KVK / ICAR crop production advisories | ICAR (icar.gov.in, kvk.icar.gov.in) | crops, irrigation, fertilizer | National network, authoritative |
| Package of Practices / crop guides | State agriculture universities (e.g. UAS Dharwad/Bengaluru, TNAU) | crop management | University-published, region-specific accuracy |
| Crop husbandry advisories | Karnataka Agriculture Department (krishiber Karnataka / agri.kar.nic.in) | regional practices | State official, matches Kannada audience |
| Scheme + advisory info | Ministry of Agriculture / PIB (agricoop.nic.in, pib.gov.in) | policy, general guidance | Government of India |
| Soil-health based fertilizer guidance | ICAR-ISSR / state soil health boards | fertilizer | Fertilizer dose credibility |

Target: enough documents to support 30–50 evaluation cases across crop
management, irrigation, and fertilizer topics in all three languages.
