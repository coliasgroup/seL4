#
# Copyright 2020, Data61, CSIRO (ABN 41 687 119 230)
#
# SPDX-License-Identifier: BSD-2-Clause
#

cmake_minimum_required(VERSION 3.7.2)

project(libsel4 C)

set(configure_string "")

config_choice(
    LibSel4FunctionAttributes
    LIB_SEL4_FUNCTION_ATTRIBUTE
    "Function attributes \
    default->Verification friendly default configuration. syscalls will be inlined, \
        but generated functions will not. \
    inline->When set to true will mark generated functions as 'inline', allowing \
        them to be inlined by the callee user code. This may be undesirable \
        for verification, so setting to 'n' will forcibly prevent the function \
        from being inlined. \
    public->When set to true will make all user facing functions available as \
        public symbols, which can be convenient for some language bindings."
    "inline;LibSel4FunctionAttributeInline;LIB_SEL4_INLINE_INVOCATIONS"
    "default;LibSel4FunctionAttributeDefault;LIB_SEL4_DEFAULT_FUNCTION_ATTRIBUTES"
    "public;LibSel4FunctionAttributePublic;LIB_SEL4_PUBLIC_SYMBOLS"
)

config_option(
    LibSel4StubsUseIPCBufferOnly LIB_SEL4_STUBS_USE_IPC_BUFFER_ONLY
    "use only IPC buffer for syscalls. When generating syscall wrappers, only use the \
    IPC buffer for marshalling and unmarshalling arguments. Without this option set, \
    arguments will be passed in registers where possible for better performance."
    DEFAULT OFF
)

config_string(
    LibSel4PrintInvocationErrors LIB_SEL4_PRINT_INVOCATION_ERRORS
    "Generated stubs on error will print the message contained in the IPC buffer"
    DEFAULT 1
    DEPENDS "KernelInvocationReportErrorIPC" DEFAULT_DISABLED 0
    UNQUOTE
)

config_option(
    LibSel4UseRust LIB_SEL4_USE_RUST
    ""
    DEFAULT ON
    # DEFAULT OFF
)

if(LibSel4StubsUseIPCBufferOnly)
    set(buffer "--buffer")
endif()

RequireFile(SYSCALL_STUB_GEN_PATH syscall_stub_gen.py PATHS tools)

add_config_library(sel4 "${configure_string}")

# Currently we use autoconf.h, so generate one of those
generate_autoconf(sel4_autoconf "kernel;sel4")

gen_invocation_header(OUTPUT include/sel4/invocation.h XML include/interfaces/sel4.xml LIBSEL4)

gen_invocation_header(
    OUTPUT sel4_arch_include/${KernelSel4Arch}/sel4/sel4_arch/invocation.h
    XML "${CMAKE_CURRENT_SOURCE_DIR}/sel4_arch_include/${KernelSel4Arch}/interfaces/sel4arch.xml"
    LIBSEL4 SEL4ARCH
)

gen_invocation_header(
    OUTPUT arch_include/${KernelArch}/sel4/arch/invocation.h
    XML "${CMAKE_CURRENT_SOURCE_DIR}/arch_include/${KernelArch}/interfaces/sel4arch.xml"
    LIBSEL4 ARCH
)

set(
    source_header_dirs
    "${CMAKE_CURRENT_SOURCE_DIR}/include"
    "${CMAKE_CURRENT_SOURCE_DIR}/arch_include/${KernelArch}"
    "${CMAKE_CURRENT_SOURCE_DIR}/sel4_arch_include/${KernelSel4Arch}"
    "${CMAKE_CURRENT_SOURCE_DIR}/sel4_plat_include/${KernelPlatform}"
    "${CMAKE_CURRENT_SOURCE_DIR}/mode_include/${KernelWordSize}"
)
include_directories("${source_header_dirs}")

# Add the include directory of autoconf.h to the cflags for the bitfield generation
include_directories("$<TARGET_PROPERTY:sel4_autoconf,INTERFACE_INCLUDE_DIRECTORIES>")

function(genbf target_prefix pbf_location bf_location header_output)
    get_generated_files(gen_list sel4_autoconf_Gen)
    cppfile(
        "${pbf_location}"
        ${target_prefix}_pbf
        "${bf_location}"
        EXTRA_FLAGS
        -P
        EXTRA_DEPS
        sel4_autoconf_Gen
        ${gen_list}
    )
    GenHBFTarget(
        "libsel4"
        ${target_prefix}_h
        "${header_output}"
        "${pbf_location}"
        ${target_prefix}_pbf
        ""
        ""
        "${bf_location}"
    )
endfunction(genbf)

genbf(
    "libsel4_shared_types_gen"
    "${CMAKE_CURRENT_BINARY_DIR}/include/sel4/shared_types.pbf"
    "${CMAKE_CURRENT_SOURCE_DIR}/mode_include/${KernelWordSize}/sel4/shared_types.bf"
    "${CMAKE_CURRENT_BINARY_DIR}/include/sel4/shared_types_gen.h"
)

genbf(
    "libsel4_sel4_arch_types_gen"
    "${CMAKE_CURRENT_BINARY_DIR}/sel4_arch_include/${KernelSel4Arch}/sel4/sel4_arch/types.pbf"
    "${CMAKE_CURRENT_SOURCE_DIR}/sel4_arch_include/${KernelSel4Arch}/sel4/sel4_arch/types.bf"
    "${CMAKE_CURRENT_BINARY_DIR}/sel4_arch_include/${KernelSel4Arch}/sel4/sel4_arch/types_gen.h"
)

if(KernelIsMCS)
    set(mcs --mcs)
endif()
if(KernelX86_64VTX64BitGuests)
    set(64bitguests --x86-vtx-64-bit-guests)
endif()
add_custom_command(
    OUTPUT include/sel4/syscall.h
    COMMAND rm -f include/sel4/syscall.h
    COMMAND
        "${XMLLINT_PATH}"
        --noout
        --schema
            "${CMAKE_CURRENT_SOURCE_DIR}/include/api/syscall.xsd"
            "${CMAKE_CURRENT_SOURCE_DIR}/include/api/syscall.xml"
    COMMAND
        ${PYTHON3} "${SYSCALL_ID_GEN_PATH}"
        --xml "${CMAKE_CURRENT_SOURCE_DIR}/include/api/syscall.xml"
        --libsel4_header include/sel4/syscall.h ${mcs}
    DEPENDS
        "${SYSCALL_ID_GEN_PATH}" "${CMAKE_CURRENT_SOURCE_DIR}/include/api/syscall.xsd"
        "${CMAKE_CURRENT_SOURCE_DIR}/include/api/syscall.xml"
    COMMENT "Generate syscall.h"
    VERBATIM
)

set(
    interface_xmls
    "${CMAKE_CURRENT_SOURCE_DIR}/sel4_arch_include/${KernelSel4Arch}/interfaces/sel4arch.xml"
    "${CMAKE_CURRENT_SOURCE_DIR}/arch_include/${KernelArch}/interfaces/sel4arch.xml"
    "${CMAKE_CURRENT_SOURCE_DIR}/include/interfaces/sel4.xml"
)
add_custom_command(
    OUTPUT include/interfaces/sel4_client.h
    COMMAND rm -f include/interfaces/sel4_client.h
    COMMAND
        echo "CONFIG_WORD_SIZE=${KernelWordSize}" > config
    COMMAND
        "${PYTHON3}" "${SYSCALL_STUB_GEN_PATH}" ${buffer} ${64bitguests} ${mcs} -a
        "${KernelSel4Arch}" -c config -o include/interfaces/sel4_client.h ${interface_xmls}
    DEPENDS
        "${SYSCALL_STUB_GEN_PATH}"
        ${interface_xmls}
        BYPRODUCTS
        config
    COMMENT "Generate sel4_client.h"
    VERBATIM
)

add_custom_target(
    sel4_generated
    DEPENDS
        include/interfaces/sel4_client.h
        include/sel4/syscall.h
        include/sel4/invocation.h
        arch_include/${KernelArch}/sel4/arch/invocation.h
        include/sel4/shared_types_gen.h
        sel4_arch_include/${KernelSel4Arch}/sel4/sel4_arch/invocation.h
        sel4_arch_include/${KernelSel4Arch}/sel4/sel4_arch/types_gen.h
)

add_library(sel4_pre "src/sel4_bootinfo.c")
target_link_libraries(sel4_pre PRIVATE kernel_Config sel4_Config sel4_autoconf)
target_include_directories(
    sel4_pre
    PUBLIC
        ${source_header_dirs}
        "${CMAKE_CURRENT_BINARY_DIR}/include"
        "${CMAKE_CURRENT_BINARY_DIR}/arch_include/${KernelArch}"
        "${CMAKE_CURRENT_BINARY_DIR}/sel4_arch_include/${KernelSel4Arch}"
)
add_dependencies(sel4_pre sel4_generated)

set(empty_c "src/empty.c")

if(NOT LibSel4UseRust)
    add_library(sel4 ${empty_c})
    target_link_libraries(sel4 PUBLIC sel4_pre)
else()
    if(NOT DEFINED HACK_CARGO_MANIFEST_PATH)
        message(FATAL_ERROR "HACK_CARGO_MANIFEST_PATH must be set" )
    endif()
    if(NOT DEFINED HACK_CARGO_CONFIG)
        message(FATAL_ERROR "HACK_CARGO_CONFIG must be set" )
    endif()

    if(HACK_CARGO_RELEASE)
        set(cargo_profile_flags "--release" )
    endif()

    if(NOT HACK_CARGO_NO_BUILD_SYSROOT)
        set(cargo_build_sysroot_flags "-Zbuild-std=core,alloc,compiler_builtins" "-Zbuild-std-features=compiler-builtins-mem,compiler-builtins-weak-intrinsics")
    endif()

    set(rust_target "${HACK_RUST_TARGET}")
    set(cargo_manifest_path "${HACK_CARGO_MANIFEST_PATH}")
    set(cargo_config "${HACK_CARGO_CONFIG}")
    set(rust_build_root_dir "${CMAKE_CURRENT_BINARY_DIR}/rust")
    set(rust_build_target_dir "${rust_build_root_dir}/target")
    set(rust_build_out_dir "${rust_build_root_dir}/out")
    set(rust_crate_name "sel4_sys_wrappers")
    set(rust_lib_filename "lib${rust_crate_name}.a")
    set(rust_lib_file "${rust_build_out_dir}/${rust_lib_filename}")

    set(sel4_include_dirs "$<JOIN:$<TARGET_PROPERTY:sel4_pre,INCLUDE_DIRECTORIES>,:>")

    add_custom_target(
        sel4_rust_cargo
        DEPENDS
            sel4_pre
        BYPRODUCTS
            ${rust_lib_file}
        COMMAND
            ${CMAKE_COMMAND} -E env
                SEL4_INCLUDE_DIRS=${sel4_include_dirs}
                SEL4_OBJECT_API=${CMAKE_CURRENT_SOURCE_DIR}/include/interfaces/sel4.xml
                SEL4_OBJECT_API_ARCH=${CMAKE_CURRENT_SOURCE_DIR}/arch_include/${KernelArch}/interfaces/sel4arch.xml
                SEL4_OBJECT_API_SEL4_ARCH=${CMAKE_CURRENT_SOURCE_DIR}/sel4_arch_include/${KernelSel4Arch}/interfaces/sel4arch.xml
                    cargo build
                        -Z unstable-options
                        --config ${cargo_config}
                        --locked
                        --target ${rust_target}
                        ${cargo_build_sysroot_flags}
                        ${cargo_profile_flags}
                        --target-dir ${rust_build_target_dir}
                        --out-dir ${rust_build_out_dir}
                        --manifest-path ${cargo_manifest_path}
                        -p sel4-sys-wrappers
        USES_TERMINAL
    )

    add_library(sel4_rust STATIC IMPORTED GLOBAL)
    set_property(
        TARGET sel4_rust
        PROPERTY IMPORTED_LOCATION "${rust_lib_file}"
    )
    add_dependencies(sel4_rust sel4_rust_cargo)

    set(patched_headers_dir "${CMAKE_CURRENT_BINARY_DIR}/patched_headers.d")
    set(patch_headers_py "${CMAKE_CURRENT_SOURCE_DIR}/tools/patch_headers.py")

    add_custom_target(
        patched_headers
        DEPENDS
            sel4_pre
            ${patch_headers_py}
        BYPRODUCTS
            ${patched_headers_dir}
        COMMAND
            rm -rf ${patched_headers_dir}
        COMMAND
            mkdir -p ${patched_headers_dir}
        COMMAND
            python3 ${patch_headers_py}
                ${patched_headers_dir}
                ${sel4_include_dirs}
        USES_TERMINAL
    )

    add_library(sel4 ${empty_c})
    target_link_libraries(sel4 PUBLIC sel4_rust)
    target_include_directories(
        sel4
        PUBLIC
            ${patched_headers_dir}
    )
    add_dependencies(sel4 patched_headers)
endif()
