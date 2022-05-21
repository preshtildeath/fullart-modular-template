"""
PRESHTILDEATH TEMPLATES
"""
import os
import re
import time
import tools
import crt_tools
import proxyshop.text_layers as txt_layers
import proxyshop.templates as temp
import proxyshop.helpers as psd
from proxyshop.constants import con
from proxyshop.settings import cfg
from proxyshop import gui
import photoshop.api as ps
from configs import presh_config

console = gui.console_handler
app = ps.Application()

# Ensure scaling with pixels, font size with points
app.preferences.rulerUnits = ps.Units.Pixels
app.preferences.typeUnits = ps.Units.Points


"""
Functions and Classes live here that multiple templates want to use
"""
class ModTextaArea (txt_layers.FormattedTextArea):

    def __init__(self, layer, contents, text_color, flavor_text, ref_lyr, is_centered=False):
        super().__init__(layer, contents, text_color, flavor_text, ref_lyr, is_centered, False)

    def execute(self):
        super().execute()
        self.layer.translate(0, -10)


class CreatureModTextaArea (txt_layers.CreatureFormattedTextArea):

    def __init__(self, layer, contents, text_color, flavor_text, ref_lyr, pt_ref_lyr, pt_top_ref_lyr, is_centered=False):
        super().__init__(layer, contents, text_color, flavor_text, ref_lyr, pt_ref_lyr, pt_top_ref_lyr, is_centered, False)

    def execute(self):
        super().execute()
        self.layer.translate(0, -10)


# For templates like PW, Leveler, Saga, and Class
class PWLoyaltyCost (txt_layers.TextField):

    def __init__ (self, layer, text_contents, text_color, badge):

        super().__init__(layer, text_contents, text_color)
        self.badge = badge

    def execute (self):

        super().execute()
        doc = app.activeDocument

        tools.magic_wand_select(self.badge, 10, 10)
        doc.selection.invert()
        doc.activeLayer = self.layer
        psd.align_vertical()

        if "—" in self.text_contents or "-" in self.text_contents:
            layer_w = self.layer.bounds[2] - self.layer.bounds[0]
            text_l = len(self.text_contents)
            delta = ((1 / text_l) * layer_w) / 3
            self.layer.translate(-delta, 0)

        badge_scale(self.layer, self.badge, expand=True)


class FormattedTextBottom (ModTextaArea):

    def __init__(self, layer, content, color, flavor, ref_lyr, badge, is_centered=False):
        super().__init__(layer, content, color, flavor, ref_lyr, is_centered, False)
        self.badge = badge

    def execute(self):
        super().execute()
        badge_scale(self.layer, self.badge, expand=True, invert=True)

        # psd.select_layer_pixels(self.reference_layer)
        # app.activeDocument.activeLayer = self.layer
        # psd.align_vertical()


def badge_scale(layer, badge, expand=False, invert=False):

    doc = app.activeDocument
    textitem = layer.textItem

    while True:

        layer_copy = layer.duplicate(app.activeDocument, ps.ElementPlacement.PlaceInside)
        layer_copy.rasterize(ps.RasterizeType.TextContents)
        tools.magic_wand_select(badge, 10, 10)
        if invert:
            doc.selection.invert()
        if expand:
            doc.selection.expand(16)
        tools.magic_wand_select(layer_copy, 10, 10, "interfaceWhite")
        doc.selection.invert()
        doc.selection.clear()
        doc.selection.deselect()
        w, h = psd.compute_layer_dimensions(layer_copy)
        layer_copy.remove()

        if w == 0 or h == 0:
            return True

        textitem.size -= 0.2
        if "Minus" in badge.name:
            textitem.baselineShift += 0.3
        elif "Zero" in badge.name:
            textitem.baselineShift += 0.15
    

def move_art(layout):
    console.update("Moving art file...")

    # Set up paths and determine file extension
    work_path = os.path.dirname(layout.file)
    new_name = f"{layout.name} ({layout.artist}) [{layout.set}]"
    ext = os.path.splitext(os.path.basename(layout.file))[1]
    layout_type = type(layout).__name__

    if "finished" not in work_path:
        fin_path = os.path.join(work_path, "finished")
        if layout_type != "NormalLayout":
            fin_path = os.path.join(fin_path, layout_type)
    else:
        fin_path = work_path

    if not os.path.exists(fin_path):
        os.mkdir(fin_path)

    new_file = os.path.join(fin_path, f"{new_name}{ext}")
    try:
        if new_file != layout.file:
            os.replace(layout.file, tools.filename_append(new_file, fin_path))
    except Exception as e:
        console.update("Could not move art file!", exception=e)


class FullArtModularTemplate(temp.StarterTemplate):
    """
    Created by preshtildeath
    Expands the textbox based on how much oracle text a card has
    Also expanding this template to service other card types
    """

    def template_file_name(self):
        return "preshtildeath/fullart-modular"

    def template_suffix (self):

        try:
            if cfg.save_jpeg:
                test_file = f"{self.layout.name} ({self.suffix}).jpg"
            else:
                test_file = f"{self.layout.name} ({self.suffix}).png"

            # Check for multiples
            end_file = tools.filename_append(
                test_file, os.path.join(con.cwd, "out")
            )

            # Cut to basename, then strip extension, then isolate suffix
            end_file = os.path.splitext(os.path.basename(end_file))[0]  
            end_file = end_file[
                end_file.find("(") + 1 : end_file.rfind(")")
            ]
            return end_file  # "Base suffix) (x"
        except:
            return self.suffix

    def load_artwork(self):

        # Loads the specified art file into the specified layer.
        psd.paste_file(self.art_layer, self.layout.file)
        tools.zero_transform(self.art_layer)

    def collector_info(self): pass

    def __init__(self, layout):

        self.suffix = "Full Mod"
        app.preferences.interpolation = ps.ResampleMethod.BicubicAutomatic
        cfg.remove_flavor = True
        cfg.remove_reminder = True

        super().__init__(layout)
        
        filename = os.path.splitext(os.path.basename(layout.file))[0]
        if filename.rfind("[") < filename.rfind("]"):
            self.set = filename[filename.rfind("[") + 1 : filename.rfind("]")].upper()
        else:
            self.set = layout.set

        # Check presh_config
        if presh_config.hollow_mana:
            # con.rgb_primary = {"r": 194, "g": 194, "b": 194}
            # con.rgb_c = {"r": 194, "g": 194, "b": 194}
            # con.rgb_w = {"r": 232, "g": 232, "b": 230}
            # con.rgb_u = {"r": 0, "g": 122, "b": 196}
            # con.rgb_b = {"r": 70, "g": 48, "b": 71}
            # con.rgb_bh = {"r": 70, "g": 48, "b": 71}
            # con.rgb_r = {"r": 233, "g": 63, "b": 46}
            # con.rgb_g = {"r": 0, "g": 134, "b": 80}
            con.rgbi_c = {"r": 194, "g": 194, "b": 194}
            con.rgbi_w = {"r": 232, "g": 232, "b": 230}
            con.rgbi_u = {"r":  64, "g": 185, "b": 255}
            con.rgbi_b = {"r": 147, "g":  31, "b": 153}
            con.rgbi_bh ={"r": 147, "g":  31, "b": 153}
            con.rgbi_r = {"r": 255, "g": 140, "b": 128}
            con.rgbi_g = {"r":  22, "g": 217, "b": 139}
            for c in [("rgb_"+s) for s in (list("wubrgc")+["bh", "primary"])]:
                setattr(con, c, {"r": 250, "g": 250, "b": 250})
            for sym in con.symbols:
                con.symbols[sym] = re.sub("[Qqo]", "v", con.symbols[sym])

        # Define some characteristics
        if not hasattr(self, "is_planeswalker"):
            self.is_planeswalker = False
        if not hasattr(self, "is_basic"):
            self.is_basic = False
        if hasattr(layout, "type_line"):
            if layout.type_line.find("Land") >= 0 or self.is_basic:
                self.is_land = True
        else:
            self.is_land = False

        # Choose your border
        if self.is_land:
            self.art_reference = tools.get_layer("Full Art Frame", "Ref")
        elif self.is_legendary:
            self.art_reference = tools.get_layer("Legendary Frame", "Ref")
        else:
            self.art_reference = tools.get_layer("Art Frame", "Ref")

    def text_layers(self):
        console.update("Preparing text layers...")

        # Set up some layers
        mana_layer = tools.get_layer("Text", "Mana Cost")
        name_layer = tools.get_layer("Card Name", "Text and Icons")
        exp_layer = tools.get_layer("Expansion Symbol", "Expansion")
        exp_ref = tools.get_layer("Expansion", "Ref")
        type_layer = tools.get_layer("Typeline", "Text and Icons")
        self.textbox_ref = tools.get_layer("Textbox", "Ref")

        # Move typeline and modify textbox reference and text outlines if certain criteria is met
        scale = tools.dirty_text_scale(self.layout.oracle_text, 36)
        if self.is_creature:
            if scale > 9:
                modifier = -320
            elif scale > 6:
                modifier = -160
            elif scale <= 1:
                modifier = 240
            elif scale <= 3:
                modifier = 160
            else:
                modifier = 0
        else:
            if scale > 0:
                modifier = max(480 - ((scale * 68) + 112), -600)
            else:
                modifier = 480

        # Apply typeline translate and textbox stretch
        type_layer.translate(0, modifier)
        tools.layer_vert_stretch(self.textbox_ref, modifier, "bottom")

        # Set artist info
        artist_text = tools.get_layer("Artist", "Legal").textItem
        artist_text.contents = self.layout.artist

        # Set symbol
        set_pdf = tools.get_set_pdf(self.set)
        exp_layer = tools.get_expansion(
            exp_layer, self.layout.rarity, exp_ref, set_pdf
        )

        # Mana, Name, and Type text
        self.tx_layers.extend(
            [
                txt_layers.BasicFormattedTextField(
                    layer=mana_layer,
                    text_contents=self.layout.mana_cost,
                    text_color=tools.rgbcolor(0, 0, 0),
                ),
                txt_layers.ScaledTextField(
                    layer=type_layer,
                    text_contents=self.layout.type_line,
                    text_color=psd.get_text_layer_color(type_layer),
                    reference_layer=exp_layer,
                ),
                txt_layers.ScaledTextField(
                    layer=name_layer,
                    text_contents=self.layout.name,
                    text_color=psd.get_text_layer_color(name_layer),
                    reference_layer=mana_layer,
                ),
            ]
        )

        if self.is_creature:

            # Center the rules text if the text is at most two lines
            is_centered = bool(scale <= 2)

            # Creature card - set up creature layer for rules text and insert p/t
            power_toughness = tools.get_layer("Power / Toughness", "Text and Icons")
            rules_text = tools.get_layer(
                f"Rules Text - Creature {modifier}", "Text and Icons"
            )
            self.tx_layers.extend(
                [
                    txt_layers.TextField(
                        layer=power_toughness,
                        text_contents=f"{self.layout.power}/{self.layout.toughness}",
                        text_color=psd.get_text_layer_color(power_toughness),
                    ),
                    CreatureModTextaArea(
                        layer=rules_text,
                        text_contents=self.layout.oracle_text,
                        text_color=psd.get_text_layer_color(rules_text),
                        flavor_text=self.layout.flavor_text,
                        ref_lyr=self.textbox_ref,
                        pt_ref_lyr=tools.get_layer("PT Adjustment", "Ref"),
                        pt_top_ref_lyrr=tools.get_layer("PT Top", "Ref"),
                        is_centered=is_centered
                    )
                ]
            )

        elif not self.is_planeswalker:

            # Center the rules text if the text is at most four lines
            is_centered = bool(scale <= 4)

            # Noncreature card - use the normal rules text layer and disable the p/t layer
            tools.get_layer("Power / Toughness", "Text and Icons").visible = False
            rules_text = tools.get_layer("Rules Text - Noncreature", "Text and Icons")
            rules_text.translate(0, modifier)
            self.tx_layers += [
                ModTextaArea(
                    layer=rules_text,
                    contents=self.layout.oracle_text,
                    text_color=psd.get_text_layer_color(rules_text),
                    flavor_text=self.layout.flavor_text,
                    ref_lyr=self.textbox_ref,
                    is_centered=is_centered
                )
            ]

    def enable_frame_layers(self):

        # Initialize our text layers
        self.text_layers()

        # Eldrazi formatting?
        if self.layout.is_colorless:

            # Devoid formatting?
            if self.layout.pinlines != self.layout.twins:
                self.layout.pinlines = "Land"
            else:
                self.layout.pinlines = "Land"
                self.layout.twins = "Land"
            tools.get_layer(self.layout.twins, "Border").visible = True
        if self.layout.is_nyx:
            tools.get_layer(f"Nyx {self.layout.pinlines}", "Border").visible = True

        # Twins and p/t box
        tools.get_layer(self.layout.twins, "Name").visible = True
        tools.get_layer(self.layout.twins, "Type").visible = True
        if self.is_creature:
            tools.get_layer(self.layout.twins, "PT Box").visible = True

        # Pinlines & Textbox
        if len(self.layout.pinlines) != 2:
            tools.get_layer(self.layout.pinlines, "Pinlines").visible = True
            tools.get_layer(self.layout.pinlines, "Textbox").visible = True
        else:
            tools.wubrg_layer_sort(self.layout.pinlines, "Pinlines")
            tools.wubrg_layer_sort(self.layout.pinlines, "Textbox")
        tools.get_layer("Side Pinlines", "Masked", "Pinlines").visible = presh_config.side_pins

        # legendary crown
        if self.is_legendary:
            if presh_config.side_pins:
                style = "Legendary"
            else:
                style = "Floating"
            tools.get_layer(f"{style} Crown", "Masked", "Pinlines").visible = True
            title_ref = tools.get_layer(style, "Ref")
            if not self.is_land:
                tools.get_layer("Crown Mask", "Mask Wearer", "Border").visible = True
        else:
            title_ref = tools.get_layer("Title", "Ref")

        # Give the lands a sexy transparent border
        if self.is_land:
            land_textbox = tools.get_layer("Land", "Textbox")
            if not land_textbox.visible:
                land_textbox.fillOpacity = 50
                land_textbox.visible = True
            app.activeDocument.activeLayer = tools.get_layer("Normal", "Mask Wearer", "Border")
            psd.enable_active_layer_mask()
            if len(self.layout.pinlines) != 2:
                tools.get_layer(self.layout.pinlines, "Border").visible = True
            else:
                tools.wubrg_layer_sort(self.layout.pinlines, "Border")

        # Give colored artifacts the grey pinlines on the sides of the art and main textbox
        if self.layout.pinlines != "Artifact" and self.layout.background == "Artifact":

            # Set textbox to artifact
            tools.get_layer(self.layout.background, "Textbox").visible = True

            # Point to type reference (title reference is set in the legendary check)
            type_ref = tools.get_layer("Type", "Ref")

            # Apply artifact clipping mask
            pin_mask = tools.get_layer(self.layout.background, "Pinlines")
            pin_mask.visible = True

            # Enable layer mask
            app.activeDocument.activeLayer = pin_mask
            psd.enable_active_layer_mask()

            # Modify layer mask
            psd.clear_selection()
            tools.add_select_layer(title_ref)  # Create selection based on the type box
            tools.add_select_layer(type_ref)  # Add to selection based on the title box
            tools.layer_mask_select(pin_mask)  # Select the layer mask
            app.activeDocument.selection.fill(
                tools.rgbcolor(0, 0, 0)
            )  # Fill it with black
            app.activeDocument.selection.deselect()  # Deselect

    def post_execute(self):

        con.reload()

        if presh_config.move_art:
            move_art(self.layout)


class FullArtTextlessTemplate (FullArtModularTemplate):
    # Useful for textless duals.
    # TODO: Tweak layout for creatures so they can get rid of textbox

    def __init__(self, layout):
        layout.oracle_text = ""
        super().__init__(layout)


class BasicModularTemplate (FullArtModularTemplate):

    def __init__(self, layout):

        self.suffix = f"{self.layout.artist}) ({self.set}"  # Base suffix
        self.is_basic = True
        self.name_key = {
            "Plains": "W",
            "Island": "U",
            "Swamp": "B",
            "Mountain": "R",
            "Forest": "G",
        }
        
        super().__init__(layout)

    def text_layers(self):

        # Define some layers
        name_layer = tools.get_layer("Card Name", "Text and Icons")
        exp_layer = tools.get_layer("Expansion Symbol", "Expansion")
        exp_ref = tools.get_layer("Expansion", "Ref")
        type_layer = tools.get_layer("Typeline", "Text and Icons")
        text_ref = tools.get_layer("Textbox", "Ref")

        # Apply typeline translate and textbox stretch
        type_layer.translate(0, 480)
        text_ref.resize(100, 0, 7)

        # Set artist info
        artist_text = tools.get_layer("Artist", "Artist").textItem
        artist_text.contents = self.layout.artist

        # Name and type text
        self.tx_layers.extend(
            [
                txt_layers.TextField(
                    layer=name_layer,
                    text_contents=self.layout.name,
                    text_color=psd.get_text_layer_color(name_layer),
                ),
                txt_layers.TextField(
                    layer=type_layer,
                    text_contents=f"Basic Land — {self.layout.name}",
                    text_color=psd.get_text_layer_color(type_layer),
                ),
            ]
        )
        # Set symbol
        set_pdf = tools.get_set_pdf(self.set)
        tools.get_expansion(exp_layer, "common", exp_ref, set_pdf)

    def enable_frame_layers(self):
        layer_name = self.name_key[self.layout.name]
        for target in ["Pinlines", "Name", "Type", "Border"]:
            tools.get_layer(layer_name, target).visible = True
        for target in ["Name", "Type"]:
            layer = tools.get_layer("Land", target)
            tools.set_opacity(layer, 50)
            layer.visible = True


class DFCModularTemplate(FullArtModularTemplate):
    # One-size-fits-all for MDFC Front, MDFC Back, Transform, and Ixalan land back. Lessons too, I guess.
    def transform (self):

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
        if self.layout.transform_icon == "modal_dfc":
            dfc = "MDFC"
            tools.get_layer(dfc, mask_wearer).visible = True
        else:
            dfc = "TDFC"
            tools.get_layer(dfc, "Name").visible = True
        mask_wearer = tools.get_layer_set("Mask Wearer", "Name")
        tools.get_layer("Name", mask_wearer).visible = False
        tools.get_layer("DFC", mask_wearer).visible = True

        # Setup transform icon
        dfc_icon = tools.get_layer(dfc, "Text and Icons")
        dfc_icon.textItem.contents = trans_icon[self.layout.transform_icon][self.layout.face]
        dfc_icon.visible = True

        # Cut out the icon from the legendary frame if necessary
        dfc_pin = tools.get_layer(dfc, "Masked", "Pinlines")
        if self.is_legendary:
            legend_mask = tools.get_layer(f"{top} Crown", "Masked", "Pinlines")
            tools.magic_wand_select(dfc_pin, 0, 0)
            app.activeDocument.selection.expand(2)
            app.activeDocument.selection.invert()
            tools.layer_mask_select(legend_mask)
            app.activeDocument.selection.fill(tools.rgbcolor(0, 0, 0))
            app.activeDocument.selection.deselect()

        # Turn on/off pinlines
        tools.get_layer("Standard", "Masked", "Pinlines").visible = False
        dfc_pin.visible = True

    def text_layers(self):

        super().text_layers()
        self.transform()


class PWFullArtModularTemplate (FullArtModularTemplate):
    
    def __init__(self, layout):

        self.is_planeswalker = True
        super().__init__(layout)

    def text_layers(self):

        super().text_layers()

        # Establish arrays for abilities
        doc = app.activeDocument
        reference = tools.get_layer("Textbox", "Ref")
        left, right = reference.bounds[0], reference.bounds[2]
        ref_h = psd.compute_layer_dimensions(reference)["height"]
        b, w = [0]*3, [255]*3
        black, white = tools.rgbcolor(*b), tools.rgbcolor(*w)
        oracle_array = self.layout.oracle_text.split("\n")
        # oracle_len = len(self.layout.oracle_text)
        overlay = tools.get_layer("Overlay", "Textbox").duplicate()
        centered = False 

        """
        Testing pre-establishing text size
        """
        try:

            text_layer = tools.get_layer("Static", "PW Ability", "Text and Icons").duplicate()
            text_layer.visible = True

            temp_text = self.layout.oracle_text.replace("\n", "\r")
            temp_text = re.sub('\{.*?\}', 'X', temp_text)
            text_layer.textItem.contents = temp_text
            
            text_heights = []

            txt_layers.scale_text_to_fit_reference(text_layer, reference)
            
            for i, line in enumerate(temp_text.split("\r")):
                text_layer.textItem.contents = line
                tools.magic_wand_select(text_layer, 0, 0)
                doc.selection.invert()
                bounds = doc.selection.bounds
                height = bounds[3] - bounds[1]
                text_heights += [height]
            text_layer.textItem.contents = ""
            text_layer.remove()

            text_heights = list(map(lambda x: x + 40, text_heights))
            text_h = sum(text_heights)
            text_size = text_layer.textItem.size

        except:
            print("Nope")

        for i, ability in enumerate(oracle_array):

            # # Draw overlay
            # overlay_height = (len(ability) / oracle_len) * ref_h
            overlay_height = (text_heights[i] / text_h) * ref_h
            overlayer = overlay.duplicate()
            doc.activeLayer = overlayer
            if i == 0:
                top = reference.bounds[1]
            else:
                top = bottom
            if i == len(oracle_array):
                bottom = reference.bounds[3]
            else:
                bottom = top + overlay_height
            doc.selection.select([
                [left, top],
                [right, top],
                [right, bottom],
                [left, bottom]
            ])
            if i % 2 == 0:
                doc.selection.fill(black)
            else:
                doc.selection.fill(white)

            # Determing if the ability is activated
            colon_index = ability.find(": ")
            if colon_index > 0 < 5:

                # Determine cost text
                cost_text = ability[:colon_index]

                # Grab correct badge, setup cost text, link them
                if "X" not in cost_text:
                    cost_text = int(cost_text)
                    if cost_text > 0:
                        badge = tools.get_layer("Plus", "Loyalty", "PW").duplicate()
                    elif cost_text < 0:
                        badge = tools.get_layer("Minus", "Loyalty", "PW").duplicate()
                    else:
                        badge = tools.get_layer("Zero", "Loyalty", "PW").duplicate()
                else:
                    if "-" in cost_text or "—" in cost_text:
                        badge = tools.get_layer("Minus", "Loyalty", "PW").duplicate()
                    else:
                        badge = tools.get_layer("Plus", "Loyalty", "PW").duplicate()

                # Setup cost text layer
                cost = tools.get_layer("PW Cost", "Text and Icons").duplicate()
                doc.activeLayer = badge
                psd.align_vertical()
                doc.selection.deselect()
                self.tx_layers += [
                    PWLoyaltyCost(
                        layer=cost,
                        text_contents=str(cost_text),
                        text_color=white,
                        badge=badge
                    )
                ]

                # Fix ability text
                centered = False
                ability_text = ability[colon_index+2:]
                ability_layer = tools.get_layer("Activated", "PW Ability", "Text and Icons").duplicate()

            else:
                # Fix ability text
                centered = True
                ability_text = ability
                ability_layer = tools.get_layer("Static", "PW Ability", "Text and Icons").duplicate()

            ability_layer.translate(0, top + 20 - ability_layer.bounds[1])
            ability_layer.textItem.size = text_size

            # Add divider
            if i > 0:
                divider = tools.get_layer("Divider", "Loyalty", "PW").duplicate()
                tools.magic_wand_select(divider, 0, 0)
                doc.selection.invert()
                bounds = doc.selection.bounds
                divider.translate(0, top-2-bounds[1])
                doc.selection.deselect()
            
            overlayer = overlayer.duplicate(reference, ps.ElementPlacement.PlaceAfter)
            if i < len(oracle_array):
                self.tx_layers += [
                    ModTextaArea(
                        layer=ability_layer,
                        contents=ability_text,
                        text_color=white,
                        flavor_text=self.layout.flavor_text,
                        ref_lyr=overlayer,
                        is_centered=centered
                    )
                ]
            else:
                self.tx_layers += [
                    FormattedTextBottom(
                        layer=ability_layer,
                        text_contents=ability_text,
                        text_color=white,
                        flavor_text=self.layout.flavor_text,
                        ref_lyr=overlayer,
                        badge=tools.get_layer("Badge", "PW"),
                        is_centered=centered
                    )
                ]
        
        tools.get_layer("Badge", "PW").visible = True
        self.tx_layers += [
            txt_layers.TextField(
                layer=tools.get_layer("Power / Toughness", "Text and Icons"),
                text_contents=self.layout.loyalty,
                text_color=white
            )
        ]


class PWTransformFullArtTemplate (PWFullArtModularTemplate):

    def text_layers(self):

        DFCModularTemplate.transform(self)
        super().text_layers()


class PixelModularTemplate(temp.StarterTemplate):
    """
    Created by preshtildeath
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

    def load_artwork(self):

        console.update("Loading artwork...")

        # Establish size to scale down to and resize
        ref_w = self.art_reference.bounds[2] - self.art_reference.bounds[0]
        ref_h = self.art_reference.bounds[3] - self.art_reference.bounds[1]
        art_doc = app.load(self.layout.file)
        scale = 100 * max(ref_w / art_doc.width, ref_h / art_doc.height)
        if scale < 50:
            crt_tools.img_resize(art_doc, scale)
            app.activeDocument = art_doc
            # Dither index
            crt_tools.index_color(16, "adaptive")
        # Copy/paste into template doc, then align with art reference
        app.activeDocument.selection.selectAll()
        app.activeDocument.selection.copy()
        art_doc.close(ps.SaveOptions.DoNotSaveChanges)
        app.activeDocument.activeLayer = self.art_layer
        app.activeDocument.paste()
        psd.select_layer_pixels(self.art_reference)
        psd.align_horizontal()
        psd.align_vertical()
        psd.clear_selection()
        tools.zero_transform(layer=self.art_layer, i="nearestNeighbor")

    def collector_info(self):
        pass

    def __init__(self, layout):

        # Setup some parameters
        app.preferences.interpolation = ps.ResampleMethod.NearestNeighbor
        cfg.remove_flavor = True
        cfg.remove_reminder = True
        con.font_rules_text = "m5x7"
        con.font_rules_text_italic = "Silver"

        # If inverted or circle-less, inner symbols are colored and background circle is black
        if presh_config.invert_mana or not presh_config.symbol_bg:
            for c in [("rgb_"+s) for s in (list("wubrgc")+["bh"])]:
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
                con.symbols[s] = re.sub("[Qqo]", "^", con.symbols[s])
        super().__init__(layout)

        self.text_layers()

    def text_layers(self):

        console.update("Preparing text layers...")

        # Set up text layers
        name_layer = tools.get_layer("Name", "Text")
        type_layer = tools.get_layer("Typeline", "Text")
        mana_layer = tools.get_layer("Mana", "Text")
        body_layer = tools.get_layer("Oracle", "Text")
        textbox = tools.get_layer("Mask", "Textbox")
        self.art_reference = tools.get_layer("Art Ref", "Ref")
        title_pin = tools.get_layer("Title", "Pinlines")
        type_pin = tools.get_layer("Type", "Pinlines")

        # Set artist info
        artist_text = tools.get_layer("Artist", "Legal").textItem
        artist_text.contents = self.layout.artist

        # Name, Type, Mana, and Body text
        self.tx_layers.extend(
            [
                txt_layers.TextField(
                    layer=name_layer,
                    text_contents=self.layout.name,
                    text_color=psd.get_text_layer_color(name_layer),
                ),
                txt_layers.TextField(
                    layer=type_layer,
                    text_contents=self.layout.type_line,
                    text_color=psd.get_text_layer_color(type_layer),
                ),
                txt_layers.BasicFormattedTextField(
                    layer=mana_layer,
                    text_contents=self.layout.mana_cost,
                    text_color=psd.get_text_layer_color(mana_layer),
                ),
            ]
        )

        body_text = txt_layers.BasicFormattedTextField(
            layer=body_layer,
            text_contents=self.layout.oracle_text,
            text_color=psd.get_text_layer_color(body_layer),
        )
        body_text.execute()
        body_layer.textItem.antiAliasMethod = ps.AntiAlias.NoAntialias
        body_layer.textItem.leading *= 0.8

        if self.is_creature:
            power_toughness = tools.get_layer("PT Text", "Text")
            self.tx_layers += [
                txt_layers.TextField(
                    layer=power_toughness,
                    text_contents=f"{self.layout.power}/{self.layout.toughness}",
                    text_color=psd.get_text_layer_color(power_toughness),
                )
            ]
            delta = body_layer.bounds[3] - textbox.bounds[3] + 8
        else:
            delta = body_layer.bounds[3] - textbox.bounds[3] + 3
        body_layer.translate(0, -delta)
        type_layer.translate(0, -delta)
        h_delta = textbox.bounds[3] - (type_pin.bounds[1] + 26)
        h_percent = h_delta / (textbox.bounds[3] - textbox.bounds[1]) * 100
        tools.zero_transform(textbox, "nearestNeighbor", y=-delta, h=h_percent)

        l, t, r, b = (
            10,
            title_pin.bounds[3] - 4,
            app.activeDocument.width - 10,
            type_pin.bounds[1] + 4,
        )
        app.activeDocument.selection.select([[l, t], [r, t], [r, b], [l, b]])
        app.activeDocument.activeLayer = self.art_reference
        app.activeDocument.selection.fill(tools.rgbcolor(0, 0, 0))

    def enable_frame_layers(self):

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
        body_layer = tools.get_layer("Oracle", "Text")

        # Fix any anti-aliasing and kerning weirdness
        text_layers = [name_layer, type_layer, mana_layer, body_layer]
        for layer in text_layers:
            layer.textItem.antiAliasMethod = ps.AntiAlias.NoAntialias
            layer.textItem.autoKerning = ps.AutoKernType.Metrics
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
            psd.replace_text(body_layer, "^", "")
        mana_layer.textItem.font = con.font_mana
        time.sleep(0.2)
        mana_layer.textItem.font = con.font_mana

        # Blow up to 800dpi, and do the CRT filter if presh_config says to
        crt_tools.blow_up(presh_config.crt_filter)

    def post_execute(self):
        con.reload()
        if presh_config.move_art:
            # Move art source to a new folder
            console.update("Moving art file...")
            move_art(self.layout)