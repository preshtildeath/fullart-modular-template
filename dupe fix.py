import time
start = time.process_time_ns()
import os
import json
import requests
from os import path
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF

def parent_dirs(file, depth=1):
    for d in range(depth): file = os.path.dirname(file)
    return file

cwd = os.path.join(parent_dirs(__file__, 4), "SetPDF")

# if path.exists(path.join(cwd, "sets.json")): set_json = json.load("sets.json")
# else: 
def scry_scrape ():
    set_dict = {}
    allsets = requests.get("https://api.scryfall.com/sets", timeout=1).json()
    for sets in allsets["data"]:
        setcode = sets["code"].upper()
        icon_svg_uri = sets["icon_svg_uri"]
        filename = path.splitext(path.basename(icon_svg_uri))[0].upper()
        if filename == "CON": filename = "CONFLUX"
        if filename in set_dict: set_dict[filename].append(setcode)
        else: set_dict[filename] = [setcode]
        # if filename in set_dict:
        #     set_dict[filename].append(setcode)
        # else:
        #     pdf_file = path.join(cwd, f'{filename}.pdf')
        #     if not path.exists(pdf_file):
        #         svg_file = path.join(cwd, f'{filename}.svg')
        #         scry_svg = requests.get(icon_svg_uri, timeout=1).content
        #         with open(svg_file, "wb") as svg: svg.write(scry_svg)
        #         renderPDF.drawToFile(svg2rlg(svg_file), pdf_file)
        #         os.remove(svg_file)
        #     set_dict[filename] = [setcode]
    return set_dict

def json_write(filename, dict):
    try:
        with open(filename, "w") as file:
            json.dump(dict, file)
        return "Success"
    except Exception as e: return e

def json_read(filename):
    with open(filename, "r") as file:
        dict = json.load(file)
    return dict

json_file = path.join(cwd, "set_pdf.json")
json_dict = scry_scrape()
json_write(json_file, json_dict)
final = time.process_time_ns() - start
print(final/(10 ** 9))