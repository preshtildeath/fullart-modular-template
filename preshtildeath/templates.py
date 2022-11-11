"""
PRESHTILDEATH TEMPLATES
"""
import os
import re
import proxyshop.gui as gui
from proxyshop.constants import con
from proxyshop.settings import cfg
import proxyshop.text_layers as txt_layers
import proxyshop.templates as temp
import proxyshop.helpers as psd
import photoshop.api as ps
from PIL import Image
import tools
import crt_tools
from tools import presh_config

console = gui.console_handler
app = ps.Application()

# Ensure scaling with pixels, font size with points
app.preferences.rulerUnits = ps.Units.Pixels
app.preferences.typeUnits = ps.Units.Points


class PWLoyaltyCost(txt_layers.TextField):
    """Shrink loyalty ability costs to fit inside the badge."""
    def __init__(self, layer, contents, color=None, badge=None):

        super().__init__(layer, contents, color)
        self.badge = badge

    def execute(self):

        super().execute()
        doc = app.activeDocument

        tools.select_nonblank_pixels(self.badge)
        doc.activeLayer = self.layer
        psd.align_vertical()
        doc.selection.deselect()

        if "—" in self.contents or "-" in self.contents:
            # Let's just give this guy a tiny bitty nudge
            layer_w = psd.get_dimensions_no_effects(self.layer)["width"]
            text_l = len(self.contents)
            delta = ((1 / text_l) * layer_w) / 5
            self.layer.translate(-delta, 0)

        self.layer.link(self.badge)

        while True:
            tools.select_nonblank_pixels(self.layer)
            doc.selection.expand(20)
            tools.select_nonblank_pixels(self.badge, "Sbtr")

            if tools.selection_exists(doc.selection):
                doc.selection.deselect()
                self.layer.textItem.size -= 0.2
                if "Minus" in self.badge.name:
                    self.layer.textItem.baselineShift += 0.12
                elif "Zero" in self.badge.name:
                    self.layer.textItem.baselineShift += 0.06
            else:
                return


class FullArtModularTemplate(temp.StarterTemplate):
    """
    Created by preshtildeath.
    Expands the textbox based on how much oracle text a card has.
    Also expanding this template to service other card types.
    """

    template_file_name = "preshtildeath/fullart-modular"
    template_suffix = "Full Mod"

    def get_file_name(self):

        try:
            save = ".jpg" if cfg.save_jpeg else ".png"
            # Check for multiples
            end_file = os.path.splitext(
                os.path.basename(
                    tools.filename_append(
                        f"{self.layout.name} ({self.template_suffix})" + save,
                        os.path.join(con.cwd, "out")
                        )
                    )
                )[0]
            return end_file  # "Filename (template_suffix) (x)"
        except:
            return f"{self.layout.name} ({self.template_suffix})"

    def load_artwork(self):

        doc_dpi = app.activeDocument.resolution
        with Image.open(self.layout.file) as im:
            if "dpi" in im.info.keys():
                img_dpi = im.info["dpi"][0]
            else: img_dpi = 72
        self.art_layer = tools.place_image(self.art_layer, self.layout.file, p=100*(img_dpi/doc_dpi))

    def collector_info(self): pass

    def __init__(self, layout):

        app.preferences.interpolation = ps.ResampleMethod.BicubicAutomatic
        cfg.remove_flavor = True
        cfg.remove_reminder = True

        try:
            font = app.fonts.getByName("Plantin MT Pro").name
            con.font_rules_text = font
            con.font_rules_text_italic = font
        except:
            console.update("'Plantin MT Pro' font not found, please install for best results.")
            try:
                con.font_rules_text = app.fonts.getByName("MPlantin").name
                con.font_rules_text_italic = app.fonts.getByName("MPlantin-Italic").name
            except:
                console.update("'MPlantin' or 'MPlantin-Italic' fonts not found, oops! Sticking to defaults.")

        super().__init__(layout)

        filename = os.path.splitext(os.path.basename(layout.file))[0]
        if filename.rfind("[") < filename.rfind("]"):
            self.set = filename[filename.rfind("[") + 1 : filename.rfind("]")].upper()
        else:
            self.set = layout.set

        # Check presh_config
        if presh_config.hollow_mana:
            con.rgbi_c = {"r": 194, "g": 194, "b": 194}
            con.rgbi_w = {"r": 232, "g": 232, "b": 230}
            con.rgbi_u = {"r": 64, "g": 185, "b": 255}
            con.rgbi_b = {"r": 125, "g": 47, "b": 129}
            con.rgbi_bh = {"r": 125, "g": 47, "b": 129}
            con.rgbi_r = {"r": 255, "g": 140, "b": 128}
            con.rgbi_g = {"r": 22, "g": 217, "b": 139}
            for c in [("rgb_" + s) for s in list("wubrgc") + ["bh", "primary"]]:
                setattr(con, c, {"r": 250, "g": 250, "b": 250})
            for sym in con.symbols:
                con.symbols[sym] = con.symbols[sym].replace("o", "v")
                con.symbols[sym] = con.symbols[sym].replace("Q", "\u00E8")
                con.symbols[sym] = con.symbols[sym].replace("q", "\u00EF")

        # Define some characteristics
        if not hasattr(self, "is_planeswalker"):
            self.is_planeswalker = False
        if not hasattr(self, "is_basic"):
            self.is_basic = False
        if hasattr(layout, "type_line"):
            if layout.type_line.find("Land") >= 0:
                self.is_land = True
        elif not hasattr(self, "is_basic"):
            self.is_land = False

        # Let's pick an art reference layer
        if presh_config.borderless:
            self.art_reference = tools.get_layer("Full Art Borderless", "Ref")
        elif self.is_land or self.is_planeswalker:
            self.art_reference = tools.get_layer("Full Art Frame", "Ref")
        elif self.is_legendary:
            self.art_reference = tools.get_layer("Legendary Frame", "Ref")
        else:
            self.art_reference = tools.get_layer("Art Frame", "Ref")
        
        ### LETS JUST TEST THE STRETCH AND FILL METHOD
        self.art_reference = tools.get_layer("Art Frame", "Ref")

    def enable_frame_layers(self):

        # Initialize our text layers
        console.update("Preparing text layers...")
        self.text_layers()
        console.update("Turning on our frame elements...")
        doc = app.activeDocument

        # Eldrazi formatting?
        if self.layout.is_colorless:
            # Devoid formatting?
            if self.layout.pinlines != self.layout.twins:
                self.layout.pinlines = "Land"
            else:
                self.layout.pinlines = "Land"
                self.layout.twins = "Land"
            tools.get_layer(self.layout.twins, "Border").visible = True

        # Nyx Formatting
        if self.layout.is_nyx:
            tools.get_layer(f"Nyx {self.layout.pinlines}", "Border").visible = True

        # Twins and p/t box
        tools.get_layer(self.layout.twins, "Name").visible = True
        tools.get_layer(self.layout.twins, "Type").visible = True
        if self.is_creature:
            self.pt_box = tools.get_layer(self.layout.twins, "PT Box")
            self.pt_box.visible = True

        # Pinlines & Textbox
        if len(self.layout.pinlines) != 2:
            tools.get_layer(self.layout.pinlines, "Pinlines").visible = True
            tools.get_layer(self.layout.pinlines, "Textbox").visible = True
        else:
            tools.wubrg_layer_sort(self.layout.pinlines, "Pinlines")
            tools.wubrg_layer_sort(self.layout.pinlines, "Textbox")
        tools.get_layer(
            "Side Pinlines", "Masked", "Pinlines"
        ).visible = presh_config.side_pins

        # Legendary crown
        if self.is_legendary:
            if presh_config.side_pins:
                style = "Legendary"
            else:
                style = "Floating"
            tools.get_layer(f"{style} Crown", "Masked", "Pinlines").visible = True
            title_ref = tools.get_layer(style, "Ref")
            if not bool(self.is_land or self.is_planeswalker or presh_config.borderless):
                tools.get_layer("Crown Mask", "Mask Wearer", "Border").visible = True
        else:
            title_ref = tools.get_layer("Title", "Ref")

        # Give colored artifacts the grey pinlines on the sides of the art and main textbox
        if self.layout.pinlines != "Artifact" and self.layout.background == "Artifact":
            tools.get_layer(self.layout.background, "Textbox").visible = True
            type_ref = tools.get_layer("Type", "Ref")
            pin_mask = tools.get_layer(self.layout.background, "Pinlines")
            pin_mask.visible = True
            doc.activeLayer = pin_mask
            psd.enable_active_layer_mask()
            tools.select_layer(title_ref)
            tools.add_select_layer(type_ref)
            tools.layer_mask_select(pin_mask)
            doc.selection.fill(tools.rgbcolor(0, 0, 0))
            doc.selection.deselect()

        # Give the lands a sexy transparent border
        if self.is_land and not presh_config.borderless:
            land_textbox = tools.get_layer("Land", "Textbox")
            if not land_textbox.visible:
                land_textbox.fillOpacity = 50
                land_textbox.visible = True
            doc.activeLayer = tools.get_layer("Normal", "Mask Wearer", "Border")
            psd.enable_active_layer_mask()
            if len(self.layout.pinlines) != 2:
                tools.get_layer(self.layout.pinlines, "Border").visible = True
            else:
                tools.wubrg_layer_sort(self.layout.pinlines, "Border")

        # Give our PW a sexy transparent border
        elif self.is_planeswalker and not presh_config.borderless:
            doc.activeLayer = tools.get_layer("Normal", "Mask Wearer", "Border")
            psd.enable_active_layer_mask()
            if len(self.layout.pinlines) != 2:
                tools.get_layer(f"PW {self.layout.pinlines}", "Border").visible = True
                tools.get_layer(self.layout.pinlines, "Border").visible = True
            else:
                tools.wubrg_layer_sort(f"PW {self.layout.pinlines}", "Border")
                tools.wubrg_layer_sort(self.layout.pinlines, "Border")

    def text_layers(self):

        # Set up some layers
        mana_layer = tools.get_layer("Text", "Mana Cost")
        name_layer = tools.get_layer("Card Name", "Text and Icons")
        exp_layer = tools.get_layer("Expansion Symbol", "Expansion")
        exp_ref = tools.get_layer("Expansion", "Ref")
        type_layer = tools.get_layer("Typeline", "Text and Icons")

        # Set artist info
        artist_text = tools.get_layer("Artist", "Legal").textItem
        artist_text.contents = self.layout.artist

        # Set symbol
        # Maybe we change this back to the KeyRune font?
        exp_layer = tools.get_expansion(
            exp_layer, self.layout.rarity, exp_ref, self.set
        )
        exp_layer.parent.link(type_layer)

        # Mana, Name, and Type text
        self.tx_layers.extend(
            [
                txt_layers.BasicFormattedTextField(
                    layer=mana_layer,
                    contents=self.layout.mana_cost,
                    color=tools.rgbcolor(0, 0, 0),
                ),
                txt_layers.ScaledTextField(
                    layer=type_layer,
                    contents=self.layout.type_line,
                    color=psd.get_text_layer_color(type_layer),
                    reference=exp_layer,
                ),
                txt_layers.ScaledTextField(
                    layer=name_layer,
                    contents=self.layout.name,
                    color=psd.get_text_layer_color(name_layer),
                    reference=mana_layer,
                ),
            ]
        )

        if self.is_creature:
            self.rules_text = tools.get_layer("Rules Text - Creature", "Text and Icons")
            self.tx_layers.extend(
                [
                    txt_layers.TextField(
                        layer=tools.get_layer("Power / Toughness", "Text and Icons"),
                        contents=f"{self.layout.power}/{self.layout.toughness}",
                    ),
                    txt_layers.FormattedTextField(
                        layer=self.rules_text,
                        contents=self.layout.oracle_text,
                        centered=False,
                    ),
                ]
            )
            self.is_centered = bool(len(self.layout.oracle_text) <= 20)

        elif not self.is_planeswalker:
            self.rules_text = tools.get_layer("Rules Text - Noncreature", "Text and Icons")
            self.tx_layers += [
                txt_layers.FormattedTextField(
                    layer=self.rules_text,
                    contents=self.layout.oracle_text,
                    centered=False,
                )
            ]
            self.is_centered = bool(len(self.layout.oracle_text) <= 120)

    def post_text_layers(self):
        console.update("Shifting text and frame...")

        # Set up some variables
        type_layer = tools.get_layer("Typeline", "Text and Icons")
        textbox_ref = tools.get_layer("Textbox", "Ref")

        # Pre-size down our text based on default size
        txtbx_h = psd.get_layer_dimensions(textbox_ref)["height"]
        txt_h = psd.get_layer_dimensions(self.rules_text)["height"]
        presize = self.rules_text.textItem.size
        size_adjust = max(
            min(
                round(presize - ((txt_h / txtbx_h) ** 2), 1)+0.2,
                presize
            ),
            7
        )

        if presize != size_adjust:
            self.rules_text.textItem.size = size_adjust
            self.rules_text.textItem.leading = size_adjust
        txt_h = psd.get_layer_dimensions(self.rules_text)["height"]

        # Establish how much we are shifting down everything
        modifier = txtbx_h-txt_h-60
        if modifier < 0: modifier = 0
        if len(self.layout.oracle_text) == 0: 
            if not self.is_creature:
                modifier = 1080
            else:
                modifier = 840
                #TODO add more stuff for textless creatures

        # Move the top left and top right anchors for the creature text bounding box,
        # OR translate the whole text layer down
        if self.is_creature:
            tools.creature_text_path_shift(self.rules_text, modifier)
            new_txt_h = psd.get_layer_dimensions(self.rules_text)["height"]
            diff = txt_h-new_txt_h
            if diff < 0:
                modifier += diff
                tools.creature_text_path_shift(self.rules_text, diff)
        else:
            self.rules_text.translate(0, modifier)

        # Shift typeline, resize textbox and art reference
        type_layer.translate(0, modifier)
        tools.layer_vert_stretch(textbox_ref, modifier)
        tools.layer_vert_stretch(self.art_reference, -modifier/2, "top")
        # Let's make sure it fits, both vertically and the right bound.
        tools.fit_text(self.rules_text, textbox_ref)
        tools.frame(self.rules_text, textbox_ref, False, self.is_centered, True)

        console.update("Framing our art layer...")
        tools.frame(self.art_layer, self.art_reference)
        if presh_config.borderless:
            tools.get_layer("Normal", "Mask Wearer", "Border").visible = False
            psd.content_fill_empty_area(self.art_layer)

        tools.select_nonblank_pixels(tools.get_layer("Name", "Mask Wearer", "Name"))
        tools.select_nonblank_pixels(tools.get_layer("Mask Wearer", "Type"), "Add ")
        tools.select_nonblank_pixels(tools.get_layer("Base", "Textbox"), "Add ")
        crt_tools.lens_blur(self.art_layer, 24, 1, 224, 1)
        app.activeDocument.selection.deselect()

    def post_execute(self):

        if (
            self.is_creature and
            not os.path.exists(os.path.join(os.getcwd(), f"out/{self.layout.name} ({self.template_suffix}) blank.png")) and
            presh_config.blank_creature_copy
        ):
            self.art_layer.visible = False
            tools.get_layer("Artist", "Legal").visible = False
            tools.get_layer_set("Expansion").visible = False
            txt = tools.get_layer_set("Text and Icons")
            mana = tools.get_layer_set("Mana Cost")
            exp = tools.get_layer_set("Expansion")
            txt.visible = False
            mana.visible = False
            exp.visible = False
            psd.save_document_png(f"{self.layout.name} ({self.template_suffix}) blank")
            desc = ps.ActionDescriptor()
            list = ps.ActionList()
            refr = ps.ActionReference()
            refr.putIdentifier(app.charIDToTypeID("Lyr "), txt.id)
            list.putReference(refr)
            desc.putList(app.charIDToTypeID("null"), list)
            desc.putBoolean(app.charIDToTypeID("TglO"), True)
            app.executeAction(app.charIDToTypeID("Shw "), desc, ps.DialogModes.DisplayNoDialogs)
            mana.visible = True
            exp.visible = True
            psd.save_document_png(f"{self.layout.name} ({self.template_suffix}) text")
            

        if presh_config.move_art:
            console.update("Moving art file...")
            moved = tools.move_art(self.layout, self.set)
            if moved != True:
                console.update(f"Could not move art file: {moved}")


class FullArtTextlessTemplate(FullArtModularTemplate):
    # Useful for textless duals.
    # TODO: Tweak layout for creatures so they can get rid of textbox

    def __init__(self, layout):
        layout.oracle_text = ""
        super().__init__(layout)


class BasicModularTemplate(FullArtModularTemplate):
    def __init__(self, layout):

        self.is_basic = True
        super().__init__(layout)
        self.suffix = f"({layout.artist}) [{layout.set}]"

    def text_layers(self):

        # Define some layers
        name_layer = tools.get_layer("Card Name", "Text and Icons")
        exp_layer = tools.get_layer("Expansion Symbol", "Expansion")
        exp_ref = tools.get_layer("Expansion", "Ref")
        type_layer = tools.get_layer("Typeline", "Text and Icons")
        tools.get_layer("Text", "Mana Cost").visible = False

        # Set artist info
        artist_text = tools.get_layer("Artist", "Legal").textItem
        artist_text.contents = self.layout.artist

        # Name and type text
        self.tx_layers.extend(
            [
                txt_layers.TextField(
                    layer=name_layer,
                    contents=self.layout.name,
                    color=psd.get_text_layer_color(name_layer),
                ),
                txt_layers.TextField(
                    layer=type_layer,
                    contents=f"Basic Land — {self.layout.name}",
                    color=psd.get_text_layer_color(type_layer),
                ),
            ]
        )
        # Set symbol
        tools.get_expansion(exp_layer, "common", exp_ref, self.set)

    def enable_frame_layers(self):

        self.text_layers()
        name_key = {
            "Plains": "W",
            "Island": "U",
            "Swamp": "B",
            "Mountain": "R",
            "Forest": "G",
        }

        layer_name = name_key[self.layout.name]
        for target in ["Pinlines", "Name", "Type", "Border"]:
            tools.get_layer(layer_name, target).visible = True
        for target in ["Name", "Type"]:
            layer = tools.get_layer("Land", target)
            layer.fillOpacity = 50
            layer.visible = True

        if presh_config.borderless:
            tools.get_layer("Normal", "Mask Wearer", "Border").fillOpacity = 50
            psd.content_fill_empty_area(self.art_layer)

        if not presh_config.side_pins:
            tools.get_layer(
                "Side Pinlines", "Masked", "Pinlines"
            ).visible = False


class DFCModularTemplate(FullArtModularTemplate):
    """
    One-size-fits-all for MDFC Front, MDFC Back, Transform, and Ixalan land back.
    Lessons too, I guess?
    """

    def text_layers(self):

        super().text_layers()

        doc = app.activeDocument
        trans_icon = {
            "sunmoondfc": ["", ""],
            "mooneldrazidfc": ["", ""],
            "compasslanddfc": ["", ""],
            "modal_dfc": ["", ""],
            "originpwdfc": ["", ""],
            "lesson": "",
        }
        if presh_config.side_pins:
            top = "Legendary"
        else:
            top = "Floating"

        # Scoot name text over
        tools.get_layer("Card Name", "Text and Icons").translate(140, 0)

        # If MDFC, set the pointy, else it's the circle
        mask_wearer = tools.get_layer_set("Mask Wearer", "Name")
        if self.layout.transform_icon == "modal_dfc":
            dfc = "MDFC"
            tools.get_layer(dfc, mask_wearer).visible = True
            doc.activeLayer = tools.get_layer_set("Mask Wearer", "Border")
            psd.enable_active_layer_mask()
        else:
            dfc = "TDFC"
            tools.get_layer(dfc, "Name").visible = True
        tools.get_layer("Name", mask_wearer).visible = False
        tools.get_layer("DFC", mask_wearer).visible = True

        # Setup transform icon
        dfc_icon = tools.get_layer(dfc, "Text and Icons")
        dfc_icon.textItem.contents = trans_icon[self.layout.transform_icon][
            self.layout.face
        ]
        dfc_icon.visible = True

        # Cut out the icon from the legendary frame if necessary
        dfc_pin = tools.get_layer(dfc, "Masked", "Pinlines")
        if self.is_legendary:
            legend_mask = tools.get_layer(f"{top} Crown", "Masked", "Pinlines")
            tools.magic_wand_select(dfc_pin, 0, 0)
            doc.selection.expand(2)
            doc.selection.invert()
            tools.layer_mask_select(legend_mask)
            doc.selection.fill(tools.rgbcolor(0, 0, 0))
            doc.selection.deselect()

        # Turn on/off pinlines
        tools.get_layer("Standard", "Masked", "Pinlines").visible = False
        dfc_pin.visible = True


"""
TODO: FIX WITH NEW TEXT RENDER METHOD
"""
class PWFullArtModularTemplate(FullArtModularTemplate):
    def __init__(self, layout):

        self.is_planeswalker = True
        super().__init__(layout)

    def text_layers(self):

        super().text_layers()

        oracle_array = re.findall(r"(^[^:]*$|^.*:.*$)", self.layout.oracle_text, re.MULTILINE)

        # self.tx_layers.append(
        #     txt_layers.FormattedTextField(
        #         layer=tools.get_layer("Static", "PW Ability", "Text and Icons"),
        #         contents=self.layout.oracle_text,
        #         centered=bool(len(self.layout.oracle_text) <= 20),
        #     )
        # )
        centered = False
        self.badge = []
        self.rules_text = []

        for i, ability in enumerate(oracle_array):

            # init values for enumeration later
            self.badge += [None]
            self.rules_text += [None]

            # Determing if the ability is activated
            colon_index = ability.find(": ")
            if 0 < colon_index < 5:

                # Determine cost text
                cost_text = ability[:colon_index]

                # Grab correct badge, setup cost text, link them
                if "X" not in cost_text:
                    cost_text = int(cost_text)
                    if cost_text > 0:
                        self.badge[i] = tools.get_layer("Plus", "Loyalty", "PW").duplicate()
                    elif cost_text < 0:
                        self.badge[i] = tools.get_layer("Minus", "Loyalty", "PW").duplicate()
                    else:
                        self.badge[i] = tools.get_layer("Zero", "Loyalty", "PW").duplicate()
                else:
                    if "-" in cost_text or "—" in cost_text:
                        self.badge[i] = tools.get_layer("Minus", "Loyalty", "PW").duplicate()
                    else:
                        self.badge[i] = tools.get_layer("Plus", "Loyalty", "PW").duplicate()

                # Setup cost text layer
                cost = tools.get_layer(
                    "Cost", "PW Ability", "Text and Icons"
                ).duplicate()
                cost.visible = True
                self.badge[i].visible = True
                self.tx_layers += [
                    PWLoyaltyCost(
                        layer=cost,
                        contents=str(cost_text),
                        color=tools.rgbcolor(255,255,255),
                        badge=self.badge[i],
                    )
                ]

                # Fix ability text
                centered = False
                ability_text = ability[colon_index+2:]
                self.rules_text[i] = tools.get_layer(
                    "Activated", "PW Ability", "Text and Icons"
                ).duplicate() if ability != oracle_array[-1] else tools.pw_ability_shift(
                    tools.get_layer(
                        "Rules Text - Creature", "Text and Icons"
                    ).duplicate()
                )

            else:
                # Fix ability text
                centered = bool("\n" not in ability and "\r" not in ability)
                ability_text = ability
                self.rules_text[i] = tools.get_layer(
                    "Static", "PW Ability", "Text and Icons"
                ).duplicate() if ability != oracle_array[-1] else tools.get_layer(
                        "Rules Text - Creature", "Text and Icons"
                ).duplicate()

            self.rules_text[i].visible = True
            self.tx_layers += [
                txt_layers.FormattedTextField(
                    layer=self.rules_text[i],
                    contents=ability_text,
                    centered=centered,
                )
            ]

        loyalty = tools.get_layer("Loyalty", "PW Ability", "Text and Icons")
        badge = tools.get_layer("Badge", "PW")
        loyalty.visible = True
        badge.visible = True
        self.tx_layers += [
            PWLoyaltyCost(
                layer=loyalty,
                contents=self.layout.loyalty,
                badge=badge,
            )
        ]
    
    def post_text_layers(self):

        doc = app.activeDocument

        type_layer = tools.get_layer("Typeline", "Text and Icons")
        textbox_ref = tools.get_layer("Textbox", "Ref")
        overlay = tools.get_layer("Overlay", "Textbox")
        overlay.visible = True

        black, white = tools.rgbcolor(0,0,0), tools.rgbcolor(255,255,255)

        left, right = textbox_ref.bounds[0], textbox_ref.bounds[2]
        
        # establish new text size
        txtbx_h = psd.get_layer_dimensions(textbox_ref)["height"]
        txt_h = 0
        for i, layer in enumerate(self.rules_text):
            txt_h += (layer.bounds[3]-layer.bounds[1])+60
        txt_h -= 60
        size_adjust = max(
            round(self.rules_text[0].textItem.size - 2 * ((txt_h / txtbx_h) ** 2), 1),
            6
        )
        
        # going from bottom to top
        for i, layer in reversed(list(enumerate(self.rules_text))):
            layer.textItem.size = size_adjust
            layer.textItem.leading = size_adjust
            overlay_height = (layer.bounds[3]-layer.bounds[1]) + 60
            doc.activeLayer = overlay
            if layer == self.rules_text[-1]:
                bottom = textbox_ref.bounds[3]
                tools.creature_text_path_shift(
                    layer,
                    bottom-layer.bounds[3]-30
                    )
                diff = overlay_height-(layer.bounds[3]-layer.bounds[1]+60)
                if diff < 0:
                    tools.creature_text_path_shift(layer, diff)
                    overlay_height -= diff
            else:
                bottom = top
            top = bottom - overlay_height
            doc.selection.select(
                [[left, top], [right, top], [right, bottom], [left, bottom]]
            )
            doc.selection.fill(black if i % 2 == 0 else white)
            if self.badge[i]:
                doc.activeLayer = self.badge[i]
                psd.align_vertical()

            # Add divider
            if i > 0:
                divider = tools.get_layer("Divider", "Loyalty", "PW").duplicate()
                divider.visible = True
                tools.select_nonblank_pixels(divider)
                divider.translate(0, (top - 2) - doc.selection.bounds[1])
                doc.selection.deselect()

            layer.translate(0, top+30-layer.bounds[1])

        delta = self.rules_text[0].bounds[1]-textbox_ref.bounds[1]-30
        tools.layer_vert_stretch(textbox_ref, delta)
        tools.layer_vert_stretch(self.art_reference, -delta/2, "top")
        type_layer.translate(0, delta)

        if presh_config.borderless:
            tools.get_layer("Normal", "Mask Wearer", "Border").visible = False
            psd.frame_layer(self.art_layer, self.art_reference)
            psd.content_fill_empty_area(self.art_layer)

        tools.select_nonblank_pixels(tools.get_layer("Name", "Mask Wearer", "Name"))
        tools.select_nonblank_pixels(tools.get_layer("Mask Wearer", "Type"), "Add ")
        tools.select_nonblank_pixels(tools.get_layer("Base", "Textbox"), "Add ")
        crt_tools.lens_blur(self.art_layer, 24, 1, 224, 1)
        app.activeDocument.selection.deselect()


class PWTransformFullArtTemplate(PWFullArtModularTemplate):
    def text_layers(self):

        DFCModularTemplate.transform(self)
        super().text_layers()


class PixelModularTemplate(temp.StarterTemplate):
    """
    Expandable pixel-art template
    100dpi start, then can blow up to 800dpi with the CRT filter
    """

    def template_file_name(self):
        return "preshtildeath/pixel-template"

    def template_suffix(self):
        suffix = "PXL Mod"  # Base suffix
        try:
            if cfg.save_jpeg:
                test_file = f"{self.layout.name} ({suffix}).jpg"
            else:
                test_file = f"{self.layout.name} ({suffix}).png"
            end_file = tools.filename_append(
                test_file, os.path.join(con.cwd, "out")
            )  # Check for multiples
            end_file = os.path.splitext(os.path.basename(end_file))[
                0
            ]  # Cut to basename, then strip extension
            end_file = end_file[
                end_file.find("(") + 1 : end_file.rfind(")")
            ]  # Take out everything between first "(" and last ")"
            return end_file  # "Base suffix) (x"
        except:
            return suffix

    def load_artwork(self): pass

    def collector_info(self):
        pass

    def __init__(self, layout):

        # Setup some parameters
        app.preferences.interpolation = ps.ResampleMethod.NearestNeighbor
        cfg.remove_flavor = True
        cfg.remove_reminder = True

        try:
            con.font_rules_text = app.fonts.getByName("m5x7").name
            con.font_rules_text_italic = app.fonts.getByName("Silver").name
        except:
            console.update("'m5x7' or 'Silver' fonts not found, oops! Sticking to defaults.")

        layout.oracle_text = re.sub(r"[—•]", "-", layout.oracle_text)

        # If inverted or circle-less, inner symbols are colored and background circle is black
        if presh_config.invert_mana or not presh_config.symbol_bg:
            for c in [("rgb_" + s) for s in (list("wubrgc") + ["bh"])]:
                setattr(con, c, {"r": 13, "g": 13, "b": 13})
            con.rgb_primary = {"r": 217, "g": 217, "b": 217}
            con.rgbi_c = {"r": 217, "g": 217, "b": 217}
            con.rgbi_w = {"r": 255, "g": 255, "b": 255}
            con.rgbi_u = {"r": 64, "g": 134, "b": 255}
            con.rgbi_bh = {"r": 125, "g": 0, "b": 255}
            con.rgbi_b = {"r": 125, "g": 0, "b": 255}
            con.rgbi_r = {"r": 255, "g": 128, "b": 128}
            con.rgbi_g = {"r": 128, "g": 255, "b": 128}
        else:
            con.rgb_c = {"r": 217, "g": 217, "b": 217}
            con.rgb_w = {"r": 255, "g": 255, "b": 255}
            con.rgb_u = {"r": 64, "g": 134, "b": 255}
            con.rgb_bh = {"r": 125, "g": 0, "b": 255}
            con.rgb_b = {"r": 125, "g": 0, "b": 255}
            con.rgb_r = {"r": 255, "g": 128, "b": 128}
            con.rgb_g = {"r": 128, "g": 255, "b": 128}
        # Replace Q, q, and o with ^ for later deletion
        if not presh_config.symbol_bg:
            for s in con.symbols.keys():
                con.symbols[s] = re.sub(r"[Qqo]", "^", con.symbols[s])

        super().__init__(layout)

    def text_layers(self):

        # Set up text layers
        name_layer = tools.get_layer("Name", "Text")
        type_layer = tools.get_layer("Typeline", "Text")
        mana_layer = tools.get_layer("Mana", "Text")
        self.body_layer = tools.get_layer("Oracle", "Text")
        self.art_reference = tools.get_layer("Art Ref", "Ref")

        # Set artist info
        artist_text = tools.get_layer("Artist", "Legal").textItem
        artist_text.contents = self.layout.artist

        # Name, Type, Mana, and Body text
        self.tx_layers.extend(
            [
                txt_layers.TextField(
                    layer=name_layer,
                    contents=self.layout.name,
                    color=psd.get_text_layer_color(name_layer),
                ),
                txt_layers.TextField(
                    layer=type_layer,
                    contents=self.layout.type_line,
                    color=psd.get_text_layer_color(type_layer),
                ),
                txt_layers.BasicFormattedTextField(
                    layer=mana_layer,
                    contents=self.layout.mana_cost,
                    color=psd.get_text_layer_color(mana_layer),
                ),
            ]
        )

        self.tx_layers += [
            txt_layers.BasicFormattedTextField(
                layer=self.body_layer,
                contents=self.layout.oracle_text,
            )
        ]

        if self.is_creature:
            power_toughness = tools.get_layer("PT Text", "Text")
            self.tx_layers += [
                txt_layers.TextField(
                    layer=power_toughness,
                    contents=f"{self.layout.power}/{self.layout.toughness}",
                )
            ]

    def enable_frame_layers(self):

        console.update("Preparing text layers...")
        self.text_layers()

        # Eldrazi formatting?
        if self.layout.is_colorless:
            # Devoid formatting?
            if self.layout.pinlines == self.layout.twins:
                self.layout.twins = "Land"
            self.layout.pinlines = "Land"
        # Twins and p/t box
        tools.get_layer(self.layout.twins, "Name").visible = True
        tools.get_layer(self.layout.twins, "Type").visible = True
        if self.is_creature:
            tools.get_layer_set("PT Box").visible = True
            tools.get_layer(self.layout.twins, "PT Box").visible = True
        # Pinlines & Textbox
        if len(self.layout.pinlines) != 2:
            tools.get_layer(self.layout.pinlines, "Pinlines").visible = True
            tools.get_layer(self.layout.pinlines, "Textbox").visible = True
        else:
            tools.wubrg_layer_sort(self.layout.pinlines, "Pinlines")
            tools.wubrg_layer_sort(self.layout.pinlines, "Textbox")
        # Land formatting
        if self.is_land:
            land_textbox = tools.get_layer("Land", "Textbox")
            if not land_textbox.visible:
                land_textbox.fillOpacity = 50
            land_textbox.visible = True

    def post_text_layers(self):

        console.update("Post text layers...")

        # Establish the layers
        name_layer = tools.get_layer("Name", "Text")
        type_layer = tools.get_layer("Typeline", "Text")
        mana_layer = tools.get_layer("Mana", "Text")
        textbox = tools.get_layer("Mask", "Textbox")
        title_pin = tools.get_layer("Title", "Pinlines")
        type_pin = tools.get_layer("Type", "Pinlines")
        doc = app.activeDocument

        # Fix any anti-aliasing and kerning weirdness
        text_layers = [name_layer, type_layer, mana_layer, self.body_layer]
        for layer in text_layers:
            layer.textItem.antiAliasMethod = ps.AntiAlias.NoAntialias
            layer.textItem.autoKerning = ps.AutoKernType.Metrics
        self.body_layer.textItem.leading *= 0.8

        # Attempt to fix type line if it goes spilling off the side
        if type_layer.bounds[2] > 233:
            if "Legendary" in self.layout.type_line:
                if "Creature" in self.layout.type_line:
                    psd.replace_text(type_layer, "Creature ", "")
                else:
                    psd.replace_text(type_layer, "Legendary ", "")
            elif "Creature" in self.layout.type_line:
                psd.replace_text(type_layer, "Creature ", "")

        # Get rid of the "^" symbols if the symbol_bg is False in our presh_config
        if not presh_config.symbol_bg:
            psd.replace_text(mana_layer, "^", "")

        # Move oracle text and resize textbox
        delta = textbox.bounds[3]-self.body_layer.bounds[3]
        self.body_layer.translate(0, delta)
        type_layer.translate(0, delta)
        textbox.resize()
        tools.layer_vert_stretch(textbox, delta)

        l, t, r, b = (
            10,
            title_pin.bounds[3] - 4,
            doc.width - 10,
            type_pin.bounds[1] + 4,
        )
        doc.selection.select([[l, t], [r, t], [r, b], [l, b]])
        doc.activeLayer = self.art_reference
        doc.selection.fill(tools.rgbcolor(0, 0, 0))

        console.update("Loading artwork...")

        # Establish size to scale down to and resize
        ref_w, ref_h = psd.get_layer_dimensions(self.art_reference).values()
        art_doc = app.load(self.layout.file)
        scale = 100 * max(ref_w / art_doc.width, ref_h / art_doc.height)
        if scale < 50:
            crt_tools.img_resize(art_doc, scale)
            app.activeDocument = art_doc
            # Dither index
            crt_tools.index_color(16, "adaptive")
        # Copy/paste into template doc, then align with art reference
        art_doc.selection.selectAll()
        art_doc.selection.copy()
        art_doc.close(ps.SaveOptions.DoNotSaveChanges)
        doc.activeLayer = self.art_layer
        doc.paste()
        tools.frame(self.art_layer, self.art_reference, False, resample="nearestNeighbor")

        # Blow up to 800dpi, and do the CRT filter if presh_config says to
        crt_tools.blow_up(presh_config.crt_filter)

    def post_execute(self):
        if presh_config.move_art:
            # Move art source to a new folder
            console.update("Moving art file...")
            tools.move_art(self.layout, self.set)
