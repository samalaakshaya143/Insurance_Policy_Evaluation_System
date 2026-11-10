"""Run the insurance policy evaluation data generator."""

import argparse
import json

from generate_data import build


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scale",
        type=int,
        default=3000,
        help="number of synthetic applicants (minimum 8)",
    )
    parser.add_argument("--seed", type=int, default=20261022)
    parser.add_argument("--out", default="data/generated")
    args = parser.parse_args()

    if args.scale < 8:
        parser.error("--scale must be at least 8 for required exception scenarios")

    result = build(args.scale, args.seed, args.out)
    print(json.dumps(result, indent=2))

    if result["validation"]["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()