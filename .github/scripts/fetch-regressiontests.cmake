#
# This file is part of the GROMACS molecular simulation package.
#
# Copyright 2022- The GROMACS Authors
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

# Release fixtures supplement the current source tree's unit/integration tests.
set(regression_version 2026.4)
set(regression_sha256 c1d9b1f8518100fdf113d32f3a67e5d5934bb456cf2e0ba8cb4bceba748ded8f)
set(archive "${CMAKE_CURRENT_BINARY_DIR}/regressiontests-${regression_version}.tar.gz")
file(DOWNLOAD
    "https://ftp.gromacs.org/regressiontests/regressiontests-${regression_version}.tar.gz"
    "${archive}"
    EXPECTED_HASH "SHA256=${regression_sha256}"
    TLS_VERIFY ON
    STATUS download_status)
list(GET download_status 0 download_result)
if(NOT download_result EQUAL 0)
    message(FATAL_ERROR "Regression test download failed: ${download_status}")
endif()
file(ARCHIVE_EXTRACT INPUT "${archive}" DESTINATION "${CMAKE_CURRENT_BINARY_DIR}")
if(NOT EXISTS "${CMAKE_CURRENT_BINARY_DIR}/regressiontests-${regression_version}/gmxtest.pl")
    message(FATAL_ERROR "Regression test archive is missing gmxtest.pl")
endif()
