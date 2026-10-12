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
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(__file__).with_name("corpus.json")


def check_corpus(manifest, root):
    if manifest["version"] != 1:
        raise ValueError("Unsupported corpus version")
    if not manifest["cases"]:
        raise ValueError("Corpus must contain cases")
    names = set()
    suite = json.loads((root / "tests/physicalvalidation/systems.json").read_text())
    for case in manifest["cases"]:
        name = case["name"]
        if name in names:
            raise ValueError(f"Duplicate case: {name}")
        names.add(name)
        for filename, expected in case["inputs"].items():
            path = (root / filename).resolve()
            if not path.is_relative_to(root.resolve()):
                raise ValueError(f"Input outside repository: {filename}")
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError(f"Input checksum changed: {filename}")
        if case["validation"] not in suite:
            raise ValueError(f"Validation definition changed: {name}")
        benchmark = case["benchmark"]
        if any(value <= 0 for value in benchmark.values()):
            raise ValueError(
                f"Benchmark durations/sample counts must be positive: {name}"
            )


def select_cases(manifest, tags):
    selected = [case for case in manifest["cases"] if set(tags) <= set(case["tags"])]
    if not selected:
        raise ValueError("No corpus cases match all requested tags")
    return selected


def main():
    parser = argparse.ArgumentParser(description="Check and select canonical corpus v1")
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--physical-validation", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    check_corpus(manifest, ROOT)
    cases = select_cases(manifest, args.tag)
    if args.physical_validation:
        result = [case["validation"] for case in cases]
    else:
        result = {**manifest, "cases": cases}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
