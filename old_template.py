"""
PRESHTILDEATH TEMPLATES
"""
import os
import sys
import tools
import proxyshop.text_layers as txt_layers
import proxyshop.templates as temp
import proxyshop.constants as con
import proxyshop.helpers as psd
import photoshop.api as ps
from proxyshop.constants import con
from proxyshop.settings import cfg
from proxyshop import format_text, gui
console = gui.console_handler
app = ps.Application()

print(sys.path)

# Ensure scaling with pixels, font size with points
app.preferences.rulerUnits = ps.Units.Pixels
app.preferences.typeUnits = ps.Units.Points


class FullArtModularTemplate (temp.BaseTemplate):
    """
     * Created by preshtildeath
     * Expands the textbox based on how much oracle text a card has
    """        
    def template_file_name (self):
        return "preshtildeath/fullart-modular"
    
    def template_suffix (self):
        return "Full Mod"

    def load_template (self):
        """
         * Opens the template's PSD file in Photoshop.
        """
        self.file_path = os.path.join(
            con.cwd,
            f"templates/{self.template_file_name()}.psd"
        )
        app.load(self.file_path)
        # TODO: if that's the file that's currently open, reset instead of opening?

    def load_artwork (self):
        """
         * Loads the specified art file into the specified layer.
        """
        psd.paste_file(self.art_layer, self.file)

    def __init__ (self, layout, file):
        # Setup inherited info, tx_layers, template PSD
        self.failed = False
        self.layout = layout
        self.file = file
        self.tx_layers = []
        
        try: self.load_template()
        except Exception as e:
            result = console.log_error(
                "PSD not found! Make sure to download the photoshop templates!",
                self.layout.name,
                self.template_file_name(),
                e
                )

        self.art_layer = psd.getLayer('Layer 1')

        # set stroke size
        cfg.symbol_stroke = 4

        # define some characteristics
        try: self.is_creature = bool(self.layout.power and self.layout.toughness)
        except: self.is_creature = False
        try: self.is_legendary = bool(self.layout.type_line.find("Legendary") >= 0)
        except: self.is_legendary = False
        try: self.is_land = bool(self.layout.type_line.find("Land") >= 0)
        except: self.is_land = False
        try: self.is_basic = self.is_basic
        except: self.is_basic = False
        
        # rip out the flavor and reminder texts
        layout.no_collector = True
        layout.flavor_text = ""
        if not self.is_basic:
            layout.oracle_text = format_text.strip_reminder_text(layout.oracle_text)
                
        # lands have a fun border
        if self.is_land or self.is_basic: self.art_reference = psd.getLayer('Full Art Frame', 'Ref')
        # legendary framing is slightly scooted down
        elif self.is_legendary: self.art_reference = psd.getLayer('Legendary Frame', 'Ref')
        # everything else is just normie
        else: self.art_reference = psd.getLayer('Art Frame', 'Ref')

    def execute (self):
        """
         * Perform actions to populate this template.
         * Load and frame artwork, enable frame layers, and execute all text layers.
        """
        # Load in artwork and frame it
        self.load_artwork()
        psd.frame_layer(self.art_layer, self.art_reference)

        # Set up text layers
        self.text_layers()

        # Enable the layers we need
        try:
            console.update("Enabling frame layers...")
            self.enable_frame_layers()
        except Exception as e:
            result = console.log_error(
                "This card is incompatible with this Template!",
                self.layout.name,
                self.template_file_name(),
                e
            )
            return result

        # Input and format each text layer
        try:
            console.update("Formatting text...")
            for this_layer in self.tx_layers:
                this_layer.execute()
        except Exception as e:
            result = console.log_error(
                "This card is incompatible with this Template!",
                self.layout.name,
                self.template_file_name(),
                e
            )
            return result

        # Exit early defined?
        try: self.exit_early
        except Exception: self.exit_early = False

        # Manual edit step?
        if self.exit_early or cfg.exit_early:
            console.wait(
                "Manual editing enabled! When you're ready to save, click continue..."
            )
            console.update("Saving document...\n")

        # Format file name
        file_name = f"{self.layout.name} ({self.template_suffix()})"

        # Save the document
        try:
            if cfg.save_jpeg:
                file_name = tools.filename_append(
                    os.path.join(con.cwd, 'out/'),
                    file_name,
                    '.jpg'
                )
                psd.save_document_jpeg(file_name)
            else:
                file_name = tools.filename_append(
                    os.path.join(con.cwd, 'out/'),
                    file_name,
                    '.png'
                )
                psd.save_document_png(file_name)
            console.update(f"{file_name} rendered successfully!")
            # Reset document
            psd.reset_document(os.path.basename(self.file_path))
        except: console.update(f"Error during save process!\nMake sure the file saved.")

        # Move art source to a new folder
        try:
            ext = self.file[self.file.rfind('.'):]
            fin_path = os.path.join(con.cwd, 'art/finished')
            try: os.mkdir(fin_path)
            except: pass
            new_name = tools.filename_append(
                f'{fin_path}/',
                f'{self.layout.name} ({self.layout.artist}) [{self.layout.set}]',
                ext )
            os.rename(self.file, f'{fin_path}/{new_name}{ext}')
            console.update(f"{new_name}{ext} moved successfully!")
        except: console.update('Problem occurred moving art file.')
        console.end_await()
        return True

    def text_layers (self):
        """
         * Set up the card's mana cost, name (scaled to not overlap with mana cost), expansion symbol, and type line
         * (scaled to not overlap with the expansion symbol).
        """
        
        mana_layer = psd.getLayerSet('Symbols', 'Mana Cost')
        name_layer = psd.getLayer('Card Name', 'Text and Icons')
        exp_layer = psd.getLayer('Expansion Symbol',
            psd.getLayerSet('Expansion', 'Text and Icons')
        )
        exp_ref = psd.getLayer('Expansion', 'Ref')
        type_layer = psd.getLayer('Typeline', 'Text and Icons')
        text_box = psd.getLayer('Base', 'Textbox')
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
        artist_text = psd.getLayer('Artist', 'Text and Icons').textItem
        artist_text.contents = self.layout.artist
        
        # Do the mana cost
        if len(self.layout.mana_cost) > 0:
            mana_layer = tools.mana_cost_render(mana_layer, self.layout.mana_cost)
        else: mana_layer = tools.empty_mana_cost(mana_layer)
        
        # Name and type text
        self.tx_layers.extend([
            txt_layers.ScaledTextField(
                layer = name_layer,
                text_contents = self.layout.name,
                text_color = psd.get_text_layer_color(name_layer),
                reference_layer = mana_layer
            ),
            txt_layers.ScaledTextField(
                layer = type_layer,
                text_contents = self.layout.type_line,
                text_color = psd.get_text_layer_color(type_layer),
                reference_layer = exp_layer
            )
        ])
        
        if self.is_creature:        
            # Center the rules text if the text is at most two lines
            is_centered = bool( scale <= 2)
            # Fix modifier
            if modifier > 160: modifier = 160
            if scale == 0: modifier = 360
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
                    is_centered = is_centered
                )
            ])
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
        type_layer.translate( 0, modifier )
        tools.layer_vert_stretch( textbox_ref, modifier, 'bottom' )
        
        # Set symbol
        set_pdf = tools.get_set_pdf(self.layout.set)
        tools.get_expansion(
            exp_layer,
            self.layout.rarity,
            exp_ref,
            set_pdf
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

        # legendary crown
        if self.is_legendary:
            title_ref = psd.getLayer('Legendary', 'Ref')
            psd.getLayer('Legendary Crown', psd.getLayerSet('Masked', 'Pinlines')).visible = True
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
            app.activeDocument.selection.fill( psd.rgb_black() ) # Fill it with black
            app.activeDocument.selection.deselect() # Deselect

class BasicModularTemplate (FullArtModularTemplate):
      
    def template_file_name (self):
        return "preshtildeath/fullart-modular"
    
    def template_suffix (self):
        return self.layout.artist

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
        """
         * Set up the card's mana cost, name (scaled to not overlap with mana cost), expansion symbol, and type line
         * (scaled to not overlap with the expansion symbol).
        """

        name_layer = psd.getLayer('Card Name', 'Text and Icons')
        exp_layer = psd.getLayer('Expansion Symbol',
                                       psd.getLayerSet('Expansion', 'Text and Icons')
                                       )
        exp_ref = psd.getLayer('Expansion', 'Ref')
        type_layer = psd.getLayer('Typeline', 'Text and Icons')
        # Apply typeline translate and textbox stretch
        type_layer.translate( 0, 480 )
        # Set artist info
        artist_text = psd.getLayer('Artist', 'Text and Icons').textItem
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
        tools.get_expansion(
            exp_layer,
            'common',
            exp_ref,
            set_pdf
            )

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
        super().__init__(layout, file)
        self.layout.oracle_text = ""

class DFCModularTemplate (FullArtModularTemplate):
      
    def template_file_name (self):
        return "preshtildeath/fullart-modular"
    
    def template_suffix (self):
        return "Fullart DFC"

    def __init__ (self, layout, file):
        super().__init__(layout, file)
        
        pinline_mask_set = psd.getLayerSet('Masked', 'Pinlines')
        type_pins = psd.getLayer('Type and Pinlines', pinline_mask_set)
        legend_mask = psd.getLayer('Legendary Crown', pinline_mask_set)
        namebox_mask = psd.getLayer('Name', psd.getLayerSet('Mask Wearer', 'Name'))
        white = psd.rgb_white()
        black = psd.rgb_black()
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
            app.activeDocument.selection.fill(black)
            app.activeDocument.selection.deselect()