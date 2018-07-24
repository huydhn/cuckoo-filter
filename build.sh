#!/bin/sh

TEMP=`getopt -o '' -l release: -- "$@"`
eval set -- "$TEMP"

while true; do
    case "$1" in
        --release)
            RELEASE=$2 ; shift 2 ;;
        --) shift; break ;;
        *) echo "Internal error!" ; exit 1 ;;
    esac
done

if [[ -z $RELEASE ]] ; then
    echo "$0 - Build number is not set"
    exit 1
fi

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR

VERSION=`python ./setup.py --version`
DISTRO=`rpm --eval %{dist}`

BUILDROOT=`pwd`/build
rm -rf $BUILDROOT

mkdir -p $BUILDROOT/BUILDROOT
mkdir -p $BUILDROOT/BUILD
mkdir -p $BUILDROOT/RPMS
mkdir -p $BUILDROOT/SOURCES
mkdir -p $BUILDROOT/SPECS
mkdir -p $BUILDROOT/SRPMS

fpm --verbose \
    -s python \
    -t rpm    \
    --python-bin /usr/bin/python3.4                \
    --python-easyinstall /usr/bin/easy_install-3.4 \
    --python-package-name-prefix python34          \
    -a noarch \
    -n python34-cuckoo-filter \
    --iteration $RELEASE$DISTRO \
    -d python34-bitarray \
    -d python34-mmh3     \
    ./setup.py

RC=$?; if [[ $RC != 0 ]]; then exit $RC; fi

# get the RPMs
find $BUILDROOT/RPMS -name '*.rpm' -exec cp {} . \;
