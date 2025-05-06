# darwin.py
# Purpose: Connects to National Rail's Darwin S3 Timetable feed and lists basic info
# Requires: boto3, xml.etree.ElementTree

import boto3
from dotenv import load_dotenv
import os
import gzip
from io import BytesIO
import xml.etree.ElementTree as ET

load_dotenv()
AWS_KEY = os.getenv("DARWIN_AWS_KEY")
AWS_SECRET = os.getenv("DARWIN_AWS_SECRET")
BUCKET_NAME = os.getenv("BUCKET_NAME")
PREFIX = os.getenv("PREFIX")
REGION = os.getenv("REGION")

def list_timetable_files(s3):
    """List recent Darwin XML timetable files from S3."""
    print("🔍 Listing timetable files in S3 bucket...")
    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=PREFIX)

    files = [obj['Key'] for obj in response.get('Contents', [])]
    for f in files[-5:]:  # Show only last 5 for brevity
        print("🗂️", f)

    return files


def parse_sample_timetable(s3, key):
    print(f"📥 Downloading: {key}")
    response = s3.get_object(Bucket=BUCKET_NAME, Key=key)
    compressed = BytesIO(response['Body'].read())

    # ✅ Decompress the .gz
    with gzip.GzipFile(fileobj=compressed) as f:
        xml_data = f.read()

    # ✅ Now parse the decompressed XML
    tree = ET.parse(BytesIO(xml_data))
    root = tree.getroot()

    print("✅ XML successfully parsed!")
    first_tag = next(root.iter())
    print(f"📄 Sample Element: {first_tag.tag.split('}')[-1]}, Attributes: {first_tag.attrib}")


def get_journeys_between(s3, key, origin_crs, dest_crs):
    print(f"⚡ Searching timetable {key} for {origin_crs} → {dest_crs}...")
    response = s3.get_object(Bucket="darwin.xmltimetable", Key=key)
    compressed = BytesIO(response['Body'].read())

    with gzip.GzipFile(fileobj=compressed) as f:
        xml_data = f.read()

    root = ET.fromstring(xml_data)

    ns = {'tt': 'http://www.thalesgroup.com/rtti/XmlTimetable/v8'}
    journeys = []

    for journey in root.findall(".//tt:Journey", ns):
        found_origin = found_dest = None
        for loc in journey.findall("tt:Location", ns):
            crs = loc.attrib.get("tpl")
            if crs == origin_crs:
                found_origin = loc.find("tt:gbtt_pt", ns)
            if crs == dest_crs:
                found_dest = loc.find("tt:gbtt_pt", ns)

        if found_origin is not None and found_dest is not None:
            journeys.append({
                'train_id': journey.attrib.get('rid'),
                'origin_time': found_origin.text,
                'dest_time': found_dest.text
            })

    print(f"✅ Found {len(journeys)} journeys from {origin_crs} to {dest_crs}")
    return journeys


if __name__ == "__main__":
    # 🔐 Create S3 client
    s3 = boto3.client(
        's3',
        aws_access_key_id=AWS_KEY,  # ✅ correct
        aws_secret_access_key=AWS_SECRET,  # ✅ correct
        region_name=REGION
    )

    # 📦 List and parse latest timetable
    all_files = list_timetable_files(s3)
    if all_files:
        parse_sample_timetable(s3, all_files[-1])
