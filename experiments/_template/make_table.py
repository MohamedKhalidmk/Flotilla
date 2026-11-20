"""test-NN table, built only from files under runs/ (never typed numbers). Writes table.csv/.md here and in results/tables/."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from _common import write_table

rows = []  # one dict per row, read from runs/run-NN/
write_table(HERE, "table", rows, "What the table shows.")
