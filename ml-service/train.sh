#!/usr/bin/env bash
cd "$(dirname "$0")"
.venv/bin/python train.py --dataset dataset/genres_original
