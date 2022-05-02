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

def get_set_pdf(code):
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
                    pdf_scrape(set_json[key]["icon_svg_uri"], set_json[key]["pdf"])
                return set_json[key]["pdf"]
        # This block is to update the JSON and fetch the PDF if necessary
        temp_dict, filename = scry_scrape(code) # Check scryfall for the base code
        if filename in set_json:
            set_json[filename]["codes"].append(temp_dict["codes"])
        else:
            set_json[filename] = temp_dict
            pdf_scrape(set_json[filename]["icon_svg_uri"], set_json[filename]["pdf"])
        with open(set_pdf_json, "w") as file: json.dump(set_json, file)
        return set_json[code]["pdf"]
    # Pull data from scryfall and update our JSON file
    else:
        set_json, filename = scry_scrape(code)
        pdf_scrape(set_json[filename]["icon_svg_uri"], set_json[filename]["pdf"])
        with open(set_pdf_json, "w") as file: json.dump(set_json, file)
        return set_json[filename]["pdf"]

def scry_scrape(code):
    set_json = requests.get(f"https://api.scryfall.com/sets/{code}", timeout=1).json()
    code = set_json["code"]
    icon_svg_uri = set_json["icon_svg_uri"]
    filename = os.path.splitext(os.path.basename(icon_svg_uri))[0].upper()
    pdf = os.path.join(cwd, f"{filename}.pdf")
    return { "codes": [code], "pdf": pdf, "icon_svg_uri": icon_svg_uri }, filename

def pdf_scrape(icon_svg_uri, file):
    code_svg = os.path.join(os.getcwd(), "scrysvg.svg")
    scry_svg = requests.get(icon_svg_uri, timeout=1).content
    with open(code_svg, "wb") as svg: svg.write(scry_svg)
    renderPDF.drawToFile(svg2rlg(code_svg), file)
    os.remove(code_svg)

print(get_set_pdf("CON"))