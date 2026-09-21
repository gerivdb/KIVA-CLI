# Automation Targets — Meta Aggregation Report

**Scopes**: 1
**KG Engines**: 120 targets
**Total targets**: 121
**Existing**: 1
**Missing**: 0
**Patterns**: 1

## Scopes

### KIVA-CLI

- **Path**: `D:\DO\WEB\TOOLS\L1-INFRA\KIVA-CLI`
- **Targets**: 1 (existing: 1, missing: 0)
- **Patterns**: 1

## KG Engines

### KG_L

- **Count**: 115
- ✅ **CONCEPT**: garde_fou
- ✅ **CONCEPT**: gguf
- ✅ **CONCEPT**: q243
- ✅ **CONCEPT**: piano_diff
- ✅ **CONCEPT**: kbin
- ✅ **CONCEPT**: llux_native
- ✅ **CONCEPT**: ternary_weights
- ✅ **CONCEPT**: transport_ptx1
- ✅ **CONCEPT**: i2_s
- ✅ **CONCEPT**: empirical_spec_port

### VOLTX

- **Count**: 4
- ✅ **CONCEPT**: VERSES
- ✅ **BRIDGE**: VOLTX <-> KG-L
- ✅ **ROUTINE**: verses_versioning
- ✅ **BRIDGE**: KG-L <-> VOLTX bridge

### VERSES

- **Count**: 1
- ✅ **CONCEPT**: verse-discipline

### Non-Overlap Analysis

| Engine | Unique | Overlap |
|--------|--------|---------|
| KG-L | 115 | 0 with VOLTX |
| VOLTX | 4 | 0 with VERSES |
| VERSES | 1 | 0 with KG-L |

## Recommendations

