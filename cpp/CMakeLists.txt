cmake_minimum_required(VERSION 3.15)
project(cf_rating_analysis LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(naive src/naive.cpp)
add_executable(fft   src/fft.cpp)

if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(naive PRIVATE -Wall -Wextra -Wpedantic)
    target_compile_options(fft   PRIVATE -Wall -Wextra -Wpedantic)
endif()
