#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module contains unit tests for the arc.rmgdb module
"""

from __future__ import (absolute_import, division, print_function, unicode_literals)
import unittest

from rmgpy.reaction import Reaction
from rmgpy.species import Species
from rmgpy.data.kinetics.library import LibraryReaction

import arc.rmgdb as rmgdb

################################################################################


class TestRMGDB(unittest.TestCase):
    """
    Contains unit tests for the rmgdb module
    """
    @classmethod
    def setUpClass(cls):
        """
        A method that is run before all unit tests in this class.
        """
        cls.rmgdb = rmgdb.make_rmg_database_object()
        rmgdb.load_rmg_database(rmgdb=cls.rmgdb)

    def test_load_rmg_database(self):
        """Test loading the full RMG database"""
        self.assertTrue(any([fam == 'H_Abstraction' for fam in self.rmgdb.kinetics.families]))
        self.assertTrue(any([lib == 'BurkeH2O2inN2' for lib in self.rmgdb.kinetics.libraries]))
        self.assertTrue(any([lib == 'thermo_DFT_CCSDTF12_BAC' for lib in self.rmgdb.thermo.libraries]))
        self.assertTrue(any([lib == 'NOx2018' for lib in self.rmgdb.transport.libraries]))

    def test_thermo(self):
        """Test that thermodata is loaded correctly from RMG's database"""
        spc = Species().fromSMILES(str('O=C=O'))
        spc.thermo = self.rmgdb.thermo.getThermoData(spc)
        self.assertAlmostEqual(spc.getEnthalpy(298), -393547.040000, 5)
        self.assertAlmostEqual(spc.getEntropy(298), 213.71872, 5)
        self.assertAlmostEqual(spc.getHeatCapacity(1000), 54.35016, 5)

    def test_determining_rmg_kinetics(self):
        """Test the determine_rmg_kinetics() function"""
        r1 = Species().fromSMILES(str('C'))
        r2 = Species().fromSMILES(str('O[O]'))
        p1 = Species().fromSMILES(str('[CH3]'))
        p2 = Species().fromSMILES(str('OO'))
        r1.thermo = self.rmgdb.thermo.getThermoData(r1)
        r2.thermo = self.rmgdb.thermo.getThermoData(r2)
        p1.thermo = self.rmgdb.thermo.getThermoData(p1)
        p2.thermo = self.rmgdb.thermo.getThermoData(p2)
        rxn = Reaction(reactants=[r1, r2], products=[p1, p2])
        dh_rxn298 = sum([product.getEnthalpy(298) for product in rxn.products])\
            - sum([reactant.getEnthalpy(298) for reactant in rxn.reactants])
        rmg_reactions = rmgdb.determine_rmg_kinetics(rmgdb=self.rmgdb, reaction=rxn, dh_rxn298=dh_rxn298)
        self.assertFalse(rmg_reactions[0].kinetics.isPressureDependent())
        found_rxn = False
        for rxn in rmg_reactions:
            if isinstance(rxn, LibraryReaction) and rxn.library == 'Klippenstein_Glarborg2016':
                self.assertAlmostEqual(rxn.kinetics.getRateCoefficient(1000, 1e5), 38.2514795642, 7)
                found_rxn = True
        self.assertTrue(found_rxn)


################################################################################

if __name__ == '__main__':
    unittest.main(testRunner=unittest.TextTestRunner(verbosity=2))
