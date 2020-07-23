import logging
from typing import List
import pandas as pd
import numpy as np
import xarray as xr
import itertools
from scipy import interpolate

import matplotlib

from sbmlsim.result import XResult
from sbmlsim.data import DataSet, Data
from sbmlsim.plot import Figure, SubPlot, Plot, Curve, Axis


from matplotlib.pyplot import GridSpec
from matplotlib import pyplot as plt
from matplotlib.pyplot import Figure as FigureMPL

from sbmlsim.utils import deprecated

logger = logging.getLogger(__name__)

kwargs_data = {'marker': 's', 'linestyle': '--', 'linewidth': 1, 'capsize': 3}
kwargs_sim = {'marker': None, 'linestyle': '-', 'linewidth': 2}


def interp(x, xp, fp):
    """ Interpolation for speedup of plots

    :param x:
    :param xp:
    :param fp:
    :return:
    """
    # y = np.interp(x=x, xp=xp, fp=fp)
    tck = interpolate.splrep(xp, fp, s=0)

    y = interpolate.splev(x, tck, der=0)
    return y


class MatplotlibFigureSerializer(object):
    """
    Serializing figure to matplotlib figure.
    """
    def to_figure(figure: Figure) -> plt.Figure:
        """Convert sbmlsim.Figure to matplotlib figure."""

        # create new figure
        fig = plt.figure(figsize=(figure.width, figure.height),
                         dpi=Figure.fig_dpi, facecolor=Figure.fig_facecolor)  # type: plt.Figure

        if figure.name:
            fig.suptitle(figure.name, fontsize=Figure.fig_titlesize,
                         fontweight=Figure.fig_titleweight)

        # create grid for figure
        gs = GridSpec(figure.num_rows, figure.num_cols, figure=fig)

        def get_scale(axis):
            if axis.scale == Axis.AxisScale.LINEAR:
                return "linear"
            elif axis.scale == Axis.AxisScale.LOG10:
                return "log"
            else:
                raise ValueError(f"Unsupported axis scale: '{axis.scale}'")

        for subplot in figure.subplots:  # type: SubPlot

            ridx = subplot.row - 1
            cidx = subplot.col - 1
            ax = fig.add_subplot(
                gs[ridx:ridx+subplot.row_span, cidx:cidx+subplot.col_span]
            )  # type: plt.Axes

            plot = subplot.plot
            xax = plot.xaxis  # type: Axis
            yax = plot.yaxis  # type: Axis

            # units
            if xax is None:
                logger.warning(f"No xaxis in plot: {subplot}")
                ax.spines['bottom'].set_color(Figure.fig_facecolor)
                ax.spines['top'].set_color(Figure.fig_facecolor)
            if yax is None:
                logger.warning(f"No yaxis in plot: {subplot}")
                ax.spines['right'].set_color(Figure.fig_facecolor)
                ax.spines['left'].set_color(Figure.fig_facecolor)
            if (not xax) or (not yax):
                if len(plot.curves) > 0:
                    raise ValueError(f"xaxis and yaxis are required for plotting curves, but "
                                     f"'xaxis={xax}' and 'yaxis={yax}'.")

            xunit = xax.unit if xax else None
            yunit = yax.unit if yax else None

            for curve in plot.curves:
                # TODO: sort by order

                kwargs = {}
                if curve.style:
                    kwargs = curve.style.to_mpl_kwargs()

                # mean quantity
                x = curve.x.get_data(to_units=xunit)
                y = curve.y.get_data(to_units=yunit)

                # additional data exists in xres
                # FIXME: get access to the full data matrix and support plotting
                # if isinstance(x, XResult):
                #    x_mean = x.mean(dim=self._op_dims(), skipna=True).values * self.ureg(self.udict[key])

                x_std, x_min, x_max = None, None, None
                if curve.x.dtype == Data.Types.TASK:
                    data = curve.x
                    xres = data.experiment.results[data.task_id]  # type: XResult
                    if not xres.is_timecourse():
                        x_std = xres.dim_std(data.index).to(xunit)
                        x_min = xres.dim_min(data.index).to(xunit)
                        x_max = xres.dim_max(data.index).to(xunit)

                y_std, y_min, y_max = None, None, None
                if curve.y.dtype == Data.Types.TASK:
                    data = curve.y
                    xres = data.experiment.results[data.task_id]  # type: XResult
                    if not xres.is_timecourse():
                        y_std = xres.dim_std(data.index).to(yunit)
                        y_min = xres.dim_min(data.index).to(yunit)
                        y_max = xres.dim_max(data.index).to(yunit)
                # print(y_std)

                xerr = None
                if curve.xerr is not None:
                    xerr = curve.xerr.get_data(to_units=xunit)

                yerr = None
                if curve.yerr is not None:
                    yerr = curve.yerr.get_data(to_units=yunit)


                # use interpolation
                # show_figures            4.7645 [s]
                # save_figures           26.8983 [s]
                # run                    32.5651 [s]
                # run_experiments        32.5654 [s]
                x_ip = np.linspace(start=x.magnitude[0], stop=x.magnitude[-1], num=100)

                if (y_min is not None) and (y_max is not None):
                    # areas can be very slow to render!
                    # ax.fill_between(x.magnitude, y_min.magnitude, y_max.magnitude,
                    ax.fill_between(
                        x_ip,
                        interp(x_ip, x.magnitude, y_min.magnitude),
                        interp(x_ip, x.magnitude, y_max.magnitude),
                        color=kwargs.get("color", "black"),
                        alpha=0.1, label="__nolabel__"
                    )

                if y_std is not None:
                    # areas can be very slow to render!
                    # ax.plot(x.magnitude, y.magnitude, label="curve.name", **kwargs)
                    y_ip = interp(x=x_ip, xp=x.magnitude, fp=y.magnitude)
                    y_std_ip = interp(x=x_ip, xp=x.magnitude, fp=y_std.magnitude)

                    # ax.fill_between(x.magnitude, y.magnitude - y_std.magnitude, y.magnitude + y_std.magnitude,
                    ax.fill_between(
                        x_ip, y_ip - y_std_ip, y_ip + y_std_ip,
                        color=kwargs.get("color", "black"),
                        alpha=0.25, label="__nolabel__"
                    )

                if (xerr is None) and (yerr is None):
                    if y_std is None:
                        # single trajectory
                        ax.plot(x.magnitude, y.magnitude, label=curve.name, **kwargs)
                elif yerr is not None:
                    ax.errorbar(x.magnitude, y.magnitude, yerr.magnitude,
                                label=curve.name, **kwargs)

            # plot settings
            if plot.name and plot.title_visible:
                ax.set_title(plot.name)

            if xax:
                ax.set_xscale(get_scale(xax))
                ax.set_xlim(xmin=xax.min, xmax=xax.max)

                if xax.label_visible:
                    if xax.name:
                        ax.set_xlabel(f"{xax.name} [{xax.unit}]")
                if not xax.ticks_visible:
                    ax.set_xticklabels([])  # hide ticks

            if yax:
                ax.set_yscale(get_scale(yax))
                ax.set_ylim(ymin=yax.min, ymax=yax.max)

                if yax.label_visible:
                    if yax.name:
                        ax.set_ylabel(f"{yax.name} [{yax.unit}]")
                if not yax.ticks_visible:
                    ax.set_yticklabels([])  # hide ticks

            # recompute the ax.dataLim
            # ax.relim()
            # update ax.viewLim using the new dataLim
            # ax.autoscale_view()

            # figure styling
            ax.title.set_fontsize(Figure.axes_titlesize)
            ax.title.set_fontweight(Figure.axes_titleweight)
            ax.xaxis.label.set_fontsize(Figure.axes_labelsize)
            ax.xaxis.label.set_fontweight(Figure.axes_labelweight)
            ax.yaxis.label.set_fontsize(Figure.axes_labelsize)
            ax.yaxis.label.set_fontweight(Figure.axes_labelweight)
            ax.tick_params(axis='x', labelsize=Figure.xtick_labelsize)
            ax.tick_params(axis='y', labelsize=Figure.ytick_labelsize)

            # hide none-existing axes
            if xax is None:
                ax.tick_params(axis='x', colors=Figure.fig_facecolor)
                ax.xaxis.label.set_color(Figure.fig_facecolor)
            if yax is None:
                ax.tick_params(axis='y', colors=Figure.fig_facecolor)
                ax.yaxis.label.set_color(Figure.fig_facecolor)

            xgrid = xax.grid if xax else None
            ygrid = yax.grid if yax else None

            if xgrid and ygrid:
                ax.grid(True, axis="both")
            elif xgrid:
                ax.grid(True, axis="x")
            elif ygrid:
                ax.grid(True, axis="y")
            else:
                ax.grid(False)

            if plot.legend:
                ax.legend(fontsize=Figure.legend_fontsize, loc=Figure.legend_loc)

        fig.subplots_adjust(wspace=0.3, hspace=0.3)
        return fig


def add_line(ax: plt.Axes, xres: XResult,
             xid: str, yid: str,
             xunit, yunit,
             yres: XResult = None,
             xf=1.0, yf=1.0, all_lines=False,
             label='__nolabel__', **kwargs):
    """ Adding information from a simulation result to a matplotlib figure.

    This is deprecated the sbmlsim.plot.plotting Figure, Plot, Curves, ...
    should be used.

    :param ax: axis to plot to
    :param xres: Result data structure
    :param xid: id for xdata
    :param yid: id for ydata
    :param all_lines: plot all individual lines
    :param xunit: target unit for x
    :param yunit: target unit for y

    :param color:
    :return:
    """
    if not isinstance(xres, XResult):
        raise ValueError(f"Only XResult supported in plotting, but found: "
                         f"'{type(xres)}'")

    # mean data with units
    x = xres.dim_mean(xid)
    y = xres.dim_mean(yid) * yf

    # reduction over all dimensions (not necessarily what is wanted !)
    ystd = xres.dim_std(yid) * yf
    ymin = xres.dim_min(yid) * yf
    ymax = xres.dim_max(yid) * yf

    # convert units to requested units
    if xunit:
        x = x.to(xunit)
    if yunit:
        y = y.to(yunit)
        ystd = ystd.to(yunit)
        ymin = ymin.to(yunit)
        ymax = ymax.to(yunit)

    # get next color
    prop_cycler = ax._get_lines.prop_cycler
    color = kwargs.get("color", next(prop_cycler)['color'])
    kwargs["color"] = color

    if all_lines:
        Q_ = xres.ureg.Quantity
        # iterate over all dimensions besides time
        # all combinations
        dims = xres._redop_dims()
        index_vecs = [xres.coords[dim].values for dim in dims]
        indices = list(itertools.product(*index_vecs))
        for k, item in enumerate(indices):
            d = dict(zip(dims, item))
            xi = Q_(xres[xid].isel(d).values, xres.udict[xid])
            yi = Q_(xres[yid].isel(d).values, xres.udict[yid])
            # FIXME: these conversions should not be necessary
            if xunit:
                xi = xi.to(xunit)
            if yunit:
                yi = yi.to(yunit)
            if k != 0:
                label = "__nolabel__"
            ax.plot(xi.magnitude, yi.magnitude, color=color, label=label)

    else:
        # calculate rational ysd, i.e., if the value if y + ysd is larger than ymax take ymax
        ysd_up = y + ystd
        ysd_up[ysd_up > ymax] = ymax[ysd_up > ymax]
        ysd_down = y - ystd
        ysd_down[ysd_down < ymin] = ymin[ysd_down < ymin]

        ax.fill_between(x.magnitude, ysd_down.magnitude, ysd_up.magnitude,
                        color=color, alpha=0.4, label="__nolabel__")
        ax.fill_between(x.magnitude, ysd_up.magnitude, ymax.magnitude,
                        color=color, alpha=0.1, label="__nolabel__")
        ax.fill_between(x.magnitude, ysd_down.magnitude, ymin.magnitude,
                        color=color, alpha=0.1, label="__nolabel__")

        ax.plot(x.magnitude, ysd_up.magnitude, '-', label="__nolabel__",
                alpha=0.8, **kwargs)
        ax.plot(x.magnitude, ysd_down.magnitude, '-', label="__nolabel__",
                alpha=0.8, **kwargs)
        ax.plot(x.magnitude, ymin.magnitude, '-', label="__nolabel__",
                alpha=0.6, **kwargs)
        ax.plot(x.magnitude, ymax.magnitude, '-', label="__nolabel__",
                alpha=0.6, **kwargs)

        # curve
        ax.plot(x.magnitude, y.magnitude, '-', label=label, **kwargs)


@deprecated
def add_data(ax: plt.Axes, data: DataSet,
             xid: str, yid: str, yid_sd=None, yid_se=None, count=None,
             xunit=None, yunit=None, xf=1.0, yf=1.0, label='__nolabel__', **kwargs):
    """ Add experimental data to a matplotlib axes.

    This is deprecated the plotting Figure, Plot, Curves, should be used
    instead.

    :param ax:
    :param data:
    :param xid:
    :param yid:
    :param xunit:
    :param yunit:
    :param label:
    :param kwargs:
    :return:
    """
    if isinstance(data, DataSet):
        dset = data
    elif isinstance(data, pd.DataFrame):
        dset = DataSet.from_df(df=data, udict=None, ureg=None)

    if dset.empty:
        logger.error(f"Empty dataset in adding data: {dset}")

    if abs(xf-1.0) > 1E-8:
        logger.warning("xf attributes are deprecated, use units instead.")
    if abs(yf - 1.0) > 1E-8:
        logger.warning("yf attributes are deprecated, use units instead.")

    # add default styles
    if 'marker' not in kwargs:
        kwargs['marker'] = 's'
    if 'linestyle' not in kwargs:
        kwargs['linestyle'] = '--'

    # data with units
    x = dset[xid].values * dset.ureg(dset.udict[xid]) * xf
    y = dset[yid].values * dset.ureg(dset.udict[yid]) * yf
    y_err = None
    y_err_type = None
    if yid_sd:
        y_err = dset[yid_sd].values * dset.ureg(dset.udict[yid]) * yf
        y_err_type = "SD"
    elif yid_se:
        y_err = dset[yid_se].values * dset.ureg(dset.udict[yid]) * yf
        y_err_type = "SE"

    # convert
    if xunit:
        x = x.to(xunit)
    if yunit:
        y = y.to(yunit)
        if y_err is not None:
            y_err = y_err.to(yunit)

    # labels
    if label != "__nolabel__":
        if y_err_type:
            label = f"{label} ± {y_err_type}"
        if count:
            label += f" (n={count})"

    # plot
    if y_err is not None:
        if 'capsize' not in kwargs:
            kwargs['capsize'] = 3
        ax.errorbar(x.magnitude, y.magnitude, y_err.magnitude, label=label, **kwargs)
    else:
        ax.plot(x, y, label=label, **kwargs)



