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
    if depth < 1:
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
def dirty_text_scale (input_text, chars_in_line):
    input_text = re.sub('\{.*?\}', 'X', input_text)
    line_count = math.ceil(input_text.count('\n') * 0.5)
    lines = input_text.split('\n')
    for line in lines:
        line_count += math.ceil(len(line) / chars_in_line)
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
def chaID(char):
    return app.charIDToTypeID(char)

def strID(string):
    return app.stringIDToTypeID(string)

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
def magic_wand_select(layer, x, y, style='new', t=0, a=True, c=True, s=False):
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

def get_layer_index(layerID):
    ref = ps.ActionReference()
    ref.putIdentifier(chaID("Lyr "), layerID)
    try:
        app.activeDocument.backgroundLayer
        return app.executeActionGet(ref).getInteger(chaID("ItmI"))-1
    except: return app.executeActionGet(ref).getInteger(chaID("ItmI"))

def move_inside(fromlayer, layerset):
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

def add_layer(name=None):
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

# Index color palette for active document
def index_color(colors=24, m="uniform"):
    method = {
        "adaptive": chaID("Adpt"),
        "uniform": chaID("Unfm")
    }
    dsc1 = ps.ActionDescriptor()
    dsc2 = ps.ActionDescriptor()
    dsc2.putEnumerated(chaID("Plt "), chaID("ClrP"), method[m])
    dsc2.putInteger(chaID("Clrs"), colors)
    dsc2.putEnumerated(chaID("FrcC"), chaID("FrcC"), chaID("None"))
    dsc2.putBoolean(chaID("Trns"), False)
    dsc2.putEnumerated(chaID("Dthr"), chaID("Dthr"), chaID("Ptrn"))
    dsc1.putObject(chaID("T   "), chaID("IndC"), dsc2)
    app.executeAction(chaID("CnvM"), dsc1, 3)

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

def default_colors():
    fore_back_color_init("reset")

def color_exchange():
    fore_back_color_init("exchange")

def fore_back_color_init(method):
    action = {"reset": chaID("Rset"), "exchange": chaID("Exch")}
    desc = ps.ActionDescriptor()
    ref = ps.ActionReference()
    ref.putProperty(chaID("Clr "), chaID("Clrs"))
    desc.putReference(chaID("null"), ref)
    app.executeAction(action[method], desc, 3)

def pattern_make(file):
    name = os.path.splitext(os.path.basename(file))[0]
    doc = app.load(file)
    desc1 = ps.ActionDescriptor()
    ref1 = ps.ActionReference()
    ref2 = ps.ActionReference()
    ref1.putClass(chaID("Ptrn"))
    desc1.putReference(chaID("null"), ref1)
    ref2.putProperty(chaID("Prpr"), chaID("fsel"))
    ref2.putEnumerated(chaID("Dcmn"), chaID("Ordn"), chaID("Trgt"))
    desc1.putReference(chaID("Usng"), ref2)
    desc1.putString(chaID("Nm  "), name)
    app.executeAction(chaID("Mk  "), desc1, 3)
    doc.close(ps.SaveOptions.DoNotSaveChanges)

def pattern_fill(layer, file, x=0, y=0):
    name = os.path.splitext(os.path.basename(file))[0]
    old_layer = app.activeDocument.activeLayer
    app.activeDocument.activeLayer = layer
    app.currentTool = "bucketTool"
    desc1 = ps.ActionDescriptor()
    desc2 = ps.ActionDescriptor()
    desc2.putUnitDouble(chaID("Hrzn"), chaID("#Pxl"), x)
    desc2.putUnitDouble(chaID("Vrtc"), chaID("#Pxl"), y)
    desc1.putObject(chaID("From"), chaID("Pnt "), desc2)
    desc1.putInteger(chaID("Tlrn"), 0)
    desc1.putEnumerated(chaID("Usng"), chaID("FlCn"), chaID("Ptrn"))
    desc3 = ps.ActionDescriptor()
    desc3.putString(chaID("Nm  "), name)
    desc1.putObject(chaID("Ptrn"), chaID("Ptrn"), desc3)
    desc1.putBoolean(chaID("Cntg"), False)
    while True:
        try: app.executeAction(chaID("Fl  "), desc1, 3)
        except: pattern_make(file)
        else: break
    app.activeDocument.activeLayer = old_layer

def replace_text(layer, from_text, to_text):
    old_layer = app.activeDocument.activeLayer
    app.activeDocument.activeLayer = layer

    dsc1 = ps.ActionDescriptor()
    dsc2 = ps.ActionDescriptor()
    ref1 = ps.ActionReference()
    ref1.putProperty(chaID("Prpr"), strID("replace"))
    ref1.putEnumerated(chaID("TxLr"), chaID("Ordn"), chaID("Trgt"))
    dsc1.putReference(chaID("null"), ref1)
    dsc2.putString(strID("find"), from_text)
    dsc2.putString(strID("replace"), to_text)
    dsc2.putBoolean(strID("checkAll"), False)
    dsc2.putBoolean(strID("forward"), True)
    dsc2.putBoolean(strID("caseSensitive"), True)
    dsc2.putBoolean(strID("wholeWord"), False)
    dsc2.putBoolean(strID("ignoreAccents"), True)
    dsc1.putObject(chaID("Usng"), strID("findReplace"), dsc2)
    app.executeAction(strID("replace"), dsc1, 3)

    app.activeDocument.activeLayer = old_layer

def channel_select(chan="all"):
    chan_dict = {
        "red": chaID("Rd  "),
        "green": chaID("Grn "),
        "blue": chaID("Bl  "),
        "all": chaID("RGB ")
    }
    desc = ps.ActionDescriptor()
    ref = ps.ActionReference()
    ref.putEnumerated(chaID("Chnl"), chaID("Chnl"), chan_dict[chan])
    desc.putReference(chaID("null"), ref)
    app.executeAction(chaID("slct"), desc, 3)

def chroma_shift(layer, delta):
    old_layer = app.activeDocument.activeLayer
    app.activeDocument.activeLayer = layer
    channel_select("red")
    app.activeDocument.selection.selectAll()
    app.activeDocument.activeLayer.applyMotionBlur(0, delta)
    app.activeDocument.selection.translate(-delta, 0)
    app.activeDocument.selection.deselect()
    channel_select("blue")
    app.activeDocument.selection.selectAll()
    app.activeDocument.activeLayer.applyMotionBlur(0, delta)
    app.activeDocument.selection.translate(delta, 0)
    app.activeDocument.selection.deselect()
    channel_select()
    app.activeDocument.activeLayer = old_layer

def lens_blur(layer, radius, bright=0, threshold=255, noise_amount=0, mono=False):
    old_layer = app.activeDocument.activeLayer
    app.activeDocument.activeLayer = layer
    desc = ps.ActionDescriptor()
    desc.putEnumerated(chaID("BkDi"), chaID("BtDi"), chaID("BeIn"))
    desc.putInteger(chaID("BkDp"), 0)
    desc.putBoolean(chaID("BkDs"), False)
    desc.putEnumerated(chaID("BkIs"), chaID("BtIs"), chaID("BeS6")) # Hex default
    desc.putDouble(chaID("BkIb"), radius)
    desc.putInteger(chaID("BkIc"), 0)
    desc.putInteger(chaID("BkIr"), 0)
    desc.putDouble(chaID("BkSb"), bright)
    desc.putInteger(chaID("BkSt"), threshold)
    desc.putInteger(chaID("BkNa"), noise_amount)
    desc.putEnumerated(chaID("BkNt"), chaID("BtNt"), chaID("BeNg"))
    desc.putBoolean(chaID("BkNm"), mono)
    app.executeAction(chaID("Bokh"), desc, 3)
    app.activeDocument.activeLayer = old_layer

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

def set_opacity(layer, percent):
    old_layer = app.activeDocument.activeLayer
    app.activeDocument.activeLayer = layer
    desc1 = ps.ActionDescriptor()
    desc2 = ps.ActionDescriptor()
    ref1 = ps.ActionReference()
    ref1.putEnumerated(chaID("Lyr "), chaID("Ordn"), chaID("Trgt"))
    desc1.putReference(chaID("null"), ref1)
    desc2.putUnitDouble(chaID("Opct"), chaID("#Prc"), percent)
    desc1.putObject(chaID("T   "), chaID("Lyr "), desc2)
    app.executeAction(chaID("setd"), desc1, 3)
    app.activeDocument.activeLayer = old_layer

def img_resize(doc, w_percent=0, h_percent=0, resolution=0, method="bicubicAutomatic", constraint=True):
    resample = {
        "nearest": chaID("Nrst"),
        "bicubicSharper": strID("bicubicSharper"),
        "bicubicAutomatic": strID("bicubicAutomatic")
    }
    old_doc = app.activeDocument
    app.activeDocument = doc
    desc = ps.ActionDescriptor()
    if w_percent != 0 and h_percent != 0:
        desc.putUnitDouble(chaID("Wdth"), chaID("#Prc"), w_percent)
        desc.putUnitDouble(chaID("Hght"), chaID("#Prc"), h_percent)
    if resolution == 0:
        resolution = doc.resolution * max(w_percent, h_percent) / 100
    desc.putUnitDouble(chaID("Rslt"), chaID("#Rsl"), resolution)
    desc.putBoolean(chaID("CnsP"), constraint)
    desc.putBoolean(strID("scaleStyles"), True)
    desc.putEnumerated(chaID("Intr"), chaID("Intp"), resample[method])
    app.executeAction(chaID("ImgS"), desc, 3)
    app.activeDocument = old_doc

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

def crt_filter():
    ass_path = "assets"
    crt_file = os.path.join(ass_path, "crt9x9.png")
    rgb_file = os.path.join(ass_path, "rgb18x9.png")
    r_file = os.path.join(ass_path, "r18x9.png")
    g_file = os.path.join(ass_path, "g18x9.png")
    b_file = os.path.join(ass_path, "b18x9.png")
    scan_file = os.path.join(ass_path, "scan1x9.png")

    doc = app.activeDocument
    doc.flatten()
    base_layer = app.activeDocument.artLayers[0]
    img_resize(doc, 900, 900, 900, "nearest")

    default_colors()
    color_exchange()

    # Extend borders for later spherize
    original_w = doc.width
    original_h = doc.height
    delta = 603
    after_delta = doc.resolution / 8
    l, t, r, b = -delta, -delta, original_w+delta, original_h+delta
    app.activeDocument.crop([l, t, r, b])
    filters = app.activeDocument.layerSets.add()
    filters.name = "Filters"

    # CRT scanline filtered layer
    dupe = base_layer.duplicate()
    dupe.move(filters, ps.ElementPlacement.PlaceInside)
    crtlayer = app.activeDocument.artLayers.add()
    crtlayer.move(filters, ps.ElementPlacement.PlaceInside)
    pattern_fill(crtlayer, crt_file, 10, 10)
    crtlayer.applyMotionBlur(0, 4)
    crtlayer.applyGaussianBlur(1)
    crtlayer.blendMode = ps.BlendMode.Multiply
    crtlayer = crtlayer.merge()
    crtlayer.applyMotionBlur(0, 2)
    crtlayer.applyMinimum(1)
    crtlayer.name = "crtlayer"

    # LCD type effect with RGB overlay
    dupe = crtlayer.duplicate()
    chroma_shift(dupe, 1)
    dupe.move(crtlayer, ps.ElementPlacement.PlaceBefore)
    lcdlayer = app.activeDocument.artLayers.add()
    lcdlayer.move(dupe, ps.ElementPlacement.PlaceBefore)
    pattern_fill(lcdlayer, rgb_file, 10, 10)
    lcdlayer.blendMode = ps.BlendMode.Multiply
    lcdlayer = lcdlayer.merge()
    # lcdlayer.fillOpacity = 40
    lcdlayer.applyMedianNoise(1)
    lens_blur(lcdlayer, 2, 30, 216)
    lcdlayer.fillOpacity = 30
    lcdlayer.name = "lcdlayer"

        # CRT sub-pixel style overlay
    # Setup base layers
    dupe = base_layer.duplicate()
    dupe.move(lcdlayer, ps.ElementPlacement.PlaceBefore)
    scan_layer = app.activeDocument.artLayers.add()
    scan_layer.move(dupe, ps.ElementPlacement.PlaceBefore)
    pattern_fill(scan_layer, scan_file, 10, 10)
    scan_layer.blendMode = ps.BlendMode.Multiply
    r_layer = scan_layer.merge()
    g_layer = r_layer.duplicate()
    b_layer = g_layer.duplicate()
    # Red pixels
    red_mask = app.activeDocument.artLayers.add()
    red_mask.move(r_layer, ps.ElementPlacement.PlaceBefore)
    pattern_fill(red_mask, r_file, 10, 10)
    lens_blur(red_mask, 1, noise_amount=1)
    red_mask.blendMode = ps.BlendMode.Multiply
    red_mask = red_mask.merge()
    red_mask.applyMaximum(0.6)
    # Green pixels
    green_mask = app.activeDocument.artLayers.add()
    green_mask.move(g_layer, ps.ElementPlacement.PlaceBefore)
    pattern_fill(green_mask, g_file, 10, 10)
    lens_blur(green_mask, 1, noise_amount=1)
    green_mask.blendMode = ps.BlendMode.Multiply
    green_mask = green_mask.merge()
    green_mask.applyMaximum(0.6)
    green_mask.blendMode = ps.BlendMode.Screen
    # Blue pixels
    blue_mask = app.activeDocument.artLayers.add()
    blue_mask.move(b_layer, ps.ElementPlacement.PlaceBefore)
    pattern_fill(blue_mask, b_file, 10, 10)
    lens_blur(blue_mask, 1, noise_amount=1)
    blue_mask.blendMode = ps.BlendMode.Multiply
    blue_mask = blue_mask.merge()
    blue_mask.applyMaximum(0.6)
    blue_mask.blendMode = ps.BlendMode.Screen
    # Merge down to one
    rgblayer = blue_mask.merge()
    rgblayer = rgblayer.merge()
    rgblayer.name = "rgblayer"
    rgblayer.blendMode = ps.BlendMode.LinearDodge
    chroma_shift(rgblayer, 1)
    lens_blur(rgblayer, 2, 40, 216, 1)
    rgblayer.applyMaximum(0.8)
    rgblayer.fillOpacity = 70

    crtlayer.applySpherize(8.5, ps.SpherizeMode.NormalSpherize)
    rgblayer.applySpherize(9, ps.SpherizeMode.NormalSpherize)
    lcdlayer.applySpherize(9.5, ps.SpherizeMode.NormalSpherize)

    crtlayer.applyUnSharpMask(40, 1.5, 4)
    crtlayer.resize(97.05, 97.05, ps.AnchorPosition.MiddleCenter)
    lcdlayer.applyMaximum(1)
    lcdlayer.resize(97.1, 97.1, ps.AnchorPosition.MiddleCenter)
    rgblayer.applyRadialBlur(1, ps.RadialBlurMethod.Zoom, ps.RadialBlurBest.RadialBlurBest)
    rgblayer.resize(97.2, 97.2, ps.AnchorPosition.MiddleCenter)
    rgblayer.adjustLevels(22, 255, 1.0, 0, 255)
    glow_layer = rgblayer.duplicate()
    glow_layer.adjustLevels(30, 250, 0.95, 0, 255)
    glow_layer.applyMaximum(2)
    glow_layer.applyGaussianBlur(24)
    glow_layer.resize(100.8, 100.8, ps.AnchorPosition.MiddleCenter)
    glow_layer.fillOpacity = 30

    l, t, r, b = delta-after_delta, delta-after_delta, original_w+delta+after_delta, original_h+delta+after_delta
    # l, t, r, b = d, d, original_w+d, original_h+d
    app.activeDocument.crop([l, t, r, b])
    img_resize(doc, resolution=800, method="bicubicSharper")