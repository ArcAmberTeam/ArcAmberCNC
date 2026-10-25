find_package(Python3 3.11 REQUIRED COMPONENTS Interpreter)
set(homing_output "${CMAKE_CURRENT_BINARY_DIR}/generated")
file(GLOB_RECURSE homing_vendor_sources CONFIGURE_DEPENDS
    "${CMAKE_SOURCE_DIR}/vendor/cnc-mesa/*")
file(GLOB_RECURSE homing_native_headers CONFIGURE_DEPENDS
    "${CMAKE_SOURCE_DIR}/src/*.h")
add_custom_command(OUTPUT "${homing_output}/zhulong_homing.so" "${homing_output}/provenance.json"
    COMMAND Python3::Interpreter "${CMAKE_CURRENT_SOURCE_DIR}/build.py"
        --source "${CMAKE_SOURCE_DIR}" --output "${homing_output}"
    DEPENDS build.py ${homing_vendor_sources} ${homing_native_headers}
        "${CMAKE_SOURCE_DIR}/VERSION" "${CMAKE_SOURCE_DIR}/src/configure.ac"
        "${CMAKE_SOURCE_DIR}/src/hal/utils/halcompile.g"
        "${CMAKE_SOURCE_DIR}/src/Makefile.modinc.in"
    VERBATIM)
add_custom_target(betterlinuxcnc-mesa-homing ALL
    DEPENDS "${homing_output}/zhulong_homing.so" "${homing_output}/provenance.json")
install(FILES "${homing_output}/zhulong_homing.so"
    DESTINATION "${CMAKE_INSTALL_LIBDIR}/linuxcnc/modules")
install(FILES "${homing_output}/provenance.json"
    DESTINATION "${CMAKE_INSTALL_DATADIR}/betterlinuxcnc/homing")
