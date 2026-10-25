cmake_minimum_required(VERSION 3.22)
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
    project(BetterLinuxCNCAppliance LANGUAGES NONE)
    include("${CMAKE_CURRENT_SOURCE_DIR}/../../cmake/ApplicationInstall.cmake")
endif()

configure_file(packaging/betterlinuxcnc-appliance.in betterlinuxcnc-appliance @ONLY)
install(PROGRAMS "${CMAKE_CURRENT_BINARY_DIR}/betterlinuxcnc-appliance"
    DESTINATION "${CMAKE_INSTALL_SBINDIR}")
install(FILES main.py maintenance.py _accounts.py _policy.py _machine.py
    DESTINATION "${CMAKE_INSTALL_LIBDIR}/betterlinuxcnc/appliance")
install(DIRECTORY templates/
    DESTINATION "${CMAKE_INSTALL_LIBDIR}/betterlinuxcnc/appliance/templates" OPTIONAL)

include(CTest)
if(BUILD_TESTING)
    find_package(Python3 3.11 REQUIRED COMPONENTS Interpreter)
    add_test(NAME appliance-provisioning COMMAND Python3::Interpreter -m unittest discover
        -s "${CMAKE_CURRENT_SOURCE_DIR}/tests" -v)
endif()
