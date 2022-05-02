"""
PRESHTILDEATH TEMPLATES
"""
import os
import tools
import proxyshop.text_layers as txt_layers
import proxyshop.templates as temp
import proxyshop.helpers as psd
import photoshop.api as ps
from proxyshop.constants import con
from proxyshop.settings import cfg
from proxyshop import gui
from configs import config
console = gui.console_handler
app = ps.Application()

# Ensure scaling with pixels, font size with points
app.preferences.rulerUnits = ps.Units.Pixels
app.preferences.typeUnits = ps.Units.Points
app.preferences.interpolation = ps.ResampleMethod.BicubicAutomatic

class FullArtModularTemplate (temp.StarterTemplate):
    """
     * Created by preshtildeath
     * Expands the textbox based on how much oracle text a card has
    """        
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
        """
         * Loads the specified art file into the specified layer.
        """
        psd.paste_file(self.art_layer, self.file)
        tools.zero_transform(self.art_layer)

    def collector_info (self): pass
    def basic_text_layers(self, text_and_icons): pass
    def enable_hollow_crown(crown, pinlines): pass
    def paste_scryfall_scan(self, reference_layer, rotate=False): pass

    def __init__ (self, layout, file):
        self.cwd = tools.parent_dirs(__file__, 4)
        cfg.remove_flavor = True
        cfg.remove_reminder = True
        con.layers["ARTIST"] = "Name"
        self.black = tools.rgbcolor(0, 0, 0)
        
        super().__init__(layout, file)

        # define some characteristics
        try: self.is_basic
        except: self.is_basic = False
        try: self.is_land = bool(self.layout.type_line.find("Land") >= 0 or self.is_basic)
        except: self.is_land = False
                
        # lands have a fun border
        if self.is_land: self.art_reference = psd.getLayer('Full Art Frame', 'Ref')
        # legendary framing is slightly scooted down
        elif self.is_legendary: self.art_reference = psd.getLayer('Legendary Frame', 'Ref')
        # everything else is just normie
        else: self.art_reference = psd.getLayer('Art Frame', 'Ref')

        # Set up text layers
        console.update("Preparing text layers...")
        self.text_layers()

    def post_exectute(self):
        # Move art source to a new folder
        work_path = os.path.dirname(self.file)
        fin_path = os.path.join(work_path, 'finished')
        try: os.mkdir(fin_path)
        except: pass
        new_file = tools.filename_append(self.file, fin_path)
        try:
            os.rename(self.file, new_file)
        except Exception as e:
            with open(os.path.join(work_path, "error.txt"), "a") as errlog: errlog.write(e)

    def text_layers (self):
        """
         * Set up the card's mana cost, name (scaled to not overlap with mana cost), expansion symbol, and type line
         * (scaled to not overlap with the expansion symbol).
        """

        name_layer = psd.getLayer('Card Name', 'Text and Icons')
        exp_layer = psd.getLayer('Expansion Symbol', 'Expansion')
        exp_ref = psd.getLayer('Expansion', 'Ref')
        type_layer = psd.getLayer('Typeline', 'Text and Icons')
        textbox_ref = psd.getLayer('Textbox', 'Ref')
        
        # Move typeline and modify textbox reference and text outlines if certain criteria is met
        scale = tools.dirty_text_scale( self.layout.oracle_text )
        if scale > 9: modifier = -320
        elif scale > 6: modifier = -160
        elif scale == 0: modifier = 480
        elif scale <= 1: modifier = 240
        elif scale <= 3: modifier = 160
        else: modifier = 0
        
        # Set artist info
        artist_text = psd.getLayer('Artist', 'Legal').textItem
        artist_text.contents = self.layout.artist
        
        # Do the mana cost
        # If config sets symbols to png mode
        # mana_layer = psd.getLayerSet('Symbols', 'Mana Cost')
        # mana_layer = tools.mana_cost_render(mana_layer, self.layout.mana_cost)
        # else:
        mana_layer = psd.getLayer('Text', 'Mana Cost')
        mana_layer.visible = True
        self.tx_layers.append(
            txt_layers.BasicFormattedTextField(
                layer=mana_layer,
                text_contents=self.layout.mana_cost,
                text_color=self.black
            )
        )
        
        if self.is_creature:        
            # Center the rules text if the text is at most two lines
            is_centered = bool( scale <= 2)
            # Fix modifier
            if modifier > 160: modifier = 160
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
            
        # Apply typeline translate and textbox stretch
        type_layer.translate(0, modifier)
        tools.layer_vert_stretch(textbox_ref, modifier, 'bottom')
        
        # Set symbol
        set_pdf = tools.get_set_pdf(self.layout.set)
        exp_layer = tools.get_expansion(exp_layer, self.layout.rarity, exp_ref, set_pdf)
        
        # Mana Cost, Name, and Type text
        self.tx_layers.extend([
            txt_layers.ScaledTextField(
                layer = name_layer,
                text_contents = self.layout.name,
                text_color = psd.get_text_layer_color(name_layer),
                reference_layer = mana_layer
            ),
            ScaledTextField(
                layer = type_layer,
                text_contents = self.layout.type_line,
                text_color = psd.get_text_layer_color(type_layer),
                reference_layer = exp_layer
            )
        ])
    #     self.tx_layers.sort(key=self.layer_sort) # Top to bottom

    # def layer_sort (self, tx_layer):
    #     return tx_layer.layer.bounds[1]

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
            app.activeDocument.selection.fill(self.black) # Fill it with black
            app.activeDocument.selection.deselect() # Deselect

class BasicModularTemplate (FullArtModularTemplate):
      
    def template_file_name (self):
        return "preshtildeath/fullart-modular"
    
    def template_suffix (self):
        names = self.layout.artist.split()
        if len(names) > 1: last_name = names[-1]
        else: last_name = names[0]
        return f"{last_name}) ({self.layout.set}"

    def __init__ (self, layout, file):
        self.is_basic = True
        super().__init__(layout, file)
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
        set_pdf = tools.get_set_pdf(self.layout.set)
        tools.get_expansion(exp_layer, 'common', exp_ref, set_pdf)

    def enable_frame_layers (self):
        layer_name = self.name_key[self.layout.name]
        psd.getLayer(layer_name, 'Pinlines').visible = True
        psd.getLayer(layer_name, 'Name').visible = True
        psd.getLayer(layer_name, 'Type').visible = True
        psd.getLayer(layer_name, 'Border').visible = True

class FullArtTextlessTemplate (FullArtModularTemplate):
      
    def template_file_name (self):
        return "preshtildeath/fullart-modular"
    
    def template_suffix (self):
        return "Fullart Textless"

    def __init__ (self, layout, file):
        self.layout.oracle_text = ""
        super().__init__(layout, file)

class DFCModularTemplate (FullArtModularTemplate):
      
    def template_file_name (self):
        return "preshtildeath/fullart-modular"
    
    def template_suffix (self):
        return "Fullart DFC"

    def __init__ (self, layout, file):
        super().__init__(layout, file)
        
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
            app.activeDocument.selection.fill(self.black)
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

class ScaledTextField (txt_layers.TextField):
    def __init__ (self, layer, text_contents, text_color, reference_layer):
        super().__init__(layer, text_contents, text_color)
        self.reference_layer = reference_layer

    def execute (self):
        super().execute()
        layer = self.layer
        reference_layer = self.reference_layer

        try:
            if reference_layer.kind is ps.LayerKind.TextLayer:
                contents = str(reference_layer.textItem.contents)
                if contents in ("", " "):
                    reference_layer.textItem.contents = "."
            elif reference_layer.bounds == [0, 0, 0, 0]:
                return None
        except Exception:
            return None

        # Can't find UnitValue object in python api
        step_size = 0.25
        reference_left_bound = reference_layer.bounds[0]
        layer_left_bound = layer.bounds[0]
        layer_right_bound = layer.bounds[2]
        old_size = layer.textItem.size

        # Obtain proper spacing for this document size
        spacing = int((app.activeDocument.width/3264)*60)

        # Guard against the reference's left bound being left of the layer's left bound or other irregularities
        if reference_left_bound >= layer_left_bound:
            # Step down the font till it clears the reference
            while layer_right_bound > (reference_left_bound-spacing):  # minimum 24 px gap
                layer.textItem.size = layer.textItem.size - step_size
                layer_right_bound = layer.bounds[2]

        # Shift baseline up to keep text centered vertically
        if old_size > layer.textItem.size:
            layer.textItem.baselineShift = (old_size * 0.3) - (layer.textItem.size * 0.3)

        # Fix corrected reference layer
        if reference_layer.kind is ps.LayerKind.TextLayer: 
            if str(reference_layer.textItem.contents) == ".":
                reference_layer.textItem.contents = contents