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

"""Launch the isolated, CPU-only benchmark image on a native Linux x86-64 host."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import re
import subprocess


DIGEST = r"sha256:[0-9a-f]{64}"
IMMUTABLE_IMAGE = re.compile(rf"(?:{DIGEST}|[^@\s]+@{DIGEST})\Z")
IMAGE_ID = re.compile(rf"{DIGEST}\Z")


def validate_image(reference):
    if not IMMUTABLE_IMAGE.fullmatch(reference):
        raise ValueError("Image must be a local sha256: ID or registry@sha256: digest")


def image_properties(reference):
    validate_image(reference)
    image_id = subprocess.check_output(
        ["docker", "image", "inspect", "--format", "{{.Id}}", reference], text=True
    ).strip()
    arch = subprocess.check_output(
        [
            "docker",
            "image",
            "inspect",
            "--format",
            "{{.Os}}/{{.Architecture}}",
            reference,
        ],
        text=True,
    ).strip()
    if not IMAGE_ID.fullmatch(image_id):
        raise ValueError("Docker returned an invalid image ID")
    if arch != "linux/amd64":
        raise ValueError(f"Expected native linux/amd64 image, got {arch}")
    return image_id


def docker_command(workspace, reference, tag, jobs, image_id, cpuset=None):
    result = [
        "docker",
        "run",
        "--rm",
        "--pull=never",
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--pids-limit=512",
        "--tmpfs=/tmp:rw,nosuid,nodev,mode=1777,size=1g",
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "--mount",
        f"type=bind,source={workspace},target=/work",
        "--env",
        f"BROMAX_CORPUS_TAG={tag}",
        "--env",
        f"BROMAX_BUILD_JOBS={jobs}",
        "--env",
        f"BROMAX_BENCH_IMAGE_REF={reference}",
        "--env",
        f"BROMAX_BENCH_IMAGE_ID={image_id}",
        "--env",
        "RUNNER_LABEL=container-linux-amd64",
    ]
    if cpuset:
        result.extend(["--cpuset-cpus", cpuset])
    return result + [reference]


def run(args):
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise ValueError("Performance measurements require a native Linux x86-64 host")
    workspace = args.workspace.resolve(strict=True)
    for tree in ("baseline", "candidate"):
        if not (workspace / tree / ".git").exists():
            raise ValueError(f"Missing independent Git checkout: {tree}")
    if (workspace / "results").exists() or (workspace / "artifacts").exists():
        raise ValueError("Existing results or artifacts: use a fresh workspace")
    if args.jobs < 1:
        raise ValueError("Build jobs must be positive")
    image_id = image_properties(args.image)
    artifacts = workspace / "artifacts"
    artifacts.mkdir()
    metadata = {
        "container_image_reference": args.image,
        "container_image_id": image_id,
        "image_architecture": "linux/amd64",
        "host_kernel": platform.release(),
        "host_architecture": platform.machine(),
        "host_cpu_affinity": sorted(os.sched_getaffinity(0)),
        "selected_cpuset": args.cpuset,
        "corpus_tag": args.tag,
        "build_jobs": args.jobs,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "note": "Image freezes userspace, not host CPU/microcode/kernel/clocks",
    }
    (artifacts / "runtime.json").write_text(json.dumps(metadata, indent=2) + "\n")
    subprocess.run(
        docker_command(
            workspace, args.image, args.tag, args.jobs, image_id, args.cpuset
        ),
        check=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--image", required=True)
    parser.add_argument("--tag", default="argon", choices=["argon", "cpu"])
    parser.add_argument("--jobs", default=2, type=int)
    parser.add_argument("--cpuset", help="Optional host CPU set, e.g. 2-3")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
