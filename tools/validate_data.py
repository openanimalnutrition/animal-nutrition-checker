"""Run the data validator: python3 -I -B tools/validate_data.py DATA_DIR [--against OLD_DATA_DIR]"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from oan import validate  # noqa: E402

if __name__ == "__main__":
    sys.exit(validate.main(sys.argv))
