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

import importlib.util
import os
import json
import shutil
import sys
from pathlib import Path
import subprocess
import tempfile
import unittest


spec = importlib.util.spec_from_file_location(
    "pr_quality", Path(__file__).with_name("pr-quality.py")
)
quality = importlib.util.module_from_spec(spec)
spec.loader.exec_module(quality)


class QualityGateTests(unittest.TestCase):
    def test_documentation_skips_build_but_deleted_source_does_not(self):
        self.assertFalse(
            quality.needs_build(["docs/CMakeLists.txt", "README", "notes.md"])
        )
        self.assertTrue(quality.needs_build(["src/removed.cpp", "docs/guide.rst"]))
        self.assertTrue(quality.needs_build([".github/workflows/linux.yml"]))
        self.assertFalse(quality.needs_build([]))

    def test_header_selects_transitive_consumer(self):
        root = Path("/repo")
        commands = [
            {"file": "/repo/consumer.cpp", "output": "consumer.o"},
            {"file": "/repo/unrelated.cpp", "output": "unrelated.o"},
        ]
        dependencies = (
            "consumer.o: #deps 2, deps mtime 1 (VALID)\n"
            "    /repo/wrapper.h\n    /repo/changed.h\n\n"
            "unrelated.o: #deps 1, deps mtime 1 (VALID)\n"
            "    /repo/other.h\n"
        )
        self.assertEqual(
            quality.tidy_sources(commands, ["changed.h"], dependencies, root),
            ["/repo/consumer.cpp"],
        )
        self.assertEqual(
            quality.tidy_sources(commands, ["unrelated.cpp"], dependencies, root),
            ["/repo/unrelated.cpp"],
        )

    @unittest.skipUnless(
        all(shutil.which(tool) for tool in ("clang-tidy-18", "clang++-18", "ninja")),
        "requires Clang 18 and Ninja (installed by the smoke job)",
    )
    def test_tidy_actually_analyzes_changed_header_and_propagates_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", directory], check=True)
            (root / ".gitattributes").write_text("*.h filter=complete_formatting\n")
            (root / ".clang-tidy").write_text(
                "Checks: '-*,clang-analyzer-core.DivideZero'\n"
                "HeaderFilterRegex: .*\nWarningsAsErrors: '*'\n"
            )
            header = root / "fixture.h"
            header.write_text("inline int division() { return 1; }\n")
            source = root / "fixture.cpp"
            source.write_text('#include "fixture.h"\nint f() { return division(); }\n')
            (root / "build.ninja").write_text(
                "rule compile\n"
                "  command = clang++-18 -MD -MF $out.d -c $in -o $out\n"
                "  depfile = $out.d\n  deps = gcc\n"
                f"build fixture.o: compile {source}\n"
            )
            subprocess.run(["ninja", "-C", directory], check=True, capture_output=True)
            commands = [
                {
                    "directory": directory,
                    "file": str(source),
                    "command": f"clang++-18 -c {source} -o fixture.o",
                    "output": "fixture.o",
                }
            ]
            (root / "compile_commands.json").write_text(json.dumps(commands))
            (root / "changed-files.json").write_text(json.dumps(["fixture.h"]))
            command = [
                sys.executable,
                str(Path(__file__).with_name("pr-quality.py")),
                "tidy",
                "--build",
                ".",
            ]
            good = subprocess.run(command, cwd=root, capture_output=True, text=True)
            self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
            header.write_text("inline int division() { return 1 / 0; }\n")
            bad = subprocess.run(command, cwd=root, capture_output=True, text=True)
            self.assertNotEqual(bad.returncode, 0, bad.stdout + bad.stderr)
            self.assertIn("division by zero", (bad.stdout + bad.stderr).lower())

    def test_git_paths_with_spaces_and_deleted_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def git(*args):
                return subprocess.check_output(
                    ["git", "-C", directory, *args], text=True
                )

            git("init", "-q")
            git("config", "user.name", "Test")
            git("config", "user.email", "test@example.invalid")
            (root / "old.cpp").write_text("old\n")
            git("add", ".")
            git("commit", "-qm", "base")
            base = git("rev-parse", "HEAD").strip()
            (root / "old.cpp").unlink()
            (root / "with spaces.py").write_text("pass\n")
            git("add", "-A")
            git("commit", "-qm", "change")
            previous = Path.cwd()
            try:
                os.chdir(root)
                self.assertEqual(
                    quality.changed_files(base), ["old.cpp", "with spaces.py"]
                )
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
