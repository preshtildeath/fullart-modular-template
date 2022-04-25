"""
PRESHTILDEATH TOOLS
"""
import os
import re
import math
import requests
from proxyshop.constants import con
from proxyshop.settings import cfg
import proxyshop.helpers as psd
import photoshop.api as ps
from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg
app = ps.Application()

#
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
    cost_lookup = mana_cost[1:-1].split('}{')
    # Go through the symbols from right to left
    for r in range(len(cost_lookup)):
        for x in range(len(sym_lookup)):
            for y in range(len(sym_lookup[x])):
                if cost_lookup[-1] == sym_lookup[x][y]:
                    layer = copy_from_paste_to(
                        symb_doc,
                        card_doc,
                        layer_set,
                        [x*110, y*110, (x+1)*110, (y+1)*110],
                        [1918-((r+1)*110+r*5), 255]
                    )
        cost_lookup.pop()
    symb_doc.close(ps.SaveOptions.DoNotSaveChanges)
    layer = layer_set.merge()
    app.activeDocument.activeLayer = layer
    magic_wand_select(layer, layer.bounds[0]-10, layer.bounds[1]-10)
    app.activeDocument.selection.expand(10)
    app.activeDocument.selection.feather(40)
    app.activeDocument.selection.invert()
    magic_wand_select(layer, layer.bounds[0]-10, layer.bounds[1]-10, 'sub')
    app.activeDocument.selection.contract(3)
    shadow_layer = app.activeDocument.artLayers.add()
    shadow_layer.visible = True
    app.activeDocument.activeLayer = shadow_layer
    app.activeDocument.selection.fill(burngrey)
    shadow_layer.blendMode = ps.BlendMode.ColorBurn
    shadow_layer.visible = True
    shadow_layer.moveAfter(layer.parent)
    psd.clear_selection()
    return layer
                    
def copy_from_paste_to(fromdoc, todoc, todoc_layer_set, copy_bounds, paste_coord):
    app.activeDocument = fromdoc
    left, top, right, bottom = copy_bounds
    app.activeDocument.selection.select([
        [left, top],
        [right, top],
        [right, bottom],
        [left, bottom]
    ])
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
    left, top, right, bottom = [1913, 255, 1918, 365]
    app.activeDocument.selection.select([
        [left, top],
        [right, top],
        [right, bottom],
        [left, bottom]
    ])
    app.activeDocument.selection.fill(psd.rgb_black())
    psd.clear_selection()
    layer.move(psd.getLayer('Ref'), 0)
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
    max_size = (reference_layer.bounds[2] - reference_layer.bounds[0]) * 5
    pdf_open(set_pdf, max_size)
    # note context switch to art file
    app.activeDocument.selection.selectAll()
    app.activeDocument.selection.copy()
    app.activeDocument.close(ps.SaveOptions.DoNotSaveChanges)
    # note context switch back to template
    app.activeDocument.paste()

    frame_expansion_symbol(layer, reference_layer)
    
    psd.apply_stroke(cfg.symbol_stroke, psd.rgb_white())
    fill_expansion_symbol(layer, psd.rgb_white())
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
    Give the symbol a background for open space symbols (i.e. M10)
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
    layer.name = "Expansion Mask"
    layer.blendMode = ps.BlendMode.NormalBlend
    layer.visible = True
    layer.moveAfter(reference)

    # Fill selection with stroke color
    app.activeDocument.selection.fill(stroke_color)

    # Clear Selection
    psd.clear_selection()

    # Maximum filter to keep the antialiasing normal
    layer.applyMaximum(1)

# Magic Wand target layer at coordinate (X, Y)
def magic_wand_select(layer, x, y, style='new', t=0, a=True, c=True, s=False):
    select = {'new': 'setd', 'add': 'AddT', 'sub': 'SbtF', 'cross': 'IntW'}
    old_layer = app.activeDocument.activeLayer
    app.activeDocument.activeLayer = layer
    coords = ps.ActionDescriptor()
    coords.putUnitDouble(app.CharIDToTypeID( "Hrzn" ),app.CharIDToTypeID( "#Pxl" ), x )
    coords.putUnitDouble(app.CharIDToTypeID( "Vrtc" ),app.CharIDToTypeID( "#Pxl" ), y )
    click = ps.ActionDescriptor()
    ref = ps.ActionReference()
    ref.putProperty(app.CharIDToTypeID( "Chnl" ), app.CharIDToTypeID( "fsel" ) )
    click.putReference(app.CharIDToTypeID( "null" ), ref )
    click.putObject(app.CharIDToTypeID( "T   " ), app.CharIDToTypeID( "Pnt " ), coords )
    click.putInteger(app.CharIDToTypeID( "Tlrn" ), t ) # Tolerance
    click.putBoolean(app.CharIDToTypeID( "AntA" ), a ) # Anti-aliasing
    if not c: click.putBoolean(app.CharIDToTypeID( "Cntg" ), c ) # Contiguous
    if not s: click.putBoolean(app.CharIDToTypeID( "Mrgd" ), s ) # Sample all layers
    app.executeAction(app.CharIDToTypeID(select[style]), click, 3 )
    app.activeDocument.activeLayer = old_layer

def paste_in_place():
    paste = ps.ActionDescriptor()
    paste.putBoolean(app.stringIDToTypeID( "inPlace" ), True)
    paste.putEnumerated(
        app.charIDToTypeID( "AntA" ),
        app.charIDToTypeID( "Antt" ),
        app.charIDToTypeID( "Anto" )
        )
    app.executeAction(app.charIDToTypeID( "past" ), paste, 3)

def pdf_open(file, size):
    """
     * Opens a pdf scaled to (height) pixels tall
    """
    open_desc = ps.ActionDescriptor()
    sett_desc = ps.ActionDescriptor()
    sett_desc.putString( app.charIDToTypeID( "Nm  " ), "pdf" )
    sett_desc.putEnumerated(
        app.charIDToTypeID( "Crop" ),
        app.stringIDToTypeID( "cropTo" ),
        app.stringIDToTypeID( "boundingBox" )
        )
    sett_desc.putUnitDouble(
        app.charIDToTypeID( "Rslt" ),
        app.charIDToTypeID( "#Rsl" ),
        800.000000
        )
    sett_desc.putEnumerated(
        app.charIDToTypeID( "Md  " ),
        app.charIDToTypeID( "ClrS" ),
        app.charIDToTypeID( "RGBC" )
        )
    sett_desc.putInteger( app.charIDToTypeID( "Dpth" ), 8 )
    sett_desc.putBoolean( app.charIDToTypeID( "AntA" ), True )
    sett_desc.putUnitDouble(
        app.charIDToTypeID( "Wdth" ),
        app.charIDToTypeID( "#Pxl" ),
        size
        )
    sett_desc.putUnitDouble(
        app.charIDToTypeID( "Hght" ),
        app.charIDToTypeID( "#Pxl" ),
        size
        )
    sett_desc.putBoolean( app.charIDToTypeID( "CnsP" ), True )
    sett_desc.putBoolean( app.stringIDToTypeID( "suppressWarnings" ), True )
    sett_desc.putBoolean( app.charIDToTypeID( "Rvrs" ), True )
    sett_desc.putEnumerated(
        app.charIDToTypeID( "fsel" ),
        app.stringIDToTypeID( "pdfSelection" ),
        app.stringIDToTypeID( "page" )
        )
    sett_desc.putInteger( app.charIDToTypeID( "PgNm" ), 1 )
    open_desc.putObject(
        app.charIDToTypeID( "As  " ),
        app.charIDToTypeID( "PDFG" ),
        sett_desc
        )
    open_desc.putPath( app.charIDToTypeID( "null" ), file )
    open_desc.putInteger( app.charIDToTypeID( "DocI" ), 727 )
    app.executeAction( app.charIDToTypeID( "Opn " ), open_desc, 3 )

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
        line_count += math.ceil( len(line) / 36 )
    return line_count

# Stretches a layer by (-modifier) pixels
def layer_vert_stretch(layer, modifier, anchor='bottom'):
    anchor_set = { 'top': 1, 'center': 4, 'bottom': 7 }
    height = layer.bounds[3] - layer.bounds[1]
    h_perc = (height - modifier) / height * 100
    layer.resize(100, h_perc, anchor_set[anchor])
    return h_perc, anchor_set[anchor]

# Rearranges two color layers in order and applies mask
def wubrg_layer_sort (color_pair, layers):
    top = psd.getLayer(color_pair[0], layers)
    bottom = psd.getLayer(color_pair[1], layers)
    top.moveBefore(bottom)
    app.activeDocument.activeLayer = top
    psd.enable_active_layer_mask()
    top.visible = True
    bottom.visible = True

# Selects the layer mask for editing
def layer_mask_select (layer):
    app.activeDocument.activeLayer = layer
    desc_mask = ps.ActionDescriptor()
    ref_mask = ps.ActionReference()
    chnl = app.CharIDToTypeID( "Chnl" )
    ref_mask.putEnumerated(
        chnl,
        chnl,
        app.charIDToTypeID( "Msk " )
        )
##    ref_mask.putName(
##        app.charIDToTypeID( "Lyr " ),
##        layer.name
##        )
    desc_mask.putReference(
        app.charIDToTypeID( "null" ),
        ref_mask
        )
    desc_mask.putBoolean( app.CharIDToTypeID( "MkVs" ), True )
    app.executeAction( app.CharIDToTypeID( "slct" ), desc_mask, 3 )
    return

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
