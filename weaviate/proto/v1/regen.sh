#!/bin/bash

set -e  # Exit on any error

echo "This script compiles protos for Protobuf 4, 5.1, 5.2, and 6 versions."

# Get script directory and navigate to project root
SCRIPT_DIR="${0%/*}"
cd "$SCRIPT_DIR"
PROJECT_ROOT=$(pwd)

echo "Project root: $PROJECT_ROOT"

# Clean up any existing proto compilation venv and recreate
PROTO_VENV="$PROJECT_ROOT/.venv_proto_compile"
if [ -d "$PROTO_VENV" ]; then
    echo "Removing existing proto compilation venv..."
    rm -rf "$PROTO_VENV"
fi

python3 -m venv "$PROTO_VENV"
source "$PROTO_VENV/bin/activate"

pip install --upgrade pip

compile_protos() {
    local version=$1
    local output_dir="$PROJECT_ROOT/$version"

    echo "Installing protobuf $version and grpcio-tools..."
    if [ "$version" = "v4" ]; then
        pip install "grpcio-tools==1.59.5"
    elif [ "$version" = "v51" ]; then
        pip install "grpcio-tools==1.60.0"
    elif [ "$version" = "v52" ]; then
        pip install "grpcio-tools==1.66.2"
    elif [ "$version" = "v6" ]; then
        pip install "grpcio-tools==1.70.0"
    else
        echo "Unsupported version: $version"
        exit 1
    fi

    echo "Compiling protos for Protobuf $version... in $output_dir"

    mkdir -p "$output_dir"

    # Compile protos
    python3 -m grpc_tools.protoc \
        -I ../../../../weaviate/grpc/proto \
        --python_out="$output_dir" \
        --pyi_out="$output_dir" \
        --grpc_python_out="$output_dir" \
        ../../../../weaviate/grpc/proto/v1/*.proto

    # Fix imports in generated files
    if [ -d "$version" ]; then
        find "$version" -name "*.py" -exec sed -i '' "s/from v1/from weaviate.proto.v1.$version.v1/g" {} \;
        find "$version" -name "*.pyi" -exec sed -i '' "s/from v1/from weaviate.proto.v1.$version.v1/g" {} \;

        touch "$output_dir"/v1/__init__.py
        touch "$output_dir"/__init__.py

        echo "Generated protos for $version in: $output_dir"
    else
        echo "Warning: No v1 directory found after compilation for $version"
    fi
}


for version in "v4" "v51" "v52" "v6"; do
   compile_protos "$version"
done

deactivate
rm -rf "$PROTO_VENV"

