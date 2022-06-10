"""
PRESHTILDEATH TOOLS
"""
import json
import math
import os
import os.path as path
import re

import photoshop.api as ps
import proxyshop.gui as gui
import proxyshop.helpers as psd
import requests
from proxyshop.settings import Config

import fpdf

console = gui.console_handler
app = ps.Application()


def get_layer(name: str, *group):
    """
    Retrieve layer object.
    """
    layer_set = app.activeDocument
    if group:
        layer_set = get_layer_set(*group)
    if isinstance(name, str):
        return layer_set.artLayers.getByName(name)
    return name


def get_layer_set(name: str, *group):
    """
    Retrieve layer group object.
    """
    layer_set = app.activeDocument
    if group:
        layer_set = get_layer_set(*group)
    if isinstance(name, str):
        return layer_set.layerSets.getByName(name)
    return name


def text_layer_bounds(layer) -> list:
    select_nonblank_pixels(layer)
    bounds = app.activeDocument.selection.bounds
    app.activeDocument.selection.deselect()
    return bounds


def text_layer_dimensions(layer) -> dict:
    bounds = text_layer_bounds(layer)
    return bounds_to_dimensions(bounds)


def get_selection_dimensions() -> dict:
    bounds = app.activeDocument.selection.bounds
    return bounds_to_dimensions(bounds)


def bounds_to_dimensions(bounds) -> dict:
    return {
        "width": bounds[2] - bounds[0],
        "height": bounds[3] - bounds[1],
    }


def is_inside(inner, outer) -> bool:
    return bool(
        inner[0] >= outer[0]
        and inner[1] >= outer[1]
        and inner[2] <= outer[2]
        and inner[3] <= outer[3]
    )


def is_outside(inner, outer) -> bool:
    return bool(
        inner[0] > outer[2]
        or inner[1] > outer[3]
        or inner[2] < outer[0]
        or inner[3] < outer[1]
    )


def is_layer_blank(layer):
    select_nonblank_pixels(layer)
    try:
        bounds = app.activeDocument.selection.bounds
        return True
    except:
        app.activeDocument.selection.deselect()
        return False

def pt_to_px(num):
    """Take given 'pt' amount and return distance in pixels for the active document."""
    doc = app.activeDocument
    pref_scale = 72 if app.preferences.pointSize == 1 else 72.27
    return num * (doc.resolution / pref_scale)


def scale_creature_text(layer, reference_layer, modifier):
    """
    * Resize a given text layer's contents (in 0.25 pt increments) until it fits inside a specified reference layer.
    * The resulting text layer will have equal font and lead sizes.
    """
    if reference_layer is None: return True
    text_item = layer.textItem
    starting_font_size = text_item.size
    font_size = starting_font_size
    step_size = 0.25
    scaled = False
    end = len(layer.textItem.contents)

    # Obtain proper spacing for this document size
    spacing = int((app.activeDocument.width/3264)*60)

    # Reduce the reference height by 64 pixels to avoid text landing on the top/bottom bevels
    ref_h = psd.get_layer_dimensions(reference_layer)['height']-spacing
    lyr_h = psd.get_layer_dimensions(layer)['height']

    # Initial nudge down to below typeline
    resize_text_array(layer, [0, 1], modifier, spacer=True)

    while ref_h < lyr_h:
        scaled = True
        new_step = font_size - (((ref_h / lyr_h) ** 0.4) * font_size)
        # step down font and lead sizes by the step size, and update those sizes in the layer
        font_size -= max(step_size, new_step)
        resize_text_array(layer, [1, end], size=font_size)
        lyr_h = psd.get_layer_dimensions(layer)['height']

    return scaled


def parent_dirs(file, depth=1):
    """Loop up through parent directories."""
    if depth >= 1:
        return path.dirname(parent_dirs(file, depth - 1))
    return file


def rgbcolor(r: int, g: int, b: int):
    """Return a SolidColor object with given decimal values."""
    color = ps.SolidColor()
    color.rgb.red = r
    color.rgb.green = g
    color.rgb.blue = b
    return color


def get_expansion(layer, rarity: str, ref_layer, set_code: str):
    """Pastes the given SVG into the specified layer."""

    # Start nice and clean
    white = rgbcolor(255, 255, 255)
    doc = app.activeDocument
    prev_active_layer = doc.activeLayer
    doc.activeLayer = layer
    set_code = set_code.upper()

    # Check if the SVG exists as named and return that if it does.
    svg_folder = path.join(parent_dirs(__file__), "assets", "Set Symbols")
    if not path.exists(svg_folder):
        os.mkdir(svg_folder)
    test_svg = path.join(svg_folder, f"{set_code}.svg")
    if path.exists(test_svg):
        return test_svg

    # Open up our JSON file if it exists.
    set_path = path.join(svg_folder, "set_svg.json")
    if path.exists(set_path):
        with open(set_path, "r") as set_fp:
            set_json = json.load(set_fp)
    else:
        set_json = {}

    # Iterate JSON looking for a match.
    key = [k for k, v in set_json.items() if set_code in v]
    if key:
        key = key[0]
        svg_uri = (
            f"https://c2.scryfall.com/file/scryfall-symbols/sets/{key.lower()}.svg"
        )
    else:
        scry_json = requests.get(f"https://api.scryfall.com/sets/{set_code.lower()}", timeout=5).json()
        svg_uri = scry_json["icon_svg_uri"]
        key = path.splitext(path.basename(svg_uri))[0].upper()
        print(key, set_code, svg_uri)
        if key == "CON":
            key = "CONFLUX"
        set_json[key] = set_json[key] + [set_code] if key in set_json.keys() else [set_code]

    # Look for our local SVG, or fetch the SVG from Scryfall.
    svg_path = path.join(svg_folder, f"{key}.svg")
    if not path.exists(svg_path):
        scry_svg = requests.get(svg_uri, timeout=5).content
        # Fix path data for photoshop
        for arc in re.findall(r"a[^ZzLlHhVvCcSsQqTtAa]+", svgstring):
            arc_after = arc
            for a_arg in re.findall(r"\S+\s\S+\s\S+\s[01][01]", arc):
                arc_after = arc_after.replace(a_arg, a_arg[:-1]+" "+a_arg[-1:]+" ")
            svgstring = svgstring.replace(arc, arc_after)
        with open(svg_path, "wb") as svg_file:
            svg_file.write(scry_svg)

    # Format our JSON for readability, keeping the values one line.
    with open(set_path, "w") as file:
        file.write(
            json.dumps(set_json)
            .replace("{", "{\n\t")
            .replace("], ", "],\n\t")
            .replace("]}", "]\n}")
        )

    # Try opening our SVG and if it is blank, convert to PDF then open that
    max_size = (ref_layer.bounds[2] - ref_layer.bounds[0]) * 2
    set_doc = svg_open(svg_path, max_size)
    if not is_layer_blank(set_doc.artLayers[0]):
        set_doc.close(ps.SaveOptions.DoNotSaveChanges)
        set_doc = pdf_open(svg_path, max_size)
    set_doc.selection.selectAll()
    set_doc.selection.copy()
    set_doc.close(ps.SaveOptions.DoNotSaveChanges)

    # Note context switch back to template.
    layer = doc.paste()
    zero_transform(layer)

    lay_dim = psd.get_layer_dimensions(layer)
    ref_dim = psd.get_layer_dimensions(ref_layer)

    # Determine how much to scale the layer by such that it fits into the reference layer's bounds.
    scale_factor = 100 * min(
        ref_dim["width"] / lay_dim["width"],
        ref_dim["height"] / lay_dim["height"]
    )
    layer.resize(scale_factor, scale_factor)

    # Align verticle center, horizontal right.
    psd.select_layer_pixels(ref_layer)
    psd.align_vertical()
    doc.selection.deselect()
    layer.translate(ref_layer.bounds[2] - layer.bounds[2], 0)

    fill_expansion_symbol(layer, white)

    # Apply rarity mask if necessary, and center it on symbol.
    if rarity != "common":
        mask_layer = get_layer(rarity, "Expansion")
        doc.activeLayer = mask_layer
        psd.select_layer_pixels(layer)
        psd.align_horizontal()
        psd.align_vertical()
        psd.clear_selection()
        mask_layer.visible = True

    doc.activeLayer = prev_active_layer
    return layer


# Resize layer to reference, center vertically, and line it up with the right bound
def frame_expansion_symbol(layer, reference_layer):

    lay_dim = psd.get_layer_dimensions(layer)
    ref_dim = psd.get_layer_dimensions(reference_layer)

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
    magic_wand_select(ref, x, y, "setd", 0, True, False)
    magic_wand_select(ref, x, y, "SbtF", 0, True)

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
    file_name, extension = path.splitext(path.basename(file))  # image, .xxx
    test_name = path.join(send_path, f"{file_name}{extension}")
    if path.exists(test_name):  # location/image.xxx
        multi = 1
        test_name = path.join(send_path, f"{file_name} ({multi}){extension}")
        while path.exists(test_name):  # location/image (1).xxx
            multi += 1
            test_name = path.join(send_path, f"{file_name} ({multi}){extension}")
    return test_name  #  returns "location/image.xxx" or "location/image (x).xxx"


# Gives an estimated number of lines at default text size
def dirty_text_scale(input_text, chars_in_line):
    input_text = re.sub("\{.*?\}", "X", input_text)
    line_count = math.ceil(input_text.count("\n") * 0.5)
    for paragraph in input_text.split("\n"):
        line_count += 1
        start, end = 0, 1
        words = paragraph.split()
        while end < len(words):
            line = " ".join(words[start:end])
            if len(line) >= chars_in_line:
                line_count += 1
                start = end
            end += 1
    console.update(f"{line_count} lines calculated.")
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
    top = get_layer(color_pair[-2], layers)
    bottom = get_layer(color_pair[-1], layers)
    top.moveBefore(bottom)
    app.activeDocument.activeLayer = top
    psd.enable_active_layer_mask()
    top.visible = True
    bottom.visible = True


def add_select_layer(layer):
    """"
    Adds to current Selection using the boundary of a layer.
    """
    select_layer(layer, ps.SelectionType.ExtendSelection)


def select_layer(layer, type=None):
    """"
    Creates a Selection using the boundary of a layer.
    """
    if type is None:
        type = ps.SelectionType.ReplaceSelection
    left, top, right, bottom = layer.bounds

    app.activeDocument.selection.select(
        [[left, top], [right, top], [right, bottom], [left, bottom]], type
    )


# Get width and height of paragraph text box
def get_text_bounding_box(layer, text_width=None, text_height=None):
    pref_scale = 72 if app.preferences.pointSize == 1 else 72.27
    scale = app.activeDocument.resolution / pref_scale
    multiplier = scale ** 2
    if text_width is None:
        text_width = layer.textItem.width * multiplier
    else:
        layer.textItem.width = text_width / scale
    if text_height is None:
        text_height = layer.textItem.height * multiplier
    else:
        layer.textItem.height = text_height / scale
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
def magic_wand_select(layer, x, y, style="setd", t=0, a=True, c=True, s=False):
    """
    Magic Wand Select target layer at coordinates (x, y)
    @param layer ArtLayer: Layer to be sampled.
    @param x int: Pixels from left of document.
    @param y int: Pixels from top of document.
    @param style str: Defaults to new selection.
        "setd": Creates new selection.
        "AddT": Adds to existing selection.
        "SbtF": Subtracts from existing selection.
        "IntW": Intersects with existing selection.
    @param t int: Tolerance.
    @param a bool: Anti-aliasing.
    @param c bool: Contiguous.
    @param s bool: Sample all layers.
    @return: Selection.
    """
    select = cid(style)
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


def select_nonblank_pixels(layer, style="setd"):
    """
    Returns a Selection around any non-blank pixels in target ArtLayer.
    @param layer: Layer to target for selection.
    @param style str: Defaults to new selection.
        "setd": Creates new selection.
        "Add ": Adds to existing selection.
        "Sbtr": Subtracts from existing selection.
        "Intr": Intersects with existing selection.
    """
    select = cid(style)
    old_layer = app.activeDocument.activeLayer
    app.activeDocument.activeLayer = layer
    dsc = ps.ActionDescriptor()
    ref_selection = ps.ActionReference()
    ref_trans_enum = ps.ActionReference()
    chan = cid("Chnl")
    ref_selection.putProperty(chan, cid("fsel"))
    ref_trans_enum.putEnumerated(chan, chan, cid("Trsp"))
    if style == "setd":
        dsc.putReference(cid("null"), ref_selection)
        dsc.putReference(cid("T   "), ref_trans_enum)
    else:
        if style == "Add ":
            point = cid("T   ")
        elif style == "Sbtr":
            point = cid("From")
        elif style == "Intr":
            point = cid("With")
        dsc.putReference(point, ref_selection)
        dsc.putReference(cid("null"), ref_trans_enum)
    app.executeAction(select, dsc, 3)
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


def svg_open(file, size):
    """
    * Opens a SVG scaled to (height) pixels tall
    """
    sett_desc = ps.ActionDescriptor()
    sett_desc.putUnitDouble(cid("Hght"), cid("#Pxl"), size)
    sett_desc.putUnitDouble(cid("Rslt"), cid("#Rsl"), 800.000000)
    sett_desc.putBoolean(cid("CnsP"), True)
    sett_desc.putEnumerated(cid("Md  "), cid("ClrS"), cid("Grys"))
    sett_desc.putBoolean(cid("AntA"), True)
    
    open_desc = ps.ActionDescriptor()
    open_desc.putPath(cid("null"), file)
    open_desc.putObject(cid("As  "), sid("svgFormat"), sett_desc)
    app.executeAction(cid("Opn "), open_desc, 3)
    return app.activeDocument


def pdf_open(svg_path, size):
    """
    Converts then opens a pdf scaled to (height) pixels tall
    """
    pdf_name = path.splitext(path.basename(svg_path))[0]+".pdf"
    pdf_path = path.join(path.dirname(svg_path), pdf_name)
    print(pdf_path)
    if path.exists(pdf_path):
        return pdf_path
    svg = fpdf.svg.SVGObject.from_file(svg_path)
    print(svg.viewbox)
    width = svg.viewbox[2] - svg.viewbox[0]
    height = svg.viewbox[3] - svg.viewbox[1]
    print(width, height)
    pdf = fpdf.FPDF(unit="pt", format=(width, height))
    pdf.add_page()
    pdf.output(pdf_path)

    sett_desc = ps.ActionDescriptor()
    sett_desc.putString(cid("Nm  "), "pdf")
    sett_desc.putEnumerated(cid("Crop"), sid("cropTo"), sid("boundingBox"))
    sett_desc.putUnitDouble(cid("Rslt"), cid("#Rsl"), 800.000000)
    sett_desc.putEnumerated(cid("Md  "), cid("ClrS"), cid("Grys"))
    sett_desc.putInteger(cid("Dpth"), 8)
    sett_desc.putBoolean(cid("AntA"), True)
    sett_desc.putUnitDouble(cid("Hght"), cid("#Pxl"), size)
    sett_desc.putBoolean(cid("CnsP"), True)
    sett_desc.putBoolean(sid("suppressWarnings"), True)
    sett_desc.putBoolean(cid("Rvrs"), True)
    sett_desc.putEnumerated(cid("fsel"), sid("pdfSelection"), sid("page"))
    sett_desc.putInteger(cid("PgNm"), 1)
    open_desc = ps.ActionDescriptor()
    open_desc.putObject(cid("As  "), cid("PDFG"), sett_desc)
    open_desc.putPath(cid("null"), pdf_path)
    app.executeAction(cid("Opn "), open_desc, 3)
    return app.activeDocument


def layer_styles_visible(layer, visible):
    show_hide = cid("Shw ") if visible else cid("Hd  ")
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
    

def zero_transform(layer, resample="bicubicAutomatic", x=0, y=0, w=100, h=100):
    """
    Free Transform a layer.
    layer: The layer to be transformed.
    resample: StringID of the resample method.
        * bicubicAutomatic
        * bicubicSharper
        * bicubicSmoother
        * bilinear
        * nearestNeighbor
        
    x: Delta translate along x-axis.
    y: Delta translate along y-axis.
    w: Stretch percentage on width.
    y: Stretch percentage on height.

    """
    style = sid(resample)
    old_tool = app.currentTool
    old_layer = app.activeDocument.activeLayer
    app.activeDocument.activeLayer = layer
    app.currentTool = "moveTool"

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
    desc1.putEnumerated(cid("Intr"), cid("Intp"), style)
    app.executeAction(cid("Trnf"), desc1, 3)

    app.currentTool = old_tool
    app.activeDocument.activeLayer = old_layer


def resize_text_array(layer, range: list, y_delta=0, size=None, oldsize=None, spacer=False):
    oldsize = oldsize if oldsize else layer.textItem.size
    after_size = (y_delta * 0.118) + oldsize if not size else size
    layer.textItem.contents = " " + layer.textItem.contents.strip()
    old_layer = app.activeDocument.activeLayer
    app.activeDocument.activeLayer = layer

    ref1 = ps.ActionReference()
    ref1.putEnumerated(cid("TxLr"), cid("Ordn"), cid("Trgt"))

    dsc4 = ps.ActionDescriptor()
    dsc4.putUnitDouble(cid("Sz  "), cid("#Pnt"), after_size)
    dsc4.putUnitDouble(sid("impliedFontSize"), cid("#Pnt"), after_size)
    if spacer: dsc4.putDouble(cid("HrzS"), 0)
    
    dsc3 = ps.ActionDescriptor()
    dsc3.putInteger(cid("From"), range[0])
    dsc3.putInteger(cid("T   "), range[1])
    dsc3.putObject(cid("TxtS"), cid("TxtS"), dsc4)

    lst1 = ps.ActionList()
    lst1.putObject(cid("Txtt"), dsc3)

    dsc2 = ps.ActionDescriptor()
    dsc2.putList(cid("Txtt"), lst1)

    dsc1 = ps.ActionDescriptor()
    dsc1.putReference(cid("null"), ref1)
    dsc1.putObject(cid("T   "), cid("TxLr"), dsc2)

    app.executeAction(cid("setd"), dsc1, 3)

    app.activeDocument.activeLayer = old_layer


cfg_path = path.join(path.dirname(__file__), "config.ini")
class MyConfig(Config):
    def __init__(self, conf=cfg_path):
        super().__init__(conf)

    def load(self):
        self.move_art = self.file.getboolean("GENERAL", "Move.Art")
        self.side_pins = self.file.getboolean("FULLART", "Side.Pinlines")
        self.hollow_mana = self.file.getboolean("FULLART", "Hollow.Mana")
        self.crt_filter = self.file.getboolean("PIXEL", "CRT.Filter")
        self.invert_mana = self.file.getboolean("PIXEL", "Invert.Mana")
        self.symbol_bg = self.file.getboolean("PIXEL", "Symbol.BG")

    def update(self):
        self.file.set("GENERAL", "Move.Art", str(self.move_art))
        self.file.set("FULLART", "Side.Pinelines", str(self.side_pins))
        self.file.set("FULLART", "Hollow.Mana", str(self.hollow_mana))
        self.file.set("PIXEL", "CRT.Filter", str(self.crt_filter))
        self.file.set("PIXEL", "Invert.Mana", str(self.invert_mana))
        self.file.set("PIXEL", "Symbol.BG", str(self.symbol_bg))
        with open("config.ini", "w", encoding="utf-8") as ini:
            self.file.write(ini)
presh_config = MyConfig(cfg_path)
presh_config.load()