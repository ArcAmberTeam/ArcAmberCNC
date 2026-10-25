cmake_minimum_required(VERSION 3.22)
project(BetterLinuxCNCUpdater LANGUAGES NONE)
include(GNUInstallDirs)

set(BETTERCNC_UPDATER_BINARY "" CACHE FILEPATH "Prebuilt release updater for the target architecture")
if(BETTERCNC_UPDATER_BINARY)
    if(NOT EXISTS "${BETTERCNC_UPDATER_BINARY}")
        message(FATAL_ERROR "BETTERCNC_UPDATER_BINARY does not exist")
    endif()
    set(updater_binary "${BETTERCNC_UPDATER_BINARY}")
else()
    find_program(CARGO_EXECUTABLE cargo REQUIRED)
    set(updater_target "${CMAKE_CURRENT_BINARY_DIR}/cargo")
    set(updater_binary "${updater_target}/release/betterlinuxcnc-updater")
    file(GLOB_RECURSE updater_sources CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/src/*.rs")
    add_custom_command(OUTPUT "${updater_binary}"
        COMMAND "${CMAKE_COMMAND}" -E env "CARGO_TARGET_DIR=${updater_target}"
            "${CARGO_EXECUTABLE}" build --release --locked --bin betterlinuxcnc-updater
        WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
        DEPENDS ${updater_sources} Cargo.toml Cargo.lock rust-toolchain.toml
        VERBATIM)
    add_custom_target(betterlinuxcnc-updater-service ALL DEPENDS "${updater_binary}")
endif()
install(PROGRAMS "${updater_binary}" DESTINATION ${CMAKE_INSTALL_BINDIR})
