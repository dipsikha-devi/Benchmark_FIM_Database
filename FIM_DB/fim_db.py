import boto3
import botocore
import os
import tempfile
from pathlib import Path
import geopandas as gpd
import tempfile

# Initialize an anonymous S3 client
s3 = boto3.client(
    's3',
    config=botocore.config.Config(signature_version=botocore.UNSIGNED)
)

bucket_name = 'sdmlab'
pwb_folder = "FIM_Database/"


#GET ALL AOIS IN EACH LEVEL FROM BUCKET
def AOIs_inS3(s3_client, bucket, prefix="FIM_Database/Levelwise_AOIs/"):
    """
    Download all .geojson files from the given S3 prefix into a temporary directory.

    Returns:
        tmp_dir (str): Path to the temporary directory with downloaded files.
        geojson_files (list): List of full paths to downloaded .geojson files.
    """
    

    tmp_dir = tempfile.mkdtemp(prefix="FIM_AOIs_")

    # List all objects
    response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
    if 'Contents' not in response:
        raise ValueError(f"No files found in s3://{bucket}/{prefix}")

    geojson_files = []

    for obj in response['Contents']:
        file_key = obj['Key']
        file_name = os.path.basename(file_key)

        if file_name.endswith('.geojson'):
            local_path = os.path.join(tmp_dir, file_name)
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            s3_client.download_file(bucket, file_key, local_path)
            geojson_files.append(local_path)

    if not geojson_files:
        raise ValueError("No .geojson files found after download.")

    return tmp_dir, geojson_files

#GET THE BENCHMARK FIM FOR USER DEFINED EVENT AND BOUNDARY
def get_benchmark_FIM(filename, level, candidate_raster, downloadFIM=True):
    parts = filename.split("_")
    folder_name = "_".join(parts[2:-1])
    s3_key = f"FIM_Database/{level}/{folder_name}/{filename}"
    local_folder = Path(candidate_raster)
    local_folder.mkdir(parents=True, exist_ok=True)
    local_file_path = local_folder / filename

    if downloadFIM:
        s3 = boto3.client(
            's3',
            config=botocore.config.Config(signature_version=botocore.UNSIGNED)
        )
        bucket = 'sdmlab'
        try:
            s3.download_file(bucket, s3_key, str(local_file_path))
            print(f"Downloaded benchmark floodmap: {filename} to {local_folder}")
        except botocore.exceptions.ClientError as e:
            raise FileNotFoundError(f"Could not find {s3_key} in bucket {bucket}") from e
    else:
        print(f"Skipping download; just using BM for evaluation")
    return local_folder