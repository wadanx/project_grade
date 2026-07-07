from parser import parse_wb
import pandas as pd
import regulations as rg


import argparse
import os
import sys


def main(in_file: str, out_file: str, reg_file: str):
    # Check input Excel file exists
    if not os.path.isfile(in_file):
        print(f"Error: input file not found: {in_file}", file=sys.stderr)
        sys.exit(1)

    # Check registry/config JSON file exists
    if not os.path.isfile(reg_file):
        print(f"Error: registry file not found: {reg_file}", file=sys.stderr)
        sys.exit(1)

    # Optional: warn if output file already exists (won't block execution)
    if os.path.isfile(out_file):
        print(f"Warning: output file already exists and will be overwritten: {out_file}")

    # ... rest of your processing logic goes here ...
    reg = rg.Regulation.load(reg_file)
    parsed_data = parse_wb(in_file, reg)
    pd.DataFrame(parsed_data).to_excel(f'{out_file}.xlsx', index=False, header=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process an Excel file using a JSON registry.")
    parser.add_argument("-i", "--input", dest="in_file", required=True, help="Path to the input Excel file")
    parser.add_argument("-o", "--output", dest="out_file", required=False, help="Path to the output file")
    parser.add_argument("-r", "--registry", dest="reg_file", required=True, help="Path to the JSON registry file")

    args = parser.parse_args()

    main(args.in_file, args.out_file if args.out_file  else "out", args.reg_file)

    

    
    
    
    
    