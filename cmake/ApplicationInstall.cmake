# Default application layout; caller-provided CMake install paths remain supported.
if(CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)
    set(CMAKE_INSTALL_PREFIX "/usr" CACHE PATH "Application install prefix" FORCE)
endif()
# Relative install destinations are strings, not host filesystem paths. Giving an
# untyped -DCMAKE_INSTALL_LIBDIR=lib a PATH type would expand it against the cwd.
set(CMAKE_INSTALL_LIBDIR "lib" CACHE STRING "Application library directory relative to the prefix")
include(GNUInstallDirs)
