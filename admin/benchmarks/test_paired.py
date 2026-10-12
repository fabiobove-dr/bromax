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
from unittest.mock import patch

from paired import (
    build_info,
    main,
    comparison,
    performance,
    scientific_text,
    tpr_physics,
)


class BenchmarkTests(unittest.TestCase):
    def pairs(self, ratio):
        return [
            {"baseline": {"ms_step": 10}, "candidate": {"ms_step": 10 * ratio}}
            for _ in range(5)
        ]

    def test_three_outcomes_and_incomplete_comparison(self):
        self.assertEqual(comparison(self.pairs(0.8))["outcome"], "improvement")
        self.assertEqual(comparison(self.pairs(1.2))["outcome"], "regression")
        self.assertEqual(
            comparison(self.pairs(1))["outcome"], "indistinguishable/noise"
        )
        noisy = copy.deepcopy(self.pairs(1))
        for pair, value in zip(noisy, [8, 12, 9, 11, 10]):
            pair["candidate"]["ms_step"] = value
        self.assertEqual(comparison(noisy)["outcome"], "indistinguishable/noise")
        with self.assertRaises(ValueError):
            comparison(noisy[:4])

    def test_dirty_sources_and_stale_binary_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch(
                "paired.subprocess.check_output", side_effect=[b"sha\n", b" M source"]
            ):
                with self.assertRaisesRegex(ValueError, "Tracked source changes"):
                    build_info(root, root, root)
            (root / "version.txt").write_text("GIT SHA1 hash: wrong\n")
            with patch(
                "paired.subprocess.check_output", side_effect=["sha\n", b""]
            ), patch("paired.command"):
                with self.assertRaisesRegex(ValueError, "Executable commit"):
                    build_info(root, root, root)

    def test_wrong_fork_failure_retains_json_and_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = [
                "paired.py",
                "--baseline",
                str(root),
                "--candidate",
                str(root),
                "--baseline-build",
                str(root),
                "--candidate-build",
                str(root),
                "--output",
                str(root / "results"),
            ]
            with patch("paired.sys.argv", args), patch("paired.command"), patch(
                "paired.subprocess.check_output",
                return_value="https://github.com/gromacs/gromacs.git",
            ):
                with self.assertRaisesRegex(ValueError, "Bromax fork"):
                    main()
            result = json.loads((root / "results/results.json").read_text())
            self.assertEqual(result["status"], "failed")
            self.assertIn("Bromax fork", (root / "results/summary.md").read_text())

    def test_real_counter_format_and_invalid_values(self):
        text = "Performance:        0.104      230.721       51.912            0.052"
        self.assertEqual(performance(text), {"ns_day": 0.104, "ms_step": 51.912})
        for invalid in ("missing", "Performance: 0 1 2", "Performance: 1 1 0"):
            with self.assertRaises(ValueError):
                performance(invalid)

    def test_provenance_comments_ignored_but_physics_changes_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mdp"
            path.write_text("; commit abc\ndt = 0.002 ; ps\n")
            first = scientific_text(path)
            path.write_text("; commit def\ndt = 0.002\n")
            self.assertEqual(first, scientific_text(path))
            path.write_text("dt = 0.004\n")
            self.assertNotEqual(first, scientific_text(path))
            path.write_text("different banner\ninputrec:\ndt = 0.002\n")
            self.assertEqual(tpr_physics(path), "dt = 0.002\n")
            path.write_text("no input record")
            with self.assertRaises(ValueError):
                tpr_physics(path)


if __name__ == "__main__":
    unittest.main()
