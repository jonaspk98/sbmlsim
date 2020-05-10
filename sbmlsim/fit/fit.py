from typing import List
from pathlib import Path
import scipy

from sbmlsim.fit.optimization import OptimizationProblem
from sbmlsim.fit.analysis import OptimizationResult


def run_optimization(
        problem: OptimizationProblem,
        size: int = 5, seed: int = 1234,
        plot_results: bool = True,
        output_path=None,
        **kwargs) -> OptimizationResult:
    """Runs the given optimization problem.

    This changes the internal state of the optimization problem
    and provides simple access to parameters and costs after
    optimization.

    :param size: number of optimization with different start values
    :param seed: random seed (for sampling of parameters)
    :param plot_results: should standard plots be generated
    :param output_path: path (directory) to store results
    :param kwargs: additional arguments for optimizer, e.g. xtol
    :return: list of optimization results
    """
    problem.report(output_path=output_path)
    op_path = output_path / problem.opid
    if not op_path.exists():
        op_path.mkdir()


    # optimize
    # TODO: store parameters, unique hash
    # TODO: parallelization
    fits, trajectories = problem.optimize(size=size, seed=seed, **kwargs)

    # process results and plots

    opt_result = OptimizationResult(parameters=problem.parameters, fits=fits,
                                    trajectories=trajectories)

    # write report (additional folders based on runs)

    opt_result.report(output_path=op_path)
    # FIXME: save and load the results
    # opt_result.save(output_path=output_path)

    if plot_results:
        if len(fits) > 1:
            opt_result.plot_waterfall(output_path=op_path)
        opt_result.plot_traces(output_path=op_path)
        opt_result.plot_correlation(output_path=op_path)

        # plot top fit

        problem.plot_costs(x=opt_result.xopt, output_path=op_path)
        problem.plot_residuals(x=opt_result.xopt, output_path=op_path)

    return opt_result

# TODO: implement loading of results and plotting
