#!/bin/sh
# Recreates the source copies the probes read, from upstream v2026.10.04 (bbf2e151).
# The probes never import the integration; they pull single functions out of these
# copies with `ast`. Byte-identical to the copies the outputs here were made with.
# usage: sh extract_blobs.sh <path-to-a-clone-that-has-bbf2e151>
set -e
REPO="${1:?path to a clone that has bbf2e151}"
REV=bbf2e151
CC=custom_components/irrigation_plus
HERE="$(cd "$(dirname "$0")" && pwd)"

git -C "$REPO" show "$REV:$CC/calculation.py" > "$HERE/calculation_blob.py"
git -C "$REPO" show "$REV:$CC/const.py" > "$HERE/const_blob.py"
git -C "$REPO" show "$REV:$CC/weather_aggregate.py" > "$HERE/weather_aggregate_blob.py"
git -C "$REPO" show "$REV:$CC/calcmodules/pyeto/__init__.py" > "$HERE/pyeto_module_init.py"
mkdir -p "$HERE/pyeto_extracted/pyeto"
for f in __init__.py _check.py convert.py fao.py thornthwaite.py version.txt; do
  git -C "$REPO" show "$REV:$CC/calcmodules/pyeto/pyeto/$f" > "$HERE/pyeto_extracted/pyeto/$f"
done
echo "extracted from $REV into $HERE"
