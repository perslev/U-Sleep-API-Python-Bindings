import logging
logger = logging.getLogger(__name__)
import random
from tempfile import NamedTemporaryFile


def random_hex_string(length=12):
    return "{:x}".format(random.randrange(16**length))


def temp_anonymized_edf(file_path):
    logger.info(f"Anonymizing file at {file_path}.")
    anon_file = NamedTemporaryFile(mode="w+b", suffix=file_path.suffix)
    logger.info(f"-- Temp file name: {anon_file.name}")
    with open(file_path, "rb") as in_f:
        while True:
            data = in_f.read(8096)
            if not data:
                break
            anon_file.write(data)
    anon_file.seek(8)
    logger.info("-- Anonymizing patient ID, sex, birthdate and name fields.")
    anon_file.write("X X X X_X".ljust(80).encode("ascii"))
    logger.info("-- Anonymizing start date and admin-, tech and equipment codes.")
    anon_file.write("Startdate 01-JAN-1970 X X X".ljust(80).encode("ascii"))
    anon_file.write("01.01.70".encode("ascii"))
    anon_file.write("00.00.00".encode("ascii"))
    anon_file.seek(0)
    return anon_file
