# Setup and Run

## Requirements

- Python 3.10 or higher
- Git (to clone the repo if needed)

---

## 1. Create a virtual environment

From the repo root:

```bash
python3 -m venv .venv
```

Activate it:

```bash
# Linux / macOS
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

---

## 2. Install dependencies

Navigate into the `streamlitapp` directory and install the package in editable mode along with all dependencies:

```bash
cd streamlitapp
pip install -e .
pip install -r requirements.txt
```

The `-e .` step installs the `meteocean_forecast` source package (under `src/`) so Streamlit pages can import it without path hacks.

---

## 3. Run the app

From inside `streamlitapp/`:

```bash
streamlit run app/Home.py
```

Streamlit will print a local URL (usually `http://localhost:8501`). Open it in your browser.

---

## 4. Run the tests (optional)

From inside `streamlitapp/`:

```bash
pytest
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: meteocean_forecast` | Make sure you ran `pip install -e .` from inside `streamlitapp/` |
| `prophet` install fails | Install system dependencies first: `sudo apt install python3-dev libstan-math-dev` (Ubuntu) or use `conda install -c conda-forge prophet` |
| Port already in use | Run on a different port: `streamlit run app/Home.py --server.port 8502` |
