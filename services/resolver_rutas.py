import sys
from pathlib import Path


def resolver_ruta_recurso(ruta_relativa: str) -> str:
  if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    base_path = Path(sys._MEIPASS)
  else:
    base_path = Path(__file__).resolve().parent.parent

  return str(base_path / ruta_relativa)