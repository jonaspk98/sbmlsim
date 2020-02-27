"""
Base classes for storing plotting information.
"""
from typing import List, Dict
import logging
import pandas as pd
from dataclasses import dataclass
from enum import Enum

from sbmlsim.result import Result
from sbmlsim.data import DataSet, Data

from matplotlib.colors import to_rgba, to_hex

logger = logging.getLogger(__name__)


class Base(object):
    """

    """
    def __init__(self, sid: str, name: str):
        self.sid = sid
        self.name = name


class LineType(Enum):
    NONE = 1
    SOLID = 2
    DASH = 3
    DOT = 4
    DASHDOT = 5
    DASHDOTDOT = 6


class MarkerType(Enum):
    NONE = 1
    SQUARE = 2
    CIRCLE = 3
    DIAMOND = 4
    XCROSS = 5
    PLUS = 6
    STAR = 7
    TRIANGLEUP = 8
    TRIANGLEDOWN = 9
    TRIANGLELEFT = 10
    TRIANGLERIGHT = 11
    HDASH = 12
    VDASH = 13


class ColorType(object):
    def __init__(self, color: str):
        self.color = color


@dataclass
class Line(object):
    type: LineType
    color: ColorType
    thickness: float


@dataclass
class Marker(object):
    size: float
    type: MarkerType
    fill: ColorType
    line_color: ColorType
    line_thickness: float = 1.0


@dataclass
class Fill(object):
    color: ColorType
    second_color: ColorType = None


class Style(Base):
    def __init__(self, sid: str = None,
                 name: str = None,
                 base_style: 'Style' = None,
                 line: Line = None,
                 marker: Marker = None,
                 fill: Fill = None):
        super(Style, self).__init__(sid, name)
        self.line = line
        self.marker = marker
        self.fill = fill

    # https://matplotlib.org/3.1.0/gallery/lines_bars_and_markers/linestyles.html
    MPL2SEDML_LINESTYLE_MAPPING = {
        '-': LineType.SOLID,
        'solid': LineType.SOLID,
        '.': LineType.DOT,
        'dotted': LineType.DOT,
        '--': LineType.DASH,
        'dashed': LineType.DASH.DASH,
        '-.': LineType.DASHDOT,
        'dashdot': LineType.DASHDOT,
        'dashdotdotted': LineType.DASHDOTDOT
    }
    SEDML2MPL_LINESTYLE_MAPPING = {v: k for (k, v) in MPL2SEDML_LINESTYLE_MAPPING.items()}

    MPL2SEDML_MARKER_MAPPING = {
        '': MarkerType.NONE,
        's': MarkerType.SQUARE,
        'o': MarkerType.CIRCLE,
        'D': MarkerType.DIAMOND,
        'x': MarkerType.XCROSS,
        '+': MarkerType.PLUS,
        '*': MarkerType.STAR,
        '^': MarkerType.TRIANGLEUP,
        'v': MarkerType.TRIANGLEDOWN,
        '<': MarkerType.TRIANGLELEFT,
        '>': MarkerType.TRIANGLERIGHT,
        '_': MarkerType.HDASH,
        '|': MarkerType.VDASH,
    }
    SEDML2MPL_MARKER_MAPPING = {v: k for (k,v) in MPL2SEDML_MARKER_MAPPING.items()}

    def to_mpl_kwargs(self) -> Dict:
        """Convert to matplotlib plotting arguments"""
        kwargs = {}
        if self.line:
            if self.line.color:
                kwargs["color"] = self.line.color
            if self.line.type:
                kwargs["linestyle"] = Style.SEDML2MPL_LINESTYLE_MAPPING[self.line.type]
            if self.line.thickness:
                kwargs["linewidth"] = self.line.thickness
        if self.marker:
            if self.marker.type:
                kwargs["marker"] = Style.SEDML2MPL_MARKER_MAPPING[self.marker.type]
            if self.marker.size:
                kwargs["markersize"] = self.marker.size
            if self.marker.fill:
                kwargs["markerfacecolor"] = self.marker.fill
            if self.marker.line_color:
                kwargs["markeredgecolor"] = self.marker.line_color
            if self.marker.line_thickness:
                kwargs["markeredgewidth"] = self.marker.line_thickness

        if self.fill:
            pass

        return kwargs

    @staticmethod
    def from_mpl_kwargs(**kwargs) -> 'Style':

        # FIXME: handle alpha colors
        # https://matplotlib.org/3.1.0/tutorials/colors/colors.html


        alpha = kwargs.get("alpha", 1.0)
        color = kwargs.get("color", None)
        if color:
            color = to_rgba(color, alpha)
            color = to_hex(color, keep_alpha=True)


        # Line
        linestyle = kwargs.get("linestyle", '-')
        if linestyle is not None:
            linestyle = Style.MPL2SEDML_LINESTYLE_MAPPING[linestyle]

        line = Line(
            color=color,
            type=linestyle,
            thickness=kwargs.get("linewidth", 1.0)
        )

        # Marker
        marker_symbol = kwargs.get("marker", None)
        if marker_symbol is not None:
            marker_symbol = Style.MPL2SEDML_MARKER_MAPPING[marker_symbol]
        marker = Marker(
            size=kwargs.get("markersize", None),
            type=marker_symbol,
            fill=kwargs.get("markerfacecolor", color),
            line_color=kwargs.get("markeredgecolor", None),
            line_thickness=kwargs.get("markeredgewidth", None)
        )

        # Fill
        # FIXME: implement

        return Style(line=line, marker=marker, fill=None)


class Axis(Base):
    def __init__(self, name: str = None, unit: str = None):
        super(Axis, self).__init__(None, name)
        if unit is None:
            unit = "?"
        self.unit = unit

    @property
    def label(self):
        return f"{self.name} [{self.unit}]"



class AbstractCurve(Base):
    def __init__(self, sid: str, name: str,
                 x: Data, order: int, style: Style, yaxis: Axis):
        """
        :param sid:
        :param name: label of the curve
        :param xdata:
        :param order:
        :param style:
        :param yaxis:
        """
        super(AbstractCurve, self).__init__(sid, name)
        self.x = x
        self.order = order
        self.style = style
        self.yaxis = yaxis


class Curve(AbstractCurve):
    def __init__(self,
                 x: Data, y: Data, xerr: Data=None, yerr: Data=None,
                 order=None, style: Style=None, yaxis=None, **kwargs):
        super(Curve, self).__init__(None, None, x, order, style, yaxis)
        self.y = y
        self.xerr = xerr
        self.yerr = yerr

        if "label" in kwargs:
            self.name = kwargs["label"]

        # parse additional arguments and create style
        self.style = Style.from_mpl_kwargs(**kwargs)

    def __str__(self):
        info = f"x: {self.x}\ny: {self.y}\nxerr: {self.xerr}\nyerr: {self.yerr}"
        return info


class Plot(Base):
    """
    A plot is the basic element of a plot.
    This corresponds to an axis.
    """
    def __init__(self, sid: str, name: str = None,
                 legend: bool = False,
                 xaxis: Axis = None,
                 yaxis: Axis = None,
                 curves: List[Curve] = None):
        """
        :param sid:
        :param name: title of the plot
        :param legend:
        :param xaxis:
        :param yaxis:
        :param curves:
        """
        super(Plot, self).__init__(sid, name)
        if curves is None:
            curves = list()
        self.legend = legend
        self.xaxis = xaxis
        self.yaxis = yaxis
        self.curves = curves

    def get_title(self):
        return self.name

    def set_title(self, name: str):
        self.name = name

    def set_xaxis(self, label: str, unit: str=None):
        self.xaxis = Axis(name=label, unit=unit)

    def set_yaxis(self, label: str, unit: str=None):
        self.yaxis = Axis(name=label, unit=unit)


    def add_curve(self, curve: Curve):
        """
        Curves are added via the helper function
        """
        if curve.sid is None:
            curve.sid = f"{self.sid}_curve{len(self.curves)+1}"
        self.curves.append(curve)

    def _default_kwargs(self, d, dtype):
        """Default plotting styles"""

        if dtype == Data.Types.SIMULATION:
            if "linestyle" not in d:
                d["linestyle"] = "-"
            if "linewidth" not in d:
                d["linewidth"] = 2.0

        elif dtype == Data.Types.DATASET:
            if "linestyle" not in d:
                d["linestyle"] = "--"
            if "marker" not in d:
                d['marker'] = 's'

        if 'capsize' not in d:
            d['capsize'] = 3
        return d

    def curve(self, x: Data, y: Data, xerr: Data=None, yerr: Data=None, **kwargs):
        """Add curve to the plot."""

        kwargs = self._default_kwargs(kwargs, x.get_type())
        curve = Curve(x, y, xerr, yerr, **kwargs)
        self.add_curve(curve)

    def add_data(self,
                 xid: str, yid: str, yid_sd=None, yid_se=None, count: int=None,
                 dataset: str=None, simulation: str=None,
                 xunit=None, yunit=None,
                 label='__nolabel__',
                 xf=1.0, yf=1.0,
                 **kwargs):
        """Wrapper around curve. """
        if yid_sd and yid_se:
            raise ValueError("Set either 'yid_sd' or 'yid_se', not both.")
        if dataset and simulation:
            raise ValueError("Set either 'dataset' or 'simulation', not both.")
        if dataset is None and simulation is None:
            raise ValueError("Set either 'dataset' or 'simulation'.")

        if abs(xf-1.0)>1E-8 or abs(yf-1.0)>1E-8:
            raise ValueError("Scaling factors not supported yet !!!")

        # yerr data
        yerr = None
        yerr_label = ''
        if yid_sd:
            yerr_label = "+-SD"
            yerr = Data(self, yid_sd, dataset=dataset, simulation=simulation, unit=yunit)
        elif yid_se:
            yerr_label = "+-SE"
            yerr = Data(self, yid_se, dataset=dataset, simulation=simulation, unit=yunit)

        # label
        if label != "__nolabel__":
            count_label = ""
            if count:
                count_label = f" (n={count})"
            label = f"{label}{yerr_label}{count_label}"

        self.curve(
            x=Data(self, xid, dataset=dataset, simulation=simulation, unit=xunit),
            y=Data(self, yid, dataset=dataset, simulation=simulation, unit=yunit),
            yerr=yerr,
            label=label, **kwargs
        )


    def add_data_old(self, data: DataSet,
                 xid: str, yid: str, yid_sd=None, yid_se=None, count=None,
                 xunit=None, yunit=None,
                 xf=1.0, yf=1.0,
                 label='__nolabel__', name=None, **kwargs):
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
            dset = DataSet.from_df(data=data, udict=None, ureg=None)

        if dset.empty:
            logger.error(f"Empty dataset in adding data: {dset}")

        if abs(xf - 1.0) > 1E-8:
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
        if name:
            label = name

        if label != "__nolabel__":
            if y_err_type:
                label = f"{label} ± {y_err_type}"
            if count:
                label += f" (n={count})"

        # plot
        if y_err is not None:
            if 'capsize' not in kwargs:
                kwargs['capsize'] = 3
            #ax.errorbar(x.magnitude, y.magnitude, y_err.magnitude, label=label,
            #            **kwargs)
            curve = Curve(sid=None, name=label,
                  xdata=x.magnitude, ydata=y.magnitude, yerr=y_err.magnitude, **kwargs)
        else:
            curve = Curve(sid=None, name=label,
                  xdata=x.magnitude, ydata=y.magnitude, **kwargs)

        self.add_curve(curve)

    def add_line(self, data: Result,
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
        if not isinstance(data, Result):
            raise ValueError("Only Result objects supported in plotting.")
        if (hasattr(xf, "magnitude") and abs(xf.magnitude - 1.0) > 1E-8) or abs(
                xf - 1.0) > 1E-8:
            logger.warning("xf attributes are deprecated, use units instead.")
        if (hasattr(yf, "magnitude") and abs(yf.magnitude - 1.0) > 1E-8) or abs(
                yf - 1.0) > 1E-8:
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

        if all_lines:
            for df in data.frames:
                xk = df[xid].values * data.ureg(data.udict[xid]) * xf
                yk = df[yid].values * data.ureg(data.udict[yid]) * yf
                xk = xk.to(xunit)
                yk = yk.to(yunit)

                self.add_curve(
                    Curve(sid=None, name=label, xdata=xk.magnitude, ydata=yk.magnitude, **kwargs)
                )
        else:
            if len(data) > 1:
                # FIXME: handle areas correctly
                # FIXME: std areas should be within min/max areas!
                ax.fill_between(x, y - y_sd, y + y_sd, color=color, alpha=0.4,
                                label="__nolabel__")

                ax.fill_between(x, y + y_sd, y_max, color=color, alpha=0.2,
                                label="__nolabel__")
                ax.fill_between(x, y - y_sd, y_min, color=color, alpha=0.2,
                                label="__nolabel__")

            self.add_curve(
                Curve(sid=None, name=label, xdata=x.magnitude, ydata=y.magnitude, **kwargs)
            )



class SubPlot(Base):
    """
    A SubPlot is a locate plot in a figure.
    """
    def __init__(self, plot: Plot,
                 row: None, col: None,
                 row_span: int = 1,
                 col_span: int = 1):
        self.plot = plot
        self.row = row
        self.col = col
        self.row_span = row_span
        self.col_span = col_span


class Figure(Base):
    """A figure consists of multiple subplots."""
    panel_width = 5.0
    panel_height = 5.0

    def __init__(self, sid: str, name: str = None,
                 subplots: List[SubPlot] = None,
                 height: float = None,
                 width: float = None,
                 num_rows: int = 1, num_cols: int = 1):
        super(Figure, self).__init__(sid, name)
        if subplots is None:
            subplots = list()
        self.subplots = subplots
        self.num_rows = num_rows
        self.num_cols = num_cols

        if width == None:
            width = num_cols * Figure.panel_width
        if height == None:
            height = num_rows * Figure.panel_height
        self.width = width
        self.height = height

    def num_subplots(self):
        """Number of existing subplots."""
        return len(self.subplots)

    def num_panels(self):
        """Number of available spots for plots."""
        return self.num_cols * self.num_rows

    def create_plots(self, xaxis: Axis=None,
                     yaxis: Axis=None, legend: bool=True) -> List[Plot]:
        """Template function for creating plots"""
        plots = [
            Plot(sid=f"plot{k}", xaxis=xaxis, yaxis=yaxis, legend=legend) for k in range(self.num_panels())
        ]
        self.add_plots(plots)
        return plots

    def add_plots(self, plots: List[Plot]):
        if len(plots) > self.num_cols*self.num_rows:
            raise ValueError("Too many plots for figure")
        ridx = 1
        cidx = 1
        for k, plot in enumerate(plots):
            self.subplots.append(
                SubPlot(plot=plot, row=ridx, col=cidx, row_span=1, col_span=1)
            )

            # increase indices for next plot
            if cidx == self.num_cols:
                cidx = 1
                ridx += 1
            else:
                cidx += 1

    @staticmethod
    def from_plots(sid, plots: List[Plot]) -> 'Figure':
        """
        Create figure object from list of plots.
        """
        num_plots = len(plots)
        return Figure(sid=sid,
                 num_rows=num_plots, num_cols=1,
                 height=num_plots*5.0, width=5.0,
                 subplots=[
                     SubPlot(plot, row=(k+1), col=1) for k, plot in enumerate(plots)
                 ])

