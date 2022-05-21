from proxyshop.settings import Config
import os.path as path
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
