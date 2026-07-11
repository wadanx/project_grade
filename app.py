from parser import parse_wb
import pandas as pd
import regulations as rg


import argparse
import os
import sys



def main(in_file: str, out_folder: str):
    # Check input Excel file exists
    if not os.path.isfile(in_file):
        print(f"Error: input file not found: {in_file}", file=sys.stderr)
        sys.exit(1)

    if(out_folder == None):
        out_folder = 'Intermediate'
    
    if not os.path.exists(out_folder):
        os.mkdir(out_folder)

    parse_wb(in_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process an Excel file using a JSON registry.")
    parser.add_argument("-i", "--input", dest="in_file", required=True, help="Path to the input Excel file")
    parser.add_argument("-o", "--output", dest="out_folder", required=False, help="Path to the output file")

    args = parser.parse_args()

    main(args.in_file, args.out_folder)

    

    
    
    
    
    