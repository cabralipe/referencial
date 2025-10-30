#!/usr/bin/env bash
set -o errexit
set -o pipefail
set -o nounset

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Build frontend bundle so Django can serve static files
npm install --prefix frontend
npm run build --prefix frontend
