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


def get_layer(name: str, *group):
    """
    Retrieve layer object.
    """
    layer_set = app.activeDocument
    if len(group) > 0:
        layer_set = get_layer_set(*group)
    if isinstance(name, str):
        return layer_set.artLayers.getByName(name)
    return name


def get_layer_set(name: str, *group):
    """
    Retrieve layer group object.
    """
    layer_set = app.activeDocument
    if len(group) > 0:
        layer_set = get_layer_set(*group)
    if isinstance(name, str):
        layer = layer_set.layers.getByName(name)
        if layer.typename == "LayerSet":
            return layer
        return layer_set.layerSets.getByName(name)
    return name


def text_layer_bounds(layer) -> list:
    select_blank_pixels(layer)
    app.activeDocument.selection.invert()
    bounds = app.activeDocument.selection.bounds
    app.activeDocument.selection.deselect()
    return bounds


def text_layer_dimensions(layer) -> list:
    bounds = text_layer_bounds(layer)
    width, height = bounds[2] - bounds[0], bounds[3] - bounds[1]
    return [width, height]


def get_selection_dimensions() -> list:
    selection = app.activeDocument.selection
    return [
        selection.bounds[2] - selection.bounds[0],
        selection.bounds[3] - selection.bounds[1],
    ]


def inside_of(inner, outer):
    test = bool(
        inner.bounds[0] >= outer.bounds[0]
        and inner.bounds[1] >= outer.bounds[1]
        and inner.bounds[2] <= outer.bounds[2]
        and inner.bounds[3] <= outer.bounds[3]
    )
    return test


# loop up through parent directories
def parent_dirs(file, depth=1):
    if depth >= 1:
        return os.path.dirname(parent_dirs(file, depth - 1))
    return file


def rgbcolor(r, g, b):
    color = ps.SolidColor()
    color.rgb.red = r
    color.rgb.green = g
    color.rgb.blue = b
    return color


def get_expansion(layer, rarity, ref_layer, set_pdf):
    # Pastes the given PDF into the specified layer.

    # Start nice and clean
    white = rgbcolor(255, 255, 255)
    doc = app.activeDocument
    prev_active_layer = doc.activeLayer
    doc.activeLayer = layer

    # open pdf twice as big as reference just in case
    max_size = (ref_layer.bounds[2] - ref_layer.bounds[0]) * 2
    pdf_open(set_pdf, max_size)

    # note context switch to art file
    app.activeDocument.selection.selectAll()
    app.activeDocument.selection.copy()
    app.activeDocument.close(ps.SaveOptions.DoNotSaveChanges)

    # note context switch back to template
    layer = doc.paste()
    zero_transform(layer)

    lay_dim = psd.compute_layer_dimensions(layer)
    ref_dim = psd.compute_layer_dimensions(ref_layer)

    # Determine how much to scale the layer by such that it fits into the reference layer's bounds
    scale_factor = 100 * min(
        ref_dim["width"] / lay_dim["width"], ref_dim["height"] / lay_dim["height"]
    )
    layer.resize(scale_factor, scale_factor)

    # Align verticle center, horizontal right
    psd.select_layer_pixels(ref_layer)
    psd.align_vertical()
    layer.translate(ref_layer.bounds[2] - layer.bounds[2], 0)
    doc.selection.deselect()

    fill_expansion_symbol(layer, white)

    # apply rarity mask if necessary, and center it on symbol
    if rarity != "common":
        mask_layer = get_layer(rarity, "Expansion")
        doc.activeLayer = mask_layer
        psd.select_layer_pixels(layer)
        psd.align_horizontal()
        psd.align_vertical()
        psd.clear_selection()
        mask_layer.visible = True

    # return document to previous state
    doc.activeLayer = prev_active_layer
    return layer


def get_set_pdf(code):
    # Grab the pdf file from our database

    # Check if the pdf exists as named and return that if it does
    pdf_folder = os.path.join(parent_dirs(__file__), "assets", "Set Symbol PDF")
    if not os.path.exists(pdf_folder):
        os.mkdir(pdf_folder)
    pdf = os.path.join(pdf_folder, f"{code}.pdf")
    if os.path.exists(pdf):
        return pdf

    # Open up our JSON file if it exists
    set_pdf_json = os.path.join(pdf_folder, "set_pdf.json")
    if os.path.exists(set_pdf_json):
        set_json = json.load(open(set_pdf_json, "r"))
    else:
        set_json = {}

    # Iterate JSON looking for a match
    code = code.upper()
    key = [k for k, v in set_json.items() if code in v]
    if key == []:
        key, svg_uri = scry_scrape(code)
        if key in set_json.keys():
            set_json[key] += [code]
        else:
            set_json[key] = [code]
    else:
        key = key[0]

    # Hacky way to check if svg_uri is assigned
    if "svg_uri" not in dir():
        svg_uri = (
            f"https://c2.scryfall.com/file/scryfall-symbols/sets/{key.lower()}.svg"
        )

    # Look for our PDF, or fetch the SVG from Scryfall and convert
    pdf = os.path.join(pdf_folder, f"{key}.pdf")
    if not os.path.exists(pdf):
        pdf_fetch(pdf_folder, key, svg_uri)

    # Format our JSON for readability, keeping the values one line
    clean_json = (
        json.dumps(set_json)
        .replace("{", "{\n\t")
        .replace("], ", "],\n\t")
        .replace("]}", "]\n}")
    )
    with open(set_pdf_json, "w") as file:
        file.write(clean_json)

    # Finally return our pdf
    return pdf


# Take a set code and return the corresponding image name
def scry_scrape(code):
    code = code.lower()
    set_json = requests.get(f"https://api.scryfall.com/sets/{code}", timeout=1).json()
    name = os.path.splitext(os.path.basename(set_json["icon_svg_uri"]))[
        0
    ].upper()  # Grab the SVG name
    if name == "CON":
        name = "CONFLUX"  # Turns out you can't make a file named CON
    svg_uri = set_json["icon_svg_uri"]
    return [name, svg_uri]


# Take the image name and download from scryfall, then convert to pdf
def pdf_fetch(folder, code, svg_uri):
    from reportlab.graphics import renderPDF
    from svglib.svglib import svg2rlg

    file = os.path.join(folder, f"{code.lower()}.pdf")
    temp_svg = os.path.join(os.getcwd(), "temp_svg.svg")
    scry_svg = requests.get(svg_uri, timeout=1).content
    with open(temp_svg, "wb") as svg:
        svg.write(scry_svg)
    renderPDF.drawToFile(svg2rlg(temp_svg), file)
    try:
        os.remove(temp_svg)
    except:
        pass


# Resize layer to reference, center vertically, and line it up with the right bound
def frame_expansion_symbol(layer, reference_layer):

    lay_dim = psd.compute_layer_dimensions(layer)
    ref_dim = psd.compute_layer_dimensions(reference_layer)

    # Determine how much to scale the layer by such that it fits into the reference layer's bounds
    scale_factor = 100 * min(
        ref_dim["width"] / lay_dim["width"], ref_dim["height"] / lay_dim["height"]
    )
    layer.resize(scale_factor, scale_factor)

    # Align verticle center, horizontal right
    psd.select_layer_pixels(reference_layer)
    app.activeDocument.activeLayer = layer
    psd.align_vertical()
    layer.translate(reference_layer.bounds[2] - layer.bounds[2], 0)
    app.activeDocument.selection.deselect()


# Give the symbol a background for open space symbols (i.e. M10)
def fill_expansion_symbol(ref, stroke_color):

    # Magic Wand non-contiguous outside symbol, then subtract contiguous
    x, y = ref.bounds[0] - 50, ref.bounds[1] - 50
    magic_wand_select(ref, x, y, "set", 0, True, False)
    magic_wand_select(ref, x, y, "subtractFrom", 0, True)

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
    file_name, extension = os.path.splitext(os.path.basename(file))  # image, .xxx
    test_name = os.path.join(send_path, f"{file_name}{extension}")
    if os.path.exists(test_name):  # location/image.xxx
        multi = 1
        test_name = os.path.join(send_path, f"{file_name} ({multi}){extension}")
        while os.path.exists(test_name):  # location/image (1).xxx
            multi += 1
            test_name = os.path.join(send_path, f"{file_name} ({multi}){extension}")
    return test_name  #  returns "location/image.xxx" or "location/image (x).xxx"


# Gives an estimated number of lines at default text size
def dirty_text_scale(input_text, chars_in_line):
    input_text = re.sub("\{.*?\}", "X", input_text)
    line_count = math.ceil(input_text.count("\n") * 0.5)
    lines = input_text.split("\n")
    for line in lines:
        line_count += math.ceil(len(line) / chars_in_line)
    return line_count


# Stretches a layer by (-modifier) pixels
def layer_vert_stretch(layer, modifier, anchor="bottom", method="nearestNeighbor"):
    transform_delta = {"top": 0, "center": modifier / 2, "bottom": modifier}
    # anchor_set = { 'top': 1, 'center': 4, 'bottom': 7 }
    height = layer.bounds[3] - layer.bounds[1]
    h_perc = (height - modifier) / height * 100
    zero_transform(layer, method, 0, transform_delta[anchor], 100, h_perc)
    # layer.resize(100, h_perc, anchor_set[anchor])


# Rearranges two color layers in order and applies mask
def wubrg_layer_sort(color_pair, layers):
    top = get_layer(color_pair[0], layers)
    bottom = get_layer(color_pair[1], layers)
    top.moveBefore(bottom)
    app.activeDocument.activeLayer = top
    psd.enable_active_layer_mask()
    top.visible = True
    bottom.visible = True


def add_select_layer(layer):
    # Select a layer's pixels and adds them to the selection
    select_layer(layer, ps.SelectionType.ExtendSelection)


def select_layer(layer, type=None):
    left, top, right, bottom = layer.bounds

    app.activeDocument.selection.select(
        [[left, top], [right, top], [right, bottom], [left, bottom]], type
    )


# Get width and height of paragraph text box
def get_text_bounding_box(layer, text_width=None, text_height=None):
    if app.preferences.pointSize == 1:
        pref_scale = 72
    else:
        pref_scale = 72.27
    doc_res = app.activeDocument.resolution
    multiplier = (doc_res / pref_scale) ** 2
    if text_width is None:
        text_width = layer.textItem.width * multiplier
    else:
        layer.textItem.width = (text_width * doc_res) / (pref_scale * multiplier)
    if text_height is None:
        text_height = layer.textItem.height * multiplier
    else:
        layer.textItem.height = (text_height * doc_res) / (pref_scale * multiplier)
    return [text_width, text_height]


"""
HERE LIES ALL THE COMPLICATED BULLSHIT THAT MAKES LITTLE SENSE
"""

# define these because otherwise they take up so many characters
def cid(char):
    return app.charIDToTypeID(char)


def sid(string):
    return app.stringIDToTypeID(string)


# Selects the layer mask for editing
def layer_mask_select(layer):
    app.activeDocument.activeLayer = layer
    desc = ps.ActionDescriptor()
    ref = ps.ActionReference()
    chnl = cid("Chnl")
    ref.putEnumerated(chnl, chnl, cid("Msk "))
    desc.putReference(cid("null"), ref)
    desc.putBoolean(cid("MkVs"), True)
    app.executeAction(cid("slct"), desc, 3)
    return


# Magic Wand target layer at coordinate (X, Y)
def magic_wand_select(layer, x, y, style="set", t=0, a=True, c=True, s=False):
    """
    Magic Wand Select target layer at coordinates (x, y)
    @param layer ArtLayer: Layer to be sampled.
    @param x int: Pixels from left of document.
    @param y int: Pixels from top of document.
    @param style str:
        "set": Creates new selection.
        "addTo": Adds to existing selection.
        "subtractFrom": Subtracts from existing selection.
        "intersectWith": Intersects with existing selection.
    @param t int: Tolerance.
    @param a bool: Anti-aliasing.
    @param c bool: Contiguous.
    @param s bool: Sample all layers.
    @return: Selection.
    """
    select = sid(style)
    old_layer = app.activeDocument.activeLayer
    app.activeDocument.activeLayer = layer
    desc1 = ps.ActionDescriptor()
    desc2 = ps.ActionDescriptor()
    ref = ps.ActionReference()
    ref.putProperty(cid("Chnl"), cid("fsel"))
    desc1.putReference(cid("null"), ref)
    desc2.putUnitDouble(cid("Hrzn"), cid("#Pxl"), x)
    desc2.putUnitDouble(cid("Vrtc"), cid("#Pxl"), y)
    desc1.putObject(cid("T   "), cid("Pnt "), desc2)
    desc1.putInteger(cid("Tlrn"), t)  # Tolerance
    desc1.putBoolean(cid("AntA"), a)  # Anti-aliasing
    desc1.putBoolean(cid("Cntg"), c)  # Contiguous
    desc1.putBoolean(cid("Mrgd"), s)  # Sample all layers
    app.executeAction(select, desc1, 3)
    app.activeDocument.activeLayer = old_layer
    return app.activeDocument.selection


def select_blank_pixels(layer):
    old_layer = app.activeDocument.activeLayer
    app.activeDocument.activeLayer = layer
    dsc = ps.ActionDescriptor()
    ref1 = ps.ActionReference()
    ref2 = ps.ActionReference()
    chan = sid("channel")
    ref1.putProperty(chan, sid("selection"))
    dsc.putReference(sid("null"), ref1)
    ref2.putEnumerated(chan, chan, sid("transparencyEnum"))
    dsc.putReference(sid("to"), ref2)
    app.executeAction(sid("set"), dsc)
    app.activeDocument.activeLayer = old_layer
    return app.activeDocument.selection


def get_layer_index(layerID):
    ref = ps.ActionReference()
    ref.putIdentifier(cid("Lyr "), layerID)
    try:
        app.activeDocument.backgroundLayer
        return app.executeActionGet(ref).getInteger(cid("ItmI")) - 1
    except:
        return app.executeActionGet(ref).getInteger(cid("ItmI"))


def move_inside(fromlayer, layerset):
    fromID = int(fromlayer.id)
    toID = int(layerset.id)
    desc = ps.ActionDescriptor()
    ref1 = ps.ActionReference()
    ref2 = ps.ActionReference()
    ref1.putIdentifier(cid("Lyr "), fromID)
    desc.putReference(cid("null"), ref1)
    ref2.putIndex(cid("Lyr "), get_layer_index(toID))
    desc.putReference(cid("T   "), ref2)
    desc.putBoolean(cid("Adjs"), False)
    desc.putInteger(cid("Vrsn"), 5)
    try:
        app.executeAction(cid("move"), desc, 3)
    except Exception as err:
        return err


def add_layer(name=None):
    layer = app.activeDocument.activeLayer
    desc = ps.ActionDescriptor()
    ref = ps.ActionReference()
    ref.putClass(cid("Lyr "))
    desc.putReference(cid("null"), ref)
    desc.putInteger(cid("LyrI"), get_layer_index(layer.id))
    app.executeAction(cid("Mk  "), desc, 3)
    layer = app.activeDocument.activeLayer
    if name is not None:
        layer.name = name
    return layer


# equivalent of ctrl+shift+v
def paste_in_place():
    paste = ps.ActionDescriptor()
    paste.putBoolean(sid("inPlace"), True)
    paste.putEnumerated(cid("AntA"), cid("Antt"), cid("Anto"))
    app.executeAction(cid("past"), paste, 3)


# opens a pdf at a fixed max width/height
def pdf_open(file, size):
    """
    * Opens a pdf scaled to (height) pixels tall
    """
    open_desc = ps.ActionDescriptor()
    sett_desc = ps.ActionDescriptor()
    pxl = cid("#Pxl")
    sett_desc.putString(cid("Nm  "), "pdf")
    sett_desc.putEnumerated(cid("Crop"), sid("cropTo"), sid("boundingBox"))
    sett_desc.putUnitDouble(cid("Rslt"), cid("#Rsl"), 800.000000)
    sett_desc.putEnumerated(cid("Md  "), cid("ClrS"), cid("RGBC"))
    sett_desc.putInteger(cid("Dpth"), 8)
    sett_desc.putBoolean(cid("AntA"), True)
    sett_desc.putUnitDouble(cid("Wdth"), pxl, size)
    sett_desc.putUnitDouble(cid("Hght"), pxl, size)
    sett_desc.putBoolean(cid("CnsP"), True)
    sett_desc.putBoolean(sid("suppressWarnings"), True)
    sett_desc.putBoolean(cid("Rvrs"), True)
    sett_desc.putEnumerated(cid("fsel"), sid("pdfSelection"), sid("page"))
    sett_desc.putInteger(cid("PgNm"), 1)
    open_desc.putObject(cid("As  "), cid("PDFG"), sett_desc)
    open_desc.putPath(cid("null"), file)
    open_desc.putInteger(cid("DocI"), 727)
    app.executeAction(cid("Opn "), open_desc, 3)


def layer_styles_visible(layer, visible):
    if visible:
        show_hide = cid("Shw ")
    else:
        show_hide = cid("Hd  ")
    old_layer = app.activeDocument.activeLayer
    app.activeDocument.activeLayer = layer
    desc1 = ps.ActionDescriptor()
    list1 = ps.ActionList()
    ref1 = ps.ActionReference()
    ref1.putClass(cid("Lefx"))
    ref1.putEnumerated(cid("Lyr "), cid("Ordn"), cid("Trgt"))
    list1.putReference(ref1)
    desc1.putList(cid("null"), list1)
    app.executeAction(show_hide, desc1, 3)
    app.activeDocument.activeLayer = old_layer


# testing to set transform to bicubic auto instead of whatever was used last
# maybe set it up to change to nearest neighbor or something for certain resizing?
def zero_transform(layer, i="bicubicAutomatic", x=0, y=0, w=100, h=100):
    resample = {
        "bicubicSharper": sid("bicubicSharper"),
        "bicubicAutomatic": sid("bicubicAutomatic"),
        "nearestNeighbor": cid("Nrst"),
    }
    old_tool = app.currentTool
    app.currentTool = "moveTool"

    old_layer = app.activeDocument.activeLayer
    app.activeDocument.activeLayer = layer

    desc1 = ps.ActionDescriptor()
    desc2 = ps.ActionDescriptor()
    ref1 = ps.ActionReference()
    idPxl = cid("#Pxl")
    idPrc = cid("#Prc")
    ref1.putEnumerated(cid("Lyr "), cid("Ordn"), cid("Trgt"))
    desc1.putReference(cid("null"), ref1)
    desc1.putEnumerated(cid("FTcs"), cid("QCSt"), cid("Qcs0"))
    desc2.putUnitDouble(cid("Hrzn"), idPxl, x)
    desc2.putUnitDouble(cid("Vrtc"), idPxl, y)
    desc1.putObject(cid("Ofst"), cid("Ofst"), desc2)
    desc1.putUnitDouble(cid("Wdth"), idPrc, w)
    desc1.putUnitDouble(cid("Hght"), idPrc, h)
    desc1.putEnumerated(cid("Intr"), cid("Intp"), resample[i])
    app.executeAction(cid("Trnf"), desc1, 3)

    app.currentTool = old_tool
    app.activeDocument.activeLayer = old_layer
