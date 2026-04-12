cmake_minimum_required(VERSION 3.16)
project(maos_fcc C)

set(CMAKE_C_STANDARD 17)
set(CMAKE_C_STANDARD_REQUIRED ON)

add_executable(maos_fcc
    src/main.c
    src/fcc_scheduler.c
)

target_include_directories(maos_fcc PRIVATE include)
