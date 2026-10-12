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

import argparse
import json
import os
from pathlib import Path
import subprocess


CPP_SUFFIXES = {".c", ".cpp", ".h", ".hpp", ".cu", ".cuh", ".cl", ".clh"}
DOC_NAMES = {"README", "AUTHORS", "COPYING", "CITATION.cff"}


def needs_build(paths):
    return any(
        not (
            path.startswith("docs/")
            or Path(path).suffix in {".md", ".rst"}
            or path in DOC_NAMES
        )
        for path in paths
    )


def changed_files(base):
    output = subprocess.check_output(["git", "diff", "--name-only", "-z", base, "HEAD"])
    return [os.fsdecode(path) for path in output.split(b"\0") if path]


def tidy_sources(commands, changed, dependencies, root):
    changed = {str((root / path).resolve()) for path in changed}
    affected = set()
    current = None
    for line in dependencies.splitlines():
        if ": #deps " in line and not line.startswith(" "):
            current = line.split(": #deps ", 1)[0]
        elif line.startswith("    ") and line[4:] in changed:
            if current is not None:
                affected.add(current)
    return sorted(
        {
            command["file"]
            for command in commands
            if command["file"] in changed or command.get("output") in affected
        }
    )


def eligible_cpp(paths):
    paths = [
        path
        for path in paths
        if Path(path).suffix in CPP_SUFFIXES and Path(path).is_file()
    ]
    if not paths:
        return []
    attributes = subprocess.check_output(
        ["git", "check-attr", "-z", "filter", "--", *paths]
    ).split(b"\0")
    return [
        os.fsdecode(attributes[i])
        for i in range(0, len(attributes) - 1, 3)
        if attributes[i + 2] in {b"complete_formatting", b"clangformat"}
    ]


def check_python(paths):
    paths = [
        path
        for path in paths
        if Path(path).suffix == ".py"
        and Path(path).is_file()
        and not path.startswith(("src/external/", "tests/physicalvalidation/"))
    ]
    if paths:
        subprocess.run(
            ["black", "--check", "--diff", "--config", ".black.toml", "--", *paths],
            check=True,
        )
        subprocess.run(["flake8", "--", *paths], check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["changes", "python", "tidy"])
    parser.add_argument("--base")
    parser.add_argument("--build", type=Path, default=Path("build"))
    args = parser.parse_args()
    if args.mode == "changes":
        if not args.base:
            parser.error("changes requires --base")
        base = subprocess.check_output(
            [
                "git",
                "rev-parse",
                "--verify",
                "--end-of-options",
                args.base + "^{commit}",
            ],
            text=True,
        ).strip()
        paths = changed_files(base)
        Path("changed-files.json").write_text(json.dumps(paths))
        output = f"build={str(needs_build(paths)).lower()}\nbase={base}\n"
        with open(os.environ["GITHUB_OUTPUT"], "a") as result:
            result.write(output)
        print(json.dumps(paths, indent=2))
    else:
        paths = json.loads(Path("changed-files.json").read_text())
        if args.mode == "python":
            check_python(paths)
        else:
            cpp = eligible_cpp(paths)
            if not cpp:
                return
            commands = json.loads((args.build / "compile_commands.json").read_text())
            deps = subprocess.check_output(
                ["ninja", "-C", str(args.build), "-t", "deps"], text=True
            )
            sources = [
                source
                for source in tidy_sources(commands, cpp, deps, Path.cwd())
                if "/src/external/" not in source
            ]
            for source in sources:
                subprocess.run(
                    [
                        "clang-tidy-18",
                        "-p",
                        str(args.build),
                        "--warnings-as-errors=*",
                        source,
                    ],
                    check=True,
                )
            if not sources:
                print(
                    "No CPU translation unit available; "
                    "backend/configuration validation required."
                )
            configured = {command["file"] for command in commands}
            for path in cpp:
                if Path(path).is_file() and Path(path).suffix in {
                    ".c",
                    ".cpp",
                    ".cu",
                    ".cl",
                }:
                    if str(Path(path).resolve()) not in configured:
                        print(
                            f"Not in CPU compilation database; "
                            f"backend check required: {path}"
                        )
            print(
                f"Analysed {len(sources)} translation units, "
                "including consumers of changed headers."
            )


if __name__ == "__main__":
    main()
