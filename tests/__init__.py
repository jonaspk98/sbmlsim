"""Definition of data and files for tests."""


from pathlib import Path

from sbmlsim import RESOURCES_DIR

TEST_PATH = Path(__file__).parents[0]  # directory of tests files
DATA_DIR = RESOURCES_DIR / "testdata"  # directory of data for tests

MODEL_DIR = DATA_DIR / "models"

MODEL_REPRESSILATOR = MODEL_DIR / "repressilator.xml"
MODEL_GLCWB = MODEL_DIR / "body21_livertoy_flat.xml"
MODEL_DEMO = MODEL_DIR / "Koenig_demo_14.xml"
MODEL_MIDAZOLAM = MODEL_DIR / "midazolam_body_flat.xml"
