from modules.constants import UI_COLORS, UI_FONTS

class StyleManager:
    @staticmethod
    def get_button_style(color=UI_COLORS['PRIMARY']):
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: {StyleManager._darken_color(color)};
            }}
        """

    @staticmethod
    def get_panel_style():
        return f"""
            QWidget {{
                background-color: {UI_COLORS['BACKGROUND']};
                border: 1px solid {UI_COLORS['BORDER']};
                border-radius: 5px;
            }}
        """

    @staticmethod
    def _darken_color(hex_color: str, factor: float = 0.8) -> str:
        # Helper method to darken a hex color
        # Implementation here
        pass 