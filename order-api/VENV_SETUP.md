# Virtual Environment Setup

This project uses Python virtual environment (venv) to manage dependencies.

## Quick Start

### For Linux/WSL (Bash)

1. **Create and setup venv:**
   ```bash
   ./setup_venv.sh
   ```

2. **Activate venv manually:**
   ```bash
   source venv/bin/activate
   ```
   Or use the helper script:
   ```bash
   ./activate_venv.sh
   ```

### For Windows (PowerShell)

1. **Create and setup venv:**
   ```powershell
   .\setup_venv.ps1
   ```

2. **Activate venv manually:**
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
   Or use the helper script:
   ```powershell
   .\activate_venv.ps1
   ```

## Manual Setup

If you prefer to set up manually:

1. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   ```
   Or on Windows:
   ```powershell
   python -m venv venv
   ```

2. **Activate virtual environment:**
   - **Linux/WSL:** `source venv/bin/activate`
   - **Windows PowerShell:** `.\venv\Scripts\Activate.ps1`
   - **Windows CMD:** `venv\Scripts\activate.bat`

3. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   pip install -r requirements-test.txt  # for test dependencies
   ```

## Deactivate

To deactivate the virtual environment:
```bash
deactivate
```

## Verify Activation

When the virtual environment is activated, you should see `(venv)` at the beginning of your command prompt.

## Notes

- The `venv/` directory is already in `.gitignore`, so it won't be committed to version control
- Always activate the virtual environment before running the application or tests
- Python version required: >=3.12 (as specified in `pyproject.toml`)

