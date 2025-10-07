# Local Python Environment

The backend is validated against Python 3.11. If you need a host-side virtual environment (outside Docker), install Python 3.11 and create the venv explicitly with that interpreter:

`powershell
# Windows PowerShell
your\path> py -3.11 -m venv .venv
PS> .\.venv\Scripts\Activate.ps1
(.venv) PS> pip install --upgrade pip
(.venv) PS> pip install --extra-index-url https://download.pytorch.org/whl/cpu -r backend/requirements.txt
`

`ash
# Linux/macOS
$ python3.11 -m venv .venv
$ source .venv/bin/activate
(.venv) $ pip install --upgrade pip
(.venv) $ pip install --extra-index-url https://download.pytorch.org/whl/cpu -r backend/requirements.txt
`

Python 3.13 is not supported because multiple ML wheels (PyTorch and friends) are still missing; stick to 3.11 for anything outside Docker.
