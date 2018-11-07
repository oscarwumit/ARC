#!/usr/bin/env python
# encoding: utf-8

import logging
import sys
import os
import time

from rmgpy.species import Species
from rmgpy.reaction import Reaction

from arc.settings import arc_path
from arc.scheduler import Scheduler
from arc.exceptions import InputError
from arc.species import ARCSpecies

##################################################################


class ARC(object):
    """
    Main ARC object.
    The software is currently configured to run on a local computer, sending jobs / commands to one or more servers.

    The attributes are:

    ====================== =================== =========================================================================
    Attribute              Type                Description
    ====================== =================== =========================================================================
    `project`              ``str``             The project's name. Used for naming the working directory.
    'rmg_species_list'     ''list''            A list RMG Species objects. Species must have a non-empty label attribute
                                                 and are assumed to be stab;e wells (not TSs)
    `arc_species_list`     ``list``            A list of ARCSpecies objects (each entry represent either a stable well
                                                 or a TS)
    'rxn_list'             ``list``            A list of RMG Reaction objects. Will (hopefully) be converted into TSs
    `level_of_theory`      ``str``             *FULL* level of theory, e.g. 'CBS-QB3',
                                                 'CCSD(T)-F12a/aug-cc-pVTZ//B3LYP/6-311++G(3df,3pd)'...
    'freq_level'           ``str``             Level of theory for frequency jobs. Default is the optimization level.
    'scan_level'           ``str``             Level of theory for rotor scan jobs. Default is 'b3lyp/6-311++g(d,p)'.
    'output'               ``dict``            Output dictionary with status and final QM files for all species
    ====================== =================== =========================================================================
    """
    def __init__(self, project, rmg_species_list=list(), arc_species_list=list(), rxn_list=list(),
                 level_of_theory='', freq_level='', scan_level='', verbose=logging.INFO):
        self.project = project
        if level_of_theory.count('//') > 1:
            raise InputError('Level of theory seems wrong. Got: {0}'.format(level_of_theory))
        if level_of_theory:
            if '/' in level_of_theory and '//' not in level_of_theory:
                # assume this is not a composite method, and the user meant to run both opt and sp at this level
                # running an sp after opt at the same level is meaningless, but doesn't matter much also
                # The '//' combination will later assist in differentiating between composite to non-composite methods
                level_of_theory = level_of_theory + '//' + level_of_theory
            self.level_of_theory = level_of_theory.lower()
        else:
            logging.warning('No level of theory specified, using B3LYP/6-311++G(d,p) by default.')
            self.level_of_theory = 'b3lyp/6-311++g(d,p)//b3lyp/6-311++g(d,p)'
        if freq_level:
            self.freq_level = freq_level.lower()
        elif '//' in self.level_of_theory:
            logging.info('No level of theory specified for frequencies.'
                         ' Using the geometry optimization level, {0}'.format(self.level_of_theory.split('//')[1]))
            self.freq_level = self.level_of_theory.split('//')[1]
        if scan_level:
            self.scan_level = scan_level.lower()
        else:
            logging.info('No level of theory specified for rotor scans. Using B3LYP/6-311++G(d,p) by default.')
            self.scan_level = 'b3lyp/6-311++g(d,p)'

        self.rmg_species_list = rmg_species_list
        self.arc_species_list = arc_species_list
        if self.rmg_species_list:
            for rmg_spc in self.rmg_species_list:
                if not isinstance(rmg_spc, Species):
                    raise InputError('All entries of rmg_species_list have to be RMG Species objects.'
                                     ' Got: {0}'.format(type(rmg_spc)))
                if not rmg_spc.label:
                    raise InputError('Missing label on RMG Species object {0}'.format(rmg_spc))
                arc_spc = ARCSpecies(is_ts=False, rmg_species=rmg_spc)  # assuming an RMG Species is not a TS
                self.arc_species_list.append(arc_spc)

        self.rxn_list = rxn_list

        self.output = dict()

        if not ('cbs' in self.level_of_theory or '//' in self.level_of_theory):
            raise InputError('Level of theory should either be a composite method (like CBS-QB3) or be of the'
                             'form sp//geometry, e.g., CCSD(T)-F12/avtz//wB97x-D3/6-311++g**')
        self.verbose = verbose
        self.output_directory = os.path.join(arc_path, 'Projects', self.project)
        if not os.path.exists(self.output_directory):
            os.makedirs(self.output_directory)
        self.initialize_log(self.verbose, os.path.join(self.output_directory, 'arc.log'))
        self.execute()

    def execute(self):
        logging.info('Starting project {0}\n\n'.format(self.project))
        for species in self.arc_species_list:
            if not isinstance(species, ARCSpecies):
                raise ValueError('All species in species_list must be ARCSpecies objects.'
                                 ' Got {0}'.format(type(species)))
            logging.info('Considering species: {0}'.format(species.label))
        for rxn in self.rxn_list:
            if not isinstance(rxn, Reaction):
                logging.error('`rxn_list` must be a list of RMG.Reaction objects. Got {0}'.format(type(rxn)))
                raise ValueError()
            logging.info('Considering reacrion {0}'.format(rxn))
        scheduler = Scheduler(project=self.project, species_list=self.arc_species_list,
                              level_of_theory=self.level_of_theory, freq_level=self.freq_level,
                              scan_level=self.scan_level)
        self.output = scheduler.output
        print self.output
        self.log_footer()

    def initialize_log(self, verbose=logging.INFO, log_file=None):
        """
        Set up a logger for ARC to use to print output to stdout.
        The `verbose` parameter is an integer specifying the amount of log text seen
        at the console; the levels correspond to those of the :data:`logging` module.
        """
        # Create logger
        logger = logging.getLogger()
        # logger.setLevel(verbose)
        logger.setLevel(logging.DEBUG)

        # Use custom level names for cleaner log output
        logging.addLevelName(logging.CRITICAL, 'Critical: ')
        logging.addLevelName(logging.ERROR, 'Error: ')
        logging.addLevelName(logging.WARNING, 'Warning: ')
        logging.addLevelName(logging.INFO, '')
        logging.addLevelName(logging.DEBUG, '')
        logging.addLevelName(0, '')

        # Create formatter and add to handlers
        formatter = logging.Formatter('%(levelname)s%(message)s')

        # Remove old handlers before adding ours
        while logger.handlers:
            logger.removeHandler(logger.handlers[0])

        # Create console handler; send everything to stdout rather than stderr
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(verbose)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        # Create file handler; always be at least verbose in the file
        if log_file:
            fh = logging.FileHandler(filename=log_file)
            fh.setLevel(min(logging.DEBUG,verbose))
            fh.setFormatter(formatter)
            logger.addHandler(fh)
            self.log_header()

    def log_header(self, level=logging.INFO):
        """
        Output a header containing identifying information about CanTherm to the log.
        """
        logging.log(level, 'ARC execution initiated at {0}'.format(time.asctime()))
        logging.log(level, '')
        logging.log(level, '###############################################################')
        logging.log(level, '#                                                             #')
        logging.log(level, '#                            ARC                              #')
        logging.log(level, '#                                                             #')
        logging.log(level, '#   Version: 0.1                                              #')
        logging.log(level, '#                                                             #')
        logging.log(level, '###############################################################')
        logging.log(level, '')

    def log_footer(self, level=logging.INFO):
        """
        Output a footer to the log.
        """
        logging.log(level, '')
        logging.log(level, 'ARC execution terminated at {0}'.format(time.asctime()))

# TODO: MRCI, determine occ
# TODO: sucsessive opt (B3LYP, CCSD, CISD(T), MRCI)
# TODO: need to know optical isomers and external symmetry (could also be read from QM, but not always right) for thermo
# TODO: calc thermo and rates
