# BIM-driven Automated Multi-scenario Screening for Carbon-robust Duct Network Design

Zhang Min¹, Li Xiaoliang¹

¹ School of Civil Engineering, North China Institute of Aerospace Engineering, Langfang 065000, China

\* Corresponding author: lixiaol@nciae.edu.cn

---

## Abstract

We compare 27 route–section candidates for one exhaust subsystem in the Nordic BIM4LCA office model. The subsystem has 158 terminals and a recorded nominal demand of 3.815 m³/s. The extraction did not include authenticated port-to-port links, so contact was inferred from bounding-box gaps of 0.005, 0.01 and 0.02 m. Paths are weighted by hop count, length, or a resistance proxy. Circular sections are either kept as drawn, replaced by the smallest catalogue diameter that keeps nominal velocity at or below 7 m/s, or replaced by the next eligible diameter inside 1.5 times the source hydraulic diameter. Rectangular sections stay at their source area.

Each candidate is calculated at design demands of 0.8, 1.0 and 1.2 times nominal, and at twelve held-out pairs of demand (0.9, 1.1, 1.3, 1.4) and grid intensity (0.05, 0.2 and 0.4 kgCO₂e/kWh). Of the 405 cells, 128 pass, 241 exceed 7 m/s at a non-terminal component, and 36 stop because 2300 ≤ Re < 4000 and no friction factor is assigned. Among the 16 candidates that pass at nominal demand, the lowest carbon is t0.01_hop_larger, at 26,388 kgCO₂e. It passes 3 of 12 held-out cells. The four candidates that pass all three design demands all use the larger sizing rule (4/9 in that rule; 0/9 in each of the other two). Inside that set, nominal, minimax and minimax-regret selection return t0.02_resistance_larger, at 26,941 kgCO₂e under the nominal scenario. The difference is 552 kgCO₂e (2.09%). That candidate passes all 12 held-out cells. The two selected candidates also differ in contact tolerance and path rule, so the difference is not an isolated diameter effect. Carbon covers duct-shell production (A1–A3) and ideal-fan electricity (B6) over 20 years. It is not a measured annual total.

**Keywords:** Building Information Modeling; Duct network design; Multi-scenario optimization; Life-cycle carbon assessment; Demand uncertainty; Automated screening

## Introduction

Duct routes in this study are taken from an IFC model, not drawn by hand for the comparison (buildingSMART International, 2023). The same model family is already used for clash inspection (Autodesk, 2026), for translating a systems model to EnergyPlus (Autodesk, 2024), and for inferring missing semantic links from geometry (Lilis et al., 2025). Calixto et al. (2026) go further and generate duct layouts with constraint programming and mixed-integer programming in MiniZinc. Those tools answer different questions. Here the question is narrower: given one extracted exhaust subsystem, what carbon difference is recorded when the same terminal loads are served by 27 enumerated route–section candidates, some of which fail when demand moves away from the nominal value.

### Research gap and motivation

Chen et al. (2022) route ducts on a graph and test six floor plans, with pressure balance, obstacles, resistance and material cost in the stated objective. Calixto et al. (2026) generate coordinated layouts in MiniZinc under spatial, flow and clearance constraints. Both treat terminal demand as known. Roberts et al. (2025) show that MEP carbon is often omitted from building totals. They do not rescore duct sections when demand is scaled. The comparison below uses one extracted network and 27 candidates. It counts how many still pass a 7 m/s screen after demand is scaled, and it records the carbon difference between the nominal pick and the pick that must pass every design demand.

### The exhaust subsystem

The case is the 302PK01 exhaust subsystem in the Nordic BIM4LCA office model: 158 terminals, 3.815 m³/s nominal. Contact gaps of 0.005, 0.01 and 0.02 m, three path weights and three sizing rules give 27 candidates. Design demands are 0.8, 1.0 and 1.2 times nominal. Held-out cells use demands of 0.9, 1.1, 1.3 and 1.4 with grid intensities of 0.05, 0.2 and 0.4 kgCO₂e/kWh. A cell passes only if no visited segment is in transitional flow and every non-terminal velocity is at most 7 m/s. Passing cells report duct-shell production (A1–A3) and ideal-fan electricity (B6) over 20 years.

### Scope and limitations

The study is based on a real BIM project from the Nordic BIM4LCA dataset but requires several assumptions. Native IFC port-to-port connectivity was unavailable, so radial contact relationships were inferred from bounding-box proximity. Five components lacked positive source dimensions in the archived extraction. Their interface sizes were read from the same office-concrete model and substituted: a rectangular 800 mm × 1400 mm tee (IFC 611084), a rectangular 1400 mm × 800 mm cap (IFC 611151), two Ø200 mm terminals (IFC 3680435 and 3680544), and one Ø250 mm terminal (IFC 3681026). Rectangular sections enter as hydraulic diameters, not as circular nominal diameters. This substitution left the 405-cell status counts and both selected designs unchanged; carbon values moved only in 23 cells of two non-selected length-based candidates. The ideal-pressure boundary, 60% fan efficiency, 2500 annual operating hours, absolute roughness, wall thickness, and the fitting class coefficient (IfcDuctFitting: 1.0, used only where source velocity is absent) remain experience-based assumptions, not field measurements. Recorded design pressure and velocity are used for all 158 terminals, 74 dampers, and 12 silencers; the corresponding class coefficients are fallbacks and are not applied to those components. These assumptions are disclosed in §3.6 Model boundaries and parameter assumptions, and their impact is explored in §4.5 Sensitivity to parameter assumptions. Transitional flow (2300 ≤ Re < 4000) is not resolved, leaving 36 cells with unknown feasibility status. The same code can be pointed at another extracted network only after that network's contacts, loads and catalogue are substituted. The 4/9 count is not a rule for another building, and this run is not a field-validated carbon estimate.

## Literature review

### Duct routing and section assignment

Published routing work already couples layout and section, but it does so for a stated demand. Chen et al. (2022) generate graph-based HVAC duct routes that account for pressure balance, obstacles, air resistance and construction cost, and they test the method on six layouts. Calixto et al. (2026) generate early-stage duct layouts in MiniZinc with constraint programming and mixed-integer programming, under spatial, flow-capacity and clearance constraints. Jorens et al. (2018) start from a predetermined layout and use a multi-start search aimed at material cost. Li et al. (2025) report automated HVAC piping layout from floor plans. Only the bibliographic record was available here, so no solver or balancing rule is attributed to that paper. None of those four methods is reimplemented. This paper therefore does not claim a better router. It takes one extracted exhaust network, builds 27 candidates from three contact gaps, three path weights and three sizing rules, and scores them when demand is scaled.

The geometry step is also narrower than existing BIM-to-analysis tools. Lilis et al. (2025) infer missing semantic links, including HVAC topology, from geometric relations among IFC objects. The contact graph here is a radial proximity screen at 0.005, 0.01 and 0.02 m. That tool is not run. Yang et al. (2019) review mixed and non-uniform room air distribution. Their subject is the room, not the duct section that supplies it.

### What is counted as duct carbon

Roberts et al. (2025) note that MEP impacts are often omitted from building life-cycle assessments and that reporting practice affects comparability. That is why the boundary is stated rather than imported. Rabani et al. (2025) find that ventilation components, particularly ductwork, account for a large share of embodied greenhouse-gas emissions in their educational and office cases, and that replacement over the service life adds further emissions. Their boundary includes replacement. The screen here uses a 20-year horizon and an assumed 30-year duct life, so the replacement count is zero. The two totals are not interchangeable. Shindo et al. (2023) compare an all-air system with a radiant system for a Danish office and report 10.1 and 9.0 kgCO₂e/m²/year. That is a whole-system comparison, not a 27-candidate duct screen.

Kiss and Szalay (2020) find, for one Hungarian apartment building, that minimizing embodied impact alone or operational impact alone can miss the life-cycle optimum, and that the energy source changes the optimum. Torabi et al. (2025) find that local grid intensity changes which early-design parameters dominate whole-life carbon across seven Canadian cities, with HVAC among the influential systems. Those two results are the reason shell production and fan electricity are reported separately, and the reason the grid factor is varied. Robati et al. (2021) identify the structure, not a duct catalogue, as the main embodied-carbon contributor in an 18-storey Sydney case. Llatas et al. (2022) place life-cycle indicators in IFC and compare structural alternatives. Neither paper supplies the 2.8 kgCO₂e/kg steel factor used here.

Calculated carbon in this case is initial duct-shell production (A1–A3) plus ideal-fan electricity (B6). Fittings, fan manufacture, insulation, supports, installation and end-of-life stages are excluded. Demand and grid factor vary. Efficiency, hours, roughness, thickness and the production factor were fixed in the 405-cell run. The later sensitivity arm perturbs those inputs inside declared ranges. It does not establish stability outside those ranges.

### Why one nominal carbon total is not enough

Liu et al. (2023) review renovation incentives under China's 2060 carbon-neutrality target. Hu et al. (2025) treat HVAC and refrigeration as the largest in-building energy use and measure an ice-storage system in a high-rise office in southern China. Al Sayed et al. (2024) review reinforcement-learning control of HVAC and describe HVAC as a major operational CO₂ source because of its energy demand. Mustafa et al. (2026) compare setpoint changes with a heat-pump retrofit in a UK non-domestic space: operational changes had lower cumulative energy demand and particulate-matter formation, but slightly higher global-warming potential while gas remained in use. The common point is that operational energy can dominate the carbon result, and that the dominant term depends on the boundary. A duct screen that reports only one nominal total would hide that dependence. The held-out cells therefore scale demand and grid intensity after the design choice is fixed.

The same dependence appears when embodied and operational terms are separated. Amiri et al. (2021) note that LEED research has concentrated on operation, and they evaluate pre-use embodied emissions for a building in Iceland. Koezjakov et al. (2018) report 52–106 MJ/(m²·a) of embodied energy for Dutch dwellings as heat demand falls, excluding technical installations. Tavares and Freire (2022) show that higher operational energy can offset the lower embodied impact of a lightweight house when climate and the electricity mix change. Zong et al. (2026) find that a time-varying electricity mix moves operational heating emissions more than embodied emissions. Walker et al. (2022) show that five modeling choices, including the analysis period and the decarbonization path, change a Swiss retrofit comparison. Zhang et al. (2022) use BIM to report life-cycle carbon and cost together because lowering one can raise the other. These papers do not validate the 2.8 kgCO₂e/kg factor or the three grid scenarios. They are why a single summed carbon number is not the result reported here.

### Coordination tools and the limit of this screen

Kubicki et al. (2019) treat 3D coordination as comparison of discipline models in order to reduce conflicts. Xu et al. (2025) connect MEP–structural clash coordination with path planning and augmented-reality navigation. Ailem and Boton (2026) filter clash relevance from BIM metadata. Navisworks Clash Detective identifies, inspects and reports 3D clashes (Autodesk, 2026). The Revit systems-analysis workflow builds an analytical model and translates it to EnergyPlus (Autodesk, 2024). Those tools answer coordination and energy-model questions. This calculation does not run them, and it does not infer a limit of their capability from the help pages.

The executed comparison is nominal, minimax and minimax-regret selection on a fixed candidate set, with three design demands and twelve held-out cells. Native port links, a clash test against the building, a fan curve and a measured operating schedule are outside that calculation.

## Methods



### Source data and topology inference

Geometric properties, design section dimensions, and terminal service demands for the 302PK01 exhaust subsystem were extracted from the Industry Foundation Classes (IFC) model authored by the professional design team within the Nordic BIM4LCA research package. The source dataset comprises 158 terminal devices with a combined nominal design demand of 3.815 m³/s, world coordinates, rectangular or circular section records for duct segments, and component class annotations for fittings, dampers, silencers, and terminals. The extraction has no authenticated port-to-port links, so contact is a bounding-box gap of 0.005, 0.01 or 0.02 m inside the declared system. Nobody inspected those contacts on site. The screen is conditional on that guess.

Five components lacked positive source dimension records in the archived extraction. Their interface sizes were read from the same office-concrete model and substituted: IFC 611084 is an 800 mm × 1400 mm rectangular tee, IFC 611151 is a 1400 mm × 800 mm rectangular cap, IFC 3680435 and 3680544 are Ø200 mm terminals, and IFC 3681026 is a Ø250 mm terminal. Rectangular sections are converted to hydraulic diameter by 4A/P. Re-evaluation left the 405-cell status counts—128 feasible, 241 velocity failures, and 36 unresolved transitional-flow cells—and both selected designs unchanged. Carbon values changed in 23 cells belonging only to the non-selected candidates t0.005_length_larger and t0.01_length_larger. This check compares the same conditional model with verified interface sizes; it is not field validation or engineering certification. The archived supplementary register still records the historical 0.16 m placeholders. For 155 other terminals, the hydraulic diameter remains the maximum mesh-face reference rather than the Revit duct-connection size: 133 faces of 160 mm against Ø125 connections, 12 of 180 mm against Ø160, and 10 of 195 mm against Ø160. Those references were not substituted, because the face and the connection are different geometric objects. One transition fitting retains an 800 mm geometric-port reference matching its circular port; its rectangular 800 mm × 1400 mm port is not represented by that single diameter. The highest-flow duct segment in the source design (IFC ID 3307429) was designated as an ideal controllable pressure boundary for conditional network calculations, not as a verified fan identity or certified device capacity. The catalogue heuristics likewise define this finite numerical comparison only.



### Hydraulic and carbon calculation model

The hydraulic model enforces flow continuity at every junction and computes pressure losses through Darcy-Weisbach straight friction with implicit Colebrook roughness (laminar 64/Re for Re < 2300) and velocity-squared local scaling. Local losses at fittings, dampers, silencers, and terminals use source design pressure records where positive velocity and loss values exist; components lacking such records receive uniform class-level coefficients (IfcDuctFitting: 1.0, IfcDamper: 2.0, IfcDuctSilencer: 2.0, IfcAirTerminal: 2.0). The root is modeled as an ideal controllable pressure source meeting critical-path demand at constant 60% efficiency, without authenticated fan curves or stable operating points. Transitional flow (2300 ≤ Re < 4000) remains uncharacterized. Five components that lacked positive archived dimensions now use the model interface sizes listed above. The class coefficients apply only when a positive source pressure and velocity pair is absent. In this subsystem that fallback is used for the fittings, which have pressure drops but no usable velocity. It is not used for the 158 terminals, 74 dampers, or 12 silencers. Independent numerical checks recompute Colebrook friction by fixed-point iteration and compare path sums at a relative and absolute tolerance of 1e-8. The case enumerates the supplied candidates directly and does not call an external mixed-integer solver, so no MIP gap applies.

Carbon accounting includes duct shell initial production (A1–A3) plus ideal-source electricity (B6) over a 20-year horizon. Duct shell mass is derived from source geometry assuming 0.7 mm galvanized steel (7850 kg/m³, 2.8 kgCO₂e/kg). The 2.8 kgCO₂e/kg factor is an experience-based assumption; region/year-specific steel EPD replacement is required before field application. Because the assumed 30-year duct lifetime exceeds the 20-year evaluation horizon, no replacement event occurs within the analyzed period; reported embodied carbon covers initial production only. Operational carbon applies 2500 annual hours at 60% efficiency under scenario-specific grid factors (0.05, 0.2, 0.4 kgCO₂e/kWh). Fitting manufacturing, insulation, supports, installation, and end-of-life stages are excluded.

### Equations and executable mapping

For a circular section, area and wetted perimeter are $A_i=\pi D_i^2/4$ and $P_i=\pi D_i$. For a source rectangular section, $A_i=w_i h_i$, $P_i=2(w_i+h_i)$ and $D_{h,i}=4A_i/P_i$. Source millimetres are converted to metres. The five previously missing sections use the model interface sizes: hydraulic diameters of the 800 mm × 1400 mm and 1400 mm × 800 mm rectangles, and circular diameters of 200 mm, 200 mm, and 250 mm. The area used in continuity and velocity remains the rectangular area for rectangular components, not the area of a circle with the same hydraulic diameter. 

Continuity and velocity are

$Q_i(s)=q_i(s)+\sum_{j\in children(i)}Q_j(s),\qquad v_i(s)=Q_i(s)/A_i.$

Here $q_i$ is terminal demand, zero at other nodes; scenario demand multiplies source terminal loads. $Q$ is in cubic metres per second, $A$ in square metres and $v$ in metres per second. Each node has one parent; this is a prescribed-load radial calculation, not a fan-network operating-point or branch-balancing solve.

Straight-segment loss is

$Re_i=v_iD_{h,i}/\nu,\qquad \Delta p_i=f_i(L_i/D_{h,i})\rho_a v_i^2/2.$

For $Re<2300$, $f=64/Re$. For $Re\geq4000$, the code solves the Colebrook equation by 60 bisections on $y=1/\sqrt f$ between 1 and 30:

$y+2\log_{10}\left(\epsilon/(3.7D_h)+2.51y/Re\right)=0.$

For $2300\leq Re<4000$ no friction result is imputed. A transitional node yields an unresolved cell with null objective before the final velocity-screen check; an unresolved cell is therefore not proof that every other component passes velocity. $\nu$ is in square metres per second, $\epsilon,D_h,L$ in metres, $\rho_a$ in kilograms per cubic metre and losses in pascals.

If a positive source loss and a source velocity exist,

$\Delta p_i=\Delta p_{src,i}(v_i/v_{src,i})^2;$

otherwise $\Delta p_i=K_{class}\rho_a v_i^2/2$ with disclosed class-level assumptions. Neither relation is a manufacturer's fitting curve. Critical-path pressure and ideal annual electricity are

$p_{req}(s)=\max_{t\in terminals}\sum_{i\in path(root,t)}\Delta p_i(s),\qquad E_{annual}(s)=Q_{root}(s)p_{req}(s)h_{annual}/(1000\eta).$

The factor 1000 converts watts times hours into kilowatt-hours. The ideal boundary supplies this pressure at fixed assumed efficiency $\eta$; no actual fan operating point or balancing loss is verified.

Only traversed duct segments contribute shell mass; component source shape or candidate circular shape determines perimeter:

$M=\sum_{i\in duct\ segments} P_i t_w L_i\rho_{steel},\quad N_{rep}=\lceil T/L_{life}\rceil-1,\quad F(c,s)=M e_{prod}(1+N_{rep})+E_{annual}(c,s)Tg_s.$

Mass is in kilograms, wall thickness and lengths in metres, production factor in kgCO2e/kg, grid factor in kgCO2e/kWh and $T,L_{life}$ in years. Here $T=20$, $L_{life}=30$ and $N_{rep}=0$. The legacy output field duct_A1_A3_B4_kgco2e therefore contains initial production only in this run. Fitting manufacturing and other excluded stages are not inserted into this objective.

A cell has a recorded feasible objective only when no visited segment returns transitional loss and every non-terminal component satisfies $v_i\leq7$ m/s. Otherwise its objective is null, with the recorded reason preserved. This status is a conditional calculation screen, never engineering certification. The independently implemented arithmetic audit and software tests check these recorded calculations; they do not verify the physical approximations or missing source permissions.

For a rectangular section, friction uses the hydraulic diameter, but flow and velocity use the rectangular area. That diameter is not a second flow, and it is not a measured non-circular correction.

### Finite candidate generation

The 27 supplied candidates combine three contact tolerances, three radial path rules and three sizing modes. 

#### Routing algorithm implementation

For each terminal device, the routing algorithm constructs a path from the designated root node (IFC ID 3307429) to the terminal using NetworkX shortest-path implementation, which applies Dijkstra's algorithm for positive edge weights. Three edge-weight strategies are applied to generate distinct routing candidates:

1. **Hop-count routing:** Unit edge weights (w_ij = 1 for all edges), minimizing the number of intermediate nodes along the path. This strategy favors topologically direct connections regardless of geometric distance or hydraulic resistance.

2. **Length routing:** Geometric edge weights w_ij = max((L_i + L_j)/2, 0.001), where L_i and L_j are the component lengths in metres. This strategy minimizes total path length, approximating material use before section sizing is applied.

3. **Resistance-proxy routing:** Hydraulic-diameter-based weights w_ij = max((L_i/D_i^5 + L_j/D_j^5)/2, 0.001), where D_i and D_j are source hydraulic diameters in metres. This heuristic approximates pressure-loss ordering without performing full Darcy-Weisbach calculations during path selection, favoring large-diameter segments in the routing stage.

The candidate network is constructed as the union of shortest paths from the root to all 158 terminals under the selected weighting scheme. The resulting topology forms a directed tree (arborescence) rooted at the designated source node. Because the source BIM model lacks authenticated native port-to-port connectivity, candidate routes are constrained to edges inferred from bounding-box proximity at the specified tolerance threshold (§3.1 Source data and topology inference). Routes stay on those inferred edges. The code does not move ducts around beams or walls, and it does not run a clash test. A project that already has port-to-port links could use those links in place of the gaps. This run does not.

#### Section sizing strategies

Actual rectangular sections remain at their source area, perimeter and hydraulic diameter in every sizing mode; there is no rectangular-to-circular replacement. The source mode preserves each source section. For non-rectangular components in velocity and larger modes, the ordered circular catalogue is filtered by nominal-load velocity at most 7 m/s and diameter at most 1.5 times the source hydraulic diameter. When exactly one diameter is eligible, both velocity and larger modes assign it (index 0). When two or more are eligible, velocity chooses index 0 and larger chooses index 1. The saved whole-network geometry comparison verifies 27 distinct candidates, including all nine velocity-versus-larger pairs; equality at one component does not imply equality of whole designs. If none is eligible, source dimensions remain and subsequent screening may fail. Length is unchanged when circular perimeter and area are reassigned. The catalogue is not a product-certified size list.



The saved geometries are 27 distinct networks. Equal dimensions on one component do not make two candidates the same.

### Uncertainty representation and decision rules

Let C be the 27 supplied candidates, D = {D0, D1, D2} the three design scenarios, and H the twelve held-out cases. Let f(c,s) denote the carbon objective in kgCO2e only for a model-feasible cell. Failed velocity screens and unresolved transitional-flow cells have null objectives and null regret. They remain in the 405-row ledger; they are never replaced with zeros or finite penalties. The scenario oracle m(s) = min f(c,s) ranges over every candidate feasible in that scenario, not just the candidates eligible for robust selection. Regret is r(c,s) = f(c,s) - m(s) for feasible cells only.

Deterministic selection minimizes f(c,D1) among candidates feasible at D1 (16 eligible). Robust eligibility requires model feasibility in every design scenario (4 eligible). Minimax minimizes max over s in D of f(c,s); minimax-regret minimizes max over s in D of r(c,s). Candidates failing or unresolved in even one required design cell are excluded from robust selection as complete candidates, not retained by dropping unfavorable cells. Exact score ties are resolved by lexicographically smallest candidate ID, as in finite_candidate_decisions.py.




For the recorded feasible set $V_s$, the conditional oracle and regret are $m_s=\min_{c\in V_s}F(c,s)$ and $r(c,s)=F(c,s)-m_s$. With $V_D=\cap_{s\in D}V_s$, the code selects $\arg\min_{c\in V_{D1}}F(c,D1)$, $\arg\min_{c\in V_D}\max_{s\in D}F(c,s)$, or $\arg\min_{c\in V_D}\max_{s\in D}r(c,s)$ for nominal, minimax and conditional minimax-regret respectively. Exact ties use candidate ID order. Unknown candidates are not certified infeasible; these objectives remain conditional on recorded status.

All prose carbon objectives are rounded to the nearest whole kgCO2e; opportunity losses are rounded to one decimal where shown. Supplementary S2 retains the original machine precision. No result is recalculated by this display convention.

### Evaluation protocol and integrity gates

D0–D2 are used for selection. The twelve held-out cells are not. The public CSV keeps all 405 cells, including null objectives. The original IFC is not in the repository.




### Model boundaries and parameter assumptions

Operating hours, grid carbon intensity, steel embodied-carbon factor, fan efficiency, absolute roughness, steel wall thickness, the fitting class coefficient used where source velocity is absent, and the counterfactual diameter catalogue were assigned experience-based nominal values before calculation; these parameters were not measured from installed equipment or field operation. Terminal, damper, and silencer losses use recorded design pressure and velocity. Five components (IFC 611084, 611151, 3680435, 3680544, and 3681026) lacked positive archived dimensions. Their model interface sizes—800 mm × 1400 mm, 1400 mm × 800 mm, Ø200 mm, Ø200 mm, and Ø250 mm—were substituted. The 405-cell status counts and both selected designs were unchanged. Carbon values moved in 23 cells of two non-selected length-based candidates. This substitution is not field verification. The assumed ideal controllable pressure boundary, nominal 60 % efficiency, 2500 annual operating hours, 20-year horizon, and 30-year duct lifetime enabled comparative carbon estimates but do not represent verified fan capacity, stable operating points, or monitored performance of the source-project 302PF01 exhaust unit. Native port topology, manufacturer-qualified fitting pressure characteristics, and a clash-free spatial envelope remain unavailable; the finite radial contact graph was inferred from bounding-box proximity at three tolerance thresholds (0.005 m, 0.01 m, and 0.02 m) rather than authenticated BIM port connectivity, and the 1.5-times source-diameter expansion envelope was not validated against structural or architectural obstacles.


The five interface sizes are model dimensions, not five active burdens in every candidate. IFC 611084 and 611151 are absent from all original candidate paths. IFC 3680435, 3680544 and 3681026 occur in all original candidate paths. Fixed counterfactual designed sizes are not replaced by uncertain source reference sizes. For 155 terminals the hydraulic diameter remains the maximum mesh-face reference rather than the Revit connection size (133 of 160 mm against Ø125, 12 of 180 mm against Ø160, and 10 of 195 mm against Ø160). These were not substituted. One 800 mm × 1400 mm to Ø800 transition retains the 800 mm circular-port reference.

## Results



### Design-split performance and feasibility

At nominal demand and 0.2 kgCO₂e/kWh, t0.01_hop_larger has 26,388 kgCO₂e: 5,188 kgCO₂e from duct-shell production (A1–A3) and 21,200 kgCO₂e from ideal-fan electricity (B6). The minimax-regret selection, t0.02_resistance_larger, has 26,941 kgCO₂e. The difference is 552 kgCO₂e, or 2.1% of the nominal selection.

Those magnitudes use inferred contacts at 0.01 m and 0.02 m, not native ports. IFC 611084 and 611151 are inactive on every original path. The three circular terminals are active. The root is an ideal pressure boundary, not a 302PF01 fan curve. Terminals, dampers and silencers use recorded design losses. Fittings use the class coefficient 1.0 where source velocity is absent. Efficiency is 60%, and annual hours are 2500. A native topology, a fan curve or a product EPD would change the magnitudes and could change the ranking.

At 1.2× demand (4.578 m³/s), t0.01_hop_larger exceeds 7 m/s in two components and has no objective. t0.02_resistance_larger remains feasible at 42,722 kgCO₂e. At 0.8× demand (3.052 m³/s), both are feasible: 16,056 and 16,351 kgCO₂e, a difference of 295 kgCO₂e (1.8%). Passing the velocity screen and reporting a carbon total are different claims. The two selected candidates also differ in contact gap and path rule, so the difference is not an isolated sizing effect.

The deterministic selection fails 9 of the 12 held-out cells, all of them at 1.1×, 1.3× and 1.4× demand. The robust selection is feasible in all 12. At 0.9× demand and 0.2 kgCO₂e/kWh the values are 20,652 and 21,062 kgCO₂e, a difference of 410 kgCO₂e (2.0%). At 1.4× demand and 0.4 kgCO₂e/kWh the deterministic selection is infeasible. The robust selection is 124,251 kgCO₂e, of which 5,211 kgCO₂e is shell production and 119,040 kgCO₂e is ideal-fan electricity. The 1.8–2.1% differences are for these two named candidates. They do not isolate one parameter.

Changing the grid factor from 0.05 to 0.4 kgCO₂e/kWh changes the carbon total and does not change who passes the velocity screen. At 0.9× demand the deterministic selection spans 9,054 to 36,116 kgCO₂e. The robust selection spans 9,174 to 36,912 kgCO₂e. The absolute difference is 119 to 796 kgCO₂e. At 1.1× demand the deterministic selection fails at every grid factor. The robust selection is 12,438, 34,118 and 63,024 kgCO₂e at 0.05, 0.2 and 0.4 kgCO₂e/kWh. t0.01_hop_larger passes the tested 1.0× case and fails the tested 1.1× case. Those two points bracket a status change. They do not locate a threshold, and the 0.8× case still differs by 295 kgCO₂e.

Fig. 1 states the executed evidence chain before the numerical comparisons. Fig. 2 shows the same 81 design cells by candidate and then by sizing mode. All four candidates that pass D0–D2 use the larger sizing mode (4/9). Source sizing passes none of the three design scenarios, and velocity sizing passes none of D2. Contact tolerance does not make this separation: the four feasible candidates are split 2, 1 and 1 across 0.005, 0.01 and 0.02 m. Fig. 3 separates duct-shell carbon from ideal-fan carbon and follows each feasible trajectory through D2. At D1 the screened candidate remains the lowest-carbon member of that four-candidate set, 552 kgCO2e above the nominal selection.

![](../figures/Fig1_screening_workflow.png)

**Fig. 1 | Screening chain and 405-cell counts.** Panel a is the executed calculation: three contact gaps, three path rules and three sizing rules. It is not a free-space layout algorithm. Panel b is the same ledger: 128 passes, 241 velocity failures and 36 unresolved cells.

![](../figures/Fig2_design_eligibility.png)

**Fig. 2 | Design-cell status.** Panel a shows 81 cells (27 candidates × D0, D1, D2). Blue passes, red fails the 7 m/s screen, and grey is unresolved transitional flow. Orange is t0.01_hop_larger. Blue is t0.02_resistance_larger. Panel b groups the same cells by sizing rule. Candidates that pass all three demands: source 0/9, velocity 0/9, larger 4/9.

![](../figures/Fig3_screening_premium.png)

**Fig. 3 | Carbon split.** Panel a separates shell production and ideal-fan electricity for the 16 candidates with a D1 objective. The other 11 are omitted, not plotted as zero. Panel b follows the four candidates that pass D0–D2. At D1 the difference is 552.23 kgCO₂e: 22.65 shell and 529.57 ideal-fan electricity.

### Complete status accounting

Table 1. Counts of candidate-scenario cells across 27 candidates per scenario. All numeric columns are counts, not physical quantities. Failed counts cells rejected by the velocity screen. Unresolved denotes an undefined transitional-flow calculation (2300 <= Reynolds number < 4000), not an established velocity failure.

| Scenario | Feasible | Failed | Unresolved | Total |
|---|---:|---:|---:|---:|
| D0 | 18 | 0 | 9 | 27 |
| D1 | 16 | 11 | 0 | 27 |
| H0_0 | 16 | 2 | 9 | 27 |
| H0_1 | 16 | 2 | 9 | 27 |
| H0_2 | 16 | 2 | 9 | 27 |
| D2 | 4 | 23 | 0 | 27 |
| H1_0 | 6 | 21 | 0 | 27 |
| H1_1 | 6 | 21 | 0 | 27 |
| H1_2 | 6 | 21 | 0 | 27 |
| H2_0 | 4 | 23 | 0 | 27 |
| H2_1 | 4 | 23 | 0 | 27 |
| H2_2 | 4 | 23 | 0 | 27 |
| H3_0 | 4 | 23 | 0 | 27 |
| H3_1 | 4 | 23 | 0 | 27 |
| H3_2 | 4 | 23 | 0 | 27 |

All 405 candidate-scenario cells, status reasons, null outcomes, carbon decompositions, scenario oracles and regret values are supplied in supplementary/S2-all-outcomes.csv. Each scenario has 27 cells. S3-scenario-status.csv supplies the denominators; S4-candidate-map.csv identifies all route-sizing combinations. These are calculated model statuses, not engineering failures or field observations. Fig. 4 retains every candidate at each distinct demand multiplier. Hydraulic status does not change across the three grid factors, so the twelve held-out cells are three accounting repeats of four demand stresses.

Fig. 4 keeps the candidate-level status and adds the carbon trajectory only where an objective exists. Grey tick labels are held out of selection. The nominal row fails from 1.1× upward, while the screened row remains feasible through 1.4×. Three other candidates also remain feasible through 1.4×, and their carbon rises faster than the screened trajectory. Fig. 3 shows why they are not the D1 selection.

![](../figures/Fig4_demand_status.png)

**Fig. 4 | Status by demand.** H0–H3 are demands 0.9, 1.1, 1.3 and 1.4. Suffixes 0, 1 and 2 are grid factors 0.05, 0.2 and 0.4 kgCO₂e/kWh. Panel a colours pass, velocity failure and unresolved flow. Panel b plots carbon only where an objective exists. The steep trajectory is t0.005_length_larger.



### Held-out scenario evaluation

The maximum held-out conditional regret is 796.4 kgCO2e at H0_2 (demand 0.9, grid 0.4); Table 2 lists all twelve cells. The H0_0 and H0_1 values are not maxima.




Fig. 5 locates the velocity margin inside the two selected networks at nominal demand. The nominal maximum is 6.954 m/s across 840 non-terminal components, immediately below the 7 m/s screen; the screened maximum is 4.857 m/s across 898 components. The medians are close, so the difference is in the extreme tail rather than in a typical component. Fig. 6 then shows that the summed loss inventory is dominated by the assumed missing local-loss term, and that registered input substitutions move D1 carbon without changing the screened label.

![](../figures/Fig5_component_margin.png)

**Fig. 5 | Velocity at nominal demand.** Orange is t0.01_hop_larger. Blue is t0.02_resistance_larger. Terminals are excluded. Marker area is the count of components at that flow and velocity. The dashed line is 7 m/s. Maxima are 6.954 and 4.857 m/s.

![](../figures/Fig6_input_sensitivity.png)

**Fig. 6 | Losses and input substitutions.** Panel a sums non-terminal pressure loss. It is not the fan pressure. Panel b is D1 carbon for t0.02_resistance_larger. The fixed arm (n=88) spans 17.83–38.69 tCO₂e. The regenerated arm (n=76) spans 18.89–100.22 tCO₂e. The dashed line is the unperturbed 26.94 tCO₂e. The selected label does not change in either arm.

### Robustness price and regret analysis


The executed replacement count is ceil(20/30)-1 = 0. This was checked against the literal source_network_model.py calculation and all 128 recorded feasible cells: duct_A1_A3_B4_kgco2e equals duct_shell_mass_kg multiplied by the assumed 2.8 kgCO2e/kg production factor, with no B4 increment. The legacy field name is retained in the artifact; it does not imply an executed replacement event. This is numerical accounting verification, not validation of the assumed lifetime or production factor.

Table 2 distinguishes scenario-specific conditional regret from the maximum over the twelve held-out cases. H0–H3 are demand multipliers 0.9, 1.1, 1.3 and 1.4; suffixes 0, 1 and 2 are grid factors 0.05, 0.2 and 0.4 kgCO2e/kWh. Selected, oracle and regret are kgCO2e. Unknown is the count of unresolved cells. Values are computed from the immutable result records and their same-scenario recorded-feasible-cell oracles; no rounded objectives are subtracted to obtain regret. The 0.9 demand / 0.2 grid value is a different cell, not an alternative estimate of the held-out maximum.

| Case | Selected | Oracle | Regret | Unknown |
|---|---:|---:|---:|---:|
| H0_0 | 9173.60 | 9054.23 | 119.38 | 9 |
| H0_1 | 21061.57 | 20652.02 | 409.55 | 9 |
| H0_2 | 36912.19 | 36115.75 | **796.45** | 9 |
| H1_0 | 12437.61 | 12437.61 | 0.00 | 0 |
| H1_1 | 34117.61 | 34117.61 | 0.00 | 0 |
| H1_2 | 63024.28 | 63024.28 | 0.00 | 0 |
| H2_0 | 17129.10 | 17129.10 | 0.00 | 0 |
| H2_1 | 52883.55 | 52883.55 | 0.00 | 0 |
| H2_2 | 100556.16 | 100556.16 | 0.00 | 0 |
| H3_0 | 20090.96 | 20090.96 | 0.00 | 0 |
| H3_1 | 64731.01 | 64731.01 | 0.00 | 0 |
| H3_2 | 124251.08 | 124251.08 | 0.00 | 0 |



These quantities are not interchangeable. The value 552.2 kgCO2e is the maximum conditional regret over D0-D2, and 796.4 kgCO2e is the maximum conditional regret over H0-H3, attained at H0_2 (demand 0.9, grid 0.4). In contrast, 42,722 kgCO2e and 124,251 kgCO2e are the selected candidate's maximum absolute carbon objectives over the design and held-out splits, respectively. An absolute objective is not a regret. H0_1 (demand 0.9, grid 0.2) has conditional regret 409.5 kgCO2e; Table 2 lists that cell separately and does not treat it as the held-out maximum. Table 1 shows that the 36 unresolved cells are confined to D0 and the three H0 grid cases.

### Sensitivity to parameter assumptions

An additional exploratory parameter sensitivity analysis was specified after the original case analysis but before its own computations. It evaluates eleven inputs using 22 individual endpoint perturbations, two joint corners and 64 joint Latin-hypercube samples, plus the original nominal point. The five missing dimensions vary independently from 0.12 to 0.20 m. That range stresses the historical 0.16 m placeholders in the archived sensitivity arm. It is not an uncertainty interval for the five interface sizes subsequently read from the model. The separate substitution check did not change the reported status counts or selected designs, and it is not a rerun of this sensitivity experiment. Efficiency varies from 0.5 to 0.7, annual hours from 2000 to 3000, roughness from 0.00005 to 0.00015 m, wall thickness from 0.0005 to 0.001 m, production factor from 2.1 to 3.5 kgCO2e/kg and missing local-loss coefficients by a common multiplier from 0.5 to 1.5. Except for the handbook-informed roughness envelope, these are illustrative stress ranges, not empirical uncertainty intervals. Joint samples supplement individual tests because individual perturbations cannot examine combined input changes.

Sensitivity conclusions use the archived fixed-design and regenerated-family computations reported in the following paragraphs.

In the fixed-design arm, the minimax-regret candidate label changes under hypothetical design-only reselection in 0 of 88 perturbed variants. The original selected candidate has at least one failed or unknown held-out cell in 0 variants. Fixed edges and designed counterfactual sizes are retained; only missing source-sized sections are replaced.

In the regenerated-family arm, hypothetical minimax-regret selection changes label in 0 of 76 variants; the original label has at least one failed or unknown held-out outcome in 0 variants. Routes and sections are regenerated under the historical placeholder perturbations, so an unchanged label does not imply identical geometry and does not describe the later interface-size substitution. These results cannot be substituted for a fixed-design robustness test.

Selection agreement does not imply magnitude agreement. In the fixed-design arm, the original selected candidate's D1 carbon objective ranges from 17831.74 to 38692.52 kgCO2e, and its maximum held-out recorded-feasible-cell conditional regret ranges from 0.00 to 1231.66 kgCO2e. IFC 611084 and 611151 are inactive in all 27 original paths, so their zero fixed-arm effect reflects exclusion, not a validated missing dimension. The other three missing source-sized inputs are tested separately; designed counterfactual sections remain fixed in the first arm.

In the regenerated-family arm, the original selected label's D1 carbon objective ranges from 18891.43 to 100223.41 kgCO2e, and its maximum held-out recorded-feasible-cell conditional regret ranges from 0.00 to 1197.23 kgCO2e. Label agreement therefore does not establish stable carbon magnitudes; this arm also changes the geometry generated under the substituted source-reference inputs.

| Arm | Variants | Label changes | Failures |
|---|---:|---:|---:|
| Fixed design | 88 | 0 | 0 |
| Regenerated family | 76 | 0 | 0 |

Table 3. Added exploratory input screening. The three numeric columns are counts. Failures counts variants whose original selected label has at least one held-out failure or unknown cell. The fixed-arm count excludes the nominal baseline: 89 total minus one nominal equals 88 perturbed variants (22 individual endpoints, two corners and 64 joint samples). The regenerated arm is executed only when a missing source-reference diameter changes: ten individual dimension endpoints, two corners and 64 joint samples give 76 variants; it does not represent exclusion of failed outcomes. These are declared stress cases, not a probability sample of installations. All candidate/scenario cells and null outcomes are retained in the supplementary sensitivity files.

For every perturbation, D0-D2 determine hypothetical selection and H0-H3 remain evaluation only. Unknown pressure states are not imputed. These bounded observations do not certify stability over the continuous parameter space, validate inferred topology or establish source-specific fan behavior. Measured inputs and independent physical validation remain necessary for engineering recommendations.

### Within-set policy comparison and unexecuted baselines

No sequential route-then-size arm was run. The comparison is inside the 27 candidates. Nominal selection gives t0.01_hop_larger at 26,388 kgCO₂e. Minimax regret, using only D0–D2, gives t0.02_resistance_larger. The design-stage regret is 552 kgCO₂e, or 2.1%, and it was computed before the held-out cells were read. That candidate is feasible in all 12 held-out cells.

A same-eligibility diagnostic is obtained from the existing records, without adding candidates or rerunning experiments. Nominal selection over the 16 D1-feasible candidates chooses t0.01_hop_larger. Restricting nominal selection to the four candidates feasible in all three design scenarios instead chooses t0.02_resistance_larger, the same candidate as minimax and minimax regret. The observed policy divergence therefore includes a change in admissible designs; these data do not identify an incremental benefit of minimax regret over nominal minimization with the same multi-scenario feasibility requirement.

Among 27 candidates, exactly four remain feasible across all three design scenarios (the intersection of D0, D1 and D2 feasible sets). Table 4 lists this complete set. D1 objective and design regret are kgCO2e; regret is the maximum conditional design regret. No additional eligible candidates are omitted.

---------------------------- ---------- ----------
Candidate                    D1         Regret
---------------------------- ---------- ----------
t0.02_resistance_larger       26940.52     552.23
t0.01_resistance_larger       27682.23    1293.94
t0.005_resistance_larger      27693.83    1305.54
t0.005_length_larger          48877.65   37856.49
---------------------------- ---------- ----------

The nominal premium is 552.23 kgCO2e (2.09%): 22.65 kgCO2e from initial duct-shell production and 529.57 kgCO2e from ideal-fan electricity. This is an accounting decomposition between two named candidates. It does not establish a causal effect of sizing, routing or topology. It describes the cost difference associated with the stricter design-scenario screen in this supplied set.

The twelve held-out cells contain four distinct hydraulic demand conditions, each evaluated at three grid factors. Within each candidate/demand group, hydraulic statuses, component calculations and ideal annual electricity are identical across those grid factors; only carbon accounting changes. Thus the reported 3/12 versus 12/12 statuses correspond to 1/4 versus 4/4 distinct held-out demand conditions, not twelve independent physical tests or a statistical success rate. The held-out cases were not used for candidate selection. The 66,825 added evaluations likewise are deterministic input substitutions, not independent observations of buildings.

## Discussion

The 4/9 versus 0/9 split and the 552 kgCO₂e difference are counts for this candidate list. The two selected candidates differ in contact gap and path rule as well as sizing. Held-out cells were not used to choose them. Another building needs its own contacts, loads and catalogue.

### What was not run

Three comparisons were not run. The extraction has no native port graph, so contact remains a bounding-box gap. There is no fan curve and no measured schedule, so the root stays an ideal pressure boundary. There is no sequential route-then-size arm, so the 27-candidate screen is not a test of joint design against ordinary practice. A clash test, a product EPD and a probability model for occupancy are also absent. Adding them would be a different calculation, not a correction of the 405 cells already recorded.

## Conclusions

On this 158-terminal exhaust subsystem, enumerating 27 candidates and keeping every failed cell changes the selected design. The lowest carbon among candidates that pass at nominal demand is t0.01_hop_larger, at 26,388 kgCO₂e. It fails the 1.2× design demand and passes 3 of 12 held-out cells. Requiring a pass at 0.8×, 1.0× and 1.2× leaves four candidates, all in the larger sizing rule. Nominal, minimax and minimax-regret selection inside that set return t0.02_resistance_larger, at 26,941 kgCO₂e. The difference is 552 kgCO₂e (2.09%), of which 22.65 kgCO₂e is shell production and 529.57 kgCO₂e is ideal-fan electricity. That candidate passes all 12 held-out cells. The same candidate is also chosen if nominal selection is restricted to those four, so the result does not isolate minimax regret from the feasibility screen.

The 4/9 versus 0/9 split is a count in this list, not a sizing rule for other systems. Native ports, a fan curve, and a sequential route-then-size baseline were not in the run. The code and the 405-cell scalar ledger are public at https://github.com/dynamor2019/bim-carbon-robust-duct-screening. The original IFC is not included.
## Declarations

### Funding

This research was supported by the North China Institute of Aerospace Engineering Research Project (Grant No. BKY-2021-26: Application and Implementation of AI Object Detection in Construction Management).

### Competing interests

The authors declare that they have no known competing financial interests or personal relationships that could have appeared to influence the work reported in this paper.

### Data availability

A local supplementary archive, conditional-case-support-v4.zip, accompanies this draft. It contains project-relative model code, source-derived interfaces and contacts, the assumption register, five historical 0.16 m placeholder inputs, the complete 405-cell ledger, 15 scenario-status rows, 27 candidate mappings, original and isolated replay outputs, numerical-audit report and software-test log. Both result files have SHA256 b626d640c9bed9cd45a51a77262e57097abf2906d79d90d756f6ab6cb3f73c01. The replay is byte-identical and the 15 software tests passed; these are software and numerical-accounting checks, not scientific or engineering certification. The code and the 405-cell scalar ledger are public at https://github.com/dynamor2019/bim-carbon-robust-duct-screening. There is no DOI. The full component-level result file is 146.7 MB, above GitHub's 100 MB file limit, so the public CSV omits per-component arrays; the SHA256 above identifies the complete local file. Redistribution rights for the original BIM/IFC source have not been confirmed, and the original IFC is not included. A later substitution of the five model interface sizes reproduced the archived 405-cell status counts and both selected designs; 23 carbon values changed only in non-selected length-based candidates. That check does not replace the archived hash and is not a new certified ledger. Operating hours, fan efficiency, roughness, wall thickness, grid and material factors, and the fitting-loss coefficient remain experience-based assumptions, not measured data. The original IFC is still not public.

The public repository contains the model code, the 405 scalar cell records, the 27 candidate geometries, and this manuscript. It does not contain the original IFC. Replaying the CSV does not replace lawful access to that IFC for an independent extraction check.

The supplied derived interfaces, contact graph, prepared dimensions and terminal loads are sufficient to replay the conditional numerical model without the original IFC. Original IFC access is needed to independently check their extraction and provenance, not to run this derived-input replay. Those two reproduction tasks are different; success at replay does not establish lawful source access or independent extraction.

Author names, affiliation, funding, conflicts, ethics, CRediT roles and this AI statement are in the manuscript. The original IFC is not in the public repository.

### CRediT authorship contribution statement

**Zhang Min**: Conceptualization, Methodology, Software, Validation, Formal analysis, Investigation, Data curation, Writing – original draft, Writing – review & editing, Visualization.

**Li Xiaoliang**: Conceptualization, Methodology, Resources, Writing – review & editing, Supervision, Project administration, Funding acquisition.

### Use of generative AI

Language models and the DSH writing tools were used to draft and revise prose, organize evidence and check citations. Coding assistance was used to prepare and check the local calculation package. The 405-cell results, including failures and unresolved cells, come from the recorded model, not from a language-model calculation. The authors reviewed the scientific content and remain responsible for it.

### Ethics approval and consent to participate

Not applicable. This study does not involve human subjects, animal experiments, or protected data.

---

## Highlights

- Automated BIM screening generates 27 duct candidates from IFC geometry
- Screening records 405 hydraulic-carbon cells across demand scenarios
- Larger sizing is associated with 4 of 9 design-scenario passes, not 0 of 9
- The robust screen adds 552 kgCO2e, or 2.09 percent, in this case
- Code and 405-cell ledger: github.com/dynamor2019/bim-carbon-robust-duct-screening

## References

Ailem, R., and Boton, C. (2026). Automating clash relevance filtering in BIM-based multidisciplinary coordination using machine learning. Automation in Construction, 181, 106644. https://doi.org/10.1016/j.autcon.2025.106644

Al Sayed, K., Boodi, A., Sadeghian Broujeny, R., and Beddiar, K. (2024). Reinforcement learning for HVAC control in intelligent buildings: A technical and conceptual review. Journal of Building Engineering, 95, 110085. https://doi.org/10.1016/j.jobe.2024.110085

Amiri, A., Emami, N., Ottelin, J., Sorvari, J., Marteinsson, B., Heinonen, J. T., and Junnila, S. (2021). Embodied emissions of buildings - A forgotten factor in green building certificates. Energy and Buildings, 241, 110962. https://doi.org/10.1016/j.enbuild.2021.110962

Autodesk (2024). Workflow: Revit systems analysis. Revit Analyze help. https://help.autodesk.com/cloudhelp/2024/ENU/Revit-Analyze/files/GUID-200338BB-B394-4492-9A11-1A2A80A45AAE.htm

Autodesk (2026). Overview of Clash Detective tool. Navisworks Clash Detective help. https://help.autodesk.com/cloudhelp/2026/ENU/Navisworks-Clash-Detective/files/GUID-36D9904E-12F3-4F82-8DD3-C2103DB0BC29.htm

buildingSMART International (2023). Industry Foundation Classes (IFC) - IFC 4.3 Specification. https://www.buildingsmart.org/standards/bsi-standards/industry-foundation-classes/

Calixto, V., Gambardella, C. C., Karimi, A., Le Bodic, P., and Zhong, A. Z. (2026). Modelling and optimizing HVAC systems for early-stage building design. 32nd International Conference on Principles and Practice of Constraint Programming, Article 10. https://doi.org/10.4230/LIPIcs.CP.2026.10

Chen, Z., Guan, H., Yuan, X., Xie, T., and Xu, P. (2022). Rule-based generation of HVAC duct routing. Automation in Construction, 139, 104264. https://doi.org/10.1016/j.autcon.2022.104264

Hu, X., Yuan, X., Jiang, J., Jiang, Y., Liang, Y., Jia, W., and Kosonen, R. (2025). Energy, environmental, and economic (3E) analysis of a dynamic ice storage system based on ice slurry for a super high-rise building in subtropical climates. Energy and Buildings, 331, 115373. https://doi.org/10.1016/j.enbuild.2025.115373

Jorens, S., Verhaert, I., and Sörensen, K. (2018). Design optimization of air distribution systems in non-residential buildings. Energy and Buildings, 175, 48–56. https://doi.org/10.1016/j.enbuild.2018.07.018

Kiss, B., and Szalay, Z. (2020). Modular approach to multi-objective environmental optimization of buildings. Automation in Construction, 111, 103044. https://doi.org/10.1016/j.autcon.2019.103044

Koezjakov, A., Ürge-Vorsatz, D., Crijns-Graus, W. H. J., and van den Broek, M. A. (2018). The relationship between operational energy demand and embodied energy in Dutch residential buildings. Energy and Buildings, 165, 233–245. https://doi.org/10.1016/j.enbuild.2018.01.036

Kubicki, S., Guerriero, A., Schwartz, L., Daher, E., and Idris, B. (2019). Assessment of synchronous interactive devices for BIM project coordination: Prospective ergonomics approach. Automation in Construction, 101, 160–178. https://doi.org/10.1016/j.autcon.2018.12.009

Li, J., Guan, H., Xu, P., Gu, J., and Dong, L. (2025). Automated layout generation of HVAC piping from building floor plans. Automation in Construction, 177, 106359. https://doi.org/10.1016/j.autcon.2025.106359

Lilis, G. N., Wang, M., Katsigarakis, K., Mavrokapnidis, D., Korolija, I., and Rovas, D. (2025). BIM-based semantic enrichment and knowledge graph generation via geometric relation checking. Automation in Construction, 173, 106081. https://doi.org/10.1016/j.autcon.2025.106081

Liu, Z., Yu, C., Qian, Q. K., Huang, R., You, K., Visscher, H. J., and Zhang, G. (2023). Incentive initiatives on energy-efficient renovation of existing buildings towards carbon–neutral blueprints in China: Advancements, challenges and prospects. Energy and Buildings, 296, 113343. https://doi.org/10.1016/j.enbuild.2023.113343

Llatas, C., Soust-Verdaguer, B., Hollberg, A., Palumbo, E., and Quiñones, R. (2022). BIM-based LCSA application in early design stages using IFC. Automation in Construction, 138, 104259. https://doi.org/10.1016/j.autcon.2022.104259

Mustafa, M., Rezgui, Y., and Beach, T. (2026). Operational optimisation versus mechanical retrofit in non-domestic buildings: An SRI-informed life cycle assessment. Building and Environment, 296, 114496. https://doi.org/10.1016/j.buildenv.2026.114496

Rabani, M., Petersen, A. J., Steneng, C. V., Utstøl, S., Halla, H., and Liaøy, A. R. (2025). Quantifying greenhouse gas emissions from HVAC - A case study of natural, hybrid and mechanical ventilation strategies. Journal of Building Engineering, 112, 113642. https://doi.org/10.1016/j.jobe.2025.113642

Robati, M., Oldfield, P., Nezhad, A. A., Carmichael, D. G., and Kuru, A. (2021). Carbon value engineering: A framework for integrating embodied carbon and cost reduction strategies in building design. Building and Environment, 192, 107620. https://doi.org/10.1016/j.buildenv.2021.107620

Roberts, M., Ouellet-Plamondon, C., and Raftery, P. (2025). Embodied carbon in mechanical, electrical, and plumbing systems: A critical literature review. Building and Environment, 275, 112823. https://doi.org/10.1016/j.buildenv.2025.112823

Shindo, K., Shinoda, J., Kazanci, O. B., Bogatu, D.-I., Tanabe, S., and Olesen, B. W. (2023). A comparative study of the whole life carbon of a radiant system and an all-air system in a non-residential building. Energy and Buildings, 300, 113668. https://doi.org/10.1016/j.enbuild.2023.113668

Tavares, V., and Freire, F. M. C. S. (2022). Life cycle assessment of a prefabricated house for seven locations in different climates. Journal of Building Engineering, 53, 104504. https://doi.org/10.1016/j.jobe.2022.104504

Torabi, M., Simonen, K., and Evins, R. (2025). What matters the most in designing low-carbon buildings in Canada? Exploring the tradeoff between embodied and operational carbon in early stage design. Energy and Buildings, 334, 115482. https://doi.org/10.1016/j.enbuild.2025.115482

Walker, L., Hischier, I., and Schlueter, A. (2022). The impact of modeling assumptions on retrofit decision-making for low-carbon buildings. Building and Environment, 226, 109683. https://doi.org/10.1016/j.buildenv.2022.109683

Xu, W., Chen, P., Chi, H.-L., Wang, S., and Zhou, S. (2025). Digital-physical integration for MEP-structural clash coordination using path planning and AR navigation. Automation in Construction, 179, 106501. https://doi.org/10.1016/j.autcon.2025.106501

Yang, B., Melikov, A. K., Kabanshi, A., Zhang, C., Bauman, F. S., Cao, G., Awbi, H., Wigö, H., Niu, J., Cheong, D. K. W., Tham, K. W., Sandberg, M. O., Nielsen, P. V., Kosonen, R., Yao, R., Kato, S., Sekhar, C., Schiavon, S., Karimipanah, T., Li, X., and Lin, Z. (2019). A review of advanced air distribution methods - theory, practice, limitations and solutions. Energy and Buildings, 202, 109359. https://doi.org/10.1016/j.enbuild.2019.109359

Zhang, Y., Jiang, X., Cui, C., and Skitmore, M. (2022). BIM-based approach for the integrated assessment of life cycle carbon emission intensity and life cycle costs. Building and Environment, 226, 109691. https://doi.org/10.1016/j.buildenv.2022.109691

Zong, C., Banihashemi, F., Petzold, F., and Lang, W. (2026). Graph-based database structure and calculation framework for automated dynamic life cycle assessment of buildings. Automation in Construction, 191, 107183. https://doi.org/10.1016/j.autcon.2026.107183
