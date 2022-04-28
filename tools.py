"""
PRESHTILDEATH TOOLS
"""
import os
import re
import math
from proxyshop.constants import con
from proxyshop.settings import cfg
import proxyshop.helpers as psd
import photoshop.api as ps
app = ps.Application()
### imports for fetching SVGs from scryfall, then converting them to pdf
##from reportlab.graphics import renderPDF
##from svglib.svglib import svg2rlg
##import lxml
##import requests

# the whole ass mana cost
def mana_cost_render(layer_set, mana_cost):
    burngrey = ps.SolidColor()
    burngrey.rgb.red = burngrey.rgb.green = burngrey.rgb.blue = 150
    sym_lookup = [
        [ 'W', 'U', 'B', 'R', 'G', 'C'],
        [ 'W/U', 'W/B', 'U/B', 'U/R', 'B/R', 'B/G'],
        [ 'R/G', 'R/W', 'G/W', 'G/U', '0', 'X'],
        [ '2/W', '2/U', '2/B', '2/R', '2/G', 'S'],
        [ '1', '2', '3', '4', '5', '6'],
        [ '7', '8', '9', '10', '11', '12'],
        [ '13', '14', '15', '16', '20', ''],
        [ 'W/P', 'U/P', 'B/P', 'R/P', 'G/P', 'P/P'],
        [ 'W/U/P', 'W/B/P', 'U/B/P', 'U/R/P', 'B/R/P', 'B/G/P'],
        [ 'R/G/P', 'R/W/P', 'G/W/P', 'G/U/P', '', '']
    ]
    card_doc = app.activeDocument
    symb_doc = app.open(f'{con.cwd}/templates/preshtildeath/mana.png')
    cost_lookup = mana_cost[1:-1].split('}{').reverse()
    i = 110
    # Go through the symbols from right to left
    for r in range(len(cost_lookup)):
        for sym_row in sym_lookup:
            if cost_lookup[r] in sym_row:
                x = sym_lookup.index(sym_row) * i
                y = sym_row.index(cost_lookup[r]) * i
                layer = copy_from_paste_to(
                    symb_doc,
                    card_doc,
                    layer_set,
                    [x, y, x+i, y+i],
                    [1918-((r+1)*i+(r*5)), 248]
                )
                break
    # cleanup
    symb_doc.close(ps.SaveOptions.DoNotSaveChanges)
    layer_styles_visible(layer_set, "on")
    layer = layer_set.merge()
    # shadow stuff
    app.activeDocument.activeLayer = layer
    magic_wand_select(layer, 0, 0)
    app.activeDocument.selection.expand(20)
    app.activeDocument.selection.feather(30)
    app.activeDocument.selection.invert()
    shadow_layer = app.activeDocument.artLayers.add()
    app.activeDocument.activeLayer = shadow_layer
    app.activeDocument.selection.fill(burngrey)
    shadow_layer.blendMode = ps.BlendMode.ColorBurn
    shadow_layer.visible = True
    shadow_layer.moveAfter(layer.parent)
    psd.clear_selection()
    magic_wand_select(layer, 0, 0)
    app.activeDocument.selection.contract(2)
    app.activeDocument.selection.clear()
    psd.clear_selection()
    return layer
                    
def copy_from_paste_to(fromdoc, todoc, todoc_layer_set, copy_bounds, paste_coord):
    app.activeDocument = fromdoc
    l, t, r, b = copy_bounds
    app.activeDocument.selection.select([[l, t], [r, t], [r, b], [l, b]])
    app.activeDocument.selection.copy()
    app.activeDocument = todoc
    app.activeDocument.activeLayer = todoc_layer_set
    x, y = paste_coord
    app.activeDocument.paste()
    todoc_layer = app.activeDocument.activeLayer
    todoc_layer.translate(x-todoc_layer.bounds[0],y-todoc_layer.bounds[1])
    return todoc_layer

def empty_mana_cost(layer_set):
    app.activeDocument.activeLayer = layer_set
    layer = app.activeDocument.artLayers.add()
    l, t, r, b = [1913, 255, 1918, 365]
    app.activeDocument.selection.select([[l, t], [r, t], [r, b], [l, b]])
    app.activeDocument.selection.fill(psd.rgb_black())
    psd.clear_selection()
    layer.move(psd.getLayerSet('Ref'), 0)
    return layer

def get_set_pdf(code):
    if code.lower() == 'con':
        newcode = 'conflux'
        code_pdf = os.path.join(con.cwd, f'SetPDF/{newcode}.pdf')
    else:
        newcode = code
        code_pdf = os.path.join(con.cwd, f'SetPDF/{newcode}.pdf')
    try: os.mkdir('SetPDF')
    except: pass
    if os.path.exists(code_pdf): return code_pdf
    else:
        code_svg = os.path.join(con.cwd, f'SetPDF/{newcode}.svg')
        set_json = requests.get(f'https://api.scryfall.com/sets/{code}', timeout=1).json()
        scry_svg = requests.get(set_json['icon_svg_uri'], timeout=1).content
        with open(code_svg, 'wb') as svg_temp: svg_temp.write(scry_svg)
        renderPDF.drawToFile(svg2rlg(code_svg), code_pdf)
        os.remove(code_svg)
        return code_pdf
    
def get_expansion(layer, rarity, reference_layer, set_pdf):
    """
     * Pastes the given PDF into the specified layer.
    """
    prev_active_layer = app.activeDocument.activeLayer
    app.activeDocument.activeLayer = layer
    # open pdf twice as big as reference just in case
    max_size = (reference_layer.bounds[2] - reference_layer.bounds[0]) * 2
    pdf_open(set_pdf, max_size)
    # note context switch to art file
    app.activeDocument.selection.selectAll()
    app.activeDocument.selection.copy()
    app.activeDocument.close(ps.SaveOptions.DoNotSaveChanges)
    # note context switch back to template
    app.activeDocument.paste()
    zero_transform(layer)
    # move and resize symbol to appropriate place
    frame_expansion_symbol(layer, reference_layer)
    fill_expansion_symbol(layer, psd.rgb_white())
    # apply rarity mask if necessary, and center it on symbol
    if rarity != con.rarity_common:
        mask_layer = psd.getLayer(rarity, layer.parent)
        psd.select_layer_pixels(layer)
        app.activeDocument.activeLayer = mask_layer
        psd.align_horizontal()
        psd.align_vertical()
        psd.clear_selection()
        mask_layer.visible = True
    # return document to previous state
    app.activeDocument.activeLayer = prev_active_layer

def fill_expansion_symbol(reference, stroke_color):
    """
     * Give the symbol a background for open space symbols (i.e. M10)
    """
    # Magic Wand non-contiguous outside symbol
    magic_wand_select(
        reference,
        reference.bounds[0]-50,
        reference.bounds[1]-50,
        'new',
        0,
        True,
        False
        )

    # Magic Wand subtract contiguous outside symbol
    magic_wand_select(
        reference,
        reference.bounds[0]-50,
        reference.bounds[1]-50,
        'sub',
        0,
        True
        )

    # Make a new layer
    layer = app.activeDocument.artLayers.add()
    layer.name ="Expansion Mask"
    layer.blendMode = ps.BlendMode.NormalBlend
    layer.visible = True
    layer.moveAfter(reference)

    # Fill selection with stroke color
    app.activeDocument.selection.fill(stroke_color)

    # Clear Selection
    psd.clear_selection()

    # Maximum filter to keep the antialiasing normal
    layer.applyMaximum(1)

# Get width and height of paragraph text box
def get_text_bounding_box(layer):
    if app.preferences.pointSize == 1: pref_scale = 72
    else: pref_scale = 72.27
    doc_res = app.activeDocument.resolution
    text_width = layer.textItem.width * (doc_res / pref_scale) ** 2
    text_height = layer.textItem.height * (doc_res / pref_scale) ** 2
    return {
        'width': text_width,
        'height': text_height
        }

# Check if a file already exists, then adds (x) if it does
def filename_append(work_path, file_name, extension):
    if os.path.exists(os.path.join(work_path, f'{file_name}{extension}')):
        multi = 1
        while os.path.exists(os.path.join(work_path, f'{file_name} ({multi}){extension}')):
            multi += 1
        return f'{file_name} ({multi})'
    else: return file_name

# Resize layer to reference, center vertically, and line it up with the right bound
def frame_expansion_symbol(layer, reference_layer):
    lay_dim = psd.compute_layer_dimensions(layer)
    ref_dime = psd.compute_layer_dimensions(reference_layer)

    # Determine how much to scale the layer by such that it fits into the reference layer's bounds
    scale_factor = 100 * min(
        ref_dime['width'] / lay_dim['width'],
        ref_dime['height'] / lay_dim['height']
    )
    layer.resize(scale_factor, scale_factor)

    psd.select_layer_pixels(reference_layer)
    app.activeDocument.activeLayer = layer

    psd.align_vertical()
    layer.translate(reference_layer.bounds[2]-layer.bounds[2],0)
    psd.clear_selection()

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
    show_hide = {"on": "Shw ", "off": "Hd  "}
    old_layer = app.activeDocument.activeLayer
    app.activeDocument.activeLayer = layer
    desc1 = ps.ActionDescriptor()
    list1 = ps.ActionList()
    ref1 = ps.ActionReference()
    ref1.putClass(cTID("Lefx"))
    ref1.putEnumerated(cTID("Lyr "), cTID("Ordn"), cTID("Trgt"))
    list1.putEnumerated(ref1)
    desc1.putList(cTID("null"), list1)
    app.executeAction(cTID(show_hide[visible]), desc1, 3)
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

def bahamut_font(text):
    key = ["[ABCEDFGHIJKLMNO", "PQRSTUVWXYZabcde", "fghijklmnopqrstu", "vwxyz-0123456789", ".,?!\'\":;×/()*—]"]
    key_dict = {}
    r_dict = {}
    for line in key:
        for char in line:
            key_dict[char] = [line.index(char), key.index(line)]
    words = text.split()
    for word in words:
        r_dict[word] = {}
        for c in word:
            r_dict[word][c] = key_dict[c]
    return r_dict
