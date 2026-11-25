import sys
from pathlib import Path

# Streamlit puts the script's folder on the path when it runs an example. The
# tests run the examples through AppTest, which does not.
sys.path.insert(0, str(Path(__file__).parent.parent / "examples"))
