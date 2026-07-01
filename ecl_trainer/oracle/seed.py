from __future__ import annotations

import argparse

from ecl_trainer.oracle.atlas import build_option_b_atlas


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the local Option B Intelligent Context Atlas")
    parser.add_argument("path")
    args = parser.parse_args()
    build_option_b_atlas(args.path)


if __name__ == "__main__":
    main()
