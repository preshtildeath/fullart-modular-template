import os
import configparser
self_dir = os.path.dirname(__file__)
def_path = os.path.join(self_dir, "config.ini")

class preshCFG:
    def __init__(self, path=def_path):
        self.side_pins = None
        self.load(path)
    
    def load(self, path):
        self.file = configparser.ConfigParser(
            comment_prefixes="/", allow_no_value=True
            )
        self.file.optionxform = str
        self.file.read(path, encoding="utf-8")

        self.side_pins = self.file.getboolean("GENERAL", "Side.Pinlines")
        self.hollow_mana = self.file.getboolean("GENERAL", "Hollow.Mana")
        self.move_art = self.file.getboolean("GENERAL", "Move.Art")
        self.crt_filter = self.file.getboolean("PIXEL", "CRT.Filter")
        self.invert_mana = self.file.getboolean("PIXEL", "Invert.Mana")
        self.symbol_bg = self.file.getboolean("PIXEL", "Symbol.BG")

    def save(self, c):
        self.file.set("GENERAL", "Side.Pinelines", str(c["side_pins"]))
        self.file.set("GENERAL", "Hollow.Mana", str(c["hollow_mana"]))
        self.file.set("GENERAL", "Move.Art", str(c["move_art"]))
        self.file.set("PIXEL", "CRT.Filter", str(c["crt_filter"]))
        self.file.set("PIXEL", "Invert.Mana", str(c["invert_mana"]))
        self.file.set("PIXEL", "Symbol.BG", str(c["symbol_bg"]))
        with open("config.ini", "w", encoding="utf-8") as cfile:
            self.file.write(cfile)
    
    def reload(self, path=def_path):
        del self.file
        self.load(path)

config = preshCFG()