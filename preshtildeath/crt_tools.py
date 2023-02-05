import photoshop.api as ps
import os

app = ps.Application()
cid = app.charIDToTypeID
sid = app.stringIDToTypeID


def default_colors():
    fore_back_color_init("reset")


def color_exchange():
    fore_back_color_init("exchange")


def fore_back_color_init(method):
    action = {"reset": cid("Rset"), "exchange": cid("Exch")}
    desc = ps.ActionDescriptor()
    ref = ps.ActionReference()
    ref.putProperty(cid("Clr "), cid("Clrs"))
    desc.putReference(cid("null"), ref)
    app.executeAction(action[method], desc, 3)


# Index color palette for active document
def index_color(colors=24, m="uniform"):
    method = {"adaptive": cid("Adpt"), "uniform": cid("Unfm")}
    dsc1 = ps.ActionDescriptor()
    dsc2 = ps.ActionDescriptor()
    dsc2.putEnumerated(cid("Plt "), cid("ClrP"), method[m])
    dsc2.putInteger(cid("Clrs"), colors)
    dsc2.putEnumerated(cid("FrcC"), cid("FrcC"), cid("None"))
    dsc2.putBoolean(cid("Trns"), False)
    dsc2.putEnumerated(cid("Dthr"), cid("Dthr"), cid("Ptrn"))
    dsc1.putObject(cid("T   "), cid("IndC"), dsc2)
    app.executeAction(cid("CnvM"), dsc1, 3)


def pattern_make(file):
    name = os.path.splitext(os.path.basename(file))[0]
    doc = app.load(file)
    ref1 = ps.ActionReference()
    ref1.putClass(cid("Ptrn"))
    desc1 = ps.ActionDescriptor()
    desc1.putReference(cid("null"), ref1)
    ref2 = ps.ActionReference()
    ref2.putProperty(cid("Prpr"), cid("fsel"))
    ref2.putIdentifier(cid("Dcmn"), doc.id)
    desc1.putReference(cid("Usng"), ref2)
    desc1.putString(cid("Nm  "), name)
    app.executeAction(cid("Mk  "), desc1, 3)
    doc.close(ps.SaveOptions.DoNotSaveChanges)


def pattern_fill(layer, file, x=0, y=0):
    name = os.path.splitext(os.path.basename(file))[0]
    old_layer = app.activeDocument.activeLayer
    app.activeDocument.activeLayer = layer
    app.currentTool = "bucketTool"
    desc1 = ps.ActionDescriptor()
    desc2 = ps.ActionDescriptor()
    desc2.putUnitDouble(cid("Hrzn"), cid("#Pxl"), x)
    desc2.putUnitDouble(cid("Vrtc"), cid("#Pxl"), y)
    desc1.putObject(cid("From"), cid("Pnt "), desc2)
    desc1.putInteger(cid("Tlrn"), 0)
    desc1.putEnumerated(cid("Usng"), cid("FlCn"), cid("Ptrn"))
    desc3 = ps.ActionDescriptor()
    desc3.putString(cid("Nm  "), name)
    desc1.putObject(cid("Ptrn"), cid("Ptrn"), desc3)
    desc1.putBoolean(cid("Cntg"), False)
    while True:
        try:
            app.executeAction(cid("Fl  "), desc1, 3)
        except:
            pattern_make(file)
        else:
            break
    app.activeDocument.activeLayer = old_layer


def channel_select(chan="all"):
    chan_dict = {
        "red": cid("Rd  "),
        "green": cid("Grn "),
        "blue": cid("Bl  "),
        "all": cid("RGB "),
    }
    desc = ps.ActionDescriptor()
    ref = ps.ActionReference()
    ref.putEnumerated(cid("Chnl"), cid("Chnl"), chan_dict[chan])
    desc.putReference(cid("null"), ref)
    app.executeAction(cid("slct"), desc, 3)


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


def lens_blur(radius: int, bright=0, threshold=255, noise_amount=0, mono=False, depth_mask=None, invert=False):
    desc = ps.ActionDescriptor()
    desc.putInteger(cid("BkDp"), 0)
    if depth_mask:
        desc.putEnumerated(cid("BkDi"), cid("BtDi"), cid("BeIt"))
        desc.putEnumerated(cid("BkDc"), cid("BtDc"), cid("BeCm"))
        desc.putBoolean(cid("BkDs"), invert)
    else:
        desc.putEnumerated(cid("BkDi"), cid("BtDi"), cid("BeIn"))
    desc.putEnumerated(cid("BkIs"), cid("BtIs"), cid("BeS6"))  # Hex default
    desc.putDouble(cid("BkIb"), radius)
    desc.putInteger(cid("BkIc"), 0)
    desc.putInteger(cid("BkIr"), 0)
    desc.putDouble(cid("BkSb"), bright)
    desc.putInteger(cid("BkSt"), threshold)
    desc.putInteger(cid("BkNa"), noise_amount)
    desc.putEnumerated(cid("BkNt"), cid("BtNt"), cid("BeNg"))
    desc.putBoolean(cid("BkNm"), mono)
    app.executeAction(cid("Bokh"), desc)


def img_resize(
    doc,
    w_percent: int=100,
    h_percent: int=100,
    resolution: int=None,
    resample="bicubicAutomatic",
    constraint=True,
):
    """
    doc: The Document to be resized.
    w_percent: Percent width.
    h_percent: Percent height.
    resolution: Document resolution.
    resample: "nearestNeighbor", "bicubicSharper", "bicubicAutomatic" valid strings.
    constraint: Don't remember, I think it locks proportions if scaling by resolution.
    """
    app.activeDocument = doc
    dsc = ps.ActionDescriptor()
    ref = ps.ActionReference()
    ref.putIdentifier(sid("document"), doc.id)
    dsc.putReference(sid("null"), ref)
    if w_percent != 100 and h_percent != 100:
        dsc.putUnitDouble(cid("Wdth"), cid("#Prc"), w_percent)
        dsc.putUnitDouble(cid("Hght"), cid("#Prc"), h_percent)
    if not resolution:
        resolution = doc.resolution * max(w_percent, h_percent) / 100
    dsc.putUnitDouble(cid("Rslt"), cid("#Rsl"), resolution)
    dsc.putBoolean(cid("CnsP"), constraint)
    dsc.putBoolean(sid("scaleStyles"), True)
    dsc.putEnumerated(cid("Intr"), cid("Intp"), sid(resample))
    app.executeAction(cid("ImgS"), dsc)


def blow_up(filter):

    doc = app.activeDocument

    if not filter:
        doc.flatten()
        img_resize(doc, 800, 800, 800, "nearestNeighbor")
        delta = doc.resolution / 8
        doc.crop([-delta, -delta, doc.width + delta, doc.height + delta])
        return doc
    doc.flatten()
    img_resize(doc, 900, 900, 900, "nearestNeighbor")
    default_colors()
    color_exchange()

    # Set up some files
    ass_path = os.path.join(os.path.dirname(__file__), "assets")
    crt_file = os.path.join(ass_path, "crt9x9.png")
    rgb_file = os.path.join(ass_path, "rgb18x9.png")
    r_file = os.path.join(ass_path, "r18x9.png")
    g_file = os.path.join(ass_path, "g18x9.png")
    b_file = os.path.join(ass_path, "b18x9.png")
    scan_file = os.path.join(ass_path, "scan1x9.png")
    base_layer = doc.artLayers[0] # Background layer
    filters = doc.layerSets.add()
    filters.name = "Filters"

    # Extend borders for later spherize
    original_w = doc.width
    original_h = doc.height
    center_w, center_h = original_w/2, original_h/2
    rad = (center_w**2 + center_h**2) ** 0.5
    rad -= rad%9
    post_delta = doc.resolution / 8
    l, t, r, b = center_w-rad, center_h-rad, center_w+rad, center_h+rad
    l += l%9
    t += t%9
    r -= r%9
    b -= b%9
    doc.crop([l, t, r, b])

    # CRT scanline filtered layer
    dupe = base_layer.duplicate()
    dupe.move(filters, ps.ElementPlacement.PlaceInside)
    crtlayer = doc.artLayers.add()
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
    lcdlayer = doc.artLayers.add()
    lcdlayer.move(dupe, ps.ElementPlacement.PlaceBefore)
    pattern_fill(lcdlayer, rgb_file, 10, 10)
    lcdlayer.blendMode = ps.BlendMode.Multiply
    lcdlayer = lcdlayer.merge()
    # lcdlayer.fillOpacity = 40
    lcdlayer.applyMedianNoise(1)
    doc.activeLayer = lcdlayer
    lens_blur(2, 30, 216)
    lcdlayer.fillOpacity = 30
    lcdlayer.name = "lcdlayer"

    # CRT sub-pixel style overlay
    # Setup base layers
    dupe = base_layer.duplicate()
    dupe.move(lcdlayer, ps.ElementPlacement.PlaceBefore)
    scan_layer = doc.artLayers.add()
    scan_layer.move(dupe, ps.ElementPlacement.PlaceBefore)
    pattern_fill(scan_layer, scan_file, 10, 10)
    scan_layer.blendMode = ps.BlendMode.Multiply
    r_layer = scan_layer.merge()
    g_layer = r_layer.duplicate()
    b_layer = g_layer.duplicate()
    # Red pixels
    red_mask = doc.artLayers.add()
    red_mask.move(r_layer, ps.ElementPlacement.PlaceBefore)
    pattern_fill(red_mask, r_file, 10, 10)
    doc.activeLayer = red_mask
    lens_blur(1, noise_amount=1)
    red_mask.blendMode = ps.BlendMode.Multiply
    red_mask = red_mask.merge()
    red_mask.applyMaximum(0.6)
    # Green pixels
    green_mask = doc.artLayers.add()
    green_mask.move(g_layer, ps.ElementPlacement.PlaceBefore)
    pattern_fill(green_mask, g_file, 10, 10)
    doc.activeLayer = green_mask
    lens_blur(1, noise_amount=1)
    green_mask.blendMode = ps.BlendMode.Multiply
    green_mask = green_mask.merge()
    green_mask.applyMaximum(0.6)
    green_mask.blendMode = ps.BlendMode.Screen
    # Blue pixels
    blue_mask = doc.artLayers.add()
    blue_mask.move(b_layer, ps.ElementPlacement.PlaceBefore)
    pattern_fill(blue_mask, b_file, 10, 10)
    doc.activeLayer = blue_mask
    lens_blur(1, noise_amount=1)
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
    doc.activeLayer = rgblayer
    lens_blur(2, 40, 216, 1)
    rgblayer.applyMaximum(0.8)
    rgblayer.fillOpacity = 70

    crtlayer.applySpherize(8.5, ps.SpherizeMode.NormalSpherize)
    rgblayer.applySpherize(9, ps.SpherizeMode.NormalSpherize)
    lcdlayer.applySpherize(9.5, ps.SpherizeMode.NormalSpherize)

    crtlayer.applyUnSharpMask(40, 1.5, 4)
    crtlayer.resize(97.05, 97.05, ps.AnchorPosition.MiddleCenter)
    lcdlayer.applyMaximum(1)
    lcdlayer.resize(97.1, 97.1, ps.AnchorPosition.MiddleCenter)
    rgblayer.applyRadialBlur(
        1, ps.RadialBlurMethod.Zoom, ps.RadialBlurBest.RadialBlurBest
    )
    rgblayer.resize(97.2, 97.2, ps.AnchorPosition.MiddleCenter)
    rgblayer.adjustLevels(22, 255, 1.0, 0, 255)
    glow_layer = rgblayer.duplicate()
    glow_layer.adjustLevels(30, 250, 0.95, 0, 255)
    glow_layer.applyMaximum(2)
    glow_layer.applyGaussianBlur(24)
    glow_layer.resize(100.8, 100.8, ps.AnchorPosition.MiddleCenter)
    glow_layer.fillOpacity = 30

    new_hw, new_hh = doc.width/2, doc.height/2
    l, t, r, b = (
        new_hw - center_w - post_delta,
        new_hh - center_h - post_delta,
        new_hw + center_w + post_delta,
        new_hh + center_h + post_delta,
    )
    # l, t, r, b = d, d, original_w+d, original_h+d
    doc.crop([l, t, r, b])
    img_resize(doc, resolution=800, resample="bicubicSharper")
