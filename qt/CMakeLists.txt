cmake_minimum_required(VERSION 3.22)
project(BetterLinuxCNC VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(Qt6 6.8 REQUIRED COMPONENTS Quick QuickControls2 Svg)
qt_standard_project_setup(REQUIRES 6.8)

qt_add_executable(betterlinuxcnc app/main.cpp)
target_link_libraries(betterlinuxcnc PRIVATE Qt6::Quick Qt6::QuickControls2 Qt6::Svg)
set_target_properties(betterlinuxcnc PROPERTIES MACOSX_BUNDLE TRUE
    MACOSX_BUNDLE_GUI_IDENTIFIER org.betterlinuxcnc.qt
    MACOSX_BUNDLE_BUNDLE_NAME BetterLinuxCNC)

# The named QML modules declare their public types in qmldir. Private components
# stay internal; each capability owns its presentation state and resources.
file(GLOB_RECURSE QML_RESOURCES CONFIGURE_DEPENDS RELATIVE "${CMAKE_CURRENT_SOURCE_DIR}"
    "qml/*.qml" "qml/*.js" "qml/*/qmldir" "qml/*.png" "qml/*.svg")
qt_add_resources(betterlinuxcnc qml_resources PREFIX "/" FILES ${QML_RESOURCES})

include(CTest)
if(BUILD_TESTING)
    find_package(Qt6 6.8 REQUIRED COMPONENTS QuickTest)
    qt_add_executable(qml-ui-tests tests/main.cpp)
    target_link_libraries(qml-ui-tests PRIVATE Qt6::QuickTest Qt6::QuickControls2)
    target_compile_definitions(qml-ui-tests PRIVATE
        QUICK_TEST_SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}/tests")
    add_test(NAME qml-ui COMMAND qml-ui-tests -import "${CMAKE_CURRENT_SOURCE_DIR}/qml")
    set_tests_properties(qml-ui PROPERTIES ENVIRONMENT
        "QT_QPA_PLATFORM=offscreen;QT_QUICK_BACKEND=software;QT_QUICK_CONTROLS_STYLE=Basic")
    find_package(Python3 REQUIRED COMPONENTS Interpreter)
    add_test(NAME module-boundaries COMMAND Python3::Interpreter
        "${CMAKE_CURRENT_SOURCE_DIR}/scripts/check_boundaries.py")
    file(GLOB_RECURSE QML_SOURCES CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/qml/*.qml")
    add_test(NAME qml-lint COMMAND Qt6::qmllint --max-warnings 0
        -I "${CMAKE_CURRENT_SOURCE_DIR}/qml" ${QML_SOURCES})
endif()

install(TARGETS betterlinuxcnc BUNDLE DESTINATION . RUNTIME DESTINATION bin)
install(FILES packaging/betterlinuxcnc-qt.desktop DESTINATION share/applications)
install(FILES ../COPYING qml/BetterCnc/Catalog/assets/NOTICE.md
    qml/BetterCnc/Catalog/assets/TOOLBAR-LICENSE DESTINATION share/doc/betterlinuxcnc-qt)
set(CPACK_PACKAGE_NAME "betterlinuxcnc-qt")
set(CPACK_PACKAGE_VERSION "${PROJECT_VERSION}")
set(CPACK_PACKAGE_CONTACT "BetterLinuxCNC maintainers")
set(CPACK_PACKAGE_DESCRIPTION_SUMMARY "Native Qt Quick machine-operation interface prototype")
set(CPACK_DEBIAN_PACKAGE_SHLIBDEPS ON)
set(CPACK_DEBIAN_PACKAGE_DEPENDS "qml6-module-qtqml, qml6-module-qtqml-models, qml6-module-qtquick, qml6-module-qtquick-window, qml6-module-qtquick-controls, qml6-module-qtquick-layouts, qml6-module-qtquick-templates, qml6-module-qtquick-shapes, qml6-module-qtqml-workerscript, fonts-noto-cjk, fonts-liberation")
include(CPack)
