import argparse
import shutil
import os
from pathlib import Path


def main():
    # Defining arguments for very sophisticated program 
    parser = argparse.ArgumentParser(description="Create a zip folder with all datasets for each country")
    parser.add_argument('-a', '--archivename', required=True, 
                        help="Name of the final archive (e.g., 'country_data_archive', DO NOT include the extension).")
    
    parser.add_argument('-f', '--format', default='zip', 
                        help="Archive format (e.g., 'zip', 'tar', 'gztar'). Defaults to 'zip'.")
    
    parser.add_argument('-r', '--rootdir', required=True, 
                        help='The directory containing the folder to be archived.')
    
    parser.add_argument('-b', '--basedir', required=True, 
                        help='The specific folder within the rootdir whose contents will be archived.')
    
    parser.add_argument('-o', '--outputdir', required=True, 
                        help='Output directory where the final archive will be placed.')
    args = parser.parse_args()
    # Making sure outputdir exists
    os.makedirs(args.outputdir, exist_ok=True)

    output_base_path = os.path.join(args.outputdir, args.archivename)


    archive_path = shutil.make_archive(
            base_name=output_base_path,
            format=args.format,
            root_dir=args.rootdir,
            base_dir=args.basedir
        )

    print(f"Successfully created: {archive_path}")

if __name__ == '__main__':
    main()