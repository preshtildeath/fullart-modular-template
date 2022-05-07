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

# loop up through parent directories
def parent_dirs(file, depth=1):
    for d in range(depth): file = os.path.dirname(file)
    return file

cwd = parent_dirs(__file__, 4)
plugin_dir = parent_dirs(__file__)

def rgbcolor(r, g, b):
    color = ps.SolidColor()
    color.rgb.red = r
    color.rgb.green = g
    color.rgb.blue = b
    return color

# the whole ass mana cost
def mana_cost_render(layer_set, mana_cost):
    sym_lookup = [
        [ 'W', 'U', 'B', 'R', 'G', 'C'],
        [ 'W/U', 'W/B', 'U/B', 'U/R', 'B/R', 'B/G'],
        [ 'R/G', 'R/W', 'G/W', 'G/U', '0', 'X'],
        [ '2/W', '2/U', '2/B', '2/R', '2/G', 'S'],
        [ '1', '2', '3', '4', '5', '6'],
        [ '7', '8', '9', '10', '11', '12'],
        [ '13', '14', '15', '16', '20'],
        [ 'W/P', 'U/P', 'B/P', 'R/P', 'G/P', 'P/P'],
        [ 'W/U/P', 'W/B/P', 'U/B/P', 'U/R/P', 'B/R/P', 'B/G/P'],
        [ 'R/G/P', 'R/W/P', 'G/W/P', 'G/U/P']
    ]
    cost_lookup = mana_cost[1:-1].split('}{')
    w = 110
    h = 110
    card_doc = app.activeDocument
    symb_doc = app.open(f'{plugin_dir}/assets/mana.png')
    # w = symb_doc.width / len(sym_lookup) # Width divided by length of whole list
    # h = symb_doc.height / max(len(line for line in sym_lookup)) # Height divided by longest line in list
    for r in range(len(cost_lookup)):
        for x in range(len(sym_lookup)):
            for y in range(len(sym_lookup[x])):
                if cost_lookup[-1] == sym_lookup[x][y]:
                    layer = copy_from_paste_to(
                        symb_doc,
                        card_doc,
                        layer_set,
                        [x*w, y*h, (x+1)*w, (y+1)*h],
                        [1918-((r+1)*w+(r*5)), 251]
                    )
        cost_lookup.pop()
    # cleanup
    symb_doc.close(ps.SaveOptions.DoNotSaveChanges)
    layer = layer_set.merge()
    # shadow stuff
        # burngrey = rgbcolor(150, 150, 150)
        # app.activeDocument.activeLayer = layer
        # magic_wand_select(layer, 0, 0)
        # app.activeDocument.selection.expand(20)
        # app.activeDocument.selection.invert()
        # app.activeDocument.selection.feather(30)
        # shadow_layer = add_layer("Shadow")
        # app.activeDocument.activeLayer = shadow_layer
        # app.activeDocument.selection.fill(burngrey)
        # shadow_layer.blendMode = ps.BlendMode.ColorBurn
        # shadow_layer.visible = True
        # shadow_layer.moveAfter(layer.parent)
        # app.activeDocument.selection.deselect()
        # magic_wand_select(layer, 0, 0)
        # app.activeDocument.selection.expand(2)
        # app.activeDocument.selection.clear()
        # app.activeDocument.selection.deselect()
    return layer
                    
def copy_from_paste_to(fromdoc, todoc, todoc_layer_set, copy_bounds, paste_coord):
    l, t, r, b = copy_bounds
    x, y = paste_coord
    app.activeDocument = fromdoc
    app.activeDocument.selection.select([[l, t], [r, t], [r, b], [l, b]])
    app.activeDocument.selection.copy()
    app.activeDocument = todoc
    app.activeDocument.activeLayer = todoc_layer_set
    layer = app.activeDocument.paste()
    magic_wand_select(layer, 0, 0)
    app.activeDocument.selection.invert()
    bounds = app.activeDocument.selection.bounds
    app.activeDocument.selection.deselect()
    layer.translate(x-bounds[0],y-bounds[1])
    return layer

def empty_mana_cost(layer_set):
    black = rgbcolor(0, 0, 0)
    app.activeDocument.activeLayer = layer_set
    layer = add_layer("Empty")
    app.activeDocument.activeLayer = layer
    l, t, r, b = [1913, 255, 1918, 365]
    app.activeDocument.selection.select([[l, t], [r, t], [r, b], [l, b]])
    app.activeDocument.selection.fill(black)
    layer.blendMode = ps.BlendMode.Screen
    return layer

# Grab the pdf file from our database
def get_set_pdf(code):
    code, key = code.upper(), "" # Init values
    pdf_folder = os.path.join(plugin_dir, "assets", "Set Symbol PDF")
    if not os.path.exists(pdf_folder): os.mkdir(pdf_folder) # Make sure the Set PDF folder exists
    set_pdf_json = os.path.join(pdf_folder, "set_pdf.json")
    if os.path.getsize(set_pdf_json) > 32: # Open up our JSON file if it exists
        with open(set_pdf_json, "r") as file: set_json = json.load(file)
    else: set_json = {}
    for set in set_json: # Iterate JSON looking for a match
        if code in set_json[set]: key = set; break
    if key == "": # No match, gotta fetch
        key = scry_scrape(code)
        if key in set_json: set_json[key].append(code) # Append list
        else: set_json[key] = [code] # Create list
    pdf = os.path.join(pdf_folder, f"{key}.pdf")
    if not os.path.exists(pdf): pdf_fetch(pdf_folder, key) # Fetch SVG and convert to PDF if needed
    with open(set_pdf_json, "w") as file: json.dump(set_json, file)
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

    psd.select_layer_pixels(reference_layer)
    app.activeDocument.activeLayer = layer
    # Align verticle center, horizontal right
    psd.align_vertical()
    layer.translate(reference_layer.bounds[2]-layer.bounds[2],0)
    app.activeDocument.selection.deselect()
    # Check against pixel curvature
    # dupe = layer.duplicate()
    # magic_wand_select(offset_layer, 10, 10)
    # app.activeDocument.selection.invert()
    # app.activeDocument.selection.clear()
    # app.activeDocument.selection.deselect()
    # x_delta = dupe.bounds[2] - dupe.bounds[0]
    # layer.translate(-x_delta,0)
    # dupe.remove()

def fill_expansion_symbol(ref, stroke_color):
    """
     * Give the symbol a background for open space symbols (i.e. M10)
    """
    x, y = ref.bounds[0]-50, ref.bounds[1]-50
    # Magic Wand non-contiguous outside symbol
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

# Get width and height of paragraph text box
def get_text_bounding_box(layer, text_width=None, text_height=None):
    if app.preferences.pointSize == 1: pref_scale = 72
    else: pref_scale = 72.27
    doc_res = app.activeDocument.resolution
    multiplier = (doc_res / pref_scale) ** 2
    if text_width is None: layer.textItem.width = text_width * multiplier
    else: text_width = layer.textItem.width * multiplier
    if text_height is None: layer.textItem.height = text_height * multiplier
    else: text_height = layer.textItem.height * multiplier
    return [text_width, text_height]

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
def dirty_text_scale (input_text):
    input_text = re.sub('\{.?.?.?.?\}', 'X', input_text)
    line_count = 0
    if input_text.count('\n') >= 3: line_count += 1
    lines = input_text.split('\n')
    for line in lines:
        line_count += math.ceil(len(line) / 36)
    return line_count

# Stretches a layer by (-modifier) pixels
def layer_vert_stretch(layer, modifier, anchor='bottom'):
    anchor_set = { 'top': 1, 'center': 4, 'bottom': 7 }
    height = layer.bounds[3] - layer.bounds[1]
    h_perc = (height - modifier) / height * 100
    layer.resize(100, h_perc, anchor_set[anchor])

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
    ], 2)

def paste_file(layer, file):
    """
     * Pastes the given file into the specified layer.
    """
    prev_active_layer = app.activeDocument.activeLayer
    app.activeDocument.activeLayer = layer
    app.load(file)
    # note context switch to art file
    app.activeDocument.selection.selectAll()
    app.activeDocument.selection.copy()
    app.activeDocument.close(ps.SaveOptions.DoNotSaveChanges)
    # note context switch back to template
    app.activeDocument.paste()

    # return document to previous state
    app.activeDocument.activeLayer =prev_active_layer

"""
HERE LIES ALL THE COMPLICATED BULLSHIT THAT MAKES LITTLE SENSE
"""

# define these because otherwise they take up so many characters
def cTID(char):
    return app.charIDToTypeID(char)

def sTID(string):
    return app.stringIDToTypeID(string)

# Selects the layer mask for editing
def layer_mask_select (layer):
    app.activeDocument.activeLayer = layer
    desc_mask = ps.ActionDescriptor()
    ref_mask = ps.ActionReference()
    chnl = cTID("Chnl")
    ref_mask.putEnumerated(chnl, chnl, cTID("Msk "))
    desc_mask.putReference(cTID("null"), ref_mask)
    desc_mask.putBoolean(cTID("MkVs"), True)
    app.executeAction(cTID("slct"), desc_mask, 3)
    return

# Magic Wand target layer at coordinate (X, Y)
def magic_wand_select(layer, x, y, style='new', t=0, a=True, c=True, s=False):
    select_key = {'new': 'setd', 'add': 'AddT', 'sub': 'SbtF', 'cross': 'IntW'}
    old_layer = app.activeDocument.activeLayer
    app.activeDocument.activeLayer = layer
    coords = ps.ActionDescriptor()
    coords.putUnitDouble(cTID("Hrzn"), cTID("#Pxl"), x)
    coords.putUnitDouble(cTID("Vrtc"), cTID("#Pxl"), y)
    click = ps.ActionDescriptor()
    ref = ps.ActionReference()
    ref.putProperty(cTID("Chnl"), cTID("fsel"))
    click.putReference(cTID("null"), ref)
    click.putObject(cTID("T   "), cTID("Pnt "), coords)
    click.putInteger(cTID("Tlrn"), t) # Tolerance
    click.putBoolean(cTID("AntA"), a) # Anti-aliasing
    click.putBoolean(cTID("Cntg"), c) # Contiguous
    click.putBoolean(cTID("Mrgd"), s) # Sample all layers
    app.executeAction(cTID(select_key[style]), click, 3)
    app.activeDocument.activeLayer = old_layer

def get_layer_index(layerID):
    ref = ps.ActionReference()
    ref.putIdentifier(cTID("Lyr "), layerID)
    try:
        app.activeDocument.backgroundLayer
        return app.executeActionGet(ref).getInteger(cTID("ItmI"))-1
    except: return app.executeActionGet(ref).getInteger(cTID("ItmI"))

def move_inside(fromlayer, layerset):
    fromID = fromlayer.id
    toID = layerset.id
    desc = ps.ActionDescriptor()
    ref1 = ps.ActionReference()
    ref2 = ps.ActionReference()
    ref1.putIdentifier(cTID("Lyr "), int(fromID))
    desc.putReference(cTID("null"), ref1)
    ref2.putIndex(cTID("Lyr "), get_layer_index(toID))
    desc.putReference(cTID("T   "), ref2)
    desc.putBoolean(cTID('Adjs'), False)
    desc.putInteger(cTID('Vrsn'), 5)
    try:
        app.executeAction(cTID("move"), desc, 3)
    except Exception as err:
        return err

def add_layer(name=None):
    layer = app.activeDocument.activeLayer
    desc = ps.ActionDescriptor()
    ref = ps.ActionReference()
    ref.putClass(cTID("Lyr "))
    desc.putReference(cTID("null"), ref)
    desc.putInteger(cTID("LyrI"), get_layer_index(layer.id))
    app.executeAction(cTID("Mk  "), desc, 3)
    layer = app.activeDocument.activeLayer
    if name is not None: layer.name = name
    return layer

# equivalent of ctrl+shift+v
def paste_in_place():
    paste = ps.ActionDescriptor()
    paste.putBoolean(sTID("inPlace"), True)
    paste.putEnumerated(
        cTID("AntA"),
        cTID("Antt"),
        cTID("Anto")
       )
    app.executeAction(cTID("past"), paste, 3)

# opens a pdf at a fixed max width/height
def pdf_open(file, size):
    """
     * Opens a pdf scaled to (height) pixels tall
    """
    open_desc = ps.ActionDescriptor()
    sett_desc = ps.ActionDescriptor()
    pxl = cTID("#Pxl")
    sett_desc.putString(cTID("Nm  "), "pdf")
    sett_desc.putEnumerated(cTID("Crop"), sTID("cropTo"), sTID("boundingBox"))
    sett_desc.putUnitDouble(cTID("Rslt"), cTID("#Rsl"), 800.000000)
    sett_desc.putEnumerated(cTID("Md  "), cTID("ClrS"), cTID("RGBC"))
    sett_desc.putInteger(cTID("Dpth"), 8)
    sett_desc.putBoolean(cTID("AntA"), True)
    sett_desc.putUnitDouble(cTID("Wdth"), pxl, size)
    sett_desc.putUnitDouble(cTID("Hght"), pxl, size)
    sett_desc.putBoolean(cTID("CnsP"), True)
    sett_desc.putBoolean(sTID("suppressWarnings"), True)
    sett_desc.putBoolean(cTID("Rvrs"), True)
    sett_desc.putEnumerated(cTID("fsel"), sTID("pdfSelection"), sTID("page"))
    sett_desc.putInteger(cTID("PgNm"), 1)
    open_desc.putObject(cTID("As  "), cTID("PDFG"), sett_desc)
    open_desc.putPath(cTID("null"), file)
    open_desc.putInteger(cTID("DocI"), 727)
    app.executeAction(cTID("Opn "), open_desc, 3)

def layer_styles_visible(layer, visible):
    if visible: show_hide = cTID("Shw ")
    else: show_hide = cTID("Hd  ")
    old_layer = app.activeDocument.activeLayer
    app.activeDocument.activeLayer = layer
    desc1 = ps.ActionDescriptor()
    list1 = ps.ActionList()
    ref1 = ps.ActionReference()
    ref1.putClass(cTID("Lefx"))
    ref1.putEnumerated(cTID("Lyr "), cTID("Ordn"), cTID("Trgt"))
    list1.putReference(ref1)
    desc1.putList(cTID("null"), list1)
    app.executeAction(show_hide, desc1, 3)
    app.activeDocument.activeLayer = old_layer

def set_opacity(layer, percent):
    old_layer = app.activeDocument.activeLayer
    app.activeDocument.activeLayer = layer
    desc1 = ps.ActionDescriptor()
    desc2 = ps.ActionDescriptor()
    ref1 = ps.ActionReference()
    ref1.putEnumerated(cTID("Lyr "), cTID("Ordn"), cTID("Trgt"))
    desc1.putReference(cTID("null"), ref1)
    desc2.putUnitDouble(cTID("Opct"), cTID("#Prc"), percent)
    desc1.putObject(cTID("T   "), cTID("Lyr "), desc2)
    app.executeAction(cTID("setd"), desc1, 3)
    app.activeDocument.activeLayer = old_layer

# testing to set transform to bicubic auto instead of whatever was used last
# maybe set it up to change to nearest neighbor or something for certain resizing?
def zero_transform(layer, i="bicubicAutomatic", x=0, y=0, w=100, h=100):
    resample = {
       "bicubicSharper": sTID("bicubicSharper"),
       "bicubicAutomatic": sTID("bicubicAutomatic"),
       "nearestNeighbor": cTID("Nrst")
        }
    old_tool = app.currentTool
    old_layer = app.activeDocument.activeLayer

    app.currentTool = "moveTool"
    app.activeDocument.activeLayer = layer

    desc1 = ps.ActionDescriptor()
    desc2 = ps.ActionDescriptor()
    ref1 = ps.ActionReference()
    idPxl = cTID("#Pxl")
    idPrc = cTID("#Prc")
    ref1.putEnumerated(cTID("Lyr "), cTID("Ordn"), cTID("Trgt"))
    desc1.putReference(cTID("null"), ref1)
    desc1.putEnumerated(cTID("FTcs"), cTID("QCSt"), cTID("Qcs0"))
    desc2.putUnitDouble(cTID("Hrzn"), idPxl, x)
    desc2.putUnitDouble(cTID("Vrtc"), idPxl, y)
    desc1.putObject(cTID("Ofst"), cTID("Ofst"), desc2)
    desc1.putUnitDouble(cTID("Wdth"), idPrc, w)
    desc1.putUnitDouble(cTID("Hght"), idPrc, h)
    desc1.putEnumerated(cTID("Intr"), cTID("Intp"), resample[i])
    app.executeAction(cTID("Trnf"), desc1, 3)

    app.currentTool = old_tool
    app.activeDocument.activeLayer = old_layer

def bitmap_font(text, bounds):
    key = ["ABCDEFGHI", "JKLMNOPQR", "STUVWXYZ0",
        "abcdefghi", "jklmnopqr", "stuvwxyz—",
        "123456789", "!?-+/%.:," ]
    key_dict = {}
    txt_dict = {}
    txt_lines = []
    #build dictionary with relative x,y coordinates
    for line in key:
        for char in line:
            key_dict[char] = [line.index(char), key.index(line)]
    #parse text against dictionary
    #assemble based on widths and adding lines as necessary
    words = text.split()
    for word in words:
        txt_dict[word] = {}
        for c in word:
            txt_dict[word][c] = key_dict[c]

app = ps.Application()