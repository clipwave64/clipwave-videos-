#!/usr/bin/env bash
# Rebuilds everything the ClipWave generator needs in a fresh cloud workspace.
# Usage: bash engine/setup.sh   (run from the clipwave folder)
set -e
cd "$(dirname "$0")/.."
mkdir -p models

if ! command -v espeak-ng >/dev/null; then
  echo "Building espeak-ng (phonemizer)..."
  rm -rf /tmp/espeak-ng
  git clone -q --depth 1 --branch 1.52.0 https://github.com/espeak-ng/espeak-ng.git /tmp/espeak-ng
  (cd /tmp/espeak-ng && cmake -B build -DCMAKE_BUILD_TYPE=Release -DUSE_MBROLA=OFF -DUSE_LIBSONIC=OFF \
     -DUSE_LIBPCAUDIO=OFF -DUSE_SPEECHPLAYER=OFF -DUSE_KLATT=OFF -DCMAKE_INSTALL_PREFIX=/usr/local >/dev/null \
   && cmake --build build -j8 >/dev/null && cmake --install build >/dev/null)
  ldconfig || true
fi

BASE=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
[ -s models/kokoro-v1.0.onnx ] || curl -sSL -o models/kokoro-v1.0.onnx $BASE/kokoro-v1.0.onnx
[ -s models/voices-v1.0.bin ] || curl -sSL -o models/voices-v1.0.bin $BASE/voices-v1.0.bin
if [ ! -s models/config.json ]; then
  rm -rf /tmp/kokoro-onnx
  git clone -q --depth 1 https://github.com/thewh1teagle/kokoro-onnx.git /tmp/kokoro-onnx
  cp /tmp/kokoro-onnx/src/kokoro_onnx/config.json models/
fi

python3 -c "import onnxruntime, PIL, numpy" && command -v ffmpeg >/dev/null
echo "ClipWave setup OK"
