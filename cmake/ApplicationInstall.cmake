# Default application layout; caller-provided CMake install paths remain supported.
if(CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)
    set(CMAKE_INSTALL_PREFIX "/usr" CACHE PATH "Application install prefix" FORCE)
endif()
set(CMAKE_INSTALL_LIBDIR "lib" CACHE PATH "Application library directory")
include(GNUInstallDirs)
