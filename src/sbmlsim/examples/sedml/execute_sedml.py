from pathlib import Path

from pprint import pprint

from sbmlsim.combine.sedml.io import read_sedml
from sbmlsim.combine.sedml.parser import SEDMLParser
from sbmlsim.experiment import SimulationExperiment, ExperimentRunner
from sbmlsim.simulator import SimulatorSerial
from sbmlsim.simulator.simulation_ray import SimulatorParallel

import xmltodict
import json

base_path = Path(__file__).parent


def sedmltojson(sedml_path: Path) -> None:
    """Convert SED-ML to JSON file."""
    with open(sedml_path, "r") as f_sedml:
        xml = f_sedml.read()

    my_dict = xmltodict.parse(xml)
    json_data = json.dumps(my_dict, indent=2)

    json_path = sedml_path.parent / f"{sedml_path.name}.json"
    with open(json_path, "w") as f_json:
        # print(json_data)
        f_json.write(json_data)


def execute_omex(omex_path: Path, working_dir: Path = None) -> None:
    """Execute omex archive.

    :param omex_path: Path to COMBINE archive (OMEX)
    :param working_dir: Directory to execute the archive (temporary directory of None)
    :return:
    """
    # extract combine archive
    from sbmlsim.combine.omex import Omex
    omex = Omex(omex_path=omex_path, working_dir=working_dir)
    omex.extract()
    print(omex)

    sedml_locations = omex.locations_by_format(format_key="sed-ml")
    print(sedml_locations)
    for location, master in sedml_locations:
        if master:
            execute_sedml(working_dir=working_dir, )


def execute_sedml(sedml_path: Path, working_dir: Path) -> None:
    """Execute the given SED-ML in the working directory."""
    # convert to json
    sedmltojson(sedml_path)

    sed_doc, errorlog, _, _ = read_sedml(
        source=str(sedml_path), working_dir=working_dir
    )

    if errorlog.getNumErrors() > 0:
        raise IOError(f"Errors in SED-ML document for '{sedml_path}',")

    sed_parser = SEDMLParser(sed_doc, working_dir=working_dir, name=sedml_path.stem)
    sed_parser.print_info()

    # check created experiment
    exp: SimulationExperiment = sed_parser.exp_class()
    exp.initialize()
    print(exp)

    # execute simulation experiment
    base_path = Path(__file__).parent
    data_path = base_path
    runner = ExperimentRunner(
        [sed_parser.exp_class],
        simulator=SimulatorSerial(),
        data_path=data_path,
        base_path=base_path,
    )
    _results = runner.run_experiments(
        output_path=base_path / "results", show_figures=True,
        figure_formats=["svg", "png"]
    )

    # TODO: write experiment to SED-ML file
    # serialization of experiments


if __name__ == "__main__":
    # ----------------------
    # L1V4 Plotting
    # ----------------------
    working_dir = base_path / "l1v4_plotting"
    for sedml_file in [
        "repressilator_urn.xml"
        # "markertype.sedml",
        # "linetype.sedml",
        # "axis.sedml",
        # "curve_types.sedml",
        # "curve_types_errors.sedml",
        # "right_yaxis.sedml",
        # "line_overlap_order.sedml",
        # "repressilator_figure.xml",
        # "repressilator_l1v3.xml",
        # "test_file_1.sedml",
        # "test_line_fill.sedml",
        # "stacked_bar.sedml",
        # "stacked_bar2.sedml",
        # "test_3hbarstacked.sedml",
        # "test_bar.sedml",
        # "test_bar3stacked.sedml",
        # "test_file.sedml",
        # "test_hbar_stacked.sedml",
        # "test_shaded_area.sedml",
        # "test_shaded_area_overlap_order.sedml",
        # "test_base_styles.sedml",
    ]:
        execute_sedml(
            sedml_path=working_dir / sedml_file,
            working_dir=working_dir,
        )

    # ----------------------
    # L1V4 Parameter Fitting
    # ----------------------
    working_dir = base_path / "l1v4_parameter_fitting"
    for name, sedml_file in [
        # "Elowitz_Nature2000.xml",
    ]:
        execute_sedml(
            working_dir=working_dir,
            sedml_path=working_dir / sedml_file
        )
