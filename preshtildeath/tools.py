"""
PRESHTILDEATH TOOLS
"""
import os
import re
import json
import math
import requests
import os.path as path
import photoshop.api as ps
import proxyshop.helpers as psd
from proxyshop.settings import Config
from proxyshop import gui

console = gui.console_handler
app = ps.Application()

try:
    from reportlab.graphics import renderPDF
    from svglib.svglib import svg2rlg
except Exception as e:
    console.log_error(e)


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
    return {
        "width": bounds[2] - bounds[0],
        "height": bounds[3] - bounds[1],
    }


def get_selection_dimensions() -> dict:
    bounds = app.activeDocument.selection.bounds
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


def scale_text_to_fit_reference(layer, reference_layer):
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

    # Obtain proper spacing for this document size
    spacing = int((app.activeDocument.width/3264)*60)

    # Reduce the reference height by 64 pixels to avoid text landing on the top/bottom bevels
    ref_h = psd.compute_layer_dimensions(reference_layer)['height']-spacing
    lyr_h = text_layer_dimensions(layer)['height']

    while ref_h < lyr_h:
        scaled = True
        new_step = font_size - (((ref_h / lyr_h) ** 0.4) * font_size)
        # step down font and lead sizes by the step size, and update those sizes in the layer
        font_size -= max(step_size, new_step)
        text_item.size = font_size
        lyr_h = text_layer_dimensions(layer)['height']

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


def get_expansion(layer, rarity: str, ref_layer, set_pdf: str):
    """Pastes the given PDF into the specified layer."""

    # Start nice and clean
    white = rgbcolor(255, 255, 255)
    doc = app.activeDocument
    prev_active_layer = doc.activeLayer
    doc.activeLayer = layer

    # Open PDF twice as big as reference just in case, since we don't know the PDF dimensions
    max_size = (ref_layer.bounds[2] - ref_layer.bounds[0]) * 2
    pdf_open(set_pdf, max_size)

    # Note context switch to art file.
    app.activeDocument.selection.selectAll()
    app.activeDocument.selection.copy()
    app.activeDocument.close(ps.SaveOptions.DoNotSaveChanges)

    # Note context switch back to template.
    layer = doc.paste()
    zero_transform(layer)

    lay_dim = psd.compute_layer_dimensions(layer)
    ref_dim = psd.compute_layer_dimensions(ref_layer)

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
        mask_layer = get_layer(rarity, layer.parent)
        doc.activeLayer = mask_layer
        psd.select_layer_pixels(layer)
        psd.align_horizontal()
        psd.align_vertical()
        psd.clear_selection()
        mask_layer.visible = True

    doc.activeLayer = prev_active_layer
    return layer


def get_set_pdf(code):
    """Grab the pdf file from our database."""

    # Check if the pdf exists as named and return that if it does
    pdf_folder = path.join(parent_dirs(__file__), "assets", "Set Symbol PDF")
    if not path.exists(pdf_folder):
        os.mkdir(pdf_folder)
    pdf = path.join(pdf_folder, f"{code}.pdf")
    if path.exists(pdf):
        return pdf

    # Open up our JSON file if it exists
    set_pdf_json = path.join(pdf_folder, "set_pdf.json")
    if path.exists(set_pdf_json):
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
        svg_uri = (
            f"https://c2.scryfall.com/file/scryfall-symbols/sets/{key.lower()}.svg"
        )

    # Look for our PDF, or fetch the SVG from Scryfall and convert
    pdf = path.join(pdf_folder, f"{key}.pdf")
    if not path.exists(pdf):
        pdf_fetch(pdf_folder, key, svg_uri)

    # Format our JSON for readability, keeping the values one line
    with open(set_pdf_json, "w") as file:
        file.write(
            json.dumps(set_json)
            .replace("{", "{\n\t")
            .replace("], ", "],\n\t")
            .replace("]}", "]\n}")
        )
        
    return pdf


# Take a set code and return the corresponding image name
def scry_scrape(code):
    code = code.lower()
    set_json = requests.get(f"https://api.scryfall.com/sets/{code}", timeout=1).json()
    name = path.splitext(path.basename(set_json["icon_svg_uri"]))[
        0
    ].upper()  # Grab the SVG name
    if name == "CON":
        name = "CONFLUX"  # Turns out you can't make a file named CON
    svg_uri = set_json["icon_svg_uri"]
    return [name, svg_uri]


# Take the image name and download from scryfall, then convert to pdf
def pdf_fetch(folder, code, svg_uri):
    file = path.join(folder, f"{code.lower()}.pdf")
    temp_svg = path.join(os.getcwd(), "temp_svg.svg")
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
    @param style str: Defaults to new selection.
        "setd": Creates new selection.
        "AddT": Adds to existing selection.
        "SbtF": Subtracts from existing selection.
        "IntW": Intersects with existing selection.
    """
    select = cid(style)
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