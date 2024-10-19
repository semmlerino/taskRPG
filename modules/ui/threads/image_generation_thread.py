# modules/ui/threads/image_generation_thread.py

from PyQt5.QtCore import QThread, pyqtSignal
from modules.image_generator import ImageGenerator

class ImageGenerationThread(QThread):
    """
    Thread class for generating images without freezing the UI.
    """
    image_generated = pyqtSignal(str)

    def __init__(self, image_generator: ImageGenerator, prompt: str):
        super().__init__()
        self.image_generator = image_generator
        self.prompt = prompt

    def run(self):
        image_path = self.image_generator.generate_image(self.prompt)
        self.image_generated.emit(image_path)
