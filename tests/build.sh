#!/usr/bin/env bash
## Build Dynamic Fire System for the test cases.
##
## Usage: tests/build.sh <landis_image@sha256:...> <out_dir> [sdk_image@sha256:...]
##
## Builds a copy of src/ in the .NET SDK container, against the three library DLLs inside the
## LANDIS-II image, i.e. the libraries the cases run with. Landis.Core comes from the feeds in
## src/NuGet.Config. Writes <out_dir>/Landis.Extension.DynamicFire-v4.dll and <out_dir>/build.log.
set -euo pipefail
[ $# -ge 2 ] && [ $# -le 3 ] || { sed -n '2,9p' "$0" | sed 's/^## \{0,1\}//'; exit 2; }
img=$1
out=$2
sdk=${3:-mcr.microsoft.com/dotnet/sdk@sha256:ff39a765f04619c8d146796fc09b38499ae5984f4a2a4c3a0a57d0022855daee}
for i in "$img" "$sdk"; do
  [[ $i =~ @sha256:[0-9a-f]{64}$ ]] || { echo "build.sh: pin images by digest, got: $i" >&2; exit 2; }
done
repo=$(cd "$(dirname "$0")/.." && pwd)
dll=Landis.Extension.DynamicFire-v4.dll
lib=/opt/landis-ii/Core-Model-v8-LINUX/build/Release
mkdir -p "$out"
out=$(cd "$out" && pwd)
work=$(mktemp -d)
cid=
trap 'rm -rf "$work"; [ -z "$cid" ] || docker rm -f "$cid" > /dev/null' EXIT

cp -r "$repo/src" "$work/src"
rm -rf "$work/src/obj" "$work/src/bin"
mkdir -p "$work/src/lib"
cid=$(docker create "$img")
for f in Landis.Library.UniversalCohorts-v2.dll Landis.Library.Parameters-v2.dll Landis.Library.Metadata-v2.dll; do
  docker cp -q "$cid:$lib/$f" "$work/src/lib/$f"
done

## As root: the CLI's first-run NuGet mutex fails for a user the container does not know.
## Ownership of the build tree is handed back afterwards.
docker run --rm -e DOTNET_CLI_TELEMETRY_OPTOUT=1 -v "$work:/w" -w /w/src "$sdk" \
  sh -c "dotnet build dynamic-fire.csproj -c Release -o /w/out; rc=\$?; chown -R $(id -u):$(id -g) /w; exit \$rc" \
  > "$out/build.log" 2>&1 || { tail -20 "$out/build.log" >&2; echo "build.sh: build failed" >&2; exit 1; }
cp "$work/out/$dll" "$out/$dll"
echo "build.sh: $(sha256sum "$out/$dll" | cut -c1-64)  $dll"
