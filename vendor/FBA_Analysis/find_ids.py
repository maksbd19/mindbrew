#!/usr/bin/env python3
"""Offline find_ids stub — use real find_ids.py from FBA_Analysis submodule."""

import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("model_ref")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    data = {
        "model_ref": args.model_ref,
        "recommended": {
            "carbon_source_rxn": "EX_ole_e",
            "product_metabolite": "wax_ester_c",
        },
        "gene_alias_resolution": {
            "recommended_knockouts": ["ACOAO8p", "ACOAO4p", "POX1"],
            "ACOAO8p": ["ACOAO8p"],
            "POX1": ["POX1"],
        },
        "feedstock_options": {
            "oleate": "EX_ole_e",
            "linoleate": "EX_lnl_e",
            "plant_oil": "EX_ole_e",
        },
    }
    if args.json:
        print(json.dumps(data))
    else:
        print(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
