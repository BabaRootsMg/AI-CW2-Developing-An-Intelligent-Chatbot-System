import boto3
import xml.etree.ElementTree as ET
from io import BytesIO
import gzip
from collections import defaultdict
from station_lookup import get_tiploc_from_crs, get_name_from_crs
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Get values from the environment
AWS_ACCESS_KEY = os.getenv("DARWIN_AWS_KEY")
AWS_SECRET_KEY = os.getenv("DARWIN_AWS_SECRET")
REGION = os.getenv("REGION")
BUCKET_NAME = os.getenv("BUCKET_NAME")
PREFIX = os.getenv("PREFIX")
NS = {'tt': 'http://www.thalesgroup.com/rtti/XmlTimetable/v8'}

def list_available_file_versions():
    """List the latest version of each available XML.gz timetable by date."""
    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=REGION
    )
    s3 = session.resource('s3')
    bucket = s3.Bucket(BUCKET_NAME)

    versions = defaultdict(list)

    for obj in bucket.objects.filter(Prefix=PREFIX):
        key = obj.key
        if key.endswith('.xml.gz') and '_v' in key and 'ref' not in key:
            filename = key.split('/')[-1]
            date_part = filename.split('_')[0]
            version = int(filename.split('_v')[-1].split('.')[0])
            versions[date_part].append((version, key))

    latest_per_date = {}
    for date, items in versions.items():
        best = max(items)  # get highest version number
        latest_per_date[date] = best[1]

    return latest_per_date

def parse_journey_file(file_key, origin_crs='NRW', dest_crs='LST', latest_dep_time='10:00'):
    """Parse a Darwin XML timetable file and find valid journeys."""
    origin_tiploc = get_tiploc_from_crs(origin_crs)
    dest_tiploc = get_tiploc_from_crs(dest_crs)

    if not origin_tiploc or not dest_tiploc:
        print(f" Could not find TIPLOCs for {origin_crs} or {dest_crs}")
        return

    print(f"\n Searching from {origin_crs} ({origin_tiploc}) to {dest_crs} ({dest_tiploc}) before {latest_dep_time}")

    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=REGION
    )
    s3 = session.client('s3')
    obj = s3.get_object(Bucket=BUCKET_NAME, Key=file_key)
    xml_data = gzip.decompress(obj['Body'].read())

    tree = ET.parse(BytesIO(xml_data))
    root = tree.getroot()
    journeys = root.findall('tt:Journey', NS)

    print(f" Total journeys in file: {len(journeys)}")

    matched = 0
    origin_found = 0

    for journey in journeys:
        stops = []
        for tag in ['OR', 'IP', 'PP', 'DT']:
            for loc in journey.findall(f'tt:{tag}', NS):
                crs = loc.attrib.get('tpl')
                dep = loc.attrib.get('ptd')
                stops.append({'crs': crs, 'dep': dep})

        crs_list = [s['crs'] for s in stops]

        if origin_tiploc in crs_list:
            origin_found += 1
            o_idx = crs_list.index(origin_tiploc)
            d_idx = crs_list.index(dest_tiploc) if dest_tiploc in crs_list else -1
            departure_time = stops[o_idx]['dep']

            if d_idx > o_idx and departure_time and departure_time < latest_dep_time:
                matched += 1
                print(f"\n MATCHED Journey:")
                print(f"- Departure from {origin_crs} at {departure_time}")
                print(f"- Route TIPLOCs: {crs_list}")

    print(f"\n Journeys that include {origin_crs}: {origin_found}")
    print(f" Matched journeys ({origin_crs} → {dest_crs} before {latest_dep_time}): {matched}")

if __name__ == "__main__":
    print("\n Fetching available Darwin timetable files...")
    files_by_date = list_available_file_versions()

    if not files_by_date:
        print("️ No valid files found.")
    else:
        latest_date = sorted(files_by_date.keys())[-1]
        best_file = files_by_date[latest_date]

        print(f"\n Latest available date: {latest_date}")
        print(f" Using file: {best_file}")

        # Try any CRS station pair
        parse_journey_file(best_file, origin_crs='NRW', dest_crs='LST', latest_dep_time='10:00')
