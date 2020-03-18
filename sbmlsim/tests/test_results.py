

import pandas as pd

from sbmlsim.models import RoadrunnerSBMLModel
from sbmlsim.result import Result
from sbmlsim.tests.constants import MODEL_REPRESSILATOR


def test_result():
    r = RoadrunnerSBMLModel(source=MODEL_REPRESSILATOR)._model
    dfs = []
    for _ in range(10):
        s = r._run_tasks(0, 10, steps=10)
        dfs.append(pd.DataFrame(s, columns=s.colnames))

    result = Result(dfs)
    assert result
    assert result.nframes == 10
    assert result.nrow == 11
    assert result.data is not None


def test_hdf5(tmp_path):
    r = RoadrunnerSBMLModel(source=MODEL_REPRESSILATOR)._model
    dfs = []
    for _ in range(10):
        s = r._run_tasks(0, 10, steps=10)
        dfs.append(pd.DataFrame(s, columns=s.colnames))

    result = Result(dfs)
    h5_path = tmp_path / "result.h5"
    result.to_hdf5(h5_path)

    result2 = Result.from_hdf5(h5_path)
    assert result
    assert result.nframes == 10
    assert result.nrow == 11
    assert result.data is not None
