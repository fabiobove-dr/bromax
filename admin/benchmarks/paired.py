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
import math
import os
from pathlib import Path
import platform
import re
import shutil
import statistics
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tests/corpus"))
from check import MANIFEST, check_corpus, select_cases  # noqa: E402


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(args, cwd, log):
    environment = os.environ.copy()
    environment.pop("OMP_NUM_THREADS", None)
    with log.open("w") as output:
        subprocess.run(
            args, cwd=cwd, stdout=output, stderr=subprocess.STDOUT, check=True
        )


def performance(text):
    match = re.search(r"^Performance:\s+([\d.]+)\s+[\d.]+\s+([\d.]+)", text, re.M)
    if not match:
        raise ValueError("Missing GROMACS ns/day and ms/step counters")
    ns_day, ms_step = map(float, match.groups())
    if not all(math.isfinite(value) and value > 0 for value in (ns_day, ms_step)):
        raise ValueError("Invalid performance counters")
    return {"ns_day": ns_day, "ms_step": ms_step}


def comparison(pairs):
    if len(pairs) != 5:
        raise ValueError("Corpus v1 requires five complete pairs")
    ratios = [
        math.log(pair["candidate"]["ms_step"] / pair["baseline"]["ms_step"])
        for pair in pairs
    ]
    mean = statistics.mean(ratios)
    margin = 2.776445105 * statistics.stdev(ratios) / math.sqrt(5)
    lower, upper = mean - margin, mean + margin
    outcome = (
        "improvement"
        if upper < 0
        else "regression" if lower > 0 else "indistinguishable/noise"
    )
    return {
        "outcome": outcome,
        "candidate_time_ratio": math.exp(mean),
        "exploratory_95_percent_interval": [math.exp(lower), math.exp(upper)],
    }


def build_info(source, build, output):
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=source, text=True
    ).strip()
    dirty = bool(
        subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=no"], cwd=source
        )
    )
    if dirty:
        raise ValueError(f"Tracked source changes in {source}")
    executable = build / "bin/gmx"
    command([str(executable), "--version"], source, output / "version.txt")
    version = (output / "version.txt").read_text()
    if not re.search(r"GIT SHA1 hash:\s+" + re.escape(sha) + r"\b", version):
        raise ValueError("Executable commit does not match its clean source checkout")
    fields = dict(re.findall(r"^([^:\n]+):\s*(.*)$", version, re.M))
    if fields.get("Precision") != "mixed" or fields.get("GPU support") != "disabled":
        raise ValueError(
            "Corpus v1 requires single/mixed precision and CPU-only builds"
        )
    shutil.copy2(build / "CMakeCache.txt", output / "CMakeCache.txt")
    return {
        "sha": sha,
        "dirty": dirty,
        "executable_sha256": digest(executable),
        "version": fields,
        "backend": "cpu",
        "ranks": 1,
    }


def prepare(case, source, executable, folder, seed):
    folder.mkdir()
    for name in case["inputs"]:
        shutil.copy2(source / name, folder / Path(name).name)
    mdp = folder / "system.mdp"
    lines = [
        line
        for line in mdp.read_text().splitlines()
        if line.split("=", 1)[0].strip().replace("_", "-").lower()
        not in {"nsteps", "ld-seed", "gen-seed"}
    ]
    steps = case["benchmark"]["warmup_steps"] + case["benchmark"]["sample_steps"]
    mdp.write_text(
        "\n".join(lines) + f"\nnsteps = {steps}\nld-seed = {seed}\ngen-seed = {seed}\n"
    )
    args = [
        str(executable),
        "grompp",
        "-f",
        "system.mdp",
        "-c",
        "system.gro",
        "-p",
        "system.top",
        "-o",
        "run.tpr",
        "-po",
        "resolved.mdp",
        "-pp",
        "processed.top",
    ]
    command(args, folder, folder / "grompp.log")
    command([str(executable), "dump", "-s", "run.tpr"], folder, folder / "tpr-dump.txt")
    return {
        "command": args,
        "tpr_sha256": digest(folder / "run.tpr"),
        "resolved_mdp_sha256": digest(folder / "resolved.mdp"),
        "processed_topology_sha256": digest(folder / "processed.top"),
    }


def scientific_text(path):
    return "\n".join(
        line.split(";", 1)[0].strip()
        for line in path.read_text().splitlines()
        if line.split(";", 1)[0].strip()
    )


def telemetry():
    readings = {}
    patterns = [
        "devices/system/cpu/cpu*/cpufreq/scaling_cur_freq",
        "class/thermal/thermal_zone*/temp",
        "class/powercap/intel-rapl*/energy_uj",
    ]
    for pattern in patterns:
        for path in Path("/sys").glob(pattern):
            try:
                readings[str(path)] = path.read_text().strip()
            except OSError:
                continue
    return readings or {
        "unavailable": "No readable sysfs frequency/thermal/power counters"
    }


def tpr_physics(path):
    text = path.read_text()
    if "\ninputrec:\n" not in text:
        raise ValueError("TPR dump has no inputrec section")
    return text.split("\ninputrec:\n", 1)[1]


def summarize(result):
    lines = [
        "# Bromax paired CPU benchmark",
        "",
        f"Status: {result['status']}",
        "",
        "Timing labels are exploratory; physical/ensemble validation is not run (#22).",
        "No performance threshold is a required PR check.",
        "",
        "| Case | Candidate/baseline time | Exploratory 95% interval | " "Outcome |",
        "| --- | --- | --- | --- |",
    ]
    for case in result["cases"]:
        if "comparison" in case:
            value = case["comparison"]
            lower, upper = value["exploratory_95_percent_interval"]
            lines.append(
                f"| {case['name']} | {value['candidate_time_ratio']:.4f} | "
                f"{lower:.4f}–{upper:.4f} | {value['outcome']} |"
            )
    if "error" in result:
        lines.extend(["", "Error: " + result["error"]])
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Paired canonical CPU benchmark")
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--baseline-build", type=Path, required=True)
    parser.add_argument("--candidate-build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tag", action="append", default=[])
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = json.loads(MANIFEST.read_text())
    result = {
        "status": "incomplete",
        "corpus": manifest,
        "manifest_sha256": digest(MANIFEST),
        "cases": [],
        "platform": platform.platform(),
        "runner_class": os.environ.get("RUNNER_LABEL", "local"),
        "affinity": sorted(os.sched_getaffinity(0)),
        "threads": 2,
        "gpu_driver_runtime": "unavailable: CPU-only corpus v1",
        "thermal_power_clocks": "Readable sysfs snapshots per sample; not controlled",
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    try:
        selected_cases = select_cases(manifest, args.tag)
        command(["lscpu", "--json"], args.output, args.output / "cpu.json")
        trees = {
            "baseline": (args.baseline.resolve(), args.baseline_build.resolve()),
            "candidate": (args.candidate.resolve(), args.candidate_build.resolve()),
        }
        origin = subprocess.check_output(
            ["git", "remote", "get-url", "origin"], cwd=trees["baseline"][0], text=True
        ).strip()
        if not re.fullmatch(
            r"(?:https://github.com/|git@github.com:|ssh://git@github.com/)"
            r"fabiobove-dr/bromax(?:\.git)?",
            origin,
        ):
            raise ValueError("Baseline origin must be the Bromax fork")
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", "HEAD", "origin/main"],
            cwd=trees["baseline"][0],
            check=True,
        )
        result["builds"] = {}
        for label, (source, build) in trees.items():
            check_corpus(manifest, source)
            folder = args.output / label
            folder.mkdir()
            result["builds"][label] = build_info(source, build, folder)
            command(
                [
                    "ctest",
                    "--test-dir",
                    str(build),
                    "--output-on-failure",
                    "--no-tests=error",
                    "--parallel",
                    "2",
                    "--output-junit",
                    str(folder / "junit.xml"),
                ],
                source,
                folder / "ctest.log",
            )
            result["builds"][label]["builtin_validation"] = "passed"
        comparable = [
            "C compiler",
            "C++ compiler",
            "C compiler flags",
            "C++ compiler flags",
            "SIMD instructions",
            "CPU FFT library",
            "MPI library",
            "Precision",
            "OpenMP support",
            "Memory model",
            "GPU support",
        ]
        for field in comparable:
            if result["builds"]["baseline"]["version"].get(field) != result["builds"][
                "candidate"
            ]["version"].get(field):
                raise ValueError(f"Build configurations differ: {field}")
        for case in selected_cases:
            if case["benchmark"]["paired_samples"] != 5:
                raise ValueError(
                    "Unsupported sample count; update the inference policy"
                )
            if case["name"] != Path(case["name"]).name or case["name"] in {
                "",
                ".",
                "..",
            }:
                raise ValueError("Case name must be a single safe path component")
            record = {
                "name": case["name"],
                "tags": case["tags"],
                "pairs": [],
                "preparation": {},
            }
            result["cases"].append(record)
            folders = {}
            for label, (source, build) in trees.items():
                folder = args.output / label / case["name"]
                record["preparation"][label] = prepare(
                    case,
                    source,
                    build / "bin/gmx",
                    folder,
                    manifest["seed_policy"]["benchmark_ld_seed"],
                )
                folders[label] = folder
            for filename in ("resolved.mdp", "processed.top"):
                if scientific_text(folders["baseline"] / filename) != scientific_text(
                    folders["candidate"] / filename
                ):
                    raise ValueError(
                        f"Resolved scientific parameters differ: "
                        f"{case['name']} {filename}"
                    )
            if tpr_physics(folders["baseline"] / "tpr-dump.txt") != tpr_physics(
                folders["candidate"] / "tpr-dump.txt"
            ):
                raise ValueError(f"Resolved TPR physics differ: {case['name']}")
            for sample in range(5):
                order = (
                    ["baseline", "candidate"]
                    if sample % 2 == 0
                    else ["candidate", "baseline"]
                )
                pair = {"order": order}
                record["pairs"].append(pair)
                for label in order:
                    run = folders[label] / f"sample-{sample}"
                    run.mkdir()
                    executable = trees[label][1] / "bin/gmx"
                    command_args = [
                        str(executable),
                        "mdrun",
                        "-s",
                        str(folders[label] / "run.tpr"),
                        "-deffnm",
                        "run",
                        "-ntmpi",
                        "1",
                        "-ntomp",
                        "2",
                        "-pin",
                        "on",
                        "-nb",
                        "cpu",
                        "-pme",
                        "cpu",
                        "-update",
                        "cpu",
                        "-notunepme",
                        "-resetstep",
                        str(case["benchmark"]["warmup_steps"]),
                    ]
                    before = telemetry()
                    start = time.perf_counter()
                    command(command_args, run, run / "console.log")
                    text = (run / "run.log").read_text()
                    if "resetting all time and cycle counters" not in text.lower():
                        raise ValueError("Warm-up timing reset missing")
                    pair[label] = {
                        **performance(text),
                        "command": command_args,
                        "wallcycle_rows": [
                            line.strip()
                            for line in text.splitlines()
                            if re.match(
                                r"\s+(Force|Neighbor search|PME |Update\s)", line
                            )
                        ],
                        "process_wall_seconds": time.perf_counter() - start,
                        "telemetry_before": before,
                        "telemetry_after": telemetry(),
                    }
                (args.output / "results.json").write_text(
                    json.dumps(result, indent=2) + "\n"
                )
            record["comparison"] = comparison(record["pairs"])
        result["status"] = "complete"
    except Exception as error:
        result["status"] = "failed"
        result["error"] = str(error)
        raise
    finally:
        (args.output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
        (args.output / "summary.md").write_text(summarize(result))


if __name__ == "__main__":
    main()
