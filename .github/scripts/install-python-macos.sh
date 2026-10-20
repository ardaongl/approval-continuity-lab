#!/usr/bin/env bash
# CI bootstrap only: CPython 3.12.14 is a source-only security release on macOS.
set -euo pipefail

runtime_root="${RUNNER_TEMP:?}/acl-cpython-3.12.14"
mkdir -p "$runtime_root"
archive="$runtime_root/Python-3.12.14.tgz"
curl --fail --location --retry 3 \
  https://www.python.org/ftp/python/3.12.14/Python-3.12.14.tgz \
  --output "$archive"
printf '%s  %s\n' \
  '6c6df908d2c3fd24e6d76869e92542abd0f33aec9dfc18df8875f89660286d43' \
  "$archive" | shasum -a 256 --check

tar -xzf "$archive" -C "$runtime_root"
cd "$runtime_root/Python-3.12.14"
openssl_prefix="$(brew --prefix openssl@3)"
sqlite_prefix="$(brew --prefix sqlite)"
test -f "$openssl_prefix/include/openssl/ssl.h"
test -f "$sqlite_prefix/include/sqlite3.h"
CPPFLAGS="-I${sqlite_prefix}/include" \
LDFLAGS="-L${sqlite_prefix}/lib" \
  ./configure --prefix="$runtime_root/install" \
    --with-openssl="$openssl_prefix" --with-ensurepip=install
make -j 3
make install
ln -s python3 "$runtime_root/install/bin/python"
printf '%s\n' "$runtime_root/install/bin" >> "${GITHUB_PATH:?}"
