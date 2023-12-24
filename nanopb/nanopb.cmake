set(this_dir ${CMAKE_CURRENT_LIST_DIR})
set(build_tool ${this_dir}/build_from_proto_c.sh)

#Function to generate nanopb source files from a .proto file.
# 
# Usage:
# nanopb_build(
#   proto_file       // full path to .proto file to be processed.
#   PROTO_PATHS      // list of --proto-path items.
#       <path1>
#       <path2>
#       ...
#   INCLUDE_PATHS    // list of -I paths
#       <path1>
#       <path2>
#       ...
#   [HEADER_PATH <path>]  // path to copy the generated header.
# )
function(nanopb_build proto_file)
    set(flags)
    set(args OUTPUT_DIR HEADER_PATH)
    set(listArgs PROTO_PATHS INCLUDE_PATHS)

    cmake_parse_arguments(arg "${flags}" "${args}" "${listArgs}" ${ARGN})

    cmake_path(GET proto_file FILENAME proto_filename)
    cmake_path(GET proto_file PARENT_PATH proto_dirname)
    cmake_path(GET proto_dirname PARENT_PATH proto_base)
    cmake_path(GET proto_file STEM proto_stem)

    # Default Files to be generated.
    set(gen_source ${proto_dirname}/${proto_stem}.pb.c)
    set(gen_header ${proto_dirname}/${proto_stem}.pb.h)

    # By default, add the parent to the .proto file as a proto-path.
    set(proto_paths --proto-path=${proto_dirname})

    # Append any other PROTO_PATHS provided.
    if(arg_PROTO_PATHS)
        foreach(p ${arg_PROTO_PATHS})
            string(CONCAT proto_paths ${proto_paths} " " --proto-path=${p})
            #list(APPEND proto_paths --proto-path=${p})
        endforeach()
    endif()

    # Default output dir.
    if(NOT arg_OUTPUT_DIR)
        set(output_dir --output-dir=${proto_dirname})
    else()
        set(output_dir --output-dir=${arg_OUTPUT_DIR})
    endif()

    # Create command to move the header to the specified header path.
    # By default, don't export the header.
    set(export_cmd)
    if(arg_HEADER_PATH)
        set(export_cmd COMMAND mv ${gen_header} ${arg_HEADER_PATH})
    endif()

    message(STATUS "Adding custom target: ${proto_stem}_proto_files")

    # Create a joined string with all --proto-path=... items.
    string(CONCAT cmd_str ${proto_paths} " " ${output_dir} " " ${proto_file})

    add_custom_command(
        OUTPUT ${gen_source}
        COMMAND ${CMAKE_COMMAND} -E echo "[nanopb] Processing ${proto_filename}."
        COMMAND cd ${this_dir} && ${build_tool} ${cmd_str}
        ${export_cmd}
        VERBATIM
        DEPENDS ${proto_file}
        )

    add_custom_target(
        ${proto_stem}_proto_files ALL
        DEPENDS ${gen_source}
        )

endfunction()
