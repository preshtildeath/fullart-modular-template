import time
from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg
import os
import json
import requests

# loop up through parent directories
def parent_dirs(file, depth=1):
    for d in range(depth): file = os.path.dirname(file)
    return file

cwd = parent_dirs(__file__, 4)

def get_set_pdf1(code):
    # Fix conflux
    if code.upper() == "CON": code = "CONFLUX"
    else: code = code.upper()
    # Make sure the Set PDF folder exists
    pdf_folder = os.path.join(cwd, "SetPDF")
    try: os.mkdir(pdf_folder)
    except: pass
    # Open up our JSON file if it exists
    set_pdf_json = os.path.join(pdf_folder, "set_pdf.json")
    with open(set_pdf_json, "r") as file:
        set_json = json.load(file)
    print(set_json["UNF"]["codes"])
    # Skip if empty
    if os.path.getsize(set_pdf_json) > 32:
        # This block is if the JSON file points to an accurate PDF (or fixes that)
        for key in set_json:
            if code in set_json[key]["codes"]:
                if not os.path.exists(set_json[key]["pdf"]): # Found the code, but the pdf file is missing
                    pdf_scrape1(set_json[key]["icon_svg_uri"], set_json[key]["pdf"])
                return set_json[key]["pdf"]
        # This block is to update the JSON and fetch the PDF if necessary
        temp_dict, filename = scry_scrape1(code) # Check scryfall for the base code
        if filename in set_json:
            set_json[filename]["codes"].append(temp_dict["codes"])
        else:
            set_json[filename] = temp_dict
            pdf_scrape1(set_json[filename]["icon_svg_uri"], set_json[filename]["pdf"])
        with open(set_pdf_json, "w") as file: json.dump(set_json, file)
        return set_json[code]["pdf"]
    # Pull data from scryfall and update our JSON file
    else:
        set_json, filename = scry_scrape1(code)
        pdf_scrape1(set_json[filename]["icon_svg_uri"], set_json[filename]["pdf"])
        with open(set_pdf_json, "w") as file: json.dump(set_json, file)
        return set_json[filename]["pdf"]

def scry_scrape1(code):
    set_json = requests.get(f"https://api.scryfall.com/sets/{code}", timeout=1).json()
    code = set_json["code"]
    icon_svg_uri = set_json["icon_svg_uri"]
    filename = os.path.splitext(os.path.basename(icon_svg_uri))[0].upper()
    pdf = os.path.join(cwd, f"{filename}.pdf")
    return { "codes": [code], "pdf": pdf, "icon_svg_uri": icon_svg_uri }, filename

def pdf_scrape1(icon_svg_uri, file):
    code_svg = os.path.join(os.getcwd(), "scrysvg.svg")
    scry_svg = requests.get(icon_svg_uri, timeout=1).content
    with open(code_svg, "wb") as svg: svg.write(scry_svg)
    renderPDF.drawToFile(svg2rlg(code_svg), file)
    os.remove(code_svg)

def get_set_pdf0(code):
    code = code.upper()
    pdf_folder = os.path.join(cwd, "SetPDF")
    try: os.mkdir(pdf_folder) # Make sure the Set PDF folder exists
    except: pass
    set_pdf_json = os.path.join(pdf_folder, "set_pdf.json")
    if os.path.getsize(set_pdf_json) > 32: # Open up our JSON file if it exists
        with open(set_pdf_json, "r") as file: set_json = json.load(file)
    if code not in set_json: set_json[code] = scry_scrape0(code) # Add to dict if needed
    pdf = os.path.join(pdf_folder, f"{set_json[code]}.pdf")
    if not os.path.exists(pdf): pdf_scrape0(pdf) # Fetch SVG and convert to PDF if needed
    with open(set_pdf_json, "w") as file: json.dump(set_json, file)
    return pdf

def scry_scrape0(code):
    set_json = requests.get(f"https://api.scryfall.com/sets/{code}", timeout=1).json()
    icon_svg_uri = set_json["icon_svg_uri"]
    filename = os.path.basename(icon_svg_uri)
    key = os.path.splitext(filename)[0].upper()
    if key == "CON": return "CONFLUX"
    else: return key

def pdf_scrape0(file):
    code = os.path.splitext(os.path.basename(file))[0].lower()
    temp_svg = os.path.join(os.getcwd(), "temp_svg.svg")
    scry_svg = requests.get(f"https://c2.scryfall.com/file/scryfall-symbols/sets/{code}.svg", timeout=1).content
    with open(temp_svg, "wb") as svg: svg.write(scry_svg)
    renderPDF.drawToFile(svg2rlg(temp_svg), file)
    os.remove(temp_svg)

def get_set_pdf2(code):
    key = code = code.upper()
    pdf_folder = os.path.join(cwd, "SetPDF")
    try: os.mkdir(pdf_folder) # Make sure the Set PDF folder exists
    except: pass
    set_pdf_json = os.path.join(pdf_folder, "set_pdf.json")
    if os.path.getsize(set_pdf_json) > 32: # Open up our JSON file if it exists
        with open(set_pdf_json, "r") as file: set_json = json.load(file)
    for set in set_json: # Iterate JSON looking for a match
        if code in set_json[set]:
            key = set
            break
    if key not in set_json: # No match, gotta fetch
        key = scry_scrape2(code)
        if key in set_json: set_json[key].append(code) # Append list
        else: set_json[key] = [code] # Create list
    pdf = os.path.join(pdf_folder, f"{key}.pdf")
    if not os.path.exists(pdf): pdf_scrape2(pdf) # Fetch SVG and convert to PDF if needed
    with open(set_pdf_json, "w") as file: json.dump(set_json, file)
    return pdf

def scry_scrape2(code):
    set_json = requests.get(f"https://api.scryfall.com/sets/{code}", timeout=1).json()
    icon_svg_uri = set_json["icon_svg_uri"]
    filename = os.path.basename(icon_svg_uri)
    name = os.path.splitext(filename)[0].upper()
    if name == "CON": return "CONFLUX"
    return name

def pdf_scrape2(file):
    code = os.path.splitext(os.path.basename(file))[0].lower()
    temp_svg = os.path.join(os.getcwd(), "temp_svg.svg")
    scry_svg = requests.get(f"https://c2.scryfall.com/file/scryfall-symbols/sets/{code}.svg", timeout=1).content
    with open(temp_svg, "wb") as svg: svg.write(scry_svg)
    renderPDF.drawToFile(svg2rlg(temp_svg), file)
    os.remove(temp_svg)

def sort_by_values_len(dict):
    dict_len= {key: len(value) for key, value in dict.items()}
    import operator
    sorted_key_list = sorted(dict_len.items(), key=operator.itemgetter(1), reverse=True)
    sorted_dict = [{item[0]: dict[item [0]]} for item in sorted_key_list]
    return sorted_dict[0]

start = time.process_time_ns()

pdf_folder = os.path.join(cwd, "SetPDF")
set_pdf_json = os.path.join(pdf_folder, "set_pdf.json")
with open(set_pdf_json, "r") as file: set_json = json.load(file)
count = 0
for set in set_json: count += len(set_json[set])
print(len(set_json))
print(count)

final = time.process_time_ns() - start
print (f"{final/(10**9)} seconds passed.")