#!/usr/bin/env julia

using ArgParse
using JLD2
using JSON
using DataFrames  # Required to properly handle DataFrame

"""
Recursively convert JLD2 data to something JSON-serializable.
Unsupported types are replaced with string descriptions.
"""
function safe_serialize(obj)
    if isa(obj, Number) || isa(obj, String) || isa(obj, Bool) || obj === nothing
        return obj
    elseif isa(obj, AbstractArray)
        return [safe_serialize(x) for x in obj]
    elseif isa(obj, Dict)
        return Dict(string(k) => safe_serialize(v) for (k, v) in obj)
    elseif isa(obj, DataFrame)
        # Serialize the DataFrame to a Dict of column names and values (for JSON compatibility)
        return Dict("columns" => names(obj), "data" => Matrix(obj))
    else
        return JSON.lower(obj)  # Try JSON-compatible lowering for other types
    end
end

function jld2_to_json(jld2_path::String, json_path::String)
    println("Reading from $jld2_path ...")
    jld_data = jldopen(jld2_path, "r")

    result = Dict{String, Any}()

    for k in keys(jld_data)
        println("Processing key: $k")
        # Ensure that we're processing the reconstructed DataFrame properly
        value = jld_data[k]

        # If it's a DataFrame, we need to serialize it differently
        result[string(k)] = safe_serialize(value)
    end

    close(jld_data)

    println("Writing to $json_path ...")
    open(json_path, "w") do io
        JSON.print(io, result)
    end

    println("Conversion complete.")
end

function main()
    s = ArgParseSettings()
    @add_arg_table s begin
        "input"
            help = "Input JLD2 file path"
            required = true
        "--output", "-o"
            help = "Output JSON file path"
            required = true
    end

    parsed_args = parse_args(s)

    input_file = parsed_args["input"]
    output_file = parsed_args["output"]

    jld2_to_json(input_file, output_file)
end

main()
