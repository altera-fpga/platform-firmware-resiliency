# Shared compiler flags for c_header_compile end-to-end tests.
CC ?= gcc
CFLAGS ?= -std=c11 -Wall -Wextra -Wpedantic -Werror -Wconversion -Wsign-conversion
LDFLAGS ?=
