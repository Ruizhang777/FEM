# FEM: ABAQUS Simulation Framework for Capsule Expansion Technology

This repository provides parameterized ABAQUS scripts for studying excavation-induced tunnel deformation and the response to capsule expansion technology (CET). The workflow creates finite-element models, runs simulation jobs, and exports displacement and capsule-area data for subsequent analysis and data-driven modelling.

The simulation code and model parameters are publicly available so that researchers with a compatible ABAQUS installation can generate simulation data and investigate additional parameter combinations.

Repository: <https://github.com/Ruizhang777/FEM>

## Repository contents

| File | Purpose |
| --- | --- |
| `main.py` | Defines parameter combinations, filters geometrically inadmissible cases, writes the input-parameter table, and calls the modelling, solution, and post-processing modules. |
| `Tools1.py` | Builds the two-dimensional finite-element models, assigns materials and boundary conditions, defines analysis steps and meshes, and writes ABAQUS input files. |
| `Tools2.py` | Submits input-file jobs, configures displacement monitoring, and waits for job completion. |
| `Tools3.py` | Reads ABAQUS output databases and exports displacement histories, capsule areas, and monitoring-point coordinates to CSV files. |

## Software requirements

- **ABAQUS/CAE and ABAQUS/Standard**, with a valid licence and access to the ABAQUS Python scripting environment.
- **Windows** for the supplied job-monitoring implementation, which uses `tasklist` and `taskkill`.
- Sufficient memory, disk space, and solver licence capacity for the selected mesh and CPU allocation.

Run these scripts inside ABAQUS/CAE. They import ABAQUS-specific modules and use an interactive parameter dialog and a CAE viewport; ordinary `python main.py` is not the entry point for this release.

The scripts contain Python 2-style CSV handling, including binary-mode CSV writes, and assumptions about dictionary-key lists. The repository does not currently specify a tested ABAQUS release. Check compatibility with the Python interpreter bundled with your installation before starting a batch. Python 3-based installations may require changes to these operations. Record the ABAQUS release and any compatibility changes with your results.

## Quick start

1. Download the repository using **Code → Download ZIP**, or clone it:

   ```bash
   git clone https://github.com/Ruizhang777/FEM.git
   ```

2. Place `main.py`, `Tools1.py`, `Tools2.py`, and `Tools3.py` together in a new working directory. Use a separate directory for each simulation campaign: the job and post-processing modules scan the working directory for `.inp` and `.odb` files, respectively.

3. Edit the parameter block in `main.py`. For an initial run, select one admissible combination and reduce the CPU allocation to match your machine. The supplied `main.py` calls `job_process_api` with `cpu_nums=48` and `gpu_nums=0`; 48 CPUs is a configuration value, not a minimum requirement.

4. Review the displacement stopping condition in `Tools2.py`, as described below, before running jobs.

5. Open ABAQUS/CAE, set its working directory to the directory containing the scripts, and use **File → Run Script** to select `main.py`. Keep the default viewport, `Viewport: 1`, available for post-processing.

6. Enter `Lct`, the capsule-to-tunnel clearance, when prompted. The displayed default is `3.0 m`.

7. Check the solver job status and generated CSV files. Preserve the input files and output databases alongside the exported data.

The workflow is:

```text
Parameter combinations and geometry checks
                  ↓
Finite-element model and input-file generation
                  ↓
ABAQUS/Standard solution and displacement monitoring
                  ↓
Output-database extraction
                  ↓
Displacement, capsule-area, and coordinate CSV files
```

## Parameters and units

The supplied parameterization uses metres for lengths and displacements, pascals for stresses and elastic moduli, and kilograms per cubic metre for density. Friction angles are entered in degrees. Maintain a consistent unit system when changing parameters.

### Geometry

| Parameter in `main.py` | Meaning | Supplied value(s) | Unit |
| --- | --- | --- | --- |
| `Ht_list` | Tunnel burial-depth parameter, `Ht` | `12.4`, `37.2` | m |
| `He_ratio` | Excavation-depth ratio, `He / Ht` | `0.5`, `2.0` | — |
| `Lwt_ratio` | Geometric distance ratio, `Lwt / He` | `0.5`, `1.0` | — |
| `We_list` | Excavation half-width, `B` | `15.0`, `45.0` | m |
| `Dcap_list` | Capsule diameter | `0.2` | m |
| `F_Dt` | Tunnel outer diameter | `6.2` | m |
| `F_Lct` | Clearance between the capsule's right side and the tunnel's left side | Interactive input; default `3.0` | m |
| `F_Tw` | Retaining-wall thickness | `0.8` | m |
| `F_tlining` | Tunnel-lining thickness | `0.35` | m |
| `F_Lc` | Capsule height | `8.0` | m |

The script computes:

```text
He  = He_ratio × Ht
Lwt = Lwt_ratio × He
```

It skips combinations satisfying either `Lwt < F_Dt + F_Lct + Dcap` or `He > 40.0 m`.

### Soil properties

Each entry in `material_data_group` has the order:

```text
[cohesion, elastic_modulus, density, friction_angle, Poisson_ratio]
```

| Material entry | Cohesion (Pa) | Elastic modulus (Pa) | Density (kg/m³) | Friction angle (°) | Poisson ratio |
| --- | --- | --- | --- | --- | --- |
| 1 | 0.0 | 9,600,000 | 2039.4 | 30.0 | 0.3 |
| 2 | 0.0 | 21,600,000 | 2039.4 | 30.0 | 0.3 |
| 3 | 0.0 | 3,360,000 | 2039.4 | 30.0 | 0.3 |
| 4 | 0.0 | 3,360,000 | 2039.4 | 35.0 | 0.3 |

### Mesh, loading, and increments

| Parameter | Supplied value | Meaning |
| --- | --- | --- |
| `mesh_size` | `0.5` | Mesh-size parameter in metres. |
| `zjnt_pressure` | `-2000000.0` | Capsule pressure-loading parameter in pascals; retain the sign convention of the model. |
| `step_zjnt_maxNumInc` | `1000` | Maximum number of increments in the capsule-loading step. |
| `step_zjnt_minInc` | `1e-5` | Minimum increment in that step. |

These values document the supplied configuration. Select the parameter combinations and analysis settings required for the study you intend to reproduce.

## Analysis and monitoring

The model-building module defines geostatic initialization (`geo`), excavation (`kw`), and capsule loading (`zjnt`). The main workflow monitors displacement component `U1` at `chenqi-1.Tunnel_7_left`.

Before running, inspect `monitor_tools3_status_check` in `Tools2.py`. Its current numerical condition is `time_now >= 2.0` and `monitor_data > 0.1`. The comparison operates on the raw monitored value; the code does not convert it to millimetres. Set the threshold in the model's displacement units and make it consistent with the intended stopping criterion and analysis-step timing.

When this condition is met, the current implementation calls `taskkill /f /t /im standard.exe`. This terminates matching ABAQUS/Standard processes on the machine, including unrelated jobs. Run this implementation in an isolated solver session, or adapt the termination logic to target the specific job before sharing a machine with other simulations.

## Output files

| File or pattern | Contents |
| --- | --- |
| `Input_para_list.csv` | Parameter table with case names, soil properties, and geometry settings. |
| `test_*.inp` | Generated ABAQUS solver input files for admissible combinations. |
| `test_*.odb` | ABAQUS output databases produced by the simulation jobs. |
| `OutPutData_<case>_histData_<group>.csv` | Displacement components for monitoring-point groups, extracted from field-output frames by the active post-processing routine. |
| `OutPutData_<case>_zjnt_area.csv` | `time` and `zjnt_total_area`, the calculated capsule cross-sectional area in m². |
| `OutPutData_<case>_coordData.csv` | Monitoring-point names and coordinates, translated so that the tunnel centre is the origin; coordinates are in metres. |

`<case>` denotes the output-database basename, such as `test_1`; `<group>` denotes the group selected by the exporter. Additional solver logs and status files are produced by ABAQUS.

### Reading the exported data

- **Parameter-table ratios:** in the current `Input_para_list.csv` exporter, the columns labelled `H_e` and `L_wt` contain `He_ratio` and `Lwt_ratio`, respectively. Convert them using the equations above before treating them as lengths. The source spelling `t_linling` denotes the lining thickness.
- **Candidate versus simulated cases:** the parameter table is written for all candidate combinations. Some candidates are subsequently skipped by the geometry checks. Match case names to generated input files, solver status, and output databases before assembling a dataset.
- **Displacements:** `U1` and `U2` are the model's first and second displacement components. Values remain in model length units; multiply metre-valued displacements by `1000` when reporting millimetres.
- **Time:** the active field-data exporter reads **step-local time** and concatenates frames across steps. Values may restart at a step boundary. Preserve step/frame identity when constructing a merged analysis table; do not treat `time` alone as a unique record identifier.
- **Capsule area:** `zjnt_total_area` is an area, not an injected volume or an expansion percentage. Apply the study's stated geometric definition when deriving those quantities.

## Using the simulations for machine learning

The exported displacement values are numerical outputs of ABAQUS simulations. Keep raw solver outputs separate from processed learning tables, and document any unit conversion, reference-state subtraction, frame selection, and derived quantities.

Assign each finite-element case a persistent case identifier. When creating training, validation, and test sets, keep all snapshots from the same case in the same split and fit normalization parameters using training cases only. Multiple frames from one simulation are correlated observations, not independent finite-element cases.

For the associated Paper1 study, retain the stated working domain of `eta ≤ 15%` during downstream data preparation. The pressure-loading value in this repository is not itself an `eta` cutoff.

## Reuse and reporting

When reporting results generated with this repository, record:

- The repository URL and commit used.
- The ABAQUS release and operating system.
- Parameter combinations, mesh settings, and stopping criteria.
- Any script modifications and the processing steps used to build analysis tables.

The public repository provides the finite-element data-generation workflow. Its scope should be distinguished from separately distributed processed datasets, learning-model implementations, trained weights, and third-party field measurements.

To reference the software, identify the repository as **“FEM: FEM algorithm for CET”**, link to <https://github.com/Ruizhang777/FEM>, and include the commit and access date. Cite any associated publication separately when its bibliographic information is available.

For questions or reproducible issue reports, use the repository's [Issues page](https://github.com/Ruizhang777/FEM/issues). Include the ABAQUS version, relevant parameter settings, and the error message.
