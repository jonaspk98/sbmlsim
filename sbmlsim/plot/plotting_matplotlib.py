import logging
import pandas as pd

from sbmlsim.result import XResult
from sbmlsim.data import DataSet
from sbmlsim.plot import Figure, SubPlot, Plot, Curve, Axis
from matplotlib import pyplot as plt

logger = logging.getLogger(__name__)

kwargs_data = {'marker': 's', 'linestyle': '--', 'linewidth': 1, 'capsize': 3}
kwargs_sim = {'marker': None, 'linestyle': '-', 'linewidth': 2}

# global settings for plots
plt.rcParams.update({
    'axes.labelsize': 'large',
    'axes.labelweight': 'bold',
    'axes.titlesize': 'medium',
    'axes.titleweight': 'bold',
    'legend.fontsize': 'small',
    'xtick.labelsize': 'large',
    'ytick.labelsize': 'large',
    'figure.facecolor': '1.00',
    'figure.dpi': '72',
})

from matplotlib.pyplot import GridSpec


def to_figure(figure: Figure):
    """Convert sbmlsim.Figure to matplotlib figure."""
    fig = plt.figure(figsize=(figure.width, figure.height))  # type: plt.Figure
    # FIXME: check that the settings are applied
    fig.subplots_adjust(wspace=0.3, hspace=0.3)

    gs = GridSpec(figure.num_rows, figure.num_cols, figure=fig)
    # TODO: subplots adjust

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
        # axes labels and legends
        plot = subplot.plot
        if plot.name:
            ax.set_title(plot.name)
        xgrid = False
        if plot.xaxis:
            xax = plot.xaxis  # type: Axis
            ax.set_xscale(get_scale(xax))
            if xax.name:
                ax.set_xlabel(f"{xax.name} [{xax.unit}]")
            if xax.min:
                ax.set_xlim(left=xax.min)
            if xax.max:
                ax.set_xlim(right=xax.max)
            if xax.grid:
                xgrid = True

        ygrid = False
        if plot.yaxis:
            yax = plot.yaxis  # type: Axis
            ax.set_yscale(get_scale(yax))
            if yax.name:
                ax.set_ylabel(f"{yax.name} [{yax.unit}]")
            if yax.min:
                ax.set_ylim(bottom=yax.min)
            if yax.max:
                ax.set_ylim(top=xax.max)
            if yax.grid:
                ygrid = True

        if xgrid and ygrid:
            ax.grid(True, axis="both")
        elif xgrid:
            ax.grid(True, axis="x")
        elif ygrid:
            ax.grid(True, axis="y")
        else:
            ax.grid(False)

        for curve in plot.curves:
            # TODO: sort by order

            kwargs = {}
            if curve.style:
                kwargs = curve.style.to_mpl_kwargs()
            x = curve.x.data
            y = curve.y.data

            yerr = None
            if curve.yerr is not None:
                yerr = curve.yerr.data

            # FIXME: x - errorbars
            xerr = None
            if curve.xerr is not None:
                xerr = curve.xerr.data

            if (xerr is None) and (yerr is None):
                ax.plot(x.magnitude, y.magnitude, label=curve.name, **kwargs)
            elif (xerr is None) and (yerr is not None):
                ax.errorbar(x.magnitude, y.magnitude, yerr.magnitude,
                            label=curve.name, **kwargs)

        if plot.legend:
            ax.legend()

    return fig



def add_data(ax, data: DataSet,
             xid: str, yid: str, yid_sd=None, yid_se=None, count=None,
             xunit=None, yunit=None,
             xf=1.0, yf=1.0,
             label='__nolabel__', **kwargs):
    """ Add experimental data

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


def add_line(ax, data: XResult,
             xid: str, yid: str,
             xunit=None, yunit=None, xf=1.0, yf=1.0, all_lines=False,
             label='__nolabel__', **kwargs):
    """
    :param ax: axis to plot to
    :param data: Result data structure
    :param xid: id for xdata
    :param yid: id for ydata
    :param all_lines: plot all individual lines
    :param xunit: target unit for x (conversion is performed automatically)
    :param yunit: target unit for y (conversion is performed automatically)

    :param color:
    :return:
    """
    if not isinstance(data, XResult):
        raise ValueError("Only Result objects supported in plotting.")
    if (hasattr(xf, "magnitude") and abs(xf.magnitude-1.0) > 1E-8) or abs(xf-1.0) > 1E-8:
        logger.warning("xf attributes are deprecated, use units instead.")
    if (hasattr(yf, "magnitude") and abs(yf.magnitude-1.0) > 1E-8) or abs(yf-1.0) > 1E-8:
        logger.warning("yf attributes are deprecated, use units instead.")

    # data with units
    x = data.mean[xid].values * data.ureg(data.udict[xid]) * xf
    y = data.mean[yid].values * data.ureg(data.udict[yid]) * yf
    y_sd = data.std[yid].values * data.ureg(data.udict[yid]) * yf
    y_min = data.min[yid].values * data.ureg(data.udict[yid]) * yf
    y_max = data.max[yid].values * data.ureg(data.udict[yid]) * yf

    # convert
    if xunit:
        x = x.to(xunit)
    if yunit:
        y = y.to(yunit)
        y_sd = y_sd.to(yunit)
        y_min = y_min.to(yunit)
        y_max = y_min.to(yunit)

    # get next color
    prop_cycler = ax._get_lines.prop_cycler
    color = kwargs.get("color", next(prop_cycler)['color'])
    kwargs["color"] = color

    if all_lines:
        for df in data.frames:
            xk = df[xid].values * data.ureg(data.udict[xid]) * xf
            yk = df[yid].values * data.ureg(data.udict[yid]) * yf
            xk = xk.to(xunit)
            yk = yk.to(yunit)
            ax.plot(xk, yk, '-', label="{}".format(label), **kwargs)
    else:
        if len(data) > 1:
            # FIXME: std areas should be within min/max areas!
            ax.fill_between(x, y - y_sd, y + y_sd, color=color, alpha=0.4, label="__nolabel__")

            ax.fill_between(x, y + y_sd, y_max, color=color, alpha=0.2, label="__nolabel__")
            ax.fill_between(x, y - y_sd, y_min, color=color, alpha=0.2, label="__nolabel__")

        ax.plot(x, y, '-', label="{}".format(label), **kwargs)
