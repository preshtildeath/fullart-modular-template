"""
PRESHTILDEATH TOOLS
"""
import os
import re
import json
import math
import requests
import photoshop.api as ps
import proxyshop.helpers as psd
app = ps.Application()

# loop up through parent directories
def parent_dirs(file, depth=1):
    if depth >= 1:
        return os.path.dirname(parent_dirs(file, depth-1))
    return file

cwd = parent_dirs(__file__, 4)
plugin_dir = parent_dirs(__file__)

def rgbcolor(r, g, b):
    color = ps.SolidColor()
    color.rgb.red = r
    color.rgb.green = g
    color.rgb.blue = b
    return color

# Grab the pdf file from our database
def get_set_pdf(code):
    code, key = code.upper(), "" # Init values
    pdf_folder = os.path.join(plugin_dir, "assets", "Set Symbol PDF")
    if not os.path.exists(pdf_folder): os.mkdir(pdf_folder) # Make sure the Set PDF folder exists
    set_pdf_json = os.path.join(pdf_folder, "set_pdf.json")
    print(str(set_pdf_json))
    if os.path.getsize(set_pdf_json) > 32: # Open up our JSON file if it exists
        with open(set_pdf_json, "r") as file: set_json = json.load(file)
    else: set_json = {}
    for set in set_json: # Iterate JSON looking for a match
        if code in set_json[set]:
            key = set
            break
    if key == "": # No match, gotta fetch
        key = scry_scrape(code)
        if key in set_json: set_json[key].append(code) # Append list
        else: set_json[key] = [code] # Create list
    pdf = os.path.join(pdf_folder, f"{key}.pdf")
    if not os.path.exists(pdf): pdf_fetch(pdf_folder, key) # Fetch SVG and convert to PDF if needed
    clean_json = json.dumps(set_json).replace("{", "{\n\t").replace("], ", "],\n\t").replace("]}", "]\n}")
    with open(set_pdf_json, "w") as file: file.write(clean_json)
    return pdf

# Take a set code and return the corresponding image name
def scry_scrape(code):
    set_json = requests.get(f"https://api.scryfall.com/sets/{code}", timeout=1).json()
    name = os.path.splitext(os.path.basename(set_json["icon_svg_uri"]))[0].upper() # Grab the SVG name
    if name == "CON": return "CONFLUX" # Turns out you can't make a file named CON
    return name

# Take the image name and download from scryfall, then convert to pdf
def pdf_fetch(folder, code):
    from reportlab.graphics import renderPDF
    from svglib.svglib import svg2rlg
    code = code.lower()
    file = os.path.join(folder, f"{code}.pdf")
    temp_svg = os.path.join(os.getcwd(), "temp_svg.svg")
    scry_svg = requests.get(f"https://c2.scryfall.com/file/scryfall-symbols/sets/{code}.svg", timeout=1).content
    with open(temp_svg, "wb") as svg: svg.write(scry_svg)
    renderPDF.drawToFile(svg2rlg(temp_svg), file)
    os.remove(temp_svg)

# Pastes the given PDF into the specified layer.
def get_expansion(layer, rarity, ref_layer, offset_layer, set_pdf):

    # Start nice and clean
    white = rgbcolor(255,255,255)
    prev_active_layer = app.activeDocument.activeLayer
    app.activeDocument.activeLayer = layer

    # open pdf twice as big as reference just in case
    max_size = (ref_layer.bounds[2] - ref_layer.bounds[0]) * 2
    pdf_open(set_pdf, max_size)

    # note context switch to art file
    app.activeDocument.selection.selectAll()
    app.activeDocument.selection.copy()
    app.activeDocument.close(ps.SaveOptions.DoNotSaveChanges)

    # note context switch back to template
    app.activeDocument.paste()
    zero_transform(layer)

    # move and resize symbol to appropriate place
    frame_expansion_symbol(layer, ref_layer)
    fill_expansion_symbol(layer, white)

    # apply rarity mask if necessary, and center it on symbol
    if rarity != "common":
        mask_layer = psd.getLayer(rarity, layer.parent)
        psd.select_layer_pixels(layer)
        app.activeDocument.activeLayer = mask_layer
        psd.align_horizontal()
        psd.align_vertical()
        psd.clear_selection()
        mask_layer.visible = True

    # return document to previous state
    app.activeDocument.activeLayer = prev_active_layer
    return layer

# Resize layer to reference, center vertically, and line it up with the right bound
def frame_expansion_symbol(layer, reference_layer):

    lay_dim = psd.compute_layer_dimensions(layer)
    ref_dim = psd.compute_layer_dimensions(reference_layer)

    # Determine how much to scale the layer by such that it fits into the reference layer's bounds
    scale_factor = 100 * min(
        ref_dim['width'] / lay_dim['width'],
        ref_dim['height'] / lay_dim['height']
    )
    layer.resize(scale_factor, scale_factor)

    # Align verticle center, horizontal right
    psd.select_layer_pixels(reference_layer)
    app.activeDocument.activeLayer = layer
    psd.align_vertical()
    layer.translate(reference_layer.bounds[2]-layer.bounds[2],0)
    app.activeDocument.selection.deselect()

# Give the symbol a background for open space symbols (i.e. M10)
def fill_expansion_symbol(ref, stroke_color):

    # Magic Wand non-contiguous outstrIDe symbol, then subtract contiguous
    x, y = ref.bounds[0]-50, ref.bounds[1]-50
    magic_wand_select(ref, x, y, 'new', 0, True, False)
    magic_wand_select(ref, x, y, 'sub', 0, True)

    # Make a new layer and fill with stroke color
    layer = add_layer("Expansion Mask")
    layer.blendMode = ps.BlendMode.NormalBlend
    layer.visible = True
    layer.moveAfter(ref)
    app.activeDocument.selection.fill(stroke_color)
    app.activeDocument.selection.deselect()

    # Maximum filter to keep the antialiasing normal
    layer.applyMaximum(1)

# Check if a file already exists, then adds (x) if it does
def filename_append(file, send_path):
    file_name, extension = os.path.splitext(os.path.basename(file)) # image, .xxx
    test_name = os.path.join(send_path, f'{file_name}{extension}')
    if os.path.exists(test_name): # location/image.xxx
        multi = 1
        test_name = os.path.join(send_path, f'{file_name} ({multi}){extension}')
        while os.path.exists(test_name): # location/image (1).xxx
            multi += 1
            test_name = os.path.join(send_path, f'{file_name} ({multi}){extension}')
    return test_name #  returns "location/image.xxx" or "location/image (x).xxx"

# Gives an estimated number of lines at default text size
def dirty_text_scale (input_text, chars_in_line):
    input_text = re.sub('\{.*?\}', 'X', input_text)
    line_count = math.ceil(input_text.count('\n') * 0.5)
    lines = input_text.split('\n')
    for line in lines:
        line_count += math.ceil(len(line) / chars_in_line)
    return line_count

# Stretches a layer by (-modifier) pixels
def layer_vert_stretch(layer, modifier, anchor='bottom', method="nearestNeighbor"):
    transform_delta = { 'top': 0, 'center': modifier/2, 'bottom': modifier }
    # anchor_set = { 'top': 1, 'center': 4, 'bottom': 7 }
    height = layer.bounds[3] - layer.bounds[1]
    h_perc = (height - modifier) / height * 100
    zero_transform(layer, method, 0, transform_delta[anchor], 100, h_perc)
    # layer.resize(100, h_perc, anchor_set[anchor])

# Rearranges two color layers in order and applies mask
def wubrg_layer_sort (color_pair, layers):
    top = psd.getLayer(color_pair[0], layers)
    bottom = psd.getLayer(color_pair[1], layers)
    top.moveBefore(bottom)
    app.activeDocument.activeLayer = top
    psd.enable_active_layer_mask()
    top.visible = True
    bottom.visible = True

# Select a layer's pixels and adds them to the selection
def add_select_layer (layer):
    """
     * Select the bounding box of a given layer.
    """
    left, top, right, bottom = layer.bounds

    app.activeDocument.selection.select([
        [left, top],
        [right, top],
        [right, bottom],
        [left, bottom]
    ], ps.SelectionType.ExtendSelection)

# Get width and height of paragraph text box
def get_text_bounding_box(layer, text_width=None, text_height=None):
    if app.preferences.pointSize == 1: pref_scale = 72
    else: pref_scale = 72.27
    doc_res = app.activeDocument.resolution
    multiplier = (doc_res / pref_scale) ** 2
    if text_width is not None: layer.textItem.width = text_width * multiplier
    else: text_width = layer.textItem.width * multiplier
    if text_height is not None: layer.textItem.height = text_height * multiplier
    else: text_height = layer.textItem.height * multiplier
    return [text_width, text_height]



"""
HERE LIES ALL THE COMPLICATED BULLSHIT THAT MAKES LITTLE SENSE
"""

# define these because otherwise they take up so many characters
def chaID (char): return app.charIDToTypeID(char)

def strID (string): return app.stringIDToTypeID(string)

# Selects the layer mask for editing
def layer_mask_select (layer):
    app.activeDocument.activeLayer = layer
    desc_mask = ps.ActionDescriptor()
    ref_mask = ps.ActionReference()
    chnl = chaID("Chnl")
    ref_mask.putEnumerated(chnl, chnl, chaID("Msk "))
    desc_mask.putReference(chaID("null"), ref_mask)
    desc_mask.putBoolean(chaID("MkVs"), True)
    app.executeAction(chaID("slct"), desc_mask, 3)
    return

# Magic Wand target layer at coordinate (X, Y)
def magic_wand_select (layer, x, y, style='new', t=0, a=True, c=True, s=False):
    select_key = {'new': 'setd', 'add': 'AddT', 'sub': 'SbtF', 'cross': 'IntW'}
    old_layer = app.activeDocument.activeLayer
    app.activeDocument.activeLayer = layer
    coords = ps.ActionDescriptor()
    coords.putUnitDouble(chaID("Hrzn"), chaID("#Pxl"), x)
    coords.putUnitDouble(chaID("Vrtc"), chaID("#Pxl"), y)
    click = ps.ActionDescriptor()
    ref = ps.ActionReference()
    ref.putProperty(chaID("Chnl"), chaID("fsel"))
    click.putReference(chaID("null"), ref)
    click.putObject(chaID("T   "), chaID("Pnt "), coords)
    click.putInteger(chaID("Tlrn"), t) # Tolerance
    click.putBoolean(chaID("AntA"), a) # Anti-aliasing
    click.putBoolean(chaID("Cntg"), c) # Contiguous
    click.putBoolean(chaID("Mrgd"), s) # Sample all layers
    app.executeAction(chaID(select_key[style]), click, 3)
    app.activeDocument.activeLayer = old_layer

def get_layer_index (layerID):
    ref = ps.ActionReference()
    ref.putIdentifier(chaID("Lyr "), layerID)
    try:
        app.activeDocument.backgroundLayer
        return app.executeActionGet(ref).getInteger(chaID("ItmI"))-1
    except: return app.executeActionGet(ref).getInteger(chaID("ItmI"))

def move_inside (fromlayer, layerset):
    fromID = int(fromlayer.id)
    toID = int(layerset.id)
    desc = ps.ActionDescriptor()
    ref1 = ps.ActionReference()
    ref2 = ps.ActionReference()
    ref1.putIdentifier(chaID("Lyr "), fromID)
    desc.putReference(chaID("null"), ref1)
    ref2.putIndex(chaID("Lyr "), get_layer_index(toID))
    desc.putReference(chaID("T   "), ref2)
    desc.putBoolean(chaID('Adjs'), False)
    desc.putInteger(chaID('Vrsn'), 5)
    try:
        app.executeAction(chaID("move"), desc, 3)
    except Exception as err:
        return err

def add_layer (name=None):
    layer = app.activeDocument.activeLayer
    desc = ps.ActionDescriptor()
    ref = ps.ActionReference()
    ref.putClass(chaID("Lyr "))
    desc.putReference(chaID("null"), ref)
    desc.putInteger(chaID("LyrI"), get_layer_index(layer.id))
    app.executeAction(chaID("Mk  "), desc, 3)
    layer = app.activeDocument.activeLayer
    if name is not None: layer.name = name
    return layer

# equivalent of ctrl+shift+v
def paste_in_place():
    paste = ps.ActionDescriptor()
    paste.putBoolean(strID("inPlace"), True)
    paste.putEnumerated(
        chaID("AntA"),
        chaID("Antt"),
        chaID("Anto")
       )
    app.executeAction(chaID("past"), paste, 3)

# opens a pdf at a fixed max width/height
def pdf_open(file, size):
    """
     * Opens a pdf scaled to (height) pixels tall
    """
    open_desc = ps.ActionDescriptor()
    sett_desc = ps.ActionDescriptor()
    pxl = chaID("#Pxl")
    sett_desc.putString(chaID("Nm  "), "pdf")
    sett_desc.putEnumerated(chaID("Crop"), strID("cropTo"), strID("boundingBox"))
    sett_desc.putUnitDouble(chaID("Rslt"), chaID("#Rsl"), 800.000000)
    sett_desc.putEnumerated(chaID("Md  "), chaID("ClrS"), chaID("RGBC"))
    sett_desc.putInteger(chaID("Dpth"), 8)
    sett_desc.putBoolean(chaID("AntA"), True)
    sett_desc.putUnitDouble(chaID("Wdth"), pxl, size)
    sett_desc.putUnitDouble(chaID("Hght"), pxl, size)
    sett_desc.putBoolean(chaID("CnsP"), True)
    sett_desc.putBoolean(strID("suppressWarnings"), True)
    sett_desc.putBoolean(chaID("Rvrs"), True)
    sett_desc.putEnumerated(chaID("fsel"), strID("pdfSelection"), strID("page"))
    sett_desc.putInteger(chaID("PgNm"), 1)
    open_desc.putObject(chaID("As  "), chaID("PDFG"), sett_desc)
    open_desc.putPath(chaID("null"), file)
    open_desc.putInteger(chaID("DocI"), 727)
    app.executeAction(chaID("Opn "), open_desc, 3)

def layer_styles_visible(layer, visible):
    if visible: show_hide = chaID("Shw ")
    else: show_hide = chaID("Hd  ")
    old_layer = app.activeDocument.activeLayer
    app.activeDocument.activeLayer = layer
    desc1 = ps.ActionDescriptor()
    list1 = ps.ActionList()
    ref1 = ps.ActionReference()
    ref1.putClass(chaID("Lefx"))
    ref1.putEnumerated(chaID("Lyr "), chaID("Ordn"), chaID("Trgt"))
    list1.putReference(ref1)
    desc1.putList(chaID("null"), list1)
    app.executeAction(show_hide, desc1, 3)
    app.activeDocument.activeLayer = old_layer

# testing to set transform to bicubic auto instead of whatever was used last
# maybe set it up to change to nearest neighbor or something for certain resizing?
def zero_transform(layer, i="bicubicAutomatic", x=0, y=0, w=100, h=100):
    resample = {
       "bicubicSharper": strID("bicubicSharper"),
       "bicubicAutomatic": strID("bicubicAutomatic"),
       "nearestNeighbor": chaID("Nrst")
        }
    old_tool = app.currentTool
    app.currentTool = "moveTool"

    old_layer = app.activeDocument.activeLayer
    app.activeDocument.activeLayer = layer

    desc1 = ps.ActionDescriptor()
    desc2 = ps.ActionDescriptor()
    ref1 = ps.ActionReference()
    idPxl = chaID("#Pxl")
    idPrc = chaID("#Prc")
    ref1.putEnumerated(chaID("Lyr "), chaID("Ordn"), chaID("Trgt"))
    desc1.putReference(chaID("null"), ref1)
    desc1.putEnumerated(chaID("FTcs"), chaID("QCSt"), chaID("Qcs0"))
    desc2.putUnitDouble(chaID("Hrzn"), idPxl, x)
    desc2.putUnitDouble(chaID("Vrtc"), idPxl, y)
    desc1.putObject(chaID("Ofst"), chaID("Ofst"), desc2)
    desc1.putUnitDouble(chaID("Wdth"), idPrc, w)
    desc1.putUnitDouble(chaID("Hght"), idPrc, h)
    desc1.putEnumerated(chaID("Intr"), chaID("Intp"), resample[i])
    app.executeAction(chaID("Trnf"), desc1, 3)

    app.currentTool = old_tool
    app.activeDocument.activeLayer = old_layer