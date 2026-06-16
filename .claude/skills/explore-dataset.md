# Skill: explore-dataset

**Trigger:** whenever you encounter a `.xlsx`, `.xls`, or `.csv` file you have not profiled before, or whenever the user asks you to "understand", "explore", "profile", or "inspect" a dataset.

---

## Goal

Build a reliable, reusable mental model of a tabular file so that every subsequent analysis step can refer to a known, authoritative description of the data instead of re-inferring it from scratch.

---

## Step 0 — Check for an existing reference

Before profiling, check whether `.claude/skills/` already contains a file named `dataset-<slug>.md` whose description matches the file in question.  
- If it exists and is current, **read it and stop here** — use that reference instead of re-profiling.  
- If it exists but seems outdated (e.g. column count differs), re-run the profiling steps and update it.

---

## Step 1 — Load the file

Use Python in a scratch cell or a `Bash` tool call. Choose the loader based on extension:

```python
import pandas as pd

# CSV
df = pd.read_csv("path/to/file.csv", encoding="utf-8", low_memory=False)

# XLSX / XLS  (list all sheets first, then load the relevant one)
xl = pd.ExcelFile("path/to/file.xlsx")
print(xl.sheet_names)          # inspect available sheets
df = pd.read_excel(xl, sheet_name=xl.sheet_names[0])
```

**Gotchas to handle:**
- Try `encoding="latin-1"` if `utf-8` raises a `UnicodeDecodeError`.
- Pass `sep=";"` or `sep="\t"` if the CSV uses a non-comma delimiter.  
  Detect it automatically: `df = pd.read_csv(path, sep=None, engine="python")`.
- For multi-header xlsx files (merged cells), use `header=[0,1]` and then flatten with  
  `df.columns = ["_".join(c).strip() for c in df.columns]`.
- Drop fully-empty rows/columns right after load:  
  `df.dropna(how="all", axis=0, inplace=True); df.dropna(how="all", axis=1, inplace=True)`.

---

## Step 2 — Generate the column profile

Run the following block and capture its output verbatim — it will be pasted into the skill reference:

```python
import numpy as np

def profile(df):
    rows = []
    for col in df.columns:
        s = df[col].dropna()
        dtype = str(df[col].dtype)
        n_null = int(df[col].isna().sum())
        pct_null = round(n_null / len(df) * 100, 1)
        n_unique = int(s.nunique())
        
        if pd.api.types.is_numeric_dtype(s):
            summary = f"min={s.min():.4g}, max={s.max():.4g}, mean={s.mean():.4g}"
        elif pd.api.types.is_datetime64_any_dtype(s):
            summary = f"from {s.min()} to {s.max()}"
        else:
            top = s.value_counts().head(3).index.tolist()
            summary = f"top values: {top}"
        
        rows.append({
            "column": col,
            "dtype": dtype,
            "nulls": f"{n_null} ({pct_null}%)",
            "unique": n_unique,
            "summary": summary,
        })
    
    import json
    print(json.dumps(rows, indent=2, default=str))

profile(df)
```

---

## Step 3 — Infer column semantics

For each column decide:

| Semantic category | Clues |
|---|---|
| **timestamp** | dtype is datetime64, name contains "date", "time", "ts", "hora", "data" |
| **numeric measure** | float/int with physical units (Hs, Tp, wind speed, depth, lat/lon) |
| **categorical label** | object dtype, low cardinality (< 50 unique), looks like a code or name |
| **identifier / key** | unique per row, name ends in "id", "ID", "cod" |
| **flag / status** | integer or string with values 0/1, True/False, "OK"/"ERR" |
| **free text** | object dtype, high cardinality, long strings |

Record the unit (m, s, °, m/s, …) when it appears in the column name or can be inferred from value ranges.

---

## Step 4 — Detect the dataset domain

After reviewing all columns, assign a **domain** from this list (add new ones as needed):

- `meteocean` — wave heights, periods, directions, sea states
- `wind` — wind speed/direction, anemometer data
- `current` — current speed/direction, ADCP profiles
- `vessel` — ship position, heading, draft, motions
- `environmental` — precipitation, temperature, salinity, visibility
- `operational` — cargo, crane, ROV, activity log
- `meteo-station` — barometric pressure, air temp, humidity at fixed station
- `generic-tabular` — multi-domain or unknown

---

## Step 5 — Decide whether to create or update a skill reference

**Create** a new reference when:
- No matching `.claude/skills/dataset-<slug>.md` exists yet.
- The domain + column fingerprint is meaningfully different from any existing reference.

**Update** an existing reference when:
- The same logical dataset appears with a new file name (e.g. updated time period).
- Additional columns are discovered that the existing reference did not cover.

**Skip** (just use the existing reference) when:
- The profile matches an existing reference within ±10% column count and the key columns are identical.

---

## Step 6 — Write the skill reference file

Create `.claude/skills/dataset-<slug>.md` following the template in  
`.claude/skills/_dataset-reference-template.md`.

Rules for the `<slug>`:
- Use the **domain** + a short distinctive label, e.g. `meteocean-hindcast`, `wind-buoy-p66`, `vessel-position`.
- Use lowercase, hyphens only, no spaces.
- If the file name itself is descriptive, derive the slug from it.

After writing the file, print: `✅ Skill reference created: .claude/skills/dataset-<slug>.md`

---

## Step 7 — Return a plain-language summary to the user

Always finish with a short human-readable paragraph that states:
- How many rows and columns the dataset has.
- What the dataset appears to represent (domain + time range if applicable).
- Which column is the primary time index (if any).
- Any data-quality warnings (high null %, mixed types, suspicious ranges).
- The name of the skill reference file that was created or updated.
