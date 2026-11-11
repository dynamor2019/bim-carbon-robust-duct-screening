# BIM-driven Automated Multi-scenario Screening for Carbon-robust Duct Network Design

Public code and derived results for the manuscript *BIM-driven Automated Multi-scenario Screening for Carbon-robust Duct Network Design* (Zhang Min and Li Xiaoliang).

The calculation enumerates 27 route–section candidates for one 158-terminal exhaust subsystem from the Nordic BIM4LCA office model and scores 405 demand and grid-carbon cells.

## What is in this repository

- `code/`: the source-anchored hydraulic and carbon model used for the recorded run.
- `data/records.csv`: all 405 cells, without the per-component arrays.
- `data/candidate_designs.json`: the 27 stored geometries.
- `data/selected_d1_components.json`: component velocities for the two selected candidates at nominal demand.
- `data/selections.json` and `data/model_assumptions.json`: the recorded decision and the stated assumptions.
- `manuscript/`: current manuscript and figures.

## What is not in this repository

The original IFC file is not included. Redistribution rights for that source file were not granted with the Nordic BIM4LCA package used here.

The full result file `source-network-results.json` is 146.7 MB because every cell stores a component array. GitHub rejects files larger than 100 MB. Its SHA256 is `b626d640c9bed9cd45a51a77262e57097abf2906d79d90d756f6ab6cb3f73c01`. The CSV above is extracted from that file and keeps every cell's status, carbon and null objectives. Failed and unresolved cells are not dropped.

## Result used in the manuscript

- Nominal selection: `t0.01_hop_larger`, 26,388 kgCO2e at nominal demand.
- Minimax and minimax-regret selection: `t0.02_resistance_larger`.
- Cells: 405. Conditional passes, velocity failures and unresolved transitional-flow cells are in `records.csv`.
- `field_validation` is false. These are conditional model calculations, not measured annual emissions.

## License

Code in `code/` is released under the MIT License. The manuscript text and the derived tables are released under CC BY 4.0. Neither license covers the original Nordic BIM4LCA IFC model.
