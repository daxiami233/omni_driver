from .app import App


class HarmonyApp(App):
    def __init__(self, app_path: str = "", package_name: str = "", entry_ability: str = ""):
        super().__init__(app_path)
        self.package_name = package_name
        self.entry_ability = entry_ability
        self.main_page = ""

