"""
PRESHTILDEATH TEMPLATES
"""
import os
import re
from functools import cached_property
from typing import Optional

from proxyshop.constants import con
from proxyshop.settings import cfg
import proxyshop.text_layers as txt_layers
import proxyshop.templates as temp
import proxyshop.helpers as psd
if not con.headless:
    from proxyshop.__console__ import console
else:
    from proxyshop.core import console

import photoshop.api as ps
from photoshop.api._artlayer import ArtLayer
from photoshop.api._layerSet import LayerSet
from PIL import Image

import tools
import crt_tools

app = ps.Application()
cid = app.charIDToTypeID
sid = app.stringIDToTypeID


class PWLoyaltyCost(txt_layers.TextField):
    """Shrink loyalty ability costs to fit inside the badge."""
    def __init__(self, layer, contents, badge=None):

        super().__init__(layer=layer, contents=contents)
        self.badge = badge

    def execute(self):

        super().execute()
        
        if self.badge.name[0] in ["-", "+"]:
            # Let's just give this guy a tiny bitty nudge
            layer_w = self.layer.bounds[2]-self.layer.bounds[0]
            text_l = len(self.contents)
            delta = ((1 / (5-text_l)) * layer_w) * 0.25
            self.layer.translate(-delta, 0)

        self.layer.link(self.badge)


class FullArtModularTemplate(temp.StarterTemplate):
    """
    Created by preshtildeath.
    Expands the textbox based on how much oracle text a card has.
    Also expanding this template to service other card types.
    """

    template_file_name = "preshtildeath/fullart-modular"
    template_suffix = "Full Mod"

    @cached_property
    def do_move_art(self) -> bool:
        return cfg.get_setting(
            section="GENERAL",
            key="Move.Art",
            default=True,
            is_bool=True,
        )

    @cached_property
    def hollow_mana(self) -> bool:
        return cfg.get_setting(
            section="GENERAL",
            key="Hollow.Mana",
            default=True,
            is_bool=True,
        )

    @cached_property
    def side_pins(self) -> bool:
        return cfg.get_setting(
            section="GENERAL",
            key="Side.Pins",
            default=False,
            is_bool=True,
        )

    @cached_property
    def is_borderless(self) -> bool:
        return cfg.get_setting(
            section="GENERAL",
            key="Borderless",
            default=False,
            is_bool=True,
        )

    @cached_property
    def text_layers_group(self) -> Optional[LayerSet]:
        return tools.get_layer_set("Text and Icons", doc=self.docref)

    @cached_property
    def ref_group(self) -> Optional[LayerSet]:
        return tools.get_layer_set("Ref", doc=self.docref)

    @cached_property
    def text_layer_name(self) -> Optional[ArtLayer]:
        return tools.get_layer("Card Name", self.text_layers_group)

    @cached_property
    def text_layer_type(self) -> Optional[ArtLayer]:
        return tools.get_layer("Typeline", self.text_layers_group)

    @cached_property
    def text_layer_rules(self) -> Optional[ArtLayer]:
        if self.is_creature:
            rules_text = tools.get_layer("Rules Text - Creature", self.text_layers_group)
            rules_text.visible = True
            return rules_text
        # Noncreature card - use the normal rules text layer and disable the p/t layer
        if self.text_layer_pt.visible:
            self.text_layer_pt.visible = False
        rules_text = tools.get_layer("Rules Text - Noncreature", self.text_layers_group)
        rules_text.visible = True
        return rules_text

    @cached_property
    def text_layer_pt(self) -> Optional[ArtLayer]:
        return tools.get_layer("Power / Toughness", self.text_layers_group)

    @cached_property
    def text_layer_mana(self) -> Optional[ArtLayer]:
        return tools.get_layer("Text", "Mana Cost", doc=self.docref)

    @cached_property
    def crown_layer(self) -> Optional[ArtLayer]:
        if self.side_pins:
            return tools.get_layer("Legendary Crown", "Masked", "Pinlines", doc=self.docref)
        return tools.get_layer("Floating Crown", "Masked", "Pinlines", doc=self.docref)

    @property
    def expansion_layer(self) -> Optional[ArtLayer]:
        return tools.get_layer("Expansion Symbol", "Expansion", doc=self.docref)

    @expansion_layer.setter
    def expansion_layer(self, value):
        self._expansion_layer = value

    @cached_property
    def pt_layer(self) -> Optional[ArtLayer]:
        return tools.get_layer(self.twins, "PT Box", doc=self.docref)

    @cached_property
    def ref_layer_textbox(self) -> Optional[ArtLayer]:
        return tools.get_layer("Textbox", self.ref_group)

    @cached_property
    def ref_layer_expansion(self) -> Optional[ArtLayer]:
        return tools.get_layer("Expansion", self.ref_group)

    @cached_property
    def art_reference(self):
        # Let's pick an art reference layer
        if self.is_borderless:
            target = "Full Art Borderless"
        elif self.is_land or self.is_planeswalker:
            target = "Full Art Frame"
        elif self.is_legendary:
            target = "Legendary Frame"
        else:
            target = "Art Frame"

        ### LETS JUST TEST THE STRETCH AND FILL METHOD
        with Image.open(self.layout.filename) as im:
            im_ratio = im.height / im.width
        art_layer = tools.get_layer("Art Frame", self.ref_group)
        l, t, r, b = art_layer.bounds
        w, h = r-l, b-t
        layer = art_layer if im_ratio < h/w else tools.get_layer("Full Art Borderless", self.ref_group)
        return layer

        return tools.get_layer(target, self.ref_group)

    def get_file_name(self):
        path_txt = tools.filename_append(
                    f"{self.layout.name} ({self.template_suffix}).jpg",
                    os.path.join(con.cwd, "out")
                    )
        return os.path.splitext(os.path.basename(path_txt))[0]

    def load_artwork(self):
        doc_dpi = self.docref.resolution
        with Image.open(self.layout.filename) as im:
            if "dpi" in im.info.keys():
                img_dpi = im.info["dpi"][0]
            else: img_dpi = 72
        self.art_layer = tools.place_image(
            layer=self.art_layer,
            file=self.layout.filename,
            percent=100*(img_dpi/doc_dpi)
            )

    @property
    def is_centered(self) -> bool:
        length = 20 if self.is_creature else 120
        return bool(len(self.layout.oracle_text) <= length)

    @property
    def is_land(self) -> bool:
        return "Land" in self.layout.type_line
    
    def collector_info(self): pass

    def __init__(self, layout):

        app.preferences.interpolation = ps.ResampleMethod.BicubicAutomatic
        cfg.remove_flavor = True
        cfg.remove_reminder = True

        super().__init__(layout)

        filename = os.path.splitext(os.path.basename(layout.filename))[0]
        if filename.rfind("[") < filename.rfind("]"):
            self.set = filename[filename.rfind("[")+1 : filename.rfind("]")].upper()
        else: self.set = layout.set

        # Check config
        if self.hollow_mana:
            con.clri_c = {"r": 194, "g": 194, "b": 194}
            con.clri_w = {"r": 232, "g": 232, "b": 230}
            con.clri_u = {"r": 64, "g": 185, "b": 255}
            con.clri_b = {"r": 125, "g": 47, "b": 129}
            con.clri_bh = con.clri_b.copy()
            con.clri_r = {"r": 255, "g": 140, "b": 128}
            con.clri_g = {"r": 22, "g": 217, "b": 139}
            for c in [("clr_" + s) for s in list("wubrgc") + ["bh", "primary", "secondary"]]:
                setattr(con, c, {"r": 250, "g": 250, "b": 250})
            for k, v in con.symbols.items():
                con.symbols[k] = v.replace("o", "v").replace("Qp", "op").replace("Qq", "\u00EF\u00E8")

        # Define some characteristics
        if not hasattr(self, "is_planeswalker"):
            self.is_planeswalker = False
        if not hasattr(self, "is_basic"):
            self.is_basic = False


    def enable_frame_layers(self):

        # Set symbol
        # Maybe we change this back to the KeyRune font?
        self.expansion_layer = tools.get_expansion(
            self.expansion_layer, self.layout.rarity, self.ref_layer_expansion, self.set
        )
        self.expansion_layer.parent.link(self.text_layer_type)

        console.update("Turning on our frame elements...")

        # Twins and p/t box
        tools.get_layer(self.layout.twins, "Name", doc=self.docref).visible = True
        tools.get_layer(self.layout.twins, "Type", doc=self.docref).visible = True
        self.pt_layer.visible = self.is_creature

        # Pinlines & Textbox
        if len(self.layout.pinlines) != 2:
            tools.get_layer(self.layout.pinlines, "Pinlines", doc=self.docref).visible = True
            tools.get_layer(self.layout.pinlines, "Textbox", doc=self.docref).visible = True
        else:
            tools.wubrg_layer_sort(self.layout.pinlines, "Pinlines", doc=self.docref)
            tools.wubrg_layer_sort(self.layout.pinlines, "Textbox", doc=self.docref)
        tools.get_layer(
            "Side Pinlines", "Masked", "Pinlines", doc=self.docref
        ).visible = self.side_pins

        # Legendary crown
        if self.is_legendary:
            style = "Legendary" if self.side_pins else "Floating"
            self.crown_layer.visible = True
            self.title_ref = tools.get_layer(style, self.ref_group)
            if not bool(self.is_land or self.is_planeswalker or self.is_borderless):
                tools.get_layer("Crown Mask", "Mask Wearer", "Border", doc=self.docref).visible = True
        else:
            self.title_ref = tools.get_layer("Title", self.ref_group)

        # Eldrazi formatting?
        if self.layout.is_colorless:
            # Devoid formatting?
            if self.layout.pinlines != self.layout.twins:
                self.layout.pinlines = "Land"
            else:
                self.layout.pinlines = "Land"
                self.layout.twins = "Land"
            tools.get_layer(self.layout.twins, "Border", doc=self.docref).visible = True

        # Nyx Formatting
        if self.layout.is_nyx:
            if len(self.layout.pinlines) != 2:
                tools.get_layer(f"Nyx {self.layout.pinlines}", "Border", doc=self.docref).visible = True
            else:
                tools.wubrg_layer_sort(self.layout.pinlines, "Border", doc=self.docref, prefix="Nyx ")

        # Give the lands a sexy transparent border
        if self.is_land and not self.is_borderless:
            land_textbox = tools.get_layer("Land", "Textbox", doc=self.docref)
            if not land_textbox.visible:
                land_textbox.fillOpacity = 50
                land_textbox.visible = True
            self.docref.activeLayer = tools.get_layer("Normal", "Mask Wearer", "Border", doc=self.docref)
            psd.enable_active_layer_mask()
            if len(self.layout.pinlines) != 2:
                tools.get_layer(self.layout.pinlines, "Border", doc=self.docref).visible = True
            else:
                tools.wubrg_layer_sort(self.layout.pinlines, "Border")

        # Give our PW a sexy transparent border
        elif self.is_planeswalker and not self.is_borderless:
            self.docref.activeLayer = tools.get_layer("Normal", "Mask Wearer", "Border", doc=self.docref)
            psd.enable_active_layer_mask()
            if len(self.layout.pinlines) != 2:
                tools.get_layer(f"PW {self.layout.pinlines}", "Border", doc=self.docref).visible = True
                tools.get_layer(self.layout.pinlines, "Border", doc=self.docref).visible = True
            else:
                tools.wubrg_layer_sort(f"PW {self.layout.pinlines}", "Border")
                tools.wubrg_layer_sort(self.layout.pinlines, "Border")

    def basic_text_layers(self):

        # Set artist info
        artist_text = tools.get_layer("Artist", "Legal", doc=self.docref).textItem
        artist_text.contents = self.layout.artist

        # Mana, Name, and Type text
        self.tx_layers.extend(
            [
                txt_layers.FormattedTextField(
                    layer=self.text_layer_mana,
                    contents=self.layout.mana_cost,
                ),
                txt_layers.ScaledTextField(
                    layer=self.text_layer_type,
                    contents=self.layout.type_line,
                    reference=self.expansion_layer,
                ),
                txt_layers.ScaledTextField(
                    layer=self.text_layer_name,
                    contents=self.layout.name,
                    reference=self.text_layer_mana,
                ),
            ]
        )

    def rules_text_and_pt_layers(self):
        self.tx_layers.append(
            txt_layers.FormattedTextField(
                layer=self.text_layer_rules,
                contents=self.layout.oracle_text,
                centered=self.is_centered,
            ),
        )
        if self.is_creature:
            self.tx_layers.append(
                txt_layers.TextField(
                    layer=self.text_layer_pt,
                    contents=f"{self.layout.power}/{self.layout.toughness}",
                )
            )


    def resize_name_and_type(self):
        if not tools.layer_empty(self.text_layer_mana):
            tools.fit_text_oneline(self.text_layer_name, self.text_layer_mana, "left", 20)
        else:
            ref = tools.get_layer("Title", self.ref_group)
            tools.fit_text_oneline(self.text_layer_name, ref, "inside", 20)

        if not tools.layer_empty(self.expansion_layer):
            tools.fit_text_oneline(self.text_layer_type, self.expansion_layer, "left", 20)
        else:
            ref = tools.get_layer("Type", self.ref_group)
            tools.fit_text_oneline(self.text_layer_type, ref, "inside", 20)
        

    def post_text_layers(self):
        self.resize_name_and_type()

        console.update("Shifting text and frame...")

        # Pre-size down our text based on default size
        txtbx_h = tools.bounds_height(self.ref_layer_textbox.bounds)
        txt_h = tools.bounds_height(self.text_layer_rules.bounds)
        presize = self.text_layer_rules.textItem.size
        # anywhere between 6.5 and 9 based on height of text layer
        size_adjust = 6.5 + max(2.5 * (((txtbx_h - txt_h) / txtbx_h) ** 2), 0)

        if presize != size_adjust:
            self.text_layer_rules.textItem.size = size_adjust
            self.text_layer_rules.textItem.leading = size_adjust
        txt_h = tools.bounds_height(self.text_layer_rules.bounds)

        # Establish how much we are shifting down everything
        pad = 20
        modifier = txtbx_h-txt_h-pad*2
        if modifier < 0: modifier = 0
        if len(self.layout.oracle_text) == 0: 
            if not self.is_creature:
                modifier = 1080
            else:
                modifier = 840
                #TODO add more stuff for textless creatures

        # Move the top left and top right anchors for the creature text bounding box,
        if self.is_creature:
            tools.creature_text_path_shift(self.text_layer_rules, modifier)
            new_txt_h = tools.bounds_height(self.text_layer_rules.bounds)
            diff = txt_h-new_txt_h
            if diff < 0:
                modifier += diff
                tools.creature_text_path_shift(self.text_layer_rules, diff)
            self.text_layer_rules.translate(0, modifier)
        else: # OR translate the whole text layer down
            self.text_layer_rules.translate(0, modifier)

        # Shift typeline, resize textbox and art reference
        ref_layer_textbox = tools.get_layer("Textbox", self.ref_group)
        tools.layer_vert_stretch(ref_layer_textbox, modifier)
        tools.layer_vert_stretch(self.art_reference, -modifier/2, "top")
        self.text_layer_type.translate(0, modifier)

        # Let's make sure it fits, both vertically and the right bound.
        if self.layout.oracle_text:
            tools.fit_text(self.text_layer_rules, self.ref_layer_textbox, padding=pad, post_frame=False)
            tools.frame(
                self.text_layer_rules,
                self.ref_layer_textbox,
                horiz="middle" if self.is_centered else None,
                resize=False,
                )

        # Give colored artifacts the grey pinlines on the sides of the art and main textbox
        if self.layout.pinlines != "Artifact" and self.layout.background == "Artifact":
            tools.get_layer(self.layout.background, "Textbox").visible = True
            type_ref = tools.get_layer("Type", self.ref_group)
            pin_mask = tools.get_layer(self.layout.background, "Pinlines", doc=self.docref)
            pin_mask.visible = True
            self.docref.activeLayer = pin_mask
            psd.enable_active_layer_mask()
            tools.select_layer(self.title_ref)
            tools.add_select_layer(type_ref)
            tools.layer_mask_select(pin_mask)
            self.docref.selection.fill(tools.rgbcolor(0, 0, 0))
            self.docref.selection.deselect()

        console.update("Framing our art layer...")
        tools.frame(self.art_layer, self.art_reference, vert="top")
        if self.is_borderless:
            tools.get_layer("Normal", "Mask Wearer", "Border", doc=self.docref).visible = False
        psd.content_fill_empty_area(self.art_layer)

        tools.select_nonblank_pixels(tools.get_layer("Name", "Mask Wearer", "Name", doc=self.docref))
        tools.select_nonblank_pixels(tools.get_layer("Mask Wearer", "Type", doc=self.docref), "Add ")
        tools.select_nonblank_pixels(tools.get_layer("Base", "Textbox", doc=self.docref), "Add ")
        crt_tools.lens_blur(24, 1, 224, 1)
        self.docref.selection.deselect()

    def post_execute(self):
        if self.do_move_art:
            console.update("Moving art file...")
            moved = tools.move_art(self.layout)
            if isinstance(moved, Exception):
                console.update(f"Could not move art file: {moved}")


class FullArtTextlessTemplate(FullArtModularTemplate):
    # Useful for textless duals.
    # TODO: Tweak layout for creatures so they can get rid of textbox

    def __init__(self, layout):
        layout.oracle_text = ""
        super().__init__(layout)


class BasicModularTemplate(FullArtModularTemplate):
    def __init__(self, layout):

        color_key = {
            "Plains": "W",
            "Island": "U",
            "Swamp": "B",
            "Mountain": "R",
            "Forest": "G",
        }
        layout.is_colorless = False
        layout.twins = color_key[layout.name]
        layout.pinlines = color_key[layout.name]
        layout.background = color_key[layout.name]
        layout.type_line = f"Basic Land — {layout.name}"
        layout.rarity = "common"
        layout.oracle_text = ""
        layout.mana_cost = ""
        self.is_basic = True
        super().__init__(layout)
        self.suffix = f"({layout.artist}) [{layout.set}]"

    def enable_frame_layers(self):
        
        super().enable_frame_layers()

        for target in ["Name", "Type"]:
            layer = tools.get_layer("Land", target, doc=self.docref)
            layer.visible = True
            layer.fillOpacity = 50


class DFCModularTemplate(FullArtModularTemplate):
    """
    One-size-fits-all for MDFC Front, MDFC Back, Transform, and Ixalan land back.
    Lessons too, I guess?
    """

    def basic_text_layers(self):

        super().basic_text_layers()
        self.transform()

    def transform(self):

        trans_icon = {
            "sunmoondfc": ["", ""],
            "mooneldrazidfc": ["", ""],
            "compasslanddfc": ["", ""],
            "modal_dfc": ["", ""],
            "originpwdfc": ["", ""],
            "lesson": "",
        }
        if self.side_pins:
            top = "Legendary"
        else:
            top = "Floating"

        # Scoot name text over
        self.text_layer_name.translate(140, 0)

        # If MDFC, set the pointy, else it's the circle
        mask_wearer = tools.get_layer_set("Mask Wearer", "Name")
        if self.layout.transform_icon == "modal_dfc":
            dfc = "MDFC"
            tools.get_layer(dfc, mask_wearer).visible = True
            tools.active_layer(tools.get_layer_set("Mask Wearer", "Border", doc=self.docref), True)
            psd.enable_active_layer_mask()
        else:
            dfc = "TDFC"
            tools.get_layer(dfc, "Name").visible = True
        tools.get_layer("Name", mask_wearer).visible = False
        tools.get_layer("DFC", mask_wearer).visible = True

        # Setup transform icon
        dfc_icon = tools.get_layer(dfc, self.text_layers_group)
        print(self.layout.transform_icon)
        print(self.layout.card_class)
        side = 0 if "front" in self.layout.card_class else 1
        dfc_icon.textItem.contents = trans_icon[self.layout.transform_icon][side]
        dfc_icon.visible = True

        # Cut out the icon from the legendary frame if necessary
        dfc_pin = tools.get_layer(dfc, "Masked", "Pinlines", doc=self.docref)
        if self.is_legendary:
            legend_mask = tools.get_layer(f"{top} Crown", "Masked", "Pinlines", doc=self.docref)
            legend_mask.visible = True
            tools.magic_wand_select(dfc_pin, 0, 0)
            self.docref.selection.expand(2)
            self.docref.selection.invert()
            tools.layer_mask_select(legend_mask)
            self.docref.selection.fill(tools.rgbcolor(0, 0, 0))
            self.docref.selection.deselect()

        # Turn on/off pinlines
        dfc_pin.visible = True
        tools.get_layer("Standard", "Masked", "Pinlines", doc=self.docref).visible = False


"""
TODO: FIX WITH NEW TEXT RENDER METHOD
"""
class PWFullArtModularTemplate(FullArtModularTemplate):
    def __init__(self, layout):

        self.is_planeswalker = True
        super().__init__(layout)

    def rules_text_and_pt_layers(self):

        oracle_array = re.findall(r"(^[^:]*$|^.*:.*$)", self.layout.oracle_text, re.MULTILINE)
        centered = False
        self.badge = []
        self.rules_text = []
        loyalty_set = tools.get_layer_set("Loyalty", "PW", doc=self.docref)
        pw_layers = {
            "plus": tools.get_layer("Plus", loyalty_set),
            "minus": tools.get_layer("Minus", loyalty_set),
            "zero": tools.get_layer("Zero", loyalty_set),
            "cost": tools.get_layer("Cost", "PW Ability", "Text and Icons", doc=self.docref),
            "activ": tools.get_layer("Activated", "PW Ability", self.text_layers_group),
            "static": tools.get_layer("Static", "PW Ability", self.text_layers_group),
            "last": tools.get_layer("Rules Text - Creature", self.text_layers_group),
        }

        for i, ability in enumerate(oracle_array):

            # Determing if the ability is activated
            colon_index = ability.find(": ")
            if 0 < colon_index < 5:

                # Determine cost text
                cost_text = ability[:colon_index]

                # Grab correct badge, setup cost text, link them
                if "X" not in cost_text:
                    if int(cost_text) > 0:
                        self.badge += [tools.dupe_layer(pw_layers["plus"], cost_text, self.docref)]
                    elif int(cost_text) < 0:
                        self.badge += [tools.dupe_layer(pw_layers["minus"], cost_text, self.docref)]
                    else:
                        self.badge += [tools.dupe_layer(pw_layers["zero"], cost_text, self.docref)]
                else:
                    if cost_text[0] in ("-", "—"):
                        self.badge += [tools.dupe_layer(pw_layers["minus"], cost_text, self.docref)]
                    else:
                        self.badge += [tools.dupe_layer(pw_layers["plus"], cost_text, self.docref)]

                # Setup cost text layer
                cost = tools.dupe_layer(pw_layers["cost"], f"Cost {i}", self.docref)
                cost.visible = True
                self.badge[-1].visible = True
                self.tx_layers += [
                    PWLoyaltyCost(
                        layer=cost,
                        contents=cost_text,
                        badge=self.badge[i],
                    )
                ]

                # Set correct text item for last ability
                centered = False
                ability_text = ability[colon_index+2:]

                if ability != oracle_array[-1]:
                    self.rules_text += [
                        tools.dupe_layer(pw_layers["activ"], f"Ability {i}", self.docref)
                    ]
                else:
                    self.rules_text += [
                        tools.dupe_layer(pw_layers["last"], "Final", self.docref)
                    ]
                    self.rules_text[-1].visible = True
                    tools.pw_ability_shift(self.rules_text[-1])
            else:
                self.badge += [None]
                # Set correct text item for last ability
                centered = all(ret not in ability for ret in ["\n", "\r"])
                ability_text = ability

                if ability != oracle_array[-1]:
                    self.rules_text += [
                        tools.dupe_layer(pw_layers["static"], f"Ability {i}", self.docref)
                    ]
                else:
                    self.rules_text += [
                        tools.dupe_layer(pw_layers["last"], "Final", self.docref)
                    ]
                    self.rules_text[-1].visible = True
                    tools.pw_ability_shift(self.rules_text[-1])

            self.rules_text[-1].visible = True
            self.tx_layers += [
                txt_layers.FormattedTextField(
                    layer=self.rules_text[-1],
                    contents=ability_text,
                    centered=centered,
                )
            ]

        loyalty = tools.get_layer("Loyalty", "PW Ability", self.text_layers_group)
        badge = tools.get_layer("Badge", "PW", doc=self.docref)
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
        self.resize_name_and_type()

        overlay = tools.get_layer("Overlay", "Textbox", doc=self.docref)
        overlay.visible = True

        black, white = tools.rgbcolor(0,0,0), tools.rgbcolor(255,255,255)

        left, right = self.ref_layer_textbox.bounds[0], self.ref_layer_textbox.bounds[2]
        txtbx_h = tools.bounds_height(self.ref_layer_textbox.bounds)
        txt_h = sum(tools.bounds_height(rule.bounds)+40 for rule in self.rules_text)-40

        size_adjust = max(
            round(self.rules_text[0].textItem.size - 2 * ((txt_h / txtbx_h) ** 2), 1),
            6.4
        )
        
        # going from bottom to top
        for i, layer in reversed(list(enumerate(self.rules_text))):
            layer.textItem.size = size_adjust
            layer.textItem.leading = size_adjust
            overlay_height = tools.bounds_height(layer.bounds)+40
            self.docref.activeLayer = overlay
            if layer == self.rules_text[-1]:
                bottom = self.ref_layer_textbox.bounds[3]
                delta = bottom-layer.bounds[3]-20
                tools.creature_text_path_shift(layer, delta)
                delta = overlay_height-(tools.bounds_height(layer.bounds)+40)
                if delta < 0:
                    tools.creature_text_path_shift(layer, delta)
                    overlay_height -= delta
            else:
                bottom = top
            top = bottom - overlay_height
            self.docref.selection.select(
                [[left, top], [right, top], [right, bottom], [left, bottom]]
            )
            self.docref.selection.fill(black if i % 2 == 0 else white)
            if self.badge[i]:
                psd.align_vertical(self.badge[i])
            self.docref.selection.deselect()

            # Add divider
            if i > 0:
                divider = tools.get_layer("Divider", "Loyalty", "PW", doc=self.docref).duplicate()
                divider.visible = True
                tools.select_nonblank_pixels(divider)
                div_top = self.docref.selection.bounds[1]
                self.docref.selection.deselect()
                divider.translate(0, (top - 2) - div_top)

            layer.translate(0, top+20-layer.bounds[1])

        delta = self.rules_text[0].bounds[1]-self.ref_layer_textbox.bounds[1]-30
        tools.layer_vert_stretch(self.ref_layer_textbox, delta)
        tools.layer_vert_stretch(self.art_reference, -delta/2, "top")
        self.text_layer_type.translate(0, delta)

        if self.is_borderless:
            tools.get_layer("Normal", "Mask Wearer", "Border", doc=self.docref).visible = False
        tools.frame(self.art_layer, self.art_reference, vert="top")
        psd.content_fill_empty_area(self.art_layer)

        tools.select_nonblank_pixels(tools.get_layer("Name", "Mask Wearer", "Name", doc=self.docref))
        tools.select_nonblank_pixels(tools.get_layer("Mask Wearer", "Type", doc=self.docref), "Add ")
        tools.select_nonblank_pixels(tools.get_layer("Base", "Textbox", doc=self.docref), "Add ")
        self.docref.activeLayer = self.art_layer
        crt_tools.lens_blur(24, 1, 224, 1)
        self.docref.selection.deselect()


class PWTransformFullArtTemplate(PWFullArtModularTemplate):
    def basic_text_layers(self):

        DFCModularTemplate.transform(self)
        super().basic_text_layers()


class PixelModularTemplate(temp.StarterTemplate):
    """
    Expandable pixel-art template
    100dpi start, then can blow up to 800dpi with the CRT filter
    """

    template_file_name = "preshtildeath/pixel-template"
    template_suffix = "PXL Mod"

    @cached_property
    def do_crt_filter(self) -> bool:
        return cfg.get_setting(
            section="GENERAL",
            key="CRT.Filter",
            default=True,
            is_bool=True,
        )

    @cached_property
    def invert_mana(self) -> bool:
        return cfg.get_setting(
            section="GENERAL",
            key="Invert.Mana",
            default=False,
            is_bool=True,
        )

    @cached_property
    def symbol_bg(self) -> bool:
        return cfg.get_setting(
            section="GENERAL",
            key="Symbol.BG",
            default=True,
            is_bool=True,
        )

    @cached_property
    def do_move_art(self) -> bool:
        return cfg.get_setting(
            section="GENERAL",
            key="Move.Art",
            default=True,
            is_bool=True,
        )

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
        layout.oracle_text = layout.oracle_text.replace("’", "`")

        # If inverted or circle-less, inner symbols are colored and background circle is black
        if self.invert_mana or not self.symbol_bg:
            for c in [("clr_" + s) for s in (list("wubrgc") + ["bh"])]:
                setattr(con, c, {"r": 13, "g": 13, "b": 13})
            con.clr_primary = {"r": 217, "g": 217, "b": 217}
            con.clri_c = {"r": 217, "g": 217, "b": 217}
            con.clri_w = {"r": 255, "g": 255, "b": 255}
            con.clri_u = {"r": 64, "g": 134, "b": 255}
            con.clri_bh = {"r": 125, "g": 0, "b": 255}
            con.clri_b = {"r": 125, "g": 0, "b": 255}
            con.clri_r = {"r": 255, "g": 128, "b": 128}
            con.clri_g = {"r": 128, "g": 255, "b": 128}
        else:
            con.clr_c = {"r": 217, "g": 217, "b": 217}
            con.clr_w = {"r": 255, "g": 255, "b": 255}
            con.clr_u = {"r": 64, "g": 134, "b": 255}
            con.clr_bh = {"r": 125, "g": 0, "b": 255}
            con.clr_b = {"r": 125, "g": 0, "b": 255}
            con.clr_r = {"r": 255, "g": 128, "b": 128}
            con.clr_g = {"r": 128, "g": 255, "b": 128}
        # Replace Q, q, and o with ^ for later deletion
        if not self.symbol_bg:
            con.symbols = {k: re.sub(r"[Qqo]", "^", v) for k, v in con.symbols.items()}

        super().__init__(layout)
    
    @cached_property
    def text_layers(self):
        return tools.get_layer_set("Text")
    
    @cached_property
    def text_layer_name(self):
        return tools.get_layer("Name", self.text_layers)
    
    @cached_property
    def text_layer_type(self):
        return tools.get_layer("Typeline", self.text_layers)
    
    @cached_property
    def text_layer_mana(self):
        return tools.get_layer("Mana", self.text_layers)
    
    @cached_property
    def text_layer_rules(self):
        return tools.get_layer("Oracle", self.text_layers)
    
    @cached_property
    def art_reference(self):
        return tools.get_layer("Art Ref", "Ref")

    def basic_text_layers(self):

        # Set artist info
        artist_layer = tools.get_layer("Artist", "Legal")
        artist_layer.textItem.contents = self.layout.artist

        # Name, Type, Mana, and Body text
        self.tx_layers.extend(
            [
                txt_layers.TextField(
                    layer=self.text_layer_name,
                    contents=self.layout.name,
                ),
                txt_layers.TextField(
                    layer=self.text_layer_type,
                    contents=self.layout.type_line,
                ),
                txt_layers.FormattedTextField(
                    layer=self.text_layer_mana,
                    contents=self.layout.mana_cost,
                ),
            ]
        )

    def rules_text_and_pt_layers(self) -> None:
        self.tx_layers += [
            txt_layers.FormattedTextField(
                layer=self.text_layer_rules,
                contents=self.layout.oracle_text,
            ),
        ]
        if self.is_creature:
            power_toughness = tools.get_layer("PT Text", self.text_layers)
            self.tx_layers += [
                txt_layers.TextField(
                    layer=power_toughness,
                    contents=f"{self.layout.power}/{self.layout.toughness}",
                )
            ]
        

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
        textbox = tools.get_layer("Mask", "Textbox")
        title_pin = tools.get_layer("Title", "Pinlines")
        type_pin = tools.get_layer("Type", "Pinlines")

        # Fix any anti-aliasing and kerning weirdness
        text_layers = [
            self.text_layer_name,
            self.text_layer_type,
            self.text_layer_mana,
            self.text_layer_rules
            ]
        for layer in text_layers:
            layer.textItem.antiAliasMethod = ps.AntiAlias.NoAntialias
            layer.textItem.autoKerning = ps.AutoKernType.Metrics
        self.text_layer_rules.textItem.leading *= 0.8

        # Attempt to fix type line if it goes spilling off the side
        while self.text_layer_type.bounds[2] > 233:
            type_text = self.text_layer_type.textItem
            if "Legend" in self.layout.type_line:
                type_text.contents = type_text.contents.replace("Legendary", "Legend")
            elif "Creature" in self.layout.type_line:
                type_text.contents = type_text.contents.replace("Creature ", "")
            if "Phyrexian" in self.layout.type_line:
                type_text.contents = type_text.contents.replace("Phyrexian ", "Phyr")
            if "Equipment" in self.layout.type_line:
                type_text.contents = type_text.contents.replace("Equipment ", "Equip")
            if "Aura" in self.layout.type_line:
                type_text.contents = type_text.contents.replace("Enchantment -", "")
            

        # Get rid of the "^" symbols if the symbol_bg is False in our config
        if not self.symbol_bg:
            tools.replace_text(self.text_layer_mana, "^", "")
            tools.replace_text(self.text_layer_rules, "^", "")

        # Move oracle text and resize textbox
        if self.is_creature:
            tools.select_nonblank_pixels(self.text_layer_rules)
            tools.select_nonblank_pixels(tools.get_layer("PT Ref", "Ref"), "Intr")
            try:
                delta = min(
                    textbox.bounds[3]-self.docref.selection.bounds[3],
                    textbox.bounds[3]-self.text_layer_rules.bounds[3]
                )
            except:
                delta = textbox.bounds[3]-self.text_layer_rules.bounds[3]-8
            self.docref.selection.deselect()
        else: delta = textbox.bounds[3]-self.text_layer_rules.bounds[3]
        self.text_layer_rules.translate(0, delta)
        self.text_layer_type.translate(0, delta)
        tools.layer_vert_stretch(textbox, delta)

        l, t, r, b = [
            10,
            title_pin.bounds[3] - 4,
            self.docref.width - 10,
            type_pin.bounds[1] + 4,
        ]

        console.update("Loading artwork...")

        # Establish size to scale down to and resize
        ref_w, ref_h = r-l, b-t
        # Switch to new doc, resize and dither
        art_doc = app.open(self.layout.filename)
        scale = 100 * max(ref_w / art_doc.width, ref_h / art_doc.height)
        if scale < 50:
            crt_tools.img_resize(art_doc, scale, scale)
            crt_tools.index_color(16, "adaptive")
        # Copy/paste into template doc, then align with art reference
        art_doc.selection.selectAll()
        art_doc.selection.copy()
        art_doc.close(ps.SaveOptions.DoNotSaveChanges)
        self.docref.activeLayer = self.art_layer
        self.docref.paste()
        tools.frame(self.art_layer, [l, t, r, b], resize=False)

        # Blow up to 800dpi, and do the CRT filter if config says to
        crt_tools.blow_up(filter=self.do_crt_filter)

    def post_execute(self):
        if self.do_move_art:
            console.update("Moving art file...")
            moved = tools.move_art(self.layout)
            if isinstance(moved, Exception):
                console.update(f"Could not move art file: {moved}")


class UniversesBeyond(temp.NormalTemplate):
    """
    Universes Beyond, normal M15 style template.
    """
    template_file_name = "preshtildeath/universes-beyond"
    template_suffix = "UB"

    @property
    def is_colorless(self) -> bool: return False

    def enable_crown(self):
        self.crown_layer.parent.visible = True
        self.crown_layer.visible = True


class Equinox(temp.NormalTemplate):
    """
    Equinox, normal M15 style template.
    """
    template_file_name = "preshtildeath/equinox"
    template_suffix = "Equinox"


class Invocation(temp.NormalTemplate):
    """
    Invocation, 'normal' M15 style template.
    """
    template_file_name = "preshtildeath/invocation"
    template_suffix = "Invocation"

    @property
    def is_colorless(self) -> bool: return False

    def enable_crown(self): pass

    @cached_property
    def pt_layer(self) -> Optional[ArtLayer]:
        if len(self.layout.power) > 1 or len(self.layout.toughness) > 1:
            self.text_layer_pt.translate(-25, 0)
            return psd.getLayer("PT Box Wide")
        return psd.getLayer("PT Box Thin")

    @cached_property
    def is_centered(self) -> bool:
        return True
    
    def __init__(self, layout):
        super().__init__(layout)

        for c in [f"clr{pre}_"+s for pre in ["","i"] for s in list("wubrgc")+["bh","primary","secondary"]]:
            setattr(con, c, {"r": 31, "g": 17, "b": 8})
        con.font_rules_text = "ShangoGothic"
        for k, v in con.symbols.items():
            con.symbols[k] = v.replace("o", "v").replace("Qp", "op").replace("Qq", "\u00EF\u00E8")

    def collector_info(self):
        psd.getLayer("Top", "Legal").textItem.contents = \
            f"{self.layout.collector_number}/{self.layout.card_count} {str(self.layout.set)}"
        psd.replace_text(psd.getLayer("Bottom", "Legal"), "Artist", self.layout.artist)

    def enable_frame_layers(self):
        super().enable_frame_layers()
        mana_length = self.layout.mana_cost.count("{")
        psd.getLayer(str(mana_length), "Extending Mana").visible = True
    
    def post_text_layers(self):
        super().post_text_layers()
        if self.is_creature:
            psd.replace_text(self.text_layer_pt,  "/", "\r")


class FullArtWeeb(FullArtModularTemplate):
    """
    Created by preshtildeath.
    Inspired by lepoulpe.
    """

    template_file_name = "preshtildeath/fullart-modular-weeb"
    template_suffix = "FA Weeb"

    @cached_property
    def base_group(self) -> Optional[LayerSet]:
        return tools.get_layer_set("Base")

    @cached_property
    def name_textbox_group(self) -> Optional[LayerSet]:
        return tools.get_layer_set("Name & Textbox", self.base_group)

    @cached_property
    def title_mask_group(self) -> Optional[LayerSet]:
        return tools.get_layer_set("Mask", self.name_textbox_group)

    @cached_property
    def art_reference(self) -> Optional[ArtLayer]:
        return tools.get_layer("Full Art Frame", "Ref")

    @cached_property
    def text_layer_mana(self) -> Optional[ArtLayer]:
        return tools.get_layer("Mana Cost", self.text_layers_group)

    @cached_property
    def text_layer_rules(self) -> Optional[ArtLayer]:
        return tools.get_layer("Rules Text", self.text_layers_group)

    @cached_property
    def text_layer_artist(self) -> Optional[ArtLayer]:
        return tools.get_layer("Artist", self.text_layers_group)

    @cached_property
    def pt_layer(self) -> Optional[ArtLayer]:
        return tools.get_layer("PT Box", self.base_group)

    @cached_property
    def mana_layer(self) -> Optional[ArtLayer]:
        return tools.get_layer("Mana Box", self.base_group)

    @cached_property
    def crown_layer(self) -> Optional[ArtLayer]:
        return tools.get_layer("Legendary Crown", self.title_mask_group)

    @cached_property
    def title_box_layer(self) -> Optional[ArtLayer]:
        return tools.get_layer("Standard", self.title_mask_group)
    
    def __init__(self, layout):
        super().__init__(layout)

        con.font_mana = "NDPMTG"
        con.font_rules_text = "Roboto-Light"
        con.font_rules_text_bold = "Roboto-Regular"
        con.font_rules_text_italic = "Roboto-LightItalic"
        con.clri_w = {"r": 255, "g": 250, "b": 178}
        con.clri_u = {"r": 9, "g": 135, "b": 195}
        con.clri_b = {"r": 71, "g": 1, "b": 137}
        con.clri_r = {"r": 246, "g": 59, "b": 110}
        con.clri_g = {"r": 36, "g": 222, "b": 58}
        con.clri_c = {"r": 222, "g": 222, "b": 222}
        con.clr_primary = {"r": 248, "g": 248, "b": 248}
        con.clr_w = con.clri_w.copy()
        con.clr_u = con.clri_u.copy()
        con.clr_b = con.clri_b.copy()
        con.clr_bh = con.clri_b.copy()
        con.clri_bh = con.clri_b.copy()
        con.clr_r = con.clri_r.copy()
        con.clr_g = con.clri_g.copy()
        con.clr_c = con.clri_c.copy()
        con.clr_secondary = con.clr_primary.copy()
        for k, v in con.symbols.items():
            con.symbols[k] = v.replace("o", "v").replace("Qp", "op").replace("Qq", "\u00EF\u00E8")
        self.layout.mana_cost = self.layout.mana_cost.replace("{", "\r{")

    def load_artwork(self):
        super().load_artwork()
        tools.frame(self.art_layer, self.art_reference, vert="top")

    def basic_text_layers(self):
        console.update("Setting up our text layers...")

        # Set artist info
        self.text_layer_artist.textItem.contents = self.layout.artist
        
        # Mana, Name, and Type text
        self.tx_layers.extend(
            [
                txt_layers.FormattedTextField(
                    layer=self.text_layer_mana,
                    contents=self.layout.mana_cost,
                ),
                txt_layers.TextField(
                    layer=self.text_layer_type,
                    contents=self.layout.type_line,
                ),
                txt_layers.TextField(
                    layer=self.text_layer_name,
                    contents=self.layout.name,
                ),
            ]
        )

    def rules_text_and_pt_layers(self):
        self.tx_layers += [
            txt_layers.FormattedTextField(
                layer=self.text_layer_rules,
                contents=self.layout.oracle_text,
                centered=self.is_centered,
            ),
        ]

        if self.is_creature:
            self.tx_layers.append(
                txt_layers.TextField(
                    layer=self.text_layer_pt,
                    contents=f"{self.layout.power}/{self.layout.toughness}",
                )
            )

    def enable_frame_layers(self):
        console.update("Turning on our frame elements...")

        self.pt_layer.visible = self.is_creature
        if len(self.layout.pinlines) != 2:
            tools.get_layer(self.layout.pinlines, self.name_textbox_group).visible = True
        else:
            tools.wubrg_layer_sort(self.layout.pinlines, self.name_textbox_group)
        if self.is_legendary:
            self.crown_layer.visible = True
        if self.is_land:
            tools.get_layer("Border", self.title_mask_group).visible = True
            tools.get_layer("Border Dodge", self.title_mask_group).visible = True
            # TODO: gotta move the whole shebang to the top
            # IDEA: Rotate group, then rotate every text layer - after render

    def post_text_layers(self):
        console.update("Shifting text...")

        if self.layout.mana_cost:
            self.text_layer_mana.textItem.leading = 8.6
            # if "v" in self.text_layer_mana.textItem.contents:
            #     psd.replace_text(self.text_layer_mana, "v", "\rv")
            # if "\u00E8" in self.text_layer_mana.textItem.contents:
            #     psd.replace_text(self.text_layer_mana, "\u00EF", "\r\u00EF")
            mana_bounds = tools.text_layer_bounds(self.text_layer_mana)
            mana_delta = tools.bounds_height(mana_bounds)
            self.mana_layer.visible = True
            self.mana_layer.translate(0, mana_delta)
        if self.is_creature:
            pt_delta = tools.bounds_width(self.text_layer_pt.bounds)
            self.pt_layer.translate(-pt_delta, 0)
            # Name text and Title text layers are linked
            self.text_layer_name.translate(-pt_delta * 0.5, 0)
        title = self.crown_layer if self.is_legendary else self.title_box_layer
        title_bounds = title.bounds
        rules_bounds = self.text_layer_rules.bounds
        delta = title_bounds[1]-rules_bounds[3]+8
        # Rules Text and Textbox Gradient layers are linked
        self.text_layer_rules.translate(0, delta)

        # shift text to the top if a land? not sure how I like the look.
        """
        if self.is_land:
            self.text_layer_name.unlink()
            self.text_layer_rules.unlink()
            shift_layers = [
                self.text_layer_rules,
                self.text_layer_name,
                self.text_layer_type,
                self.text_layer_artist,
                ]
            if self.is_creature: shift_layers += [self.text_layer_pt] # corner case
            doc_center = [self.docref.width/2, self.docref.height/2]
            for layer in shift_layers:
                b = tools.bounds_nofx(layer)
                delta = self.docref.height-b[3]
                layer.translate(0, delta-b[1])
            tools.free_transform(self.base_group, h=-100, posit=doc_center)
        """

        console.update("Applying lens blur to art...")

        # Dupe the base, merge to one layer, select transparency,
        # apply mask, deactivate, then lens blur with that depth info.
        mask_layer = self.base_group.duplicate()
        mask_layer = mask_layer.merge()
        tools.select_nonblank_pixels(mask_layer)
        mask_layer.visible = False
        tools.make_mask(self.art_layer)
        tools.layer_rgb_select(self.art_layer)
        crt_tools.lens_blur(
            radius=24,
            depth_mask=True,
            noise_amount=2,
            threshold=224,
            mono=True,
            bright=5,
            )
        psd.disable_mask(self.art_layer)