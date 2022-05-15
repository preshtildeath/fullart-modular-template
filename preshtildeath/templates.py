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
import photoshop.api as ps
from configs import config
from proxyshop import gui
console = gui.console_handler
app = ps.Application()

# Ensure scaling with pixels, font size with points
app.preferences.rulerUnits = ps.Units.Pixels
app.preferences.typeUnits = ps.Units.Points

"""
    Functions live here that each template wants to use
"""
def move_art(file, name, artist, set):
    work_path = os.path.dirname(file)
    new_name = f"{name} ({artist}) [{set}]"
    ext = os.path.splitext(os.path.basename(file))[1]

    if "finished" not in str(work_path):
        fin_path = os.path.join(work_path, 'finished')
    else:
        fin_path = work_path
    if not os.path.exists(fin_path):
        os.mkdir(fin_path)

    new_file = os.path.join(fin_path, f"{new_name}{ext}")
    try:
        if new_file != file:
            os.replace(file, tools.filename_append(new_file, fin_path))
    except Exception as e:
        console.update("Could not move art file!", exception=e)


"""
    Created by preshtildeath
    Expands the textbox based on how much oracle text a card has
    Also expanding this template to service other card types
"""     
class FullArtModularTemplate (temp.StarterTemplate):   
    def template_file_name (self):
        return "preshtildeath/fullart-modular"
    
    def template_suffix (self):
        suffix = "Full Mod" # Base suffix
        try:
            if cfg.save_jpeg: test_file = f"{self.layout.name} ({suffix}).jpg"
            else: test_file = f"{self.layout.name} ({suffix}).png"
            end_file = tools.filename_append(test_file, os.path.join(con.cwd, "out")) # Check for multiples
            end_file = os.path.splitext(os.path.basename(end_file))[0] # Cut to basename, then strip extension
            end_file = end_file[end_file.find("(")+1:end_file.rfind(")")] # Take out everything between first "(" and last ")"
            return end_file # "Base suffix) (x"
        except:
            return suffix

    def load_artwork (self):
        # Loads the specified art file into the specified layer.
        psd.paste_file(self.art_layer, self.layout.file)
        tools.zero_transform(self.art_layer)

    def collector_info (self): pass

    def __init__ (self, layout):
        app.preferences.interpolation = ps.ResampleMethod.BicubicAutomatic
        cfg.remove_flavor = True
        cfg.remove_reminder = True
        filename = os.path.splitext(os.path.basename(layout.file))[0]
        if filename.rfind("[") < filename.rfind("]"):
            self.set = filename[filename.rfind("[")+1:filename.rfind("]")]
        else:
            self.set = layout.set
        
        super().__init__(layout)

        # define some characteristics
        if not hasattr(self, "is_basic"): self.is_basic = False
        try: self.is_land = bool(self.layout.type_line.find("Land") >= 0 or self.is_basic)
        except: self.is_land = False

        # Check config
        if config.hollow_mana:
            # change mana symbol colors
            con.rgb_primary  = {'r': 194, 'g': 194, 'b': 194}
            con.rgb_c  = {'r': 194, 'g': 194, 'b': 194}
            con.rgbi_c = {'r': 194, 'g': 194, 'b': 194}
            con.rgb_w  = {'r': 232, 'g': 232, 'b': 230}
            con.rgbi_w = {'r': 232, 'g': 232, 'b': 230}
            con.rgb_u  = {'r':    0, 'g': 122, 'b': 196}
            con.rgbi_u = {'r':    0, 'g': 122, 'b': 196}
            con.rgb_b  = {'r':  70, 'g':  48, 'b':  71}
            con.rgb_bh = {'r':  70, 'g':  48, 'b':  71}
            con.rgbi_b = {'r':  70, 'g':  48, 'b':  71}
            con.rgbi_bh= {'r':  70, 'g':  48, 'b':  71}
            con.rgb_r  = {'r': 233, 'g':  63, 'b':  46}
            con.rgbi_r = {'r': 233, 'g':  63, 'b':  46}
            con.rgb_g  = {'r':   0, 'g': 134, 'b':  80}
            con.rgbi_g = {'r':   0, 'g': 134, 'b':  80}
            for sym in con.symbols:
                con.symbols[sym] = re.sub("[Qqo]", "v", con.symbols[sym])
                
        # Choose your border
        if self.is_land: self.art_reference = psd.getLayer('Full Art Frame', 'Ref')
        elif self.is_legendary: self.art_reference = psd.getLayer('Legendary Frame', 'Ref')
        else: self.art_reference = psd.getLayer('Art Frame', 'Ref')

        # Set up text layers
        console.update("Preparing text layers...")
        self.text_layers()

    def text_layers (self):
        # Set up some layers
        mana_layer = psd.getLayer('Text', 'Mana Cost')
        name_layer = psd.getLayer('Card Name', 'Text and Icons')
        exp_layer = psd.getLayer('Expansion Symbol', 'Expansion')
        exp_ref = psd.getLayer('Expansion', 'Ref')
        exp_offset = psd.getLayer('Expansion Offset', 'Ref')
        type_layer = psd.getLayer('Typeline', 'Text and Icons')
        textbox_ref = psd.getLayer('Textbox', 'Ref')
        
        # Move typeline and modify textbox reference and text outlines if certain criteria is met
        scale = tools.dirty_text_scale(self.layout.oracle_text, 36)
        if scale > 9: modifier = -320
        elif scale > 6: modifier = -160
        elif scale == 0: modifier = 480
        elif scale <= 1: modifier = 240
        elif scale <= 3: modifier = 160
        else: modifier = 0
        
        # Cap the modifier for creature textbox
        if self.is_creature and modifier > 160: modifier = 160
            
        # Apply typeline translate and textbox stretch
        type_layer.translate(0, modifier)
        tools.layer_vert_stretch(textbox_ref, modifier, 'bottom')
        
        # Set artist info
        artist_text = psd.getLayer('Artist', 'Legal').textItem
        artist_text.contents = self.layout.artist
        
        # Set symbol
        console.update(f"Looking up set symbol for [{self.set}]...")
        set_pdf = tools.get_set_pdf(self.set)
        console.update(f"Opening {set_pdf}...")
        exp_layer = tools.get_expansion(exp_layer, self.layout.rarity, exp_ref, exp_offset, set_pdf)
        
        # Mana, Name, and Type text
        self.tx_layers.extend([
            txt_layers.BasicFormattedTextField(
                    layer=mana_layer,
                    text_contents=self.layout.mana_cost,
                    text_color=tools.rgbcolor(0, 0, 0)
            ),
            txt_layers.ScaledTextField(
                layer = type_layer,
                text_contents = self.layout.type_line,
                text_color = psd.get_text_layer_color(type_layer),
                reference_layer = exp_layer
            ),
            txt_layers.ScaledTextField(
                layer = name_layer,
                text_contents = self.layout.name,
                text_color = psd.get_text_layer_color(name_layer),
                reference_layer = mana_layer
            )
        ])
        
        if self.is_creature:        
            # Center the rules text if the text is at most two lines
            is_centered = bool( scale <= 2)
            # Creature card - set up creature layer for rules text and insert p/t
            power_toughness = psd.getLayer('Power / Toughness', 'Text and Icons')
            rules_text = psd.getLayer(f'Rules Text - Creature {modifier}', 'Text and Icons')
            self.tx_layers.extend([
                txt_layers.TextField(
                    layer = power_toughness,
                    text_contents = f'{self.layout.power}/{self.layout.toughness}',
                    text_color = psd.get_text_layer_color(power_toughness)
                ),
                txt_layers.CreatureFormattedTextArea(
                    layer = rules_text,
                    text_contents = self.layout.oracle_text,
                    text_color = psd.get_text_layer_color(rules_text),
                    flavor_text = self.layout.flavor_text,
                    reference_layer = textbox_ref,
                    pt_reference_layer = psd.getLayer('PT Adjustment', 'Ref'),
                    pt_top_reference_layer = psd.getLayer('PT Top', 'Ref'),
                    is_centered = is_centered,
                    fix_length = False
                )
            ])
            # setup for Textless template
            if scale == 0: modifier = 360
        else:        
            # Center the rules text if the text is at most four lines
            is_centered = bool( scale <= 4 )
            # Noncreature card - use the normal rules text layer and disable the p/t layer
            psd.getLayer('Power / Toughness', 'Text and Icons').visible = False
            rules_text = psd.getLayer('Rules Text - Noncreature', 'Text and Icons')
            rules_text.translate(0, modifier)
            self.tx_layers.append(
                txt_layers.FormattedTextArea(
                    layer = rules_text,
                    text_contents = self.layout.oracle_text,
                    text_color = psd.get_text_layer_color(rules_text),
                    flavor_text = self.layout.flavor_text,
                    reference_layer = textbox_ref,
                    is_centered = is_centered,
                    fix_length = False
                )
            )

    def enable_frame_layers (self):
        # Eldrazi formatting?
        if self.layout.is_colorless:
            # Devoid formatting?
            if self.layout.pinlines != self.layout.twins:
                self.layout.pinlines = 'Land'
            else:
                self.layout.pinlines = 'Land'
                self.layout.twins = 'Land'
            psd.getLayer(self.layout.twins, 'Border').visible = True

        if self.layout.is_nyx:
            psd.getLayer(f'Nyx {self.layout.pinlines}', 'Border').visible = True
            
        # Twins and p/t box
        psd.getLayer(self.layout.twins, 'Name').visible = True
        psd.getLayer(self.layout.twins, 'Type').visible = True
        if self.is_creature: psd.getLayer(self.layout.twins, 'PT Box').visible = True

        # Pinlines & Textbox
        if len(self.layout.pinlines) != 2:
            psd.getLayer(self.layout.pinlines, 'Pinlines').visible = True
            psd.getLayer(self.layout.pinlines, 'Textbox').visible = True
        else:
            tools.wubrg_layer_sort(self.layout.pinlines, 'Pinlines')
            tools.wubrg_layer_sort(self.layout.pinlines, 'Textbox')

        pinline_mask_set = psd.getLayerSet('Masked', 'Pinlines')
        psd.getLayer('Side Pinlines', pinline_mask_set).visible = config.side_pins            

        # legendary crown
        if self.is_legendary:
            if config.side_pins: type = "Legendary"
            else: type = "Floating"
            psd.getLayer(f'{type} Crown', pinline_mask_set).visible = True
            title_ref = psd.getLayer(type, 'Ref')
            if not self.is_land:
                psd.getLayer(
                    'Crown Mask',
                    psd.getLayerSet('Mask Wearer', 'Border')
                ).visible = True
        else: title_ref = psd.getLayer('Title', 'Ref')

        # Give the lands a sexy transparent border
        if self.is_land:
            land_textbox = psd.getLayer("Land", 'Textbox')
            if not land_textbox.visible:
                tools.set_opacity(land_textbox, 50)
                land_textbox.visible = True
            border = psd.getLayerSet('Mask Wearer', 'Border')
            app.activeDocument.activeLayer = psd.getLayer('Normal', border)
            psd.enable_active_layer_mask()
            if len(self.layout.pinlines) != 2:
                psd.getLayer(self.layout.pinlines, border.parent).visible = True
            else: tools.wubrg_layer_sort(self.layout.pinlines, border.parent)

        # Give colored artifacts the grey pinlines on the sides of the art and main textbox
        if (self.layout.background != self.layout.pinlines and
            self.layout.background == 'Artifact'):
            # Set textbox to artifact
            psd.getLayer(self.layout.background, 'Textbox').visible = True
            
            # Point to type reference (title reference is set in the legendary check)
            type_ref = psd.getLayer('Type', 'Ref')
            
            # Apply artifact clipping mask
            pin_mask = psd.getLayer(self.layout.background, psd.getLayerSet('Pinlines'))
            pin_mask.visible = True
            
            # Enable layer mask
            app.activeDocument.activeLayer = pin_mask
            psd.enable_active_layer_mask()
            
            # Modify layer mask
            psd.clear_selection()
            tools.add_select_layer(title_ref) # Create selection based on the type box
            tools.add_select_layer(type_ref) # Add to selection based on the title box
            tools.layer_mask_select(pin_mask) # Select the layer mask
            app.activeDocument.selection.fill(tools.rgbcolor(0, 0, 0)) # Fill it with black
            app.activeDocument.selection.deselect() # Deselect

    def post_execute(self):

        con.reload()

        if config.move_art:
            # Move art source to a new folder
            console.update("Moving art file...")
            move_art(self.layout.file, self.layout.name, self.layout.artist, self.set)

# Useful for textless duals.
# TODO: Tweak layout for creatures so they can get rid of textbox
class FullArtTextlessTemplate (FullArtModularTemplate):

    def __init__ (self, layout):
        layout.oracle_text = ""
        super().__init__(layout)

class BasicModularTemplate (FullArtModularTemplate):
    
    def template_suffix (self):
        # names = self.layout.artist.split()
        # if len(names) > 1: last_name = names[-1]
        # else: last_name = names[0]
        return f"{self.layout.artist}) ({self.set}"

    def __init__ (self, layout):
        self.is_basic = True
        super().__init__(layout)
        self.name_key = {
            "Plains": "W",
            "Island": "U",
            "Swamp": "B",
            "Mountain": "R",
            "Forest": "G"
            } 

    def text_layers (self):
        # Define some layers
        name_layer = psd.getLayer('Card Name', 'Text and Icons')
        exp_layer = psd.getLayer('Expansion Symbol', 'Expansion')
        exp_ref = psd.getLayer('Expansion', 'Ref')
        type_layer = psd.getLayer('Typeline', 'Text and Icons')
        text_ref = psd.getLayer('Textbox', 'Ref')
        # Apply typeline translate and textbox stretch
        type_layer.translate( 0, 480 )
        text_ref.resize(100, 0, 7)
        # Set artist info
        artist_text = psd.getLayer('Artist', 'Artist').textItem
        artist_text.contents = self.layout.artist
        # Name and type text
        self.tx_layers.extend([
            txt_layers.TextField(
                layer = name_layer,
                text_contents = self.layout.name,
                text_color = psd.get_text_layer_color(name_layer)
            ),
            txt_layers.TextField(
                layer = type_layer,
                text_contents = f"Basic Land — {self.layout.name}",
                text_color = psd.get_text_layer_color(type_layer)
            )
        ])
        # Set symbol
        set_pdf = tools.get_set_pdf(self.set)
        tools.get_expansion(exp_layer, 'common', exp_ref, set_pdf)

    def enable_frame_layers (self):
        layer_name = self.name_key[self.layout.name]
        for target in ["Pinlines", "Name", "Type", "Border"]:
            psd.getLayer(layer_name, target).visible = True
        for target in ["Name", "Type"]:
            layer = psd.getLayer("Land", target)
            tools.set_opacity(layer, 50)
            layer.visible = True

# One-size-fits-all for MDFC Front, MDFC Back, Transform, and Ixalan land back. Lessons too I guess.
class DFCModularTemplate (FullArtModularTemplate):

    def __init__ (self, layout):
        super().__init__(layout)
        
        if config.side_pins: top = "Legendary"
        else: top = "Floating"
        pinline_mask_set = psd.getLayerSet('Masked', 'Pinlines')
        legend_mask = psd.getLayer(f'{top} Crown', pinline_mask_set)
        namebox_mask = psd.getLayer('Name', psd.getLayerSet('Mask Wearer', 'Name'))
        trans_icon = {
            'sunmoondfc': [ '', '' ], 'mooneldrazidfc': [ '', '' ],
            'compasslanddfc': [ '', '' ], 'modal_dfc': [ '', '' ],
            'lesson': ''
            }
        
        # Scoot name text over
        psd.getLayer("Card Name", "Text and Icons").translate(140, 0)
        
        # If MDFC, set the pointy, else it's the circle
        if layout.transform_icon == 'modal_dfc':
            dfc = 'MDFC'
            psd.getLayer(dfc, psd.getLayerSet('Mask Wearer', 'Name')).visible = True
        else:
            dfc = 'TDFC'
            psd.getLayer(dfc, 'Name').visible = True
        dfc_pin = psd.getLayer(dfc, pinline_mask_set)
        dfc_icon = psd.getLayer(dfc, 'Text and Icons')
        dfc_icon.textItem.contents = trans_icon[layout.transform_icon][self.layout.face]
        dfc_icon.visible = True
        
        # Cut out the icon from the legendary frame if necessary
        if self.is_legendary:
            tools.magic_wand_select(dfc_pin, 0, 0)
            app.activeDocument.selection.expand(2)
            app.activeDocument.selection.invert()
            tools.layer_mask_select(legend_mask)
            app.activeDocument.selection.fill(tools.rgbcolor(0, 0, 0))
            app.activeDocument.selection.deselect()
            
        # Turn on/off pinlines
        psd.getLayer('Standard', pinline_mask_set).visible = False
        dfc_pin.visible = True
            
        # Turn on/off the emboss
        psd.getLayer('Emboss', 'Name').visible = False
        dfc_emboss = psd.getLayer('DFC Emboss', 'Name')
        dfc_emboss.visible = True

        # Copy emboss, invert middle and adjust levels to create mask for namebox
        dfc_mask = psd.getLayer('DFC Emboss Mask', 'Name')
        dfc_mask.visible = True
        app.activeDocument.activeLayer = dfc_mask
        app.activeDocument.selection.selectAll()
        app.activeDocument.selection.copy()
        tools.layer_mask_select(namebox_mask)
        app.activeDocument.selection.clear()
        tools.paste_in_place()
        app.activeDocument.selection.deselect()
        dfc_mask.delete()


"""
    Created by preshtildeath
    Expandable pixel-art template
    100dpi start, then can blow up to 800dpi with the CRT filter
"""
class PixelModularTemplate (temp.StarterTemplate):
    """
     * Created by preshtildeath
     * 100dpi pixelart based template
    """        
    def template_file_name (self):
        return "preshtildeath/pixel-template"
    
    def template_suffix (self):
        suffix = "PXL Mod" # Base suffix
        try:
            if cfg.save_jpeg: test_file = f"{self.layout.name} ({suffix}).jpg"
            else: test_file = f"{self.layout.name} ({suffix}).png"
            end_file = tools.filename_append(test_file, os.path.join(con.cwd, "out")) # Check for multiples
            end_file = os.path.splitext(os.path.basename(end_file))[0] # Cut to basename, then strip extension
            end_file = end_file[end_file.find("(")+1:end_file.rfind(")")] # Take out everything between first "(" and last ")"
            return end_file # "Base suffix) (x"
        except:
            return suffix

    def load_artwork (self):

        console.update("Loading artwork...")

        # Establish size to scale down to and resize
        ref_w = self.art_reference.bounds[2]-self.art_reference.bounds[0]
        ref_h = self.art_reference.bounds[3]-self.art_reference.bounds[1]
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

    def collector_info (self): pass

    def __init__ (self, layout):

        # Setup some parameters
        app.preferences.interpolation = ps.ResampleMethod.NearestNeighbor
        cfg.remove_flavor = True
        cfg.remove_reminder = True
        con.font_rules_text = "m5x7"
        con.font_rules_text_italic = "Silver"

        # If inverted or circle-less, inner symbols are colored and background circle is black
        if config.invert_mana or not config.symbol_bg:
            con.rgb_primary = {'r': 217, 'g': 217, 'b': 217}
            con.rgb_c, con.rgb_w, con.rgb_u, con.rgb_bh, con.rgb_b, con.rgb_r, con.rgb_g = [{'r': 13, 'g': 13, 'b': 13}]*7
            con.rgbi_c = {'r': 217, 'g': 217, 'b': 217}
            con.rgbi_w = {'r': 255, 'g': 255, 'b': 255}
            con.rgbi_u = {'r':  64, 'g': 134, 'b': 255}
            con.rgbi_bh= {'r': 125, 'g':   0, 'b': 255}
            con.rgbi_b = {'r': 125, 'g':   0, 'b': 255}
            con.rgbi_r = {'r': 255, 'g': 128, 'b': 128}
            con.rgbi_g = {'r': 128, 'g': 255, 'b': 128}
        else:
            con.rgb_c = {'r': 217, 'g': 217, 'b': 217}
            con.rgb_w = {'r': 255, 'g': 255, 'b': 255}
            con.rgb_u = {'r':  64, 'g': 134, 'b': 255}
            con.rgb_bh= {'r': 125, 'g':   0, 'b': 255}
            con.rgb_b = {'r': 125, 'g':   0, 'b': 255}
            con.rgb_r = {'r': 255, 'g': 128, 'b': 128}
            con.rgb_g = {'r': 128, 'g': 255, 'b': 128}

        # Replace Q, q, and o with ^ for later deletion
        if not config.symbol_bg:
            for s in con.symbols.keys():
                con.symbols[s] = re.sub("[Qqo]", "^", con.symbols[s])
        
        super().__init__(layout)

        self.text_layers()

    def text_layers(self):

        console.update("Preparing text layers...")

        # Set up text layers
        name_layer = psd.getLayer('Name', 'Text')
        type_layer = psd.getLayer('Typeline', 'Text')
        mana_layer = psd.getLayer('Mana', 'Text')
        body_layer = psd.getLayer('Oracle', 'Text')
        textbox = psd.getLayer("Mask", "Textbox")
        self.art_reference = psd.getLayer("Art Ref", "Ref")
        title_pin = psd.getLayer("Title", "Pinlines")
        type_pin = psd.getLayer("Type", "Pinlines")

        # Set artist info
        artist_text = psd.getLayer('Artist', 'Legal').textItem
        artist_text.contents = self.layout.artist
        
        # Name, Type, Mana, and Body text
        self.tx_layers.extend([
            txt_layers.TextField(
                layer = name_layer,
                text_contents = self.layout.name,
                text_color = psd.get_text_layer_color(name_layer)
            ),
            txt_layers.TextField(
                layer = type_layer,
                text_contents = self.layout.type_line,
                text_color = psd.get_text_layer_color(type_layer)
            ),
            txt_layers.BasicFormattedTextField(
                layer=mana_layer,
                text_contents=self.layout.mana_cost,
                text_color = psd.get_text_layer_color(mana_layer)
            )
        ])

        body_text = txt_layers.BasicFormattedTextField(
                layer = body_layer,
                text_contents = self.layout.oracle_text,
                text_color = psd.get_text_layer_color(body_layer)
            )
        body_text.execute()
        body_layer.textItem.antiAliasMethod = ps.AntiAlias.NoAntialias
        body_layer.textItem.leading *= 0.8

        if self.is_creature:
            power_toughness = psd.getLayer("PT Text", "Text")
            self.tx_layers.append(
                txt_layers.TextField(
                    layer = power_toughness,
                    text_contents = f'{self.layout.power}/{self.layout.toughness}',
                    text_color = psd.get_text_layer_color(power_toughness)
                )
            )
            delta = body_layer.bounds[3]-textbox.bounds[3]+8
        else:
            delta = body_layer.bounds[3]-textbox.bounds[3]+3
            
        body_layer.translate(0, -delta)
        type_layer.translate(0, -delta)
        h_delta = textbox.bounds[3] - (type_pin.bounds[1] + 26)
        h_percent = h_delta / (textbox.bounds[3] - textbox.bounds[1]) * 100
        tools.zero_transform(textbox, "nearestNeighbor", y=-delta, h=h_percent)

        l, t, r, b = 10, title_pin.bounds[3]-4, app.activeDocument.width-10, type_pin.bounds[1]+4
        app.activeDocument.selection.select(
            [[l, t], [r, t], [r, b], [l, b]]
        )
        app.activeDocument.activeLayer = self.art_reference
        app.activeDocument.selection.fill(tools.rgbcolor(0,0,0))

    def enable_frame_layers (self):
        
        # Eldrazi formatting?
        if self.layout.is_colorless:

            # Devoid formatting?
            if self.layout.pinlines == self.layout.twins:
                self.layout.twins = 'Land'
            self.layout.pinlines = 'Land'
            
        # Twins and p/t box
        psd.getLayer(self.layout.twins, 'Name').visible = True
        psd.getLayer(self.layout.twins, 'Type').visible = True
        if self.is_creature:
            psd.getLayerSet("PT Box").visible = True
            psd.getLayer(self.layout.twins, 'PT Box').visible = True

        # Pinlines & Textbox
        if len(self.layout.pinlines) != 2:
            psd.getLayer(self.layout.pinlines, 'Pinlines').visible = True
            psd.getLayer(self.layout.pinlines, 'Textbox').visible = True
        else:
            tools.wubrg_layer_sort(self.layout.pinlines, 'Pinlines')
            tools.wubrg_layer_sort(self.layout.pinlines, 'Textbox')

        # Land formatting
        if self.is_land:
            land_textbox = psd.getLayer("Land", "Textbox")
            if not land_textbox.visible: land_textbox.fillOpacity = 50
            land_textbox.visible = True

    def post_text_layers(self):
        
        console.update("Post text layers...")

        # Establish the layers
        name_layer = psd.getLayer('Name', 'Text')
        type_layer = psd.getLayer('Typeline', 'Text')
        mana_layer = psd.getLayer('Mana', 'Text')
        body_layer = psd.getLayer('Oracle', 'Text')

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

        # Get rid of the "^" symbols if the symbol_bg is False in our config
        if not config.symbol_bg:
            psd.replace_text(mana_layer, "^", "")
            psd.replace_text(body_layer, "^", "")
        mana_layer.textItem.font = con.font_mana
        time.sleep(0.2)
        mana_layer.textItem.font = con.font_mana

        # Do our big bad CRT filter treatment
        if config.crt_filter:
            # app.activeDocument.activeLayer = self.art_layer
            # console.wait("CRT Filter enabled, make any adjustments then hit continue.")
            console.update("Applying CRT filter...")
            crt_tools.crt_filter()

    def post_execute(self):

        # Reset constants
        con.reload()

        if config.move_art:
            # Move art source to a new folder
            console.update("Moving art file...")
            move_art(self.layout.file, self.layout.name, self.layout.artist, self.layout.set)