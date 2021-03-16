"""Analysis of fitting results."""

import logging
from pathlib import Path
from typing import Tuple, Any, Dict

import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.figure import Figure, Axes
import matplotlib
from matplotlib.lines import Line2D

from sbmlsim.fit.optimization import OptimizationProblem
from sbmlsim.fit.options import ResidualType, WeightingCurvesType, WeightingPointsType
from sbmlsim.fit.result import OptimizationResult
from sbmlsim.plot.plotting_matplotlib import plt
from sbmlsim.utils import timeit


logger = logging.getLogger(__name__)


class OptimizationAnalysis:
    """Class for analyzing optimization results.

    Creates all plots and results.
    """

    def __init__(
        self,
        opt_result: OptimizationResult,
        output_path: Path,
        op: OptimizationProblem = None,
        show_plots: bool = True,
        show_titles: bool = True,
        residual_type: ResidualType = None,
        weighting_curves: WeightingCurvesType = None,
        weighting_points: WeightingPointsType = None,
        variable_step_size: bool = True,
        absolute_tolerance: float = 1e-6,
        relative_tolerance: float = 1e-6,
        image_format: str = "svg",
    ) -> None:
        """Construct Optimization analysis.

        :param show_plots: boolean flag to display plots, i.e., call plt.show()
        :param show_titles: boolean flag to add titles to the panels

        """
        self.sid = opt_result.sid
        self.optres: OptimizationResult = opt_result
        # the results directory uses the hash of the OptimizationResult
        results_dir: Path = output_path / self.sid
        if not results_dir.exists():
            logger.warning(f"create output directory: '{results_dir}'")
            results_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir = results_dir

        self.image_format = image_format
        self.show_plots = show_plots
        self.show_titles = show_titles

        if op:
            op.initialize(
                residual_type=residual_type,
                weighting_curves=weighting_curves,
                weighting_points=weighting_points,
                variable_step_size=variable_step_size,
                absolute_tolerance=absolute_tolerance,
                relative_tolerance=relative_tolerance,
            )

        self.op: OptimizationProblem = op  # type: ignore

    def run(self, mpl_parameters: Dict[str, Any] = None) -> None:
        """Execute complete analysis.

        This creates all plots and reports.
        """
        rc_params_copy = {**plt.rcParams}
        # from pprint import pprint
        # pprint(rc_params_copy)
        if mpl_parameters is None:
            mpl_parameters = {}

        parameters = {
            'axes.titlesize': 14,
            'axes.labelsize': 12,
            'axes.labelweight': "normal",
        }
        parameters.update(mpl_parameters)
        plt.rcParams.update(parameters)

        # write report
        problem_info: str = ""
        if self.op:
            problem_info = self.op.report(
                path=None,
                print_output=False,
            )
        result_info = self.optres.report(
            path=None,
            print_output=True,
        )
        info = problem_info + result_info
        with open(self.results_dir / "00_report.txt", "w") as f_report:
            f_report.write(info)

        # FIXME: create JSON information for problem
        self.optres.to_json(path=self.results_dir / "optimization_result.json")
        self.optres.to_tsv(path=self.results_dir / "optimization_result.tsv")

        # waterfall plot
        if self.optres.size > 1:
            self.plot_waterfall(
                path=self.results_dir / f"waterfall.{self.image_format}",
            )
        # optimization traces
        self.plot_traces(
            path=self.results_dir / f"traces.{self.image_format}",
        )

        # plot fit results for optimal parameters
        if self.op:
            xopt = self.optres.xopt

            self.plot_cost_scatter(
                x=xopt,
                path=self.results_dir / f"cost_scatter.{self.image_format}",
            )
            self.plot_cost_bar(
                x=xopt,
                path=self.results_dir / f"cost_bar.{self.image_format}",
            )
            self.plot_datapoint_scatter(
                x=xopt,
                path=self.results_dir / f"datapoint_scatter.{self.image_format}",
            )
            self.plot_residual_scatter(
                x=xopt,
                path=self.results_dir / f"residual_scatter.{self.image_format}",
            )
            self.plot_residual_boxplot(
                x=xopt,
                path=self.results_dir / f"residual_boxplot.{self.image_format}",
            )

            self.plot_fits(
                x=xopt,
                path=self.results_dir / "fits.svg",
            )

            # plot individual fit mappings
            self.plot_fit(x=xopt)

        # correlation plot
        if self.optres.size > 1:
            self.plot_correlation(path=self.results_dir / "parameter_correlation")

        # reset parameters
        plt.rcParams.update(rc_params_copy)

    def _create_mpl_figure(
        self, width: float = 5.0, height: float = 5.0) -> Tuple[Figure, Axes]:
        """Create matplotlib figure."""
        fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(width, height))
        fig.subplots_adjust(left=0.2, bottom=0.1)

        return fig, ax

    def _save_mpl_figure(self, fig, path: Path) -> None:
        """Save matplotlib figure to path."""
        if self.show_plots:
            plt.show()
        if path is not None:
            # fig.savefig(path, bbox_inches="tight")
            fig.savefig(path)
        plt.close(fig)

    @timeit
    def plot_fits(self, x: np.ndarray, path: Path) -> None:
        """Plot fitted curves with experimental data for given parameter set x.

        Creates an overview of all fit mappings.

        :param x: parameters to evaluate
        :param path: path for figure

        :return: None
        """
        n_plots = len(self.op.mapping_keys)
        fig, axes = plt.subplots(
            nrows=n_plots, ncols=2, figsize=(10, 5 * n_plots), squeeze=False
        )
        fig.subplots_adjust(hspace=0.1)

        # residual data and simulations of optimal parameters
        res_data = self.op.residuals(xlog=np.log10(x), complete_data=True)

        for k, mapping_id in enumerate(self.op.mapping_keys):

            # global reference data
            sid = self.op.experiment_keys[k]
            mapping_id = self.op.mapping_keys[k]
            x_ref = self.op.x_references[k]
            y_ref = self.op.y_references[k]
            y_ref_err = self.op.y_errors[k]
            y_ref_err_type = self.op.y_errors_type[k]
            x_id = self.op.xid_observable[k]
            y_id = self.op.yid_observable[k]

            for ax in axes[k]:
                ax.set_title(f"{sid} {mapping_id}")
                ax.set_ylabel(y_id)
                ax.set_xlabel(x_id)

                # calculated data in residuals
                x_obs = res_data["x_obs"][k]
                y_obs = res_data["y_obs"][k]

                # FIXME: add residuals

                # plot data
                if y_ref_err is None:
                    ax.plot(x_ref, y_ref, "s", color="black", label="reference_data",
                            markersize=10)
                else:
                    ax.errorbar(
                        x_ref,
                        y_ref,
                        yerr=y_ref_err,
                        marker="s",
                        color="black",
                        label=f"reference_data ± {y_ref_err_type}",
                        markersize=10
                    )
                # plot simulation
                ax.plot(x_obs, y_obs, "-", color="blue", label="observable")
                ax.legend()

            axes[k][1].set_yscale("log")
            axes[k][1].set_ylim(bottom=0.3 * np.nanmin(y_ref))

        self._save_mpl_figure(fig, path=path)

    @timeit
    def plot_fit(self, x: np.ndarray) -> None:
        """Plot residual data for all individual fit mappings.

        :param path:
        :param x: parameters to evaluate

        :return:
        """

        res_data = self.op.residuals(xlog=np.log10(x), complete_data=True)

        for k, mapping_id in enumerate(self.op.mapping_keys):
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(
                nrows=2, ncols=2, figsize=(10, 10)
            )

            # global reference data
            sid = self.op.experiment_keys[k]
            mapping_id = self.op.mapping_keys[k]
            # weights = self.op.weights_points[k]
            x_ref = self.op.x_references[k]
            y_ref = self.op.y_references[k]
            y_ref_err = self.op.y_errors[k]
            x_id = self.op.xid_observable[k]
            y_id = self.op.yid_observable[k]

            # calculated data in residuals
            x_obs = res_data["x_obs"][k]
            y_obs = res_data["y_obs"][k]
            y_obsip = res_data["y_obsip"][k]

            res = res_data["residuals"][k]
            res_weighted = res_data["residuals_weighted"][k]
            res_weighted2 = np.power(res_weighted, 2)

            for ax in (ax1, ax3):
                ax.axhline(y=0, color="black")
                ax.set_ylabel(y_id)
            for ax in (ax3, ax4):
                ax.set_xlabel(x_id)

            for ax in (ax1, ax2):
                ax.set_title(f"{sid}.{mapping_id}")
                plt.setp(ax.get_xticklabels(), visible=False)

                # residuals
                ax.plot(x_ref, res, "o", color="darkorange", label="residuals")
                ax.fill_between(
                    x_ref,
                    res,
                    np.zeros_like(res),
                    alpha=0.4,
                    color="darkorange",
                    label="__nolabel__",
                )

                # prediction
                ax.plot(x_obs, y_obs, "-", color="blue", label="observable")
                ax.plot(x_ref, y_obsip, "o", color="blue", label="interpolation")

                # reference data
                if y_ref_err is None:
                    ax.plot(x_ref, y_ref, "s", color="black", label="reference_data")
                else:
                    ax.errorbar(
                        x_ref,
                        y_ref,
                        yerr=y_ref_err,
                        marker="s",
                        color="black",
                        label="reference_data",
                    )

            for ax in (ax3, ax4):

                ax.plot(
                    x_ref,
                    res_weighted2,
                    "o",
                    color="red",
                    label="(weighted residuals)^2",
                )
                ax.fill_between(
                    x_ref,
                    res_weighted2,
                    np.zeros_like(res),
                    alpha=0.4,
                    color="darkred",
                    label="__nolabel__",
                )

                ax.set_xlim(ax1.get_xlim())

            for ax in (ax1, ax2, ax3, ax4):
                # plt.setp(ax.get_yticklabels(), visible=False)
                # ax.set_ylabel("y")
                # ax.set_yscale("log")
                ax.legend()
            for ax in (ax2, ax4):
                ax.set_yscale("log")

            self._save_mpl_figure(
                fig=fig, path=self.results_dir / f"fit_{sid}_{mapping_id}.{self.image_format}"
            )

    def _cost_df(self, x: np.ndarray) -> pd.DataFrame:
        """Calculate cost dataframe for given parameter set."""
        res_data = self.op.residuals(xlog=np.log10(x), complete_data=True)
        data = []
        for k, _ in enumerate(self.op.mapping_keys):
            data.append(
                {
                    "id": f"{self.op.experiment_keys[k]}_{self.op.mapping_keys[k]}",
                    "experiment": self.op.experiment_keys[k],
                    "mapping": self.op.mapping_keys[k],
                    "cost": res_data["cost"][k],
                    "weight_curve": res_data["weights_curve"][k]
                }
            )

        return pd.DataFrame(
            data, columns=["id", "experiment", "mapping", "cost", "weight_curve"]
        )

    def _datapoints_df(self, x: np.ndarray) -> pd.DataFrame:
        """Calculate data point dataframe for given parameter set."""
        res_data = self.op.residuals(xlog=np.log10(x), complete_data=True)

        data = []
        for k, _ in enumerate(self.op.mapping_keys):
            experiment = self.op.experiment_keys[k]
            mapping = self.op.mapping_keys[k],

            x_ref = self.op.x_references[k]
            y_ref_err = self.op.y_errors[k]
            y_ref_err_type = self.op.y_errors_type[k]
            y_ref = self.op.y_references[k]
            y_obs = res_data["y_obsip"][k]
            residuals = res_data["residuals"][k]
            for ix in range(len(y_obs)):
                if not y_ref_err_type:
                    y_err = np.NaN
                else:
                    y_err = y_ref_err[ix]

                data.append(
                    {
                        "experiment": experiment,
                        "mapping": mapping,
                        "x_ref": x_ref[ix],
                        "y_ref": y_ref[ix],
                        "y_ref_err": y_err,
                        "y_obs": y_obs[ix],
                        "residual": residuals[ix],
                    }
                )

        return pd.DataFrame(
            data, columns=["experiment", "mapping", "x_ref", "y_ref", "y_ref_err",
                           "y_obs", "residual"]
        )

    @timeit
    def plot_datapoint_scatter(self, x: np.ndarray, path: Path = None):
        """Plot cost scatter plot.

        Compares cost of model parameters to the given parameter set.
        """
        fig, ax = self._create_mpl_figure()

        dp: pd.DataFrame = self._datapoints_df(x=x)

        for experiment in sorted(dp.experiment.unique()):
            ax.plot(
                dp.y_ref[dp.experiment == experiment], dp.y_obs[dp.experiment == experiment],
                # yerr=dp.y_ref_err,
                linestyle="",
                marker="o",
                # label="model",
                # color="black",
                markersize="10",
                alpha=0.9,
            )

        min_dp = np.min(
            [
                np.min(dp.y_ref),
                np.min(dp.y_obs),
            ]
        )
        max_dp = np.max(
            [
                np.max(dp.y_ref),
                np.max(dp.y_obs),
            ]
        )

        ax.plot(
            [min_dp * 0.5, max_dp * 2],
            [min_dp * 0.5, max_dp * 2],
            "--",
            color="black",
        )

        for k in range(len(dp)):

            if np.abs(dp.y_ref.values[k]-dp.y_obs.values[k]) / dp.y_ref.values[k] > 0.5:
                ax.annotate(
                    dp.experiment.values[k],
                    xy=(
                        dp.y_ref.values[k],
                        dp.y_obs.values[k],
                    ),
                    fontsize="x-small",
                    alpha=0.9,
                )
        ax.set_xlabel("Experiment $y_{i,k}$")
        ax.set_ylabel("Prediction $f(x_{i,k})$")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.grid()
        if self.show_titles:
            ax.set_title("Data points")
        self._save_mpl_figure(fig=fig, path=path)

    @timeit
    def plot_residual_scatter(self, x: np.ndarray, path: Path = None):
        """Plot residual plot."""
        fig, ax = self._create_mpl_figure()
        dp: pd.DataFrame = self._datapoints_df(x=x)

        xdata = dp.y_ref
        ydata = dp.residual/dp.y_ref

        for experiment in sorted(dp.experiment.unique()):
            ax.plot(
                xdata[dp.experiment == experiment], ydata[dp.experiment == experiment],
                linestyle="",
                marker="o",
                # color="black",
                markersize="10",
                alpha=0.9,
            )

        min_res = np.min(ydata)
        max_res = np.max(ydata)

        ax.fill_between(
            [min_res * 0.5, max_res * 2, max_res * 2, min_res * 0.5],
            [-0.5, -0.5, 0.5, 0.5],
            color="lightgray"
        )
        ax.plot(
            [min_res * 0.5, max_res * 2],
            [0, 0],
            "--",
            color="black",
        )

        for k in range(len(dp)):
            # # errorbars
            # if dp.y_ref_err is not None:
            #     ax.errorbar(
            #         xdata[k], ydata[k],
            #         yerr=dp.y_ref_err[k]/ydata[k],
            #         linestyle="",
            #         marker="",
            #         # label="model",
            #         color="black",
            #         markersize="1",
            #         alpha=0.9,
            #     )

            if np.abs(ydata[k]) > 0.5:
                ax.annotate(
                    dp.experiment.values[k],
                    xy=(
                        xdata[k],
                        ydata[k],
                    ),
                    fontsize="x-small",
                    alpha=0.7,
                )
        ax.set_xlabel("Experiment $y_{i,k}$")
        ax.set_ylabel("Relative residual $\\frac{f(x_{i,k})-y_{i,k}}{y_{i,k}}$")
        ax.set_xscale("log")
        # ax.set_yscale("log")
        ax.grid()
        if self.show_titles:
            ax.set_title("Residuals")
        self._save_mpl_figure(fig=fig, path=path)

    @timeit
    def plot_cost_bar(self, x: np.ndarray, path: Path = None) -> None:
        """Plot cost bar plot.

        Compare costs of all curves.
        """
        costs_x: pd.DataFrame = self._cost_df(x=x)

        fig: Figure
        fig, (ax1, ax2) = plt.subplots(nrows=1, ncols=2, figsize=(7, 5))
        fig.subplots_adjust(left=0.3)

        if self.show_titles:
            fig.suptitle("Curve costs and weights")

        position = list(range(len(costs_x)))
        ticklabels = [f"{costs_x.experiment[k]}|{costs_x.mapping[k]}" for k in range(len(costs_x))]

        ax1.barh(
            position,
            costs_x.cost,
            color="black",
            alpha=0.8
        )

        ax1.set_yticks(position)
        ax1.set_yticklabels(
            ticklabels,
            # rotation=60,
            ha="right",
            fontdict={"fontsize": 8}
        )
        ax1.grid(True, axis="x")
        ax1.set_xlabel("Cost")
        ax1.set_xscale("log")

        ax2.barh(
            position,
            costs_x.weight_curve,
            color="tab:blue",
            alpha=0.8
        )

        ax2.set_yticks(position)
        plt.setp(ax2.get_yticklabels(), visible=False)
        ax2.grid(True, axis="x")
        ax2.set_xlabel("Weight curve: $w_{k}$")
        # ax1.set_xscale("log")

        self._save_mpl_figure(fig=fig, path=path)

    def plot_residual_boxplot(self, x: np.ndarray, path: Path = None) -> None:
        """Plot residual boxplot.

        Compare costs of all curves.
        """
        costs_x: pd.DataFrame = self._cost_df(x=x)

        fig, ax = self._create_mpl_figure()
        fig.subplots_adjust(left=0.5, bottom=0.1)
        if self.show_titles:
            ax.set_title("Residual contribution")

        position = list(range(1, len(costs_x)+1))
        ticklabels = [f"{costs_x.experiment[k]}|{costs_x.mapping[k]}" for k in range(len(costs_x))]

        res_data = self.op.residuals(xlog=np.log10(x), complete_data=True)

        box_data = []
        for k, mapping_id in enumerate(self.op.mapping_keys):
            res_weighted = res_data["residuals_weighted"][k]
            res_weighted2 = np.power(res_weighted, 2)
            box_data.append(res_weighted2)
            ax.plot(res_weighted2, (k+0.7)*np.ones_like(res_weighted2),
                    linestyle="", marker="s", markeredgecolor="black",
                    color="tab:blue", markersize=3
                    )

        ax.boxplot(
            # position,
            box_data,
            vert=False
            # color="black",
            # alpha=0.8
        )

        ax.set_yticks(position)
        ax.set_yticklabels(
            ticklabels,
            # rotation=60,
            ha="right",
            fontdict={"fontsize": 8}
        )
        ax.grid(True, axis="x")
        ax.set_xlabel("Weighted residuals^2\n$(w_{k} \cdot w_{i,k} (f(x_{i,k}) - y_{i,k}))^2$")
        ax.set_xscale("log")
        self._save_mpl_figure(fig=fig, path=path)

    @timeit
    def plot_cost_scatter(self, x: np.ndarray, path: Path = None):
        """Plot cost scatter plot.

        Compares cost of model parameters to the given parameter set.
        """
        costs_xmodel: pd.DataFrame = self._cost_df(x=self.op.xmodel)
        costs_x: pd.DataFrame = self._cost_df(x=x)

        min_cost = np.min(
            [
                np.min(costs_xmodel.cost),
                np.min(costs_x.cost),
            ]
        )
        max_cost = np.max(
            [
                np.max(costs_xmodel.cost),
                np.max(costs_x.cost),
            ]
        )

        fig, ax = self._create_mpl_figure()
        ax.plot(
            [min_cost * 0.5, max_cost * 2],
            [min_cost * 0.5, max_cost * 2],
            "--",
            color="black",
        )
        if self.show_titles:
            ax.set_title("Cost improvement")

        for k, exp_key in enumerate(self.op.experiment_keys):
            ax.plot(
                costs_xmodel.cost[k],
                costs_x.cost[k],
                linestyle="",
                marker="o",
                # label="model",
                color="tab:red" if costs_xmodel.cost[k] < costs_x.cost[k] else "tab:blue",
                markersize="10",
                alpha=0.8,
            )

        for k, exp_key in enumerate(self.op.experiment_keys):
            ax.annotate(
                exp_key,
                xy=(
                    costs_xmodel.cost[k],
                    costs_x.cost[k],
                ),
                fontsize="x-small",
                alpha=0.7,
            )
        ax.set_xlabel("Initial cost")
        ax.set_ylabel("Cost after fit")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.grid()


        legend_elements = [
                Line2D([0], [0], marker='o', color='tab:red', label='Increased cost',
                       markersize=10),
                Line2D([0], [0], marker='o', color='tab:blue', label='Decreased cost',
                   markersize=10),
        ]

        ax.legend(handles=legend_elements)
        self._save_mpl_figure(fig=fig, path=path)

    @timeit
    def plot_waterfall(self, path: Path):
        """Create waterfall plot for the fit results.

        Plots the optimization runs sorted by cost.
        """
        fig, ax = self._create_mpl_figure()
        if self.show_titles:
            ax.set_title("Waterfall plot")
        ax.plot(
            range(self.optres.size),
            1 + (self.optres.df_fits.cost - self.optres.df_fits.cost.iloc[0]),
            "-o",
            color="black",
        )
        ax.set_xlabel("Index (ordered optimizer run)")
        ax.set_ylabel("Offset cost value (relative to best start)")
        ax.set_yscale("log")
        self._save_mpl_figure(fig, path=path)

    @timeit
    def plot_traces(self, path: Path) -> None:
        """Plot optimization traces.

        Optimization time course of costs.
        """
        fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(5, 5))
        if self.show_titles:
            ax.set_title("Optimization traces")
        for run in range(self.optres.size):
            df_run = self.optres.df_traces[self.optres.df_traces.run == run]
            ax.plot(range(len(df_run)), df_run.cost, "-", alpha=0.8)

        for run in range(self.optres.size):
            df_run = self.optres.df_traces[self.optres.df_traces.run == run]
            ax.plot(
                len(df_run) - 1, df_run.cost.iloc[-1], "o", color="black", alpha=0.8
            )

        ax.set_xlabel("Optimization step")
        ax.set_ylabel("Cost")
        ax.set_yscale("log")

        self._save_mpl_figure(fig, path=path)

    @timeit
    def plot_correlation(
        self,
        path: Path,
    ) -> None:
        """Plot correlation of parameters for analysis."""
        df = self.optres.df_fits
        parameters = self.optres.parameters

        pids = [p.pid for p in parameters]
        npars = len(pids)
        sns.set(style="ticks", color_codes=True)
        fig, axes = plt.subplots(
            nrows=npars, ncols=npars, figsize=(5 * npars, 5 * npars)
        )
        cost_normed = df.cost - df.cost.min()
        cost_normed = 1 - cost_normed / cost_normed.max()

        size = np.power(15 * cost_normed, 2)

        bound_kwargs = {"color": "darkgrey", "linestyle": "--", "alpha": 1.0}

        for kx, pidx in enumerate(pids):
            for ky, pidy in enumerate(pids):
                if npars == 1:
                    ax = axes
                else:
                    ax = axes[ky][kx]

                # optimal values
                if kx > ky:
                    ax.set_xlabel(pidx)
                    # ax.set_xlim(self.parameters[kx].lower_bound, self.parameters[kx].upper_bound)
                    ax.axvline(x=parameters[kx].lower_bound, **bound_kwargs)
                    ax.axvline(x=parameters[kx].upper_bound, **bound_kwargs)
                    ax.set_ylabel(pidy)
                    # ax.set_ylim(self.parameters[ky].lower_bound, self.parameters[ky].upper_bound)
                    ax.axhline(y=parameters[ky].lower_bound, **bound_kwargs)
                    ax.axhline(y=parameters[ky].upper_bound, **bound_kwargs)

                    # start values
                    xall = []
                    yall = []
                    xstart_all = []
                    ystart_all = []
                    for ks in range(len(size)):
                        x = df.x[ks][kx]
                        y = df.x[ks][ky]
                        xall.append(x)
                        yall.append(y)
                        if "x0" in df.columns:
                            xstart = df.x0[ks][kx]
                            ystart = df.x0[ks][ky]
                            xstart_all.append(xstart)
                            ystart_all.append(ystart)

                    # start point
                    ax.plot(
                        xstart_all,
                        ystart_all,
                        "^",
                        color="black",
                        markersize=2,
                        alpha=0.5,
                    )
                    # optimal values
                    ax.scatter(
                        df[pidx], df[pidy], c=df.cost, s=size, alpha=0.9, cmap="jet"
                    ),

                    ax.plot(
                        self.optres.xopt[kx],
                        self.optres.xopt[ky],
                        "s",
                        color="darkgreen",
                        markersize=30,
                        alpha=0.7,
                    )

                if kx == ky:
                    ax.set_xlabel(pidx)
                    ax.axvline(x=parameters[kx].lower_bound, **bound_kwargs)
                    ax.axvline(x=parameters[kx].upper_bound, **bound_kwargs)
                    # ax.set_xlim(self.parameters[kx].lower_bound,
                    #            self.parameters[kx].upper_bound)
                    ax.set_ylabel("cost")
                    ax.plot(
                        df[pidx],
                        df.cost,
                        color="black",
                        marker="s",
                        linestyle="None",
                        alpha=1.0,
                    )

                # traces (walk through cost function)
                if kx < ky:
                    ax.set_xlabel(pidy)
                    ax.set_ylabel(pidx)
                    ax.axvline(x=parameters[ky].lower_bound, **bound_kwargs)
                    ax.axvline(x=parameters[ky].upper_bound, **bound_kwargs)
                    ax.axhline(y=parameters[kx].lower_bound, **bound_kwargs)
                    ax.axhline(y=parameters[kx].upper_bound, **bound_kwargs)

                    # ax.plot([ystart, y], [xstart, x], "-", color="black", alpha=0.7)

                    for run in range(self.optres.size):
                        df_run = self.optres.df_traces[self.optres.df_traces.run == run]
                        # ax.plot(df_run[pidy], df_run[pidx], '-', color="black", alpha=0.3)
                        ax.scatter(
                            df_run[pidy],
                            df_run[pidx],
                            c=df_run.cost,
                            cmap="jet",
                            marker="s",
                            alpha=0.8,
                        )

                    # end point
                    # ax.plot(yall, xall, "o", color="black", markersize=10, alpha=0.9)
                    ax.plot(
                        self.optres.xopt[ky],
                        self.optres.xopt[kx],
                        "s",
                        color="darkgreen",
                        markersize=30,
                        alpha=0.7,
                    )

                ax.set_xscale("log")
                if kx != ky:
                    ax.set_yscale("log")
                if kx == ky:
                    ax.set_yscale("log")

        # correct scatter limits
        for kx, _pidx in enumerate(pids):
            for ky, _pidy in enumerate(pids):
                if kx < ky:
                    axes[ky][kx].set_xlim(axes[kx][ky].get_xlim())
                    axes[ky][kx].set_ylim(axes[kx][ky].get_ylim())

        self._save_mpl_figure(fig=fig, path=path)
