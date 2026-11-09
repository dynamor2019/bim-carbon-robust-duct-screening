# Figure support provenance

The two files in this directory are byte-for-byte copies of tracked files from the DSH checkout `F:\dsh\scripts`, reused under the checkout's MIT license. No third-party or unknown-license resource was copied.

| File | Source | SHA256 |
|---|---|---|
| `figures4papers_style.py` | `F:\dsh\scripts\figures4papers_style.py` | `d9df5855231b562ce78657625ebef87e84f599706f3113b2fbe03ca8ab70068d` |
| `scientific_figure_guard.py` | `F:\dsh\scripts\scientific_figure_guard.py` | `79afc8a110da5fdaba330a4393fd196295f4c8d0a1240947dd0c5bf5c1617f2a` |
| `LICENSE` | `F:\dsh\LICENSE` | `0e0f670a824772ec9ecd1fa8a8acfb63280fc1a372cae9c5f7c215e0413363` |

`LICENSE` is the unmodified MIT text, copyright (c) 2026 dynamor2019. The source files had no separate restriction notice in the checked checkout. The project figure scripts import these helpers from this project-relative directory; they no longer require `F:\dsh\scripts`.

Figure rendering additionally requires the versions recorded in `code/requirements.txt`: Python 3.11+, Matplotlib 3.10.7, Pillow 12.3.0 and NumPy 2.3.5. This support directory does not imply that the complete paper package is externally replicated or that visual review is author approval.

## Portability check

On 2026-10-05, both canonical figure scripts were rendered in a fresh temporary directory containing only the scripts, project-relative helper copies, current evidence JSON and frozen result JSON. F1 and F2 technical QA returned PASS. The isolated PNG SHA256 values were byte-identical to the canonical PNGs (`df0a9dd7...` and `c60779ce...`). This was a local isolated-directory verification; no canonical image or result was overwritten. The check did not repeat supervisor visual review or establish independent peer review.
