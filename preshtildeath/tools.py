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

console = gui.console_handler
app = ps.Application()
cid = app.charIDToTypeID
sid = app.stringIDToTypeID


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


def rgbcolor(r: int, g: int, b: int):
    """Return a SolidColor object with given decimal values."""
    color = ps.SolidColor()
    color.rgb.red = r
    color.rgb.green = g
    color.rgb.blue = b
    return color


def get_expansion(layer, rarity: str, ref_layer, set_code: str):
    """Find and open the set symbol SVG and pop it into our document."""

    # Start nice and clean
    white = rgbcolor(255, 255, 255)
    doc = app.activeDocument
    prev_active_layer = doc.activeLayer
    doc.activeLayer = layer
    set_code = set_code.upper()
    svg_folder = path.join(path.dirname(__file__), "assets", "Set Symbols")
    if not path.exists(svg_folder):
        os.mkdir(svg_folder)

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
        if key == "CON":
            key = "CONFLUX"
        set_json[key] = set_json[key] + [set_code] if key in set_json.keys() else [set_code]

    # Look for our local SVG, or fetch the SVG from Scryfall.
    svg_path = path.join(svg_folder, f"{key}.svg")
    if not path.exists(svg_path):
        scry_svg = requests.get(svg_uri, timeout=5).text
        """
        Fix path data for photoshop.
        This needs a lot of massaging.
        """
        front = r"(\s?-?((\d+(\.\d+)?)|(\.\d+)))((,|\s)?(-?((\d+(\.\d+)?)|(\.\d+)))){2}(,|\s)+"
        back = r"[01](,|\s)?[01](,|\s)?((,|\s)?(-?((\d+(\.\d+)?)|(\.\d+)))){2}"
        full = rf"a({front}{back})+"
        for arc in re.finditer(full, scry_svg):
            for arc_args in re.finditer(front+back, arc.group()):
                astr = arc_args.group()
                for arg in re.finditer(front, arc_args.group()):
                    f = arg.span()[1]+1
                    scry_svg = scry_svg.replace(astr, astr[:f]+" "+astr[f:f+1]+" "+astr[f+1:])
        scry_svg = re.sub(r"\s+", " ", scry_svg)
        # Save our fixed file
        with open(svg_path, "w") as svg_file:
            svg_file.write(scry_svg)

    # Format our JSON for readability, keeping the values one line.
    with open(set_path, "w") as file:
        file.write(
            json.dumps(set_json)
            .replace("{", "{\n\t")
            .replace("], ", "],\n\t")
            .replace("]}", "]\n}")
        )

    # Open our SVG at twice the size of our reference layer height, just to be safe.
    max_size = (ref_layer.bounds[2] - ref_layer.bounds[0]) * 2
    set_doc = svg_open(svg_path, max_size)
    set_doc.selection.selectAll()
    set_doc.selection.copy()
    set_doc.close(ps.SaveOptions.DoNotSaveChanges)

    # Note context switch back to template.
    layer = doc.paste()
    zero_transform(layer)

    lay_dim = psd.get_dimensions_no_effects(layer)
    ref_dim = psd.get_dimensions_no_effects(ref_layer)

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


def fill_expansion_symbol(ref, stroke_color):
    """Give the symbol a background for open space symbols (i.e. M10)."""
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


def filename_append(file, send_path):
    """Check if a file already exists, then adds (x) if it does."""
    file_name, extension = path.splitext(path.basename(file))  # image, .xxx
    test_name = path.join(send_path, f"{file_name}{extension}")
    if path.exists(test_name):  # location/image.xxx
        multi = 1
        test_name = path.join(send_path, f"{file_name} ({multi}){extension}")
        while path.exists(test_name):  # location/image (1).xxx
            multi += 1
            test_name = path.join(send_path, f"{file_name} ({multi}){extension}")
    return test_name  #  returns "location/image.xxx" or "location/image (x).xxx"


def dirty_text_scale(input_text, chars_in_line):
    """Gives an estimated number of lines at default text size."""
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
    console.update(f"{line_count} oracle lines calculated.")
    return line_count


def layer_vert_stretch(layer, modifier, anchor="bottom", method="nearestNeighbor"):
    """Stretches a layer by (-modifier) pixels."""
    transform_delta = {"top": 0, "center": modifier / 2, "bottom": modifier}
    # anchor_set = { 'top': 1, 'center': 4, 'bottom': 7 }
    height = layer.bounds[3] - layer.bounds[1]
    h_perc = (height - modifier) / height * 100
    zero_transform(layer, method, 0, transform_delta[anchor], 100, h_perc)
    # layer.resize(100, h_perc, anchor_set[anchor])


def wubrg_layer_sort(color_pair, layers):
    """Rearranges two color layers in order and applies mask."""
    top = get_layer(color_pair[-2], layers)
    bottom = get_layer(color_pair[-1], layers)
    top.moveBefore(bottom)
    app.activeDocument.activeLayer = top
    psd.enable_active_layer_mask()
    top.visible = True
    bottom.visible = True


def add_select_layer(layer):
    """"Adds to current Selection using the boundary of a layer."""
    select_layer(layer, ps.SelectionType.ExtendSelection)


def select_layer(layer, type=None):
    """Creates a Selection using the boundary of a layer."""
    if type is None:
        type = ps.SelectionType.ReplaceSelection
    left, top, right, bottom = layer.bounds

    app.activeDocument.selection.select(
        [[left, top], [right, top], [right, bottom], [left, bottom]], type
    )


def get_text_bounding_box(layer, text_width=None, text_height=None):
    """Get width and height of paragraph text box."""
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


def layer_mask_select(layer):
    """Selects the layer mask for editing."""
    app.activeDocument.activeLayer = layer
    desc = ps.ActionDescriptor()
    ref = ps.ActionReference()
    chnl = cid("Chnl")
    ref.putEnumerated(chnl, chnl, cid("Msk "))
    desc.putReference(cid("null"), ref)
    desc.putBoolean(cid("MkVs"), True)
    app.executeAction(cid("slct"), desc, 3)
    return


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


def paste_in_place():
    """Equivalent of Ctrl+Shift+V."""
    paste = ps.ActionDescriptor()
    paste.putBoolean(sid("inPlace"), True)
    paste.putEnumerated(cid("AntA"), cid("Antt"), cid("Anto"))
    app.executeAction(cid("past"), paste, 3)


def svg_open(file: os.PathLike, height: int):
    """
    Opens a SVG scaled to (height) pixels tall
    """
    sett_desc = ps.ActionDescriptor()
    sett_desc.putUnitDouble(cid("Hght"), cid("#Pxl"), height)
    sett_desc.putUnitDouble(cid("Rslt"), cid("#Rsl"), 800.000000)
    sett_desc.putBoolean(cid("CnsP"), True)
    sett_desc.putEnumerated(cid("Md  "), cid("ClrS"), cid("Grys"))
    sett_desc.putBoolean(cid("AntA"), True)
    
    open_desc = ps.ActionDescriptor()
    open_desc.putPath(cid("null"), file)
    open_desc.putObject(cid("As  "), sid("svgFormat"), sett_desc)
    app.executeAction(cid("Opn "), open_desc, 3)
    return app.activeDocument


def layer_styles_visible(layer, visible):
    show_hide = cid("Shw ") if visible else cid("Hd  ")
    old_layer = app.activeDocument.activeLayer
    app.activeDocument.activeLayer = layer
    ref1 = ps.ActionReference()
    ref1.putClass(cid("Lefx"))
    ref1.putEnumerated(cid("Lyr "), cid("Ordn"), cid("Trgt"))
    list1 = ps.ActionList()
    list1.putReference(ref1)
    desc1 = ps.ActionDescriptor()
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
    ref1.putEnumerated(cid("Lyr "), cid("Ordn"), cid("Trgt"))
    desc1.putReference(cid("null"), ref1)
    desc1.putEnumerated(cid("FTcs"), cid("QCSt"), cid("Qcs0"))
    desc2.putUnitDouble(cid("Hrzn"), cid("#Pxl"), x)
    desc2.putUnitDouble(cid("Vrtc"), cid("#Pxl"), y)
    desc1.putObject(cid("Ofst"), cid("Ofst"), desc2)
    desc1.putUnitDouble(cid("Wdth"), cid("#Prc"), w)
    desc1.putUnitDouble(cid("Hght"), cid("#Prc"), h)
    desc1.putEnumerated(cid("Intr"), cid("Intp"), style)
    app.executeAction(cid("Trnf"), desc1, 3)

    app.currentTool = old_tool
    app.activeDocument.activeLayer = old_layer

def creature_text_path_shift(layer, modifier):
    old_layer = app.activeDocument.activeLayer
    app.activeDocument.activeLayer = layer
    top = layer.textItem.position[1]
    new_top = round(top+modifier)

    desc347 = ps.ActionDescriptor()
    ref50 = ps.ActionReference()
    ref50.putEnumerated(cid("TxLr"), cid("Ordn"), cid("Trgt") )
    desc347.putReference(cid("null"), ref50)
    desc348 = ps.ActionDescriptor()
    list18 = ps.ActionList()
    desc352 = ps.ActionDescriptor()
    desc353 = ps.ActionDescriptor()
    list19 = ps.ActionList()
    desc354 = ps.ActionDescriptor()
    desc354.putEnumerated(sid("shapeOperation"), sid("shapeOperation"), sid("xor") )
    list20 = ps.ActionList()
    desc355 = ps.ActionDescriptor()
    desc355.putBoolean(cid("Clsp"), True)
    list21 = ps.ActionList()

    desc356 = ps.ActionDescriptor()
    desc357 = ps.ActionDescriptor()
    desc357.putUnitDouble(cid("Hrzn"), cid("#Pxl"), 269.000000)
    desc357.putUnitDouble(cid("Vrtc"), cid("#Pxl"), new_top)
    desc356.putObject(cid("Anch"), cid("Pnt "), desc357)
    list21.putObject(cid("Pthp"), desc356)

    desc358 = ps.ActionDescriptor()
    desc359 = ps.ActionDescriptor()
    desc359.putUnitDouble(cid("Hrzn"), cid("#Pxl"), 1907)
    desc359.putUnitDouble(cid("Vrtc"), cid("#Pxl"), new_top)
    desc358.putObject(cid("Anch"), cid("Pnt "), desc359)
    list21.putObject(cid("Pthp"), desc358)

    desc360 = ps.ActionDescriptor()
    desc361 = ps.ActionDescriptor()
    desc361.putUnitDouble(cid("Hrzn"), cid("#Pxl"), 1907)
    desc361.putUnitDouble(cid("Vrtc"), cid("#Pxl"), 2595)
    desc360.putObject(cid("Anch"), cid("Pnt "), desc361)
    list21.putObject(cid("Pthp"), desc360)

    desc362 = ps.ActionDescriptor()
    desc363 = ps.ActionDescriptor()
    desc363.putUnitDouble(cid("Hrzn"), cid("#Pxl"), 1648)
    desc363.putUnitDouble(cid("Vrtc"), cid("#Pxl"), 2595)
    desc362.putObject(cid("Anch"), cid("Pnt "), desc363)
    desc364 = ps.ActionDescriptor()
    desc364.putUnitDouble(cid("Hrzn"), cid("#Pxl"), 1648)
    desc364.putUnitDouble(cid("Vrtc"), cid("#Pxl"), 2595)
    desc362.putObject(cid("Fwd "), cid("Pnt "), desc364)
    desc365 = ps.ActionDescriptor()
    desc365.putUnitDouble(cid("Hrzn"), cid("#Pxl"), 1907)
    desc365.putUnitDouble(cid("Vrtc"), cid("#Pxl"), 2595)
    desc362.putObject(cid("Bwd "), cid("Pnt "), desc365)
    desc362.putBoolean(cid("Smoo"), False)
    list21.putObject(cid("Pthp"), desc362)

    desc366 = ps.ActionDescriptor()
    desc367 = ps.ActionDescriptor()
    desc367.putUnitDouble(cid("Hrzn"), cid("#Pxl"), 1618)
    desc367.putUnitDouble(cid("Vrtc"), cid("#Pxl"), 2697.5)
    desc366.putObject(cid("Anch"), cid("Pnt "), desc367)
    desc368 = ps.ActionDescriptor()
    desc368.putUnitDouble(cid("Hrzn"), cid("#Pxl"), 1618)
    desc368.putUnitDouble(cid("Vrtc"), cid("#Pxl"), 2780)
    desc366.putObject(cid("Fwd "), cid("Pnt "), desc368)
    desc369 = ps.ActionDescriptor()
    desc369.putUnitDouble(cid("Hrzn"), cid("#Pxl"), 1618)
    desc369.putUnitDouble(cid("Vrtc"), cid("#Pxl"), 2615)
    desc366.putObject(cid("Bwd "), cid("Pnt "), desc369)
    desc366.putBoolean(cid("Smoo"), True)
    list21.putObject(cid("Pthp"), desc366)
    
    desc370 = ps.ActionDescriptor()
    desc371 = ps.ActionDescriptor()
    desc371.putUnitDouble(cid("Hrzn"), cid("#Pxl"), 1618)
    desc371.putUnitDouble(cid("Vrtc"), cid("#Pxl"), 3338)
    desc370.putObject(cid("Anch"), cid("Pnt "), desc371)
    list21.putObject(cid("Pthp"), desc370)

    desc372 = ps.ActionDescriptor()
    desc373 = ps.ActionDescriptor()
    desc373.putUnitDouble(cid("Hrzn"), cid("#Pxl"), 269)
    desc373.putUnitDouble(cid("Vrtc"), cid("#Pxl"), 3338)
    desc372.putObject(cid("Anch"), cid("Pnt "), desc373)
    list21.putObject(cid("Pthp"), desc372)

    desc355.putList(cid("Pts "), list21)
    list20.putObject(cid("Sbpl"), desc355)
    desc354.putList(cid("SbpL"), list20)
    list19.putObject(cid("PaCm"), desc354)
    desc353.putList(sid("pathComponents"), list19)
    desc352.putObject(cid("Path"), sid("pathClass"), desc353)
    desc352.putEnumerated(cid("TEXT"), cid("TEXT"), sid("box") )
    desc374 = ps.ActionDescriptor()
    desc374.putDouble(sid("tx"), -269)
    desc374.putDouble(sid("ty"), -new_top)
    desc352.putObject(cid("Trnf"), cid("Trnf"), desc374)
    list18.putObject(sid("textShape"), desc352)
    desc348.putList(sid("textShape"), list18)
    desc347.putObject(cid("T   "), cid("TxLr"), desc348)
    app.executeAction(cid("setd"), desc347, ps.DialogModes.DisplayNoDialogs)
    layer.translate(0, modifier)

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