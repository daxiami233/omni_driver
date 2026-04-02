from .app import App


class AndroidApp(App):
    def __init__(self, app_path: str = ""):
        super().__init__(app_path)
        if not app_path:
            return

        from androguard.core.apk import APK

        apk = APK(app_path)
        self.package_name = apk.get_package() or ""
        self.entry_ability = apk.get_main_activity() or ""
        self.main_page = self.entry_ability
        self.app_name = apk.get_app_name() or ""
        self.abilities = apk.get_activities() or []

