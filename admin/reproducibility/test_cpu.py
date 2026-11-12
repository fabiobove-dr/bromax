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

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from cpu import compare_outputs, main


class ReproducibilityTests(unittest.TestCase):
    def test_identity_corruption_missing_and_empty_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("first", "second", "restart"):
                (root / name).mkdir()
                for extension in ("trr", "edr"):
                    (root / name / f"run.{extension}").write_bytes(b"scientific data")
            hashes = compare_outputs(root)
            self.assertEqual(hashes["first"], hashes["restart"])
            for name in ("second", "restart"):
                path = root / name / "run.trr"
                path.write_bytes(b"scientific datb")
                with self.assertRaisesRegex(ValueError, "outputs differ"):
                    compare_outputs(root)
                path.write_bytes(b"scientific data")
            path.write_bytes(b"")
            with self.assertRaisesRegex(ValueError, "Empty scientific output"):
                compare_outputs(root)
            path.unlink()
            with self.assertRaises(FileNotFoundError):
                compare_outputs(root)

    def test_failed_build_guard_retains_report_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "results"
            argv = ["cpu.py", "--build", directory, "--output", str(output)]
            with patch.object(sys, "argv", argv), patch(
                "cpu.build_info", side_effect=ValueError("Stale binary")
            ):
                with self.assertRaisesRegex(ValueError, "Stale binary"):
                    main()
                report = json.loads((output / "result.json").read_text())
                self.assertEqual(report["status"], "failed")
                self.assertIn("Stale binary", (output / "summary.md").read_text())
                with self.assertRaises(FileExistsError):
                    main()


if __name__ == "__main__":
    unittest.main()
