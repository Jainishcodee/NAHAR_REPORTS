"""Application-wide configuration: paths, constants, defaults."""
import sys
from pathlib import Path

APP_NAME = "Clinic Report Manager"
APP_ORG = "ClinicReportManager"
APP_VERSION = "1.0.0"

# When frozen by PyInstaller, keep writable data next to the executable.
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent  # project root

DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
ASSETS_DIR = BASE_DIR / "assets"
DB_PATH = DATA_DIR / "clinic.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Report types seeded on first run: (code, name)
DEFAULT_REPORT_TYPES = [
    ("MRI", "MRI Scan"),
    ("CT", "CT Scan"),
    ("XRAY", "X-Ray"),
    ("USG", "Ultrasound"),
    ("ECG", "ECG"),
    ("CBC", "Complete Blood Count (CBC)"),
    ("BSUGAR", "Blood Sugar"),
    ("LIPID", "Lipid Profile"),
    ("LFT", "Liver Function Test"),
    ("KFT", "Kidney Function Test"),
    ("THYROID", "Thyroid Profile"),
    ("URINE", "Urine Routine"),
    ("STOOL", "Stool Routine"),
    ("COVID", "COVID-19 RT-PCR"),
    ("GENERAL", "General / Other"),
]

DEFAULT_CLINIC = {
    "clinic_name": "City Diagnostic Centre",
    "address": "123 Health Street, City - 000000",
    "phone": "+91 00000 00000",
    "email": "info@cityclinic.example",
    "logo_path": "",
}

SEX_OPTIONS = ["Male", "Female", "Other"]
REPORT_STATUSES = ["Draft", "Final"]
