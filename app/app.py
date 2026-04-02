from abc import ABC


class App(ABC):
    def __init__(self, app_path: str = ""):
        self.app_path = app_path
        self.package_name = ""
        self.entry_ability = ""
        self.main_page = ""
        self.app_name = ""

