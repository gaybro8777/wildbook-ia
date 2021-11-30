#!/usr/bin/env bash

set -ex

# See https://stackoverflow.com/a/246128/176882
export ROOT_LOC="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

export DOCKER_BUILDKIT=1

export DOCKER_CLI_EXPERIMENTAL=enabled

# Change to the script's root directory location
cd ${ROOT_LOC}

docker buildx create --name multi-arch-builder --use

# Build the images in dependence order
while [ $# -ge 1 ]; do
    if [ "$1" == "wbia-base" ]; then
        docker buildx build -t wildme/wbia-base:latest --platform linux/amd64,linux/arm64 base
    elif [ "$1" == "wbia-provision" ]; then
        docker buildx build -t wildme/wbia-provision:latest --platform linux/amd64,linux/arm64 provision
    elif [ "$1" == "wbia" ]; then
        if [ "$(uname -m)" == "aarch64" ]; then
            docker buildx build --target org.wildme.wbia.install --no-cache -t wildme/wbia:latest --platform linux/amd64,linux/arm64 .
        else
            docker buildx build --no-cache -t wildme/wbia:latest --platform linux/amd64,linux/arm64 .
        fi
    elif [ "$1" == "wbia-develop" ]; then
        cd ../
        docker buildx build -t wildme/wbia:develop --platform linux/amd64,linux/arm64 devops/develop
        cd devops/
    else
        echo "Image $1 not found"
        exit 1
    fi
    shift
done
