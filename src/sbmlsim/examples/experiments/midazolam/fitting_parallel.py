from typing import Any, Callable, Tuple

from sbmlsim.examples.experiments.midazolam import MIDAZOLAM_PATH
from sbmlsim.examples.experiments.midazolam.fitting_problems import (
    op_kupferschmidt1995,
    op_mandema1992,
    op_mid1oh_iv,
)
from sbmlsim.fit.fit import OptimizationResult
from sbmlsim.fit.analysis import process_optimization_result
from sbmlsim.fit.mpfit import run_optimization_parallel
from sbmlsim.fit.optimization import (
    FittingType,
    OptimizationProblem,
    OptimizerType,
    ResidualType,
    SamplingType,
    WeightingPointsType,
)


def fit_lsq(
    problem_factory: Callable, seed: int=1236, **fit_kwargs: Any
) -> Tuple[OptimizationResult, OptimizationProblem]:
    """Local least square fitting."""
    problem: OptimizationProblem = problem_factory()
    opt_res = run_optimization_parallel(
        problem=problem,
        size=10,
        seed=seed,
        n_cores=10,
        optimizer=OptimizerType.LEAST_SQUARE,
        **fit_kwargs
    )
    return opt_res, problem


def fit_de(
    problem_factory: Callable, seed: int=1234, **fit_kwargs: Any
) -> Tuple[OptimizationResult, OptimizationProblem]:
    """Global differential evolution fitting."""
    problem: OptimizationProblem = problem_factory()
    opt_res = run_optimization_parallel(
        problem=problem,
        size=2,
        seed=seed,
        n_cores=2,
        optimizer=OptimizerType.DIFFERENTIAL_EVOLUTION,
        **fit_kwargs
    )
    return opt_res, problem


if __name__ == "__main__":

    RESULTS_PATH = MIDAZOLAM_PATH / "results"

    fit_kwargs = {
        "fitting_type": FittingType.ABSOLUTE_VALUES,
        "residual_type": ResidualType.ABSOLUTE_NORMED_RESIDUALS,
        "weighting_local": WeightingPointsType.ABSOLUTE_ONE_OVER_WEIGHTING,
        "absolute_tolerance": 1e-6,
        "relative_tolerance": 1e-6,
    }

    # fit_id = "mid1oh_iv"
    fit_id = "kupferschmidt1995"

    fit_path = MIDAZOLAM_PATH / "results_fit"
    fit_path_lsq = fit_path / fit_id / "lsq"
    fit_path_de = fit_path / fit_id / "de"
    for p in [fit_path_de, fit_path_lsq]:
        if not p.exists():
            p.mkdir(parents=True)

    # TODO: save problem (serializable part & results)
    # TODO: run on cluster
    # json_str = opt_res_lq.to_json()
    # print(json_str)
    # opt_res2 = OptimizationResult.from_json(json_str)
    # analyze_optimization(opt_res2, problem=problem)

    if fit_id == "mid1oh_iv":
        problem_factory = op_mid1oh_iv
    elif fit_id == "kupferschmidt1995":
        problem_factory = op_kupferschmidt1995

    if 1:
        opt_res_lsq1, problem = fit_lsq(problem_factory, seed=1234, **fit_kwargs)
        opt_res_lsq2, problem = fit_lsq(problem_factory, seed=3298, **fit_kwargs)
        opt_res_lsq = OptimizationResult.combine([opt_res_lsq1, opt_res_lsq2])

        opt_res_path = fit_path_lsq / f"{opt_res_lsq.sid}.json"
        opt_res_lsq.to_json(path=opt_res_path)
        opt_res_lsq = OptimizationResult.from_json(json_info=opt_res_path)

        # FIXME: serialize problem
        problem_path = fit_path_lsq / f"{opt_res_lsq.sid}.json"
        problem = problem_factory()
        problem.to_json()
        process_optimization_result(
            opt_res_lsq, problem=problem, output_path=fit_path_lsq, **fit_kwargs
        )





    if 0:
        opt_res_de, problem = fit_de(problem_factory, **fit_kwargs)
        process_optimization_result(
            opt_res_de, problem=problem, output_path=fit_path_de, **fit_kwargs
        )
