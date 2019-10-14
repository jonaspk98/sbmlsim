"""
Functions for model loading and model manipulation.
"""
import logging
import roadrunner
import libsbml


def load_model(path, selections: bool = True) -> roadrunner.RoadRunner:
    """ Loads the latest model version.

    :param path: path to SBML model or SBML string
    :param selections: boolean flag to set selections
    :return: roadrunner instance
    """
    logging.info("Loading: '{}'".format(path))
    r = roadrunner.RoadRunner(path)
    if selections:
        set_timecourse_selections(r)
    return r


def set_timecourse_selections(r: roadrunner.RoadRunner, selections=None) -> None:
    """ Sets the full model selections. """
    if not selections:
        r_model = r.model  # type: roadrunner.ExecutableModel

        r.timeCourseSelections = ["time"] \
                                 + r_model.getFloatingSpeciesIds() \
                                 + r_model.getBoundarySpeciesIds() \
                                 + r_model.getGlobalParameterIds() \
                                 + r_model.getReactionIds() \
                                 + r_model.getCompartmentIds()
        r.timeCourseSelections += [f'[{key}]' for key in (
                    r_model.getFloatingSpeciesIds() + r_model.getBoundarySpeciesIds())]
    else:
        r.timeCourseSelections = selections


def set_integrator_settings(r: roadrunner.RoadRunner, **kwargs) -> None:
    """ Set integrator settings. """
    integrator = r.getIntegrator()
    for key, value in kwargs.items():
        # adapt the absolute_tolerance relative to the amounts
        if key == "absolute_tolerance":
            value = value * min(r.model.getCompartmentVolumes())
        integrator.setValue(key, value)
    return integrator


def clamp_species(r: roadrunner.RoadRunner, sids, boundary_condition=True) -> roadrunner.RoadRunner:
    """ Clamp/Free specie(s) via setting boundaryCondition=True/False.

    This requires changing the SBML and ODE system.

    :param r: roadrunner.RoadRunner
    :param sids: sid or iterable of sids
    :param boundary_condition: boolean flag to clamp (True) or free (False) species
    :return: modified roadrunner.RoadRunner
    """
    # get model for current SBML state
    sbml_str = r.getCurrentSBML()
    doc = libsbml.readSBMLFromString(sbml_str)  # type: libsbml.SBMLDocument
    model = doc.getModel()  # type: libsbml.Model

    if isinstance(sids, str):
        sids = [sids]

    for sid in sids:
        # set boundary conditions
        sbase = model.getElementBySId(sid)  # type: libsbml.SBase
        if not sbase:
            logging.error("No element for SId in model: {}".format(sid))
            return None
        else:
            if sbase.getTypeCode() == libsbml.SBML_SPECIES:
                species = sbase  # type: libsbml.Species
                species.setBoundaryCondition(boundary_condition)
            else:
                logging.error("SId in clamp does not match species: {}".format(sbase))
                return None

    # create modified roadrunner instance
    sbmlmod_str = libsbml.writeSBMLToString(doc)
    rmod = load_model(sbmlmod_str)  # type: roadrunner.RoadRunner
    set_timecourse_selections(rmod, r.timeCourseSelections)

    return rmod


if __name__ == "__main__":
    from matplotlib import pyplot as plt

    import sbmlsim
    from sbmlsim import plotting
    from sbmlsim.simulation import TimecourseSimulation
    from sbmlsim.model import clamp_species
    from sbmlsim.parametrization import ChangeSet

    from sbmlsim.tests.settings import MODEL_REPRESSILATOR


    def run_clamp_sid():

        def plot_results(results, title=None):
            # create figure
            fig, (ax1) = plt.subplots(nrows=1, ncols=1, figsize=(5, 5))
            fig.subplots_adjust(wspace=0.3, hspace=0.3)

            plotting.add_line(ax=ax1, data=results,
                              xid='time', yid="X", label="X")
            plotting.add_line(ax=ax1, data=results,
                              xid='time', yid="Y", label="Y", color="darkblue")

            if title:
                ax1.set_title(title)

            ax1.legend()
            plt.show()

        # reference simulation
        r = sbmlsim.load_model(MODEL_REPRESSILATOR)
        tsim = TimecourseSimulation(tstart=0, tend=400, steps=400, changeset=[{"X": 10}])

        results = sbmlsim.timecourse(r, tsim)
        plot_results(results, "control")

        # clamp simulation
        rclamp = clamp_species(r, sids="X")
        results = sbmlsim.timecourse(rclamp, tsim)
        plot_results(results, "clamp")

        # free the simulation
        rclamp = clamp_species(r, sids="X", boundary_condition=False)
        results = sbmlsim.timecourse(rclamp, tsim)
        plot_results(results, "freed clamp")


    run_clamp_sid()

