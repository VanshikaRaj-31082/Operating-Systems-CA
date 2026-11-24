#!/usr/bin/env bash
if [ -f "$HOME/.cargo/env" ]; then
    source "$HOME/.cargo/env"
elif [ -f "/root/.cargo/env" ]; then
    source "/root/.cargo/env"
fi
export PATH="$HOME/.cargo/bin:/root/.cargo/bin:$PATH"

cd "$(dirname "${BASH_SOURCE[0]}")/.."
cargo check --target x86_64-unknown-none
