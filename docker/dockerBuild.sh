#!/bin/bash

SCRIPT_DIR="${ROOT_DIR:-$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )}"
DOCKER_IMAGES=()
FORCE_REBUILD=""

get_all_images () {
    dockerFiles=($(find . -iname "dockerfile"))
    DOCKER_IMAGES=($(dirname ${dockerFiles[@]}))
} 

usage() {
    echo "Usage:"
    echo "  Building image: dockerBuild.sh build <image name>"
    echo "  List possible images: dockerBuild.sh ls"
    echo "  To build all: dockerBuild.sh build all"
    echo "  TO build all vpnspeed images: dockerBuild.sh build vpnspeedimages"
    echo "  To rebuild: dockerBuild.sh rebuild <image name/all/vpnspeedimages> "
    exit 1
}

build_image() {
    local image=$1
    local imageName=${image:2}
    local contextDir=${3:-"."}
    docker build ${FORCE_REBUILD} -f "${SCRIPT_DIR}/$image/Dockerfile" ${contextDir} -t "$imageName" 1> /dev/null && echo "Built \"$imageName\" succesfully" || echo "Build \"$imageName\" failed..."
}

build_vpnspeed() {
    build_image "./vpnspeed" "vpnspeed"
}

build_runner() {
    build_image "./runner" "runner" "${SCRIPT_DIR}/../"
}

build_all() {
    get_all_images
    build_vpnspeed
    for image in ${DOCKER_IMAGES[@]} ; do
        [[ "${image:2}" == "vpnspeed" ]] && continue # Do not build base image twice
        [[ "${image:2}" == "runner" ]] && build_runner && continue
        build_image "$image"
    done
}

ls_images() {
    get_all_images
    for image in ${DOCKER_IMAGES[@]} ; do
        echo "Image: ${image:2}, image path: $image"
    done
}

build() {
    echo "Building..."
    if [[ ${2,,} == "all" ]] ; then
        build_all
    elif [[ ${2,,} == "vpnspeedimages" ]] ; then
        build_vpnspeed
        get_all_images
        for image in ${DOCKER_IMAGES[@]} ; do
            [[ $image == *"vpnspeed/"* ]] && build_image "$image" || continue
        done
    elif [[ ${2,,} == "runner" ]] ; then
        build_runner
    else
        for image in ${@:2} ; do
            [[ $image == *"vpnspeed/"* ]] && build_vpnspeed || true
            build_image "./$image" "$image"
        done
    fi
}

rebuild() {
    FORCE_REBUILD="--no-cache"
    build $@
}

cmd=${1,,}
case "$cmd" in
        ls)
            ls_images
            ;;
        build)
            build $@
            ;;
        rebuild)
            rebuild $@
            ;;
        *)
            usage
esac
