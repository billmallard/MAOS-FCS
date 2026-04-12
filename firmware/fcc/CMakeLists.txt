cmake_minimum_required(VERSION 3.16)
project(maos_fcc C)

set(CMAKE_C_STANDARD 17)
set(CMAKE_C_STANDARD_REQUIRED ON)

enable_testing()

add_executable(maos_fcc
    src/main.c
    src/fcc_scheduler.c
    src/actuator_protocol.c
)

target_include_directories(maos_fcc PRIVATE include)

add_executable(maos_fcc_actuator_test
    src/test_actuator_protocol.c
    src/actuator_protocol.c
)

target_include_directories(maos_fcc_actuator_test PRIVATE include)

add_test(NAME actuator_protocol_conformance COMMAND maos_fcc_actuator_test)
