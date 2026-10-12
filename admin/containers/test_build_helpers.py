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

import types
import unittest

import hpccm
import scripted_gmx_docker_builds as builds


# The CLI imports HPCCM into this module before calling its recipe helpers.
builds.hpccm = hpccm


class ContainerHelperTests(unittest.TestCase):
    def test_cross_recipes_keep_toolchain_and_emulator_for_both_compilers(self):
        for architecture in ("riscv64", "aarch64"):
            for llvm in (None, 19):
                with self.subTest(architecture=architecture, llvm=llvm):
                    args = types.SimpleNamespace(cross=architecture, llvm=llvm, gcc=13)
                    stages = {"main": hpccm.Stage()}
                    builds.add_cross_compilation_support(args, stages)
                    recipe = str(stages["main"])
                    compiler = (
                        f"clang-{llvm}" if llvm else f"{architecture}-linux-gnu-gcc-13"
                    )
                    self.assertIn(f"set(CMAKE_C_COMPILER {compiler})", recipe)
                    self.assertIn(f"/opt/cross/{architecture}-toolchain.cmake", recipe)
                    self.assertIn(f"qemu-{architecture}", recipe)
                    if llvm and architecture == "riscv64":
                        self.assertIn("vlen=1024", recipe)

    def test_no_cross_configuration_emits_no_extra_steps(self):
        stages = {"main": hpccm.Stage()}
        builds.add_cross_compilation_support(types.SimpleNamespace(cross=None), stages)
        self.assertEqual(str(stages["main"]), "")


if __name__ == "__main__":
    unittest.main()
