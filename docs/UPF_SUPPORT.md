# UPF (IEEE 1801) Support Matrix

OpenLEC parses and checks a **structural subset** of IEEE 1801 (UPF 1.0 /
1801-2009 / 1801-2013). The parser is order-independent, strips `#` comments and
backslash line continuations, and accepts brace lists (`-elements {a b}`).

## Supported commands

| Command | Parsed options | Notes |
|---|---|---|
| `set_design_top` | `<name>` | sets `UPFIntent.design_top` |
| `create_power_domain` | `-elements {…}`, `-include_scope` | multiple domains supported |
| `create_supply_net` | `-domain` | nets without domain allowed |
| `set_isolation` | `-domain`, `-applies_to`, `-clamp_value`, `-isolation_signal`, `-isolation_sense`, `-location` | any option order |
| `set_retention` | `-domain`, `-retention_power_net`, `-retention_ground_net`, `-save_signal`, `-restore_signal` | any option order |

## Structural rule checks (`UPFChecker`)

| Rule | Severity | Meaning |
|---|---|---|
| `ISO_MISSING` | **halt** | a power domain with elements has no `set_isolation` strategy |
| `ISO_NOT_IMPLEMENTED` | **halt** | strategy exists but no isolation cell found in the netlist AST (only when an AST is supplied) |
| `RET_CONTROL` | **fail** | retention strategy missing save/restore control signals |
| `RET_DOMAIN` | **fail** | retention strategy references an unknown power domain |
| `SUPPLY_CLASH` | **fail** | an isolation control signal collides with a supply net name |

`run_all_checks()` returns one `UPFCheckResult` per family:
`isolation`, `retention`, `supply`.

## Examples

See `examples/upf/counter.upf` (minimal) and `examples/upf/mac_unit.upf`
(switchable domain with isolation + retention).

## Not yet supported (roadmap)

* `create_power_switch`, `add_power_state`, `create_pst` (power state tables)
* `set_level_shifter`, `set_repeater`
* `map_retention_cell`, `map_isolation_cell`
* supply sets (`create_supply_set`), `-diff_supply_only`
* `set_power_state` transitions and simstate/standby semantics
* UPF 1801-2015/2018 refinement constructs

These map to the roadmap items "Full UPF command coverage" and
"Real timing/power estimator integration (OpenSTA + Liberty + activity/VCD)".

## Conformal cross-reference

| OpenLEC | Conformal |
|---|---|
| `UPFParser` | `READ POWER INTENT` |
| `UPFChecker.check_isolation_clamps` | `CHECK LOWPOWER CELLS` (isolation) |
| `UPFChecker.check_retention_registers` | `ADD RETENTION_REGISTER MAPPING` + `CHECK LOWPOWER CELLS` |
| `UPFChecker.check_supply_network` | `COMPARE POWER GRID` (light structural subset) |
| `run_all_checks` summary | `REPORT LOWPOWER VERIFICATION` |