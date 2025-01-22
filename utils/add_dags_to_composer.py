import argparse
import glob
import os
from pathlib import Path
import tempfile
from typing import List, Tuple
from google.cloud import storage
import shutil

def _create_dags_list(dags_directory: str) -> Tuple[str, List[str]]:
    temp_dir = tempfile.mkdtemp()
    ignored = ["__init__.py", "*_test.py"]
    
    # Use pathlib for better path handling
    src_path = Path(dags_directory)
    dst_path = Path(temp_dir)
    
    # Copy files excluding ignored patterns
    for item in src_path.glob('**/*'):
        if item.is_file() and not any(item.match(pat) for pat in ignored):
            relative_path = item.relative_to(src_path)
            dst_file = dst_path / relative_path
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dst_file)

    # Get all Python files
    dags = [str(f) for f in dst_path.glob('**/*.py')]
    return (str(temp_dir), dags)

def upload_dags_to_composer(dags_directory: str, bucket_name: str, name_replacement: str = "dags/") -> None:
    """
    Uploads DAG files to a Cloud Composer environment's bucket.
    
    Args:
        dags_directory: Path to directory containing DAGs
        bucket_name: GCS bucket name without gs:// prefix
        name_replacement: Target directory in bucket (default: "dags/")
    """
    temp_dir, dags = _create_dags_list(dags_directory)
    
    if not dags:
        print("No DAGs found to upload.")
        return

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    
    for dag_path in dags:
        try:
            # Convert to relative path and construct destination
            rel_path = os.path.relpath(dag_path, temp_dir)
            dest_path = os.path.join(name_replacement, rel_path)
            
            # Upload file
            blob = bucket.blob(dest_path)
            blob.upload_from_filename(dag_path)
            print(f"Uploaded: {dest_path}")
            
        except Exception as e:
            print(f"Error uploading {dag_path}: {str(e)}")

    # Cleanup
    shutil.rmtree(temp_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload DAGs to Cloud Composer")
    parser.add_argument("--dags_directory", required=True, 
                       help="Path to source DAGs directory")
    parser.add_argument("--dags_bucket", required=True,
                       help="Composer DAGs bucket name (without gs:// prefix)")
    
    args = parser.parse_args()
    upload_dags_to_composer(args.dags_directory, args.dags_bucket)