"""Classes for running simulations with SBML models."""
from typing import Optional

import pandas as pd
from sbmlsim.model.model_roadrunner import roadrunner
from sbmlutils import log

from sbmlsim.model import ModelChange
from sbmlsim.simulation import Timecourse, TimecourseSim


logger = log.get_logger(__name__)


class SimulatorWorker:
    """Worker running simulations.

    Implements the timecourse simulation once which can be reused by
    the different simulators.
    """

    def __init__(self):
        """Init placeholder."""
        self.r: Optional[roadrunner.RoadRunner] = None

    def _timecourse(self, simulation: TimecourseSim) -> pd.DataFrame:
        """Timecourse simulation.

        Requires for all timecourse definitions in the timecourse simulation
        to be unit normalized. The changes have no units any more
        for parallel simulations.
        You should never call this function directly!

        :param simulation: Simulation definition(s)
        :return: DataFrame with results
        """
        if isinstance(simulation, Timecourse):
            simulation = TimecourseSim(timecourses=[simulation])

        if simulation.reset:
            self.r.resetToOrigin()

        frames = []
        t_offset = simulation.time_offset
        for k, tc in enumerate(simulation.timecourses):

            if k == 0 and tc.model_changes:
                # [1] apply model changes of first simulation
                logger.debug("Applying model changes")
                for key, item in tc.model_changes.items():
                    if key.startswith("init"):
                        logger.error(
                            f"Initial model changes should be provided "
                            f"without 'init': '{key} = {item}'"
                        )
                    # FIXME: implement model changes via init
                    # init_key = f"init({key})"
                    init_key = key
                    try:
                        value = item.magnitude
                    except AttributeError:
                        value = item

                    try:
                        self.r[init_key] = value
                    except RuntimeError:
                        logger.error(f"roadrunner RuntimeError: '{init_key} = {item}'")
                        # boundary condition=true species, trying direct fallback
                        # see https://github.com/sys-bio/roadrunner/issues/711
                        init_key = key
                        self.r[key] = value

                    logger.debug(f"\t{init_key} = {item}")

                # [2] re-evaluate initial assignments
                # https://github.com/sys-bio/roadrunner/issues/710
                # logger.debug("Reevaluate initial conditions")
                # FIXME/TODO: support initial model changes
                # self.r.resetAll()
                # self.r.reset(SelectionRecord.DEPENDENT_FLOATING_AMOUNT)
                # self.r.reset(SelectionRecord.DEPENDENT_INITIAL_GLOBAL_PARAMETER)

            # [3] apply model manipulations
            # model manipulations are applied to model
            if len(tc.model_manipulations) > 0:
                # FIXME: update to support roadrunner model changes
                for key, value in tc.model_changes.items():
                    if key == ModelChange.CLAMP_SPECIES:
                        for sid, formula in value.items():
                            ModelChange.clamp_species(self.r, sid, formula)
                    else:
                        raise ValueError(
                            f"Unsupported model change: "
                            f"'{key}': {value}. Supported changes are: "
                            f"['{ModelChange.CLAMP_SPECIES}']"
                        )

            # [4] apply changes
            if tc.changes:
                logger.debug("Applying simulation changes")
            for key, item in tc.changes.items():

                # FIXME: handle concentrations/amounts/default
                # TODO: Figure out the hasOnlySubstanceUnit flag! (roadrunner)
                # r: roadrunner.ExecutableModel = self.r

                try:
                    self.r[key] = float(item.magnitude)
                except AttributeError:
                    self.r[key] = float(item)
                logger.debug(f"\t{key} = {item}")

            # debug model state
            # FIXME: report issue
            # sbml_str = self.r.getCurrentSBML()
            # with open("/home/mkoenig/git/pkdb_models/pkdb_models/models/dextromethorphan/results/debug/tests.xml", "w") as f_out:
            #     f_out.write(sbml_str)

            # run simulation
            integrator = self.r.integrator
            # FIXME: support simulation by times
            if integrator.getValue("variable_step_size"):
                s = self.r.simulate(start=tc.start, end=tc.end)
            else:
                s = self.r.simulate(start=tc.start, end=tc.end, steps=tc.steps)

            df = pd.DataFrame(s, columns=s.colnames)
            df.time = df.time + t_offset

            if not tc.discard:
                # discard timecourses (pre-simulation)
                t_offset += tc.end
                frames.append(df)

        return pd.concat(frames, sort=False)
