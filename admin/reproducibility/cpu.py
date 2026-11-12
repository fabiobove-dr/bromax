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
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "admin/benchmarks"))
from paired import build_info, command, digest  # noqa: E402
from check import MANIFEST, check_corpus, select_cases  # noqa: E402


def compare_outputs(folder):
    hashes = {}
    for name in ("first", "second", "restart"):
        hashes[name] = {}
        for extension in ("trr", "edr"):
            path = folder / name / f"run.{extension}"
            if path.stat().st_size == 0:
                raise ValueError(f"Empty scientific output: {path}")
            hashes[name][extension] = digest(path)
    if hashes["first"] != hashes["second"]:
        raise ValueError(f"Repeated -reprod outputs differ: {folder}")
    if hashes["first"] != hashes["restart"]:
        raise ValueError(f"Checkpoint/restart outputs differ: {folder}")
    return hashes


def run_case(case, source, executable, folder, seed, threads):
    folder.mkdir()
    for filename in case["inputs"]:
        shutil.copy2(source / filename, folder / Path(filename).name)
    mdp = folder / "system.mdp"
    overrides = {
        "nsteps": 200,
        "nstxout": 10,
        "nstvout": 10,
        "nstfout": 10,
        "nstenergy": 10,
        "nstlog": 10,
        "ld-seed": seed,
        "gen-seed": seed,
    }
    lines = [
        line
        for line in mdp.read_text().splitlines()
        if line.split("=", 1)[0].strip().lower().replace("_", "-") not in overrides
    ]
    mdp.write_text(
        "\n".join(lines)
        + "\n"
        + "".join(f"{key} = {value}\n" for key, value in overrides.items())
    )

    def execute(args, cwd, log):
        with (folder / "commands.jsonl").open("a") as trace:
            trace.write(json.dumps({"args": args, "cwd": str(cwd)}) + "\n")
        command(args, cwd, log)

    execute(
        [
            str(executable),
            "grompp",
            "-f",
            "system.mdp",
            "-c",
            "system.gro",
            "-p",
            "system.top",
            "-o",
            "system.tpr",
            "-po",
            "mdout.mdp",
            "-pp",
            "processed.top",
        ],
        folder,
        folder / "grompp.log",
    )
    args = [
        str(executable),
        "mdrun",
        "-s",
        str(folder / "system.tpr"),
        "-deffnm",
        "run",
        "-reprod",
        "-ntmpi",
        "1",
        "-ntomp",
        str(threads),
        "-nb",
        "cpu",
        "-pme",
        "cpu",
        "-bonded",
        "cpu",
        "-update",
        "cpu",
        "-pin",
        "off",
    ]
    for name in ("first", "second", "restart"):
        run = folder / name
        run.mkdir()
        execute(
            args + (["-nsteps", "100"] if name == "restart" else []),
            run,
            run / "console.log",
        )
        if name == "restart":
            execute(args + ["-cpi", "run.cpt", "-append"], run, run / "resume.log")
    return {
        "case": case["name"],
        "seed": seed,
        "threads": threads,
        "steps": 200,
        "checkpoint_step": 100,
        "tpr_sha256": digest(folder / "system.tpr"),
        "output_sha256": compare_outputs(folder),
    }


def main():
    parser = argparse.ArgumentParser(
        description="CPU -reprod and restart bitwise checks"
    )
    parser.add_argument("--source", type=Path, default=ROOT)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source, build, output = (
        path.resolve() for path in (args.source, args.build, args.output)
    )
    output.mkdir(parents=True, exist_ok=False)
    report = {"status": "failed", "cases": []}
    try:
        report["build"] = build_info(source, build, output)
        manifest = json.loads((source / MANIFEST.relative_to(ROOT)).read_text())
        check_corpus(manifest, source)
        shutil.copy2(source / MANIFEST.relative_to(ROOT), output / "corpus.json")
        report["corpus_sha256"] = digest(output / "corpus.json")
        seed = manifest["seed_policy"]["validation_ld_seeds"][0]
        for case in select_cases(manifest, ["cpu"]):
            for threads in (1, 2):
                report["cases"].append(
                    run_case(
                        case,
                        source,
                        build / "bin/gmx",
                        output / f"{case['name']}-{threads}threads",
                        seed,
                        threads,
                    )
                )
        report["status"] = "passed"
    except Exception as error:
        report["error"] = str(error)
        raise
    finally:
        (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
        summary = (
            f"CPU repeat/restart bitwise checks: **{report['status']}**\n\n"
            f"Completed configurations: {len(report['cases'])}/6. "
            "Each compares repeated and appended-restart TRR/EDR bytes.\n"
        )
        if "error" in report:
            summary += f"\nError: {report['error']}\n"
        (output / "summary.md").write_text(summary)


if __name__ == "__main__":
    main()
