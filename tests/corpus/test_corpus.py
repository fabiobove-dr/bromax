#
# This file is part of the GROMACS molecular simulation package.
#
# Copyright 2026- The GROMACS Authors
# and the project initiators Erik Lindahl, Berk Hess and David van der Spoel.
# Consult the AUTHORS/COPYING files and https://www.gromacs.org for details.
#
# GROMACS is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation; either version 2.1
# of the License, or (at your option) any later version.
#
# GROMACS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with GROMACS; if not, see
# https://www.gnu.org/licenses, or write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA.
#
# If you want to redistribute modifications to GROMACS, please
# consider that scientific software is very special. Version
# control is crucial - bugs must be traceable. We will be happy to
# consider code for inclusion in the official distribution, but
# derived work must not be called official GROMACS. Details are found
# in the README & COPYING files - if they are missing, get the
# official version at https://www.gromacs.org.
#
# To help us fund GROMACS development, we humbly ask that you cite
# the research papers on the package. Check out https://www.gromacs.org.

import copy
import json
from pathlib import Path
import tempfile
import unittest

from check import MANIFEST, ROOT, check_corpus, select_cases


class CorpusTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(MANIFEST.read_text())

    def test_real_inputs_and_validation_definitions_match(self):
        check_corpus(self.manifest, ROOT)
        names = [c["name"] for c in select_cases(self.manifest, ["ensemble", "settle"])]
        self.assertEqual(names, ["ens_water_md_settle_pme_vr"])
        with self.assertRaisesRegex(ValueError, "No corpus cases"):
            select_cases(self.manifest, ["gpu"])

    def test_changed_input_and_validation_definition_fail(self):
        changed = copy.deepcopy(self.manifest)
        filename = next(iter(changed["cases"][0]["inputs"]))
        changed["cases"][0]["inputs"][filename] = "0" * 64
        with self.assertRaisesRegex(ValueError, "checksum changed"):
            check_corpus(changed, ROOT)
        changed = copy.deepcopy(self.manifest)
        changed["cases"][0]["validation"]["tests"][0]["args"] = "-t 999"
        with self.assertRaisesRegex(ValueError, "Validation definition changed"):
            check_corpus(changed, ROOT)

    def test_outside_path_and_invalid_benchmark_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            changed = copy.deepcopy(self.manifest)
            changed["cases"][0]["inputs"] = {str(Path(directory) / "input"): "0" * 64}
            with self.assertRaisesRegex(ValueError, "outside repository"):
                check_corpus(changed, ROOT)
        changed = copy.deepcopy(self.manifest)
        changed["cases"][0]["benchmark"]["sample_steps"] = 0
        with self.assertRaisesRegex(ValueError, "must be positive"):
            check_corpus(changed, ROOT)


if __name__ == "__main__":
    unittest.main()
