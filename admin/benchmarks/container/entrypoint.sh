#!/usr/bin/env bash
# Copyright 2026- The GROMACS Authors. LGPL-2.1-or-later.
set -euo pipefail

export HOME=/tmp
: "${BROMAX_CORPUS_TAG:?Missing corpus tag}"
: "${BROMAX_BUILD_JOBS:?Missing build jobs}"
: "${BROMAX_BENCH_IMAGE_REF:?Missing immutable image reference}"
: "${BROMAX_BENCH_IMAGE_ID:?Missing image ID}"

for tree in baseline candidate; do
    test -d "/work/${tree}/.git" -o -f "/work/${tree}/.git"
done
test ! -e /work/results
mkdir -p /work/artifacts /work/_build

# This first container profile tests CPU/mixed-precision and native x86-64 SSE2.
# The regression suite is NOT downloaded at runtime: network access is disabled.
# Missing regression-suite and long physical/ensemble checks are not qualified.
dpkg-query -W -f='${Package}=${Version}\n' \
    gcc-13 g++-13 cmake ninja-build libfftw3-dev python3 \
    > /work/artifacts/toolchain-packages.txt
uname -a > /work/artifacts/host-kernel.txt

python3 -m unittest discover -s /work/candidate/admin/benchmarks
python3 -m unittest discover -s /work/candidate/tests/corpus
for tree in baseline candidate; do
    cmake -S "/work/${tree}" -B "/work/_build/${tree}" -G Ninja \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_C_COMPILER=gcc-13 -DCMAKE_CXX_COMPILER=g++-13 \
        -DGMX_GPU=OFF -DGMX_SIMD=SSE2 -DGMX_DOUBLE=OFF \
        -DGMX_THREAD_MPI=ON -DGMX_MPI=OFF \
        -DGMX_BUILD_UNITTESTS=ON -DREGRESSIONTEST_DOWNLOAD=OFF \
        2>&1 | tee "/work/artifacts/${tree}-configure.log"
    cmake --build "/work/_build/${tree}" --target all tests \
        --parallel "${BROMAX_BUILD_JOBS}" \
        2>&1 | tee "/work/artifacts/${tree}-build.log"
done

python3 /work/candidate/admin/benchmarks/paired.py \
    --baseline /work/baseline --baseline-build /work/_build/baseline \
    --candidate /work/candidate --candidate-build /work/_build/candidate \
    --tag "${BROMAX_CORPUS_TAG}" --output /work/results
