from avro.io import DatumReader, DatumWriter
from avro.datafile import DataFileReader, DataFileWriter
import json

FILENAME = '<path_to_file>'

reader = DataFileReader(open(FILENAME, 'rb'), DatumReader())

for reading in reader:
    for event in reading['Body'].split():
        print(json.loads(event))
