#!/bin/bash
# Wrapper script to run npx without -y flag
# Cursor IDE automatically adds -y, so we intercept and remove it

# Remove -y from arguments if present
ARGS=()
for arg in "$@"; do
    if [ "$arg" != "-y" ]; then
        ARGS+=("$arg")
    fi
done

# Run npx with cleaned arguments
exec /usr/local/bin/npx "${ARGS[@]}"
