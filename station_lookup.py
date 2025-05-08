import csv

# Load once at startup
def load_station_data(csv_path='station_codes.csv'):
    data = {}
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            name = row['Description'].strip().lower()
            crs = row['CRS'].strip().upper()
            tiploc = row['Tiploc'].strip().upper()  # corrected!
            if crs and tiploc:
                data[crs] = {'tiploc': tiploc, 'name': name}
    return data

# Example usage
station_data = load_station_data()

def get_tiploc_from_crs(crs_code):
    return station_data.get(crs_code.upper(), {}).get('tiploc')

def get_name_from_crs(crs_code):
    return station_data.get(crs_code.upper(), {}).get('name')

if __name__ == '__main__':
    print(get_tiploc_from_crs('NRW'))   # Norwich
    print(get_tiploc_from_crs('LST'))   # Liverpool Street
    print(get_name_from_crs('CBG'))     # Should print 'Cambridge'
