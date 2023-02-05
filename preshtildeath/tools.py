"""
PRESHTILDEATH TOOLS
"""
import json
import math
import os
import os.path as path
import re

import photoshop.api as ps
from photoshop.api._artlayer import ArtLayer
from photoshop.api._layerSet import LayerSet
from photoshop.api._document import Document
import proxyshop.helpers as psd
import requests
from proxyshop.settings import Config

app = ps.Application()
cid = app.charIDToTypeID
sid = app.stringIDToTypeID

def get_layer(name: str, *args: str|LayerSet, **kwargs: Document) -> ArtLayer:
    """
    Retrieve layer object.
    name: The name of the layer to be found.
    args: Any number of layer group names, or a LayerSet.
    kwargs:
        doc: The parent document. If not provided, defaults to activeDocument.
    """
    doc = kwargs.get("doc", app.activeDocument)
    layer_set = get_layer_set(*args, doc=doc) if args else doc
    try:
        return layer_set.artLayers.getByName(name)
    except Exception as e:
        print(e)


def get_layer_set(name: str|LayerSet, *args: str|LayerSet, **kwargs: Document) -> LayerSet:
    """
    Retrieve layer group object.
    name: The name of the layer group to be found.
    args: Any number of layer group names, or a LayerSet.
    kwargs:
        doc: The parent document. If not provided, defaults to activeDocument.
    """
    if isinstance(name, LayerSet):
        return name
    doc = kwargs.get("doc", app.activeDocument)
    layer_set = get_layer_set(*args, doc=doc) if args else doc
    try:
        return layer_set.layerSets.getByName(name)
    except Exception as e:
        print(e)


def selection_exists(selection):
    try:
        selection.bounds
        return True
    except:
        return False


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


def bounds_height(bounds) -> int:
    return round(bounds_to_dimensions(bounds)["height"])


def bounds_width(bounds) -> int:
    return round(bounds_to_dimensions(bounds)["width"])


def bounds_center(bounds) -> dict:
    return {
        "horiz": (bounds[2] + bounds[0])/2,
        "vert": (bounds[3] + bounds[1])/2,
    }


def move_to(layer, x, y):
    layer.translate(x-layer.bounds[0], y-layer.bounds[1])


def move_art(layout):
    # Set up paths and determine file extension
    work_path = os.path.dirname(layout.filename)
    new_name = path.basename(layout.filename)
    layout_type = layout.card_class

    if "finished" in work_path:
        return False
    elif layout_type != "NormalLayout":
        fin_path = os.path.join(work_path, "finished", layout_type)
    else:
        fin_path = os.path.join(work_path, "finished")

    if not os.path.exists(fin_path):
        os.mkdir(fin_path)

    new_file = filename_append(os.path.join(fin_path, new_name), fin_path)
    try:
        os.replace(layout.filename, new_file)
        return new_file
    except Exception as e:
        return e


def frame(layer, ref, horiz="middle", vert="middle", resize=True, outside=True, resample="bicubicAutomatic"):
    """
    layer: The layer that will be moved and resized.
    ref: The reference layer.
    horiz: "left", "middle", "right" - horizontal alignment, leave empty to not move.
    vert: "top", "middle", "bottom" - horizontal alignment, leave empty to not move.
    resize: boolean, determines if the layer will be shrunk or enlarged to fit in the reference.
    """
    circum = max if outside else min
    bounds = layer.bounds
    w, h = bounds[2]-bounds[0], bounds[3]-bounds[1]
    if isinstance(ref, list|tuple):
        left, top, right, bottom = ref
    elif hasattr(ref, "bounds"):
        left, top, right, bottom = ref.bounds
    r = circum(
        (right - left) / w,
        (bottom - top) / h,
    ) if resize else 1
    ref_center = [
        (right + left) * 0.5,
        (bottom + top) * 0.5,
        ]
    layer_offset = [w * r, h * r]
    x_dict = {
        "left": left - bounds[0],
        "middle": ref_center[0] - bounds[0] - layer_offset[0]*0.5,
        "right": right - bounds[0] - layer_offset[0],
        }
    y_dict = {
        "top": top - bounds[1],
        "middle": ref_center[1] - bounds[1] - layer_offset[1]*0.5,
        "bottom": bottom - bounds[1] - layer_offset[1],
        }
    x = x_dict.get(horiz, 0)
    y = y_dict.get(vert, 0)
    free_transform(layer, x, y, w=r*100, h=r*100, resample=resample)


def remove_background(layer):
    old_layer = app.activeDocument.activeLayer
    app.activeDocument.activeLayer = layer
    desc = ps.ActionDescriptor()
    desc.putBoolean(sid("sampleAllLayers"), False)
    app.executeAction(sid("autoCutout"), desc, ps.DialogModes.DisplayNoDialogs)
    make_mask()
    desc1 = ps.ActionDescriptor()
    chnl = cid("Chnl")
    desc1.putClass(cid("Nw  "), chnl)
    ref1 = ps.ActionReference()
    ref1.putEnumerated(chnl, chnl, cid("Msk "))
    desc1.putReference(cid("At  "), ref1)
    desc1.putEnumerated(cid("Usng"), cid("UsrM"), cid("RvlS"))
    app.executeAction(cid("Mk  "), desc1, ps.DialogModes.DisplayNoDialogs)
    app.activeDocument.activeLayer = old_layer


def rgbcolor(r: int, g: int, b: int):
    """ Return a SolidColor object with given decimal values. """
    color = ps.SolidColor()
    color.rgb.red = r
    color.rgb.green = g
    color.rgb.blue = b
    return color


def get_expansion(layer, rarity: str, ref_layer, set_code: str):
    """ Find and open the set symbol SVG and pop it into our document. """

    # Start nice and clean
    white = rgbcolor(255, 255, 255)
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
            f"https://svgs.scryfall.io/sets/{key.lower()}.svg"
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
        This might need a lot of massaging.
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

    max_size = bounds_height(ref_layer.bounds)
    doc = app.activeDocument
    doc.activeLayer = layer
    svg_open(svg_path, max_size)
    new_doc = app.activeDocument
    new_doc.selection.selectAll()
    new_doc.selection.copy()
    new_doc.close(ps.SaveOptions.DoNotSaveChanges)
    doc.paste()

    # Align verticle center, horizontal right.
    frame(layer, ref_layer, horiz="right", outside=False, resize=False)

    # Magic Wand non-contiguous outside symbol, then subtract contiguous
    x, y = layer.bounds[0] - 50, layer.bounds[1] - 50
    slct = magic_wand_select(layer, x, y, "setd")
    slct.invert()
    slct.expand(1)

    # Make a new layer and fill with stroke color
    fill_layer = add_layer(name="Expansion Mask")
    fill_layer.moveAfter(layer)
    slct.fill(white)
    slct.deselect()
    
    layer.link(fill_layer)

    # Apply rarity mask if necessary, and center it on symbol.
    if rarity != "common":
        mask_layer = get_layer(rarity, "Expansion", doc=doc)
        frame(mask_layer, layer, resize=False)
        layer.link(mask_layer)

    return layer


def filename_append(file, send_path):
    """ Check if a file already exists, then adds (x) if it does. """
    file_name, ext = path.splitext(path.basename(file))  # imagename, .xxx
    test_name = path.join(send_path, f"{file_name}{ext}")
    if path.exists(test_name):  # location/imagename.xxx
        multi = 1
        test_name = path.join(send_path, f"{file_name} ({multi}){ext}")
        while path.exists(test_name):  # location/imagename (1).xxx
            multi += 1
            test_name = path.join(send_path, f"{file_name} ({multi}){ext}")
    return test_name  #  returns "location/imagename.xxx" or "location/imagename (x).xxx"


def dirty_text_scale(input_text, chars_in_line):
    """ Gives an estimated number of lines at default text size. """
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
    return line_count


def layer_vert_stretch(layer, modifier, anchor="bottom", method="nearestNeighbor"):
    """ Stretches a layer by (-modifier) pixels. """
    transform_delta = {"top": 0, "center": modifier / 2, "bottom": modifier}
    height = bounds_height(bounds_nofx(layer))
    h_perc = (height - modifier) / height * 100
    free_transform(layer, y=transform_delta[anchor], h=h_perc, resample=method)


def wubrg_layer_sort(color_pair, layers, doc=None, prefix=""):
    """ Rearranges two color layers in order and applies mask. """
    if doc == None: doc = app.activeDocument
    print(prefix+color_pair[-2])
    print(prefix+color_pair[-1])
    top = get_layer(str(prefix+color_pair[-2]), layers, doc=doc)
    bottom = get_layer(str(prefix+color_pair[-1]), layers, doc=doc)
    top.moveBefore(bottom)
    psd.set_layer_mask(top)
    top.visible = True
    bottom.visible = True


def add_select_layer(layer):
    """" Adds to current Selection using the boundary of a layer. """
    return select_layer(layer, ps.SelectionType.ExtendSelection)


def select_layer(layer, type=None):
    """ Creates a Selection using the boundary of a layer. """
    if not type: type = ps.SelectionType.ReplaceSelection
    try:
        left, top, right, bottom = layer.bounds
    except Exception as e:
        return e

    return app.activeDocument.selection.select(
        [[left, top], [right, top], [right, bottom], [left, bottom]], type
    )


def get_text_bounding_box(layer, width=None, height=None):
    """ Get width and height of paragraph text box. """
    pref_scale = 72 if app.preferences.pointSize == 1 else 72.27
    scale = app.activeDocument.resolution / pref_scale
    multiplier = scale ** 2
    layer_text = layer.textItem
    if not width:
        width = layer_text.width * multiplier
    else:
        layer_text.width = width / scale
    if not height:
        height = layer_text.height * multiplier
    else:
        layer_text.height = height / scale
    return [width, height]


def layer_mask_select(layer):
    """ Selects the layer mask for editing. """
    channel_select(layer)

def layer_rgb_select(layer):
    """ Selects the layer RGB for editing. """
    channel_select(layer, "RGB ")

def channel_select(layer, channel="Msk "):
    """
    Selects the layer mask for editing.
    - 'Msk ': Mask
    - 'RGB ': Regular
    """
    ref = ps.ActionReference()
    ref.putEnumerated(cid("Chnl"), cid("Chnl"), cid(channel))
    ref.putIdentifier(sid("layer"), layer.id)
    desc = ps.ActionDescriptor()
    desc.putReference(cid("null"), ref)
    desc.putBoolean(cid("MkVs"), True)
    app.executeAction(cid("slct"), desc, 3)


def make_mask(layer):
    app.activeDocument.activeLayer = layer
    desc = ps.ActionDescriptor()
    desc.putClass(cid("Nw  "), cid("Chnl"))
    ref = ps.ActionReference()
    ref.putEnumerated(cid("Chnl"), cid("Chnl"), cid("Msk "))
    desc.putReference(cid("At  "), ref)
    desc.putEnumerated(cid("Usng"), cid("UsrM"), cid("RvlS"))
    app.executeAction(cid("Mk  "), desc, ps.DialogModes.DisplayNoDialogs)

def load_rgb_selection():
    ref = ps.ActionReference()
    ref.putProperty(cid("Chnl"), cid("fsel"))
    dsc = ps.ActionDescriptor()
    dsc.putReference(cid("null"), ref)
    trgt_ref = ps.ActionReference()
    trgt_ref.putEnumerated(cid("Chnl"), cid("Chnl"), cid("RGB "))
    dsc.putReference(cid("T   "), trgt_ref)
    app.executeAction(cid("setd"), dsc)


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
    active_layer(layer)
    ref = ps.ActionReference()
    ref.putProperty(cid("Chnl"), cid("fsel"))
    dsc_slct = ps.ActionDescriptor()
    dsc_slct.putReference(cid("null"), ref)
    dsc_pnt = ps.ActionDescriptor()
    dsc_pnt.putUnitDouble(cid("Hrzn"), cid("#Pxl"), x)
    dsc_pnt.putUnitDouble(cid("Vrtc"), cid("#Pxl"), y)
    dsc_slct.putObject(cid("T   "), cid("Pnt "), dsc_pnt)
    dsc_slct.putInteger(cid("Tlrn"), t)  # Tolerance
    dsc_slct.putBoolean(cid("AntA"), a)  # Anti-aliasing
    dsc_slct.putBoolean(cid("Cntg"), c)  # Contiguous
    dsc_slct.putBoolean(cid("Mrgd"), s)  # Sample all layers
    app.executeAction(select, dsc_slct, ps.DialogModes.DisplayNoDialogs)
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
    id_chnl = cid("Chnl")
    ref_selection = ps.ActionReference()
    ref_selection.putProperty(id_chnl, cid("fsel"))
    ref_trans_enum = ps.ActionReference()
    ref_trans_enum.putEnumerated(id_chnl, id_chnl, cid("Trsp"))
    ref_trans_enum.putIdentifier(sid("layer"), layer.id)
    dsc = ps.ActionDescriptor()
    if style == "setd":
        dsc.putReference(cid("null"), ref_selection)
        dsc.putReference(cid("T   "), ref_trans_enum)
    else:
        prep = {"Add ": "T   ", "Sbtr": "From", "Intr": "With"}
        dsc.putReference(cid(prep[style]), ref_selection)
        dsc.putReference(cid("null"), ref_trans_enum)
    app.executeAction(select, dsc, ps.DialogModes.DisplayNoDialogs)


def get_layer_index(layerID):
    ref = ps.ActionReference()
    ref.putIdentifier(sid("layer"), layerID)
    dsc = app.executeActionGet(ref)
    if dsc.getBoolean(sid("background")): delta = 1
    else: delta = 0
    return dsc.getInteger(cid("ItmI")) - delta


def move_inside(fromlayer, layerset):
    ref1 = ps.ActionReference()
    ref1.putIdentifier(sid("layer"), fromlayer.id)
    desc = ps.ActionDescriptor()
    desc.putReference(cid("null"), ref1)
    ref2 = ps.ActionReference()
    ref2.putIndex(sid("layer"), get_layer_index(layerset.id))
    desc.putReference(cid("T   "), ref2)
    desc.putBoolean(cid("Adjs"), False)
    desc.putInteger(cid("Vrsn"), 5)
    try:
        app.executeAction(cid("move"), desc, 3)
    except Exception as err:
        return err


def add_layer(layer=None, name=False):
    if not layer: layer = app.activeDocument.activeLayer
    desc_mk = ps.ActionDescriptor()
    ref = ps.ActionReference()
    ref.putClass(sid("layer"))
    desc_mk.putReference(cid("null"), ref)
    if name:
        desc_usng = ps.ActionDescriptor()
        desc_usng.putString(sid("name"), name)
    desc_mk.putObject(cid("Usng"), cid("Lyr "), desc_usng)
    desc_mk.putInteger(cid("LyrI"), get_layer_index(layer.id))
    app.executeAction(cid("Mk  "), desc_mk, ps.DialogModes.DisplayNoDialogs)
    return app.activeDocument.activeLayer


def paste_in_place():
    """ Equivalent of Ctrl+Shift+V. """
    paste = ps.ActionDescriptor()
    paste.putBoolean(sid("inPlace"), True)
    paste.putEnumerated(cid("AntA"), cid("Antt"), cid("Anno"))
    paste.putClass(cid("As  "), cid("Pxel"))
    app.executeAction(cid("past"), paste, ps.DialogModes.DisplayNoDialogs)


def svg_open(file: str, height: int):
    """ Opens a SVG scaled to (height) pixels tall. """
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


def layer_styles_visible(layer, visible=True):
    """ Enables or disables target layer styles. """
    show_hide = cid("Shw ") if visible else cid("Hd  ")
    ref1 = ps.ActionReference()
    ref1.putClass(cid("Lefx"))
    ref1.putIdentifier(sid("layer"), int(layer.id))
    list1 = ps.ActionList()
    list1.putReference(ref1)
    desc1 = ps.ActionDescriptor()
    desc1.putList(cid("null"), list1)
    app.executeAction(show_hide, desc1, 3)
    

def free_transform(layer, x=0, y=0, w=100, h=100, posit: list=None, resample="bicubicAutomatic"):
    """
    Free Transform a layer.
    layer: The layer to be transformed.
    x: Delta translate along x-axis.
    y: Delta translate along y-axis.
    w: Stretch percentage on width.
    h: Stretch percentage on height.
    resample: StringID of the resample method.
        (bicubicAutomatic, bicubicSharper, bicubicSmoother, bilinear, nearestNeighbor)
    """

    active_layer(layer, mkvs=True)
    ref = ps.ActionReference()
    ref.putIdentifier(sid("layer"), layer.id)
    dsc_trnf = ps.ActionDescriptor()
    dsc_trnf.putReference(cid("null"), ref)
    dsc_trnf.putEnumerated(cid("FTcs"), cid("QCSt"), cid("Qcs0"))
    if posit and isinstance(posit, list|tuple):
        dsc_pstn = ps.ActionDescriptor()
        dsc_pstn.putUnitDouble(cid("Hrzn"), cid("#Pxl"), posit[0])
        dsc_pstn.putUnitDouble(cid("Vrtc"), cid("#Pxl"), posit[1])
        dsc_trnf.putObject(cid("Pstn"), cid("Pnt "), dsc_pstn)
    dsc_offset = ps.ActionDescriptor()
    dsc_offset.putUnitDouble(cid("Hrzn"), cid("#Pxl"), x)
    dsc_offset.putUnitDouble(cid("Vrtc"), cid("#Pxl"), y)
    dsc_trnf.putObject(cid("Ofst"), cid("Ofst"), dsc_offset)
    if w != 100: dsc_trnf.putUnitDouble(cid("Wdth"), cid("#Prc"), w)
    if h != 100: dsc_trnf.putUnitDouble(cid("Hght"), cid("#Prc"), h)
    if isinstance(layer, LayerSet):
        dsc_trnf.putBoolean(cid("Lnkd"), True)
    dsc_trnf.putEnumerated(cid("Intr"), cid("Intp"), sid(resample))
    app.executeAction(cid("Trnf"), dsc_trnf)


def bounds_nofx(layer) -> list:
    """ Fetches the bounds of target layer without layer effects. """
    sides = (
        sid("left"),
        sid("top"),
        sid("right"),
        sid("bottom"),
        )
    id_bounds_nofx = sid("boundsNoEffects")
    ref = ps.ActionReference()
    ref.putProperty(sid("property"), id_bounds_nofx)
    ref.putIdentifier(sid("layer"), layer.id)
    bounds_dsc = app.executeActionGet(ref).getObjectValue(id_bounds_nofx)
    return [bounds_dsc.getUnitDoubleValue(s) for s in sides]


def creature_text_path_shift(layer, modifier):
    return text_path_shift(layer, modifier, "top")


def pw_ability_shift(layer):
    layer = text_path_shift(layer, 100, "left")
    layer.translate(100, 7)
    return layer


def text_path_shift(layer, modifier, d="top"):
    modifier = min(modifier, 900)

    # Gonna try a getter instead of grabbing pathItems
    ref = ps.ActionReference()
    ref.putProperty(sid("property"), sid("textKey"))
    ref.putIdentifier(sid("layer"), layer.id)
    dsc_textkey = app.executeActionGet(ref).getObjectValue(sid("textKey"))
    tshpdesc = dsc_textkey.getList(sid("textShape")).getObjectValue(0)

    rectdesc = tshpdesc.getObjectValue(sid("bounds"))
    txt_bounds = [rectdesc.getDouble(sid(side)) for side in ("left", "top", "right", "bottom")]
    left, top, right, bottom = txt_bounds
    new_top = top + modifier if d == "top" else top
    new_left = left + modifier if d == "left" else left

    pathdesc = tshpdesc.getObjectValue(cid("Path"))
    pacmdesc = pathdesc.getList(sid("pathComponents")).getObjectValue(0)
    sbpldesc = pacmdesc.getList(cid("SbpL")).getObjectValue(0)
    pts = sbpldesc.getList(cid("Pts "))
    path_points = []
    for i in range(pts.count):
        coord = pts.getObjectValue(i)
        anch = coord.getObjectValue(cid("Anch"))
        x, y = [anch.getUnitDoubleValue(cid(dir)) for dir in ["Hrzn", "Vrtc"]]
        utx, uty = [anch.getUnitDoubleType(cid(dir)) for dir in ["Hrzn", "Vrtc"]]
        path_points += [{"x": x, "y": y, "utx": utx, "uty": uty}]
        if coord.hasKey(cid("Fwd ")) or coord.hasKey(cid("Bwd ")):
            fanch = coord.getObjectValue(cid("Fwd "))
            fx, fy = [fanch.getUnitDoubleValue(cid(dir)) for dir in ["Hrzn", "Vrtc"]]
            futx, futy = [fanch.getUnitDoubleType(cid(dir)) for dir in ["Hrzn", "Vrtc"]]
            path_points[-1].update({"fx": fx, "fy": fy, "futx": futx, "futy": futy})
            banch = coord.getObjectValue(cid("Bwd "))
            bx, by = [banch.getUnitDoubleValue(cid(dir)) for dir in ["Hrzn", "Vrtc"]]
            butx, buty = [banch.getUnitDoubleType(cid(dir)) for dir in ["Hrzn", "Vrtc"]]
            path_points[-1].update({"bx": bx, "by": by, "butx": butx, "buty": buty})
            path_points[-1].update({"smooth": coord.getBoolean(cid("Smoo"))})

    ref = ps.ActionReference()
    ref.putIdentifier(sid("layer"), layer.id)
    dsc_setd = ps.ActionDescriptor()
    dsc_setd.putReference(cid("null"), ref)
    dsc_pacm = ps.ActionDescriptor()
    dsc_pacm.putEnumerated(sid("shapeOperation"), sid("shapeOperation"), sid("xor") )
    dsc_sbpl = ps.ActionDescriptor()
    dsc_sbpl.putBoolean(cid("Clsp"), True)
    lst_pts = ps.ActionList()

    for point in path_points:
        anc_x = new_left if round(point["x"]) == round(left) else point["x"]
        anc_y = new_top if round(point["y"]) == round(top) else point["y"]
        dsc_anch_pnt = ps.ActionDescriptor()
        dsc_anch_pnt.putUnitDouble(cid("Hrzn"), point["utx"], anc_x)
        dsc_anch_pnt.putUnitDouble(cid("Vrtc"), point["uty"], anc_y)
        dsc_pthp = ps.ActionDescriptor()
        dsc_pthp.putObject(cid("Anch"), cid("Pnt "), dsc_anch_pnt)
        if "fx" in point and "bx" in point:
            dsc_fwd_pnt = ps.ActionDescriptor()
            dsc_fwd_pnt.putUnitDouble(cid("Hrzn"), point["futx"], point["fx"])
            dsc_fwd_pnt.putUnitDouble(cid("Vrtc"), point["futy"], point["fy"])
            dsc_pthp.putObject(cid("Fwd "), cid("Pnt "), dsc_fwd_pnt)
            dsc_bwd_pnt = ps.ActionDescriptor()
            dsc_bwd_pnt.putUnitDouble(cid("Hrzn"), point["butx"], point["bx"])
            dsc_bwd_pnt.putUnitDouble(cid("Vrtc"), point["buty"], point["by"])
            dsc_pthp.putObject(cid("Bwd "), cid("Pnt "), dsc_bwd_pnt)
            dsc_pthp.putBoolean(cid("Smoo"), point["smooth"])
        lst_pts.putObject(cid("Pthp"), dsc_pthp)

    dsc_sbpl.putList(cid("Pts "), lst_pts)
    lst_sbpl = ps.ActionList()
    lst_sbpl.putObject(cid("Sbpl"), dsc_sbpl)
    dsc_pacm.putList(cid("SbpL"), lst_sbpl)
    lst_pathcomp = ps.ActionList()
    lst_pathcomp.putObject(cid("PaCm"), dsc_pacm)
    dsc_pathclass = ps.ActionDescriptor()
    dsc_pathclass.putList(sid("pathComponents"), lst_pathcomp)
    dsc_txshp = ps.ActionDescriptor()
    dsc_txshp.putObject(cid("Path"), sid("pathClass"), dsc_pathclass)
    dsc_txshp.putEnumerated(cid("TEXT"), cid("TEXT"), sid("box") )

    dsc_trnf = ps.ActionDescriptor()
    dsc_trnf.putDouble(sid("xx"), 1)
    dsc_trnf.putDouble(sid("xy"), 0)
    dsc_trnf.putDouble(sid("yx"), 0)
    dsc_trnf.putDouble(sid("yy"), 1)
    dsc_trnf.putDouble(sid("tx"), 0-new_left)
    dsc_trnf.putDouble(sid("ty"), 0-new_top)
    dsc_txshp.putObject(cid("Trnf"), cid("Trnf"), dsc_trnf)

    dsc_rctn_bounds = ps.ActionDescriptor()
    dsc_rctn_bounds.putDouble(cid("Left"), new_left)
    dsc_rctn_bounds.putDouble(cid("Top "), new_top)
    dsc_rctn_bounds.putDouble(cid("Rght"), right)
    dsc_rctn_bounds.putDouble(cid("Btom"), bottom)
    dsc_txshp.putObject(sid("bounds"), cid("Rctn"), dsc_rctn_bounds)

    lst_txshp = ps.ActionList()
    lst_txshp.putObject(sid("textShape"), dsc_txshp)
    dsc_txlr = ps.ActionDescriptor()
    dsc_txlr.putList(sid("textShape"), lst_txshp)
    dsc_setd.putObject(cid("T   "), cid("TxLr"), dsc_txlr)
    app.executeAction(cid("setd"), dsc_setd, ps.DialogModes.DisplayNoDialogs)

    return layer

def fit_text(text_layer, ref_layer, padding:int=False, post_frame:bool=True):
    """
    Resize text in text_layer down until it fits inside ref_layer, with optional padding.
    """
    txt_b = bounds_nofx(text_layer)
    ref_b = bounds_nofx(ref_layer)
    if not padding: padding = txt_b[0]-ref_b[0]
    height = (ref_b[3]-ref_b[1]) - padding*2
    right = ref_b[2]-padding
    txt = text_layer.textItem
    while txt_b[3]-txt_b[1] > height or txt_b[2] > right:
        size = txt.size-0.2
        txt.size = size
        txt.leading = size
        txt_b = bounds_nofx(text_layer)
    if post_frame: frame(text_layer, ref_b, resize=False)


def fit_text_oneline(text_layer, ref_layer, loc:str="left", padding:int=False, post_frame:bool=False):
    """
    Resize text in text_layer down to fit inside ref_layer, with optional padding.
    For use on non-paragraph text.
    """
    txt_b = text_layer.bounds
    ref_b = ref_layer.bounds
    txt_w, txt_h = bounds_to_dimensions(txt_b).values()
    ref_w, ref_h = bounds_to_dimensions(ref_b).values()
    if not padding: padding = txt_b[0]-ref_b[0] # Default padding is delta of left bounds
    if loc == "inside":
        ratio = min(
            (ref_w - padding * 2) / txt_w, # Ratio of widths
            (ref_h - padding * 2) / txt_h, # Ratio of heights
            1,
            )
    else:
        side = 0 if loc == "left" else 2
        target_w = abs(ref_b[side]-txt_b[side])-padding
        ratio = min(target_w / txt_w, 1)
    old_size = text_layer.textItem.size
    text_layer.textItem.size *= ratio
    text_layer.textItem.baselineShift = (old_size - text_layer.textItem.size) * 0.32
    if post_frame:
        frame(text_layer, ref_b, resize=False)


def layer_empty(layer) -> bool:
    try:
        return all(b == 0 for b in layer.bounds)
    except:
        return None


def place_image(layer, file, percent=None):
    """Places images on target layer; or if that layer is not blank, onto a new layer."""
    offset = 0
    if not layer_empty(layer) or ".svg" in file:
        offset = 1
    active_layer(layer)
    dsc_plc = ps.ActionDescriptor()
    dsc_plc.putInteger(sid("ID"), layer.id + offset)
    dsc_plc.putPath(cid("null"), file)
    dsc_plc.putEnumerated(cid("FTcs"), cid("QCSt"), cid("Qcsa"))
    dsc_ofst = ps.ActionDescriptor()
    dsc_ofst.putUnitDouble( cid("Hrzn"), cid("Pxl "), 0)
    dsc_ofst.putUnitDouble( cid("Vrtc"), cid("Pxl "), 0)
    dsc_plc.putObject(cid("Ofst"), cid("Ofst"), dsc_ofst)
    if percent:
        dsc_plc.putUnitDouble(cid("Wdth"), cid("#Prc"), percent)
        dsc_plc.putUnitDouble(cid("Hght"), cid("#Prc"), percent)
    dsc_plc.putBoolean(cid("AntA"), True)
    app.executeAction(cid("Plc "), dsc_plc, ps.DialogModes.DisplayNoDialogs)
    if ".svg" in file:
        app.executeAction(cid("Mrg2"), ps.ActionDescriptor())
    return app.activeDocument.activeLayer


def active_layer(layer, mkvs=False):
    desc_slct = ps.ActionDescriptor()

    ref_null = ps.ActionReference()
    ref_null.putIdentifier(cid("Lyr "), layer.id)
    desc_slct.putReference(cid("null"), ref_null)
    desc_slct.putBoolean(cid("MkVs"), mkvs)

    app.executeAction(cid("slct"), desc_slct)


def dupe_layer(layer, name: str=None, doc=None):

    ref_null = ps.ActionReference()
    ref_null.putIdentifier(cid("Lyr "), layer.id)
    desc_dplc = ps.ActionDescriptor()
    desc_dplc.putReference(cid("null"), ref_null)
    if name: desc_dplc.putString(cid("Nm  "), name)
    desc_dplc.putInteger(cid("Vrsn"), 5) # What do

    # list_idnt = ps.ActionList()
    # list_idnt.putInteger(3726)
    # desc_dplc.putList(cid("Idnt"), list_idnt)

    app.executeAction(cid("Dplc"), desc_dplc)
    return doc.activeLayer


def isolate_layers(layer: ArtLayer|LayerSet):
    """Inverts back to normal if called again with same layer target."""
    ref = ps.ActionReference()
    ref.putIdentifier(sid("layer"), layer.id)
    lst = ps.ActionList()
    lst.putReference(ref)
    dsc = ps.ActionDescriptor()
    dsc.putList(cid("null"), lst)
    dsc.putBoolean(cid("TglO"), True)
    app.executeAction(cid("Shw "), dsc)


def replace_text(layer, find, repl, **kwargs):
    if isinstance(layer, int): id = layer
    else: id = layer.id
    regex = kwargs.get("regex", False)

    ref = ps.ActionReference()
    ref.putProperty(sid("property"), sid("textKey"))
    ref.putIdentifier(sid("layer"), id)
    dsc_setd = app.executeActionGet(ref)
    textkey_dsc = dsc_setd.getObjectValue(sid("textKey"))
    original = textkey_dsc.getString(sid("textKey"))

    replaced = ""
    pre_posits = []
    post_posits = []
    if regex:
        if not re.search(r"^\([\S\s]*\)$", find): find = rf"({find})" # For splitting
        pre_posits = [f.span() for f in re.finditer(find, original)]
        start = 0
        for span in pre_posits:
            replaced += original[start:span[0]]
            post_start = len(replaced)
            replaced += re.sub(find, repl, original[span[0]:span[1]])
            post_end = len(replaced)
            post_posits += [(post_start, post_end)]
            start = span[1]
    else:
        olen = len(find)
        rlen = len(repl)
        delta = rlen-olen
        if find not in original: return False # No result
        start = 0
        end = 0
        tdelta = 0
        while find in original[start:]:
            start += original[start:].find(find)
            replaced += original[end:start]+repl
            end = start + olen
            pre_posits += [(start, end)]
            post = (start+tdelta, start+tdelta+rlen)
            post_posits += [post]
            tdelta += delta
            start += olen
        replaced += original[start:]
    textkey_dsc.erase(sid("textKey"))
    textkey_dsc.putString(sid("textKey"), replaced)
    old_ranges = []
    new_ranges = []
    for text_range in ["textStyleRange", "paragraphStyleRange", "kerningRange"]:
        total_delta = 0
        if textkey_dsc.hasKey(sid(text_range)):
            old_ranges += [[]]
            new_ranges += [[]]
            tssr_lst = textkey_dsc.getList(sid(text_range))
            new_range = ps.ActionList()
            for i in range(tssr_lst.count):
                tssr_dsc = tssr_lst.getObjectValue(i)
                start = tssr_dsc.getInteger(sid("from"))
                end = tssr_dsc.getInteger(sid("to"))
                old_ranges[-1] += [(start, end)]
                start += total_delta
                for posit in zip(pre_posits, post_posits):
                    if start<posit[0][1]<=end:
                        post = posit[1][1]-posit[1][0]
                        pre = posit[0][1]-posit[0][0]
                        delta = post-pre
                        total_delta += delta
                end += total_delta
                new_ranges[-1] += [(start, end)]
                tssr_dsc.erase(sid("from"))
                tssr_dsc.putInteger(sid("from"), start)
                tssr_dsc.erase(sid("to"))
                tssr_dsc.putInteger(sid("to"), end)
                new_range.putObject(
                    sid(text_range),
                    tssr_dsc
                    )
            textkey_dsc.erase(sid(text_range))
            textkey_dsc.putList(sid(text_range), new_range)
    ref = ps.ActionReference()
    ref.putIdentifier(sid("layer"), id)
    dsc_setd = ps.ActionDescriptor()
    dsc_setd.putReference(cid("null"), ref)
    dsc_setd.putObject(cid("T   "), cid("TxLr"), textkey_dsc)
    app.executeAction(cid("setd"), dsc_setd)
    return replaced