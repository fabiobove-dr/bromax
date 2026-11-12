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

import argparse
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from container.run import docker_command, image_properties, run, validate_image


IMAGE = "sha256:" + "a" * 64


class ContainerLauncherTests(unittest.TestCase):
    def test_immutable_image_required(self):
        for mutable in ("ubuntu:24.04", "myrepo/bromax:latest", "sha256:abc", ""):
            with self.assertRaises(ValueError):
                validate_image(mutable)
        for reference in (IMAGE, "registry.invalid/bromax@" + IMAGE):
            validate_image(reference)

    def test_docker_image_architecture_is_validated(self):
        with patch(
            "container.run.subprocess.check_output",
            side_effect=[IMAGE + "\n", "linux/arm64\n"],
        ):
            with self.assertRaisesRegex(ValueError, "native linux/amd64"):
                image_properties(IMAGE)
        with patch(
            "container.run.subprocess.check_output",
            side_effect=[IMAGE + "\n", "linux/amd64\n"],
        ):
            self.assertEqual(image_properties(IMAGE), IMAGE)

    def test_isolated_native_command_no_network_or_privilege(self):
        cmd = docker_command(Path("/tmp/work"), IMAGE, "argon", 2, IMAGE, "2-3")
        self.assertIn("--network=none", cmd)
        self.assertIn("--read-only", cmd)
        self.assertIn("--cap-drop=ALL", cmd)
        self.assertIn("--security-opt=no-new-privileges", cmd)
        self.assertEqual(cmd[cmd.index("--cpuset-cpus") + 1], "2-3")
        self.assertIn("BROMAX_BENCH_IMAGE_ID=" + IMAGE, cmd)
        self.assertEqual(cmd[-1], IMAGE)

    def test_workspace_guards_and_environment_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            for side in ("baseline", "candidate"):
                (workspace / side / ".git").mkdir(parents=True)
            args = argparse.Namespace(
                workspace=workspace, image=IMAGE, tag="cpu", jobs=2, cpuset="2-3"
            )
            with patch("container.run.platform.system", return_value="Linux"), patch(
                "container.run.platform.machine", return_value="x86_64"
            ), patch("container.run.image_properties", return_value=IMAGE), patch(
                "container.run.subprocess.run"
            ) as docker:
                run(args)
            docker.assert_called_once()
            metadata = json.loads((workspace / "artifacts/runtime.json").read_text())
            self.assertEqual(metadata["container_image_id"], IMAGE)
            self.assertEqual(metadata["selected_cpuset"], "2-3")
            with self.assertRaisesRegex(ValueError, "Existing results"):
                run(args)

    def test_foreign_host_rejected_before_docker(self):
        with tempfile.TemporaryDirectory() as td, patch(
            "container.run.platform.system", return_value="Darwin"
        ):
            args = argparse.Namespace(
                workspace=Path(td), image=IMAGE, tag="cpu", jobs=2, cpuset=None
            )
            with self.assertRaisesRegex(ValueError, "native Linux"):
                run(args)


if __name__ == "__main__":
    unittest.main()
