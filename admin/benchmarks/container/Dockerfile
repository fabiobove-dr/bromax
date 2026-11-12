# syntax=docker/dockerfile:1
# CPU-only Bromax benchmark toolchain. Build once, retain the image ID/digest,
# and use only that immutable image for measurements; tags are not benchmarks.
FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
       ca-certificates cmake gcc-13 g++-13 git libfftw3-dev \
       ninja-build python3 util-linux \
    && rm -rf /var/lib/apt/lists/*

ENV CC=gcc-13 CXX=g++-13 LC_ALL=C.UTF-8 TZ=Etc/UTC
COPY admin/benchmarks/container/entrypoint.sh /usr/local/bin/bromax-benchmark
RUN chmod 0555 /usr/local/bin/bromax-benchmark
WORKDIR /work
ENTRYPOINT ["/usr/local/bin/bromax-benchmark"]
