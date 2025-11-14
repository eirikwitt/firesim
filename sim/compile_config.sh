#!/usr/bin/env bash

timestamp() {
  # Run the command passed as arguments
  # Redirect stderr to stdout so both are processed
  local status=0
  while IFS= read -r line; do
    printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$line"
  done < <("$@" 2>&1 || status=$?)
  return $status
}

config="$1"

mkdir -p logs/build_$config
{
  echo "========== Compiling $config config =========="
  timestamp env BUILD_VORTEX=1 USE_SOFTWARE_SIMULATOR=0 USE_FPNEW=1 make driver PLATFORM=alveo ALVEO_PLATFORM=u250 PLATFORM_CONFIG=BaseF1Config1Mem_F25MHz TARGET_CONFIG=FireSim"$config" JAVA_HEAP_SIZE=128G
} 2>&1 | tee -a "logs/build_$config/compile_$(date +%s).log"


