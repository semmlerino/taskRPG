# modules/ui/managers/image_manager.py

import os
import logging
import asyncio
from typing import Dict, Optional, Set, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
from PyQt6.QtWidgets import QProgressDialog, QMessageBox
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from modules.constants import ASSETS_DIR
from modules.image_generator import ImageGenerator
from modules.core.error_handler import ErrorSeverity
from modules.utils.qt_helpers import ensure_qt_application

@dataclass
class ImageGenerationTask:
    """Represents an image generation task."""
    node_key: str
    prompt: str
    save_path: str
    priority: int = 0

class ImageGenerationWorker(QThread):
    """Worker thread for image generation."""
    generation_complete = pyqtSignal(str, str, bool)  # node_key, path, success
    progress_update = pyqtSignal(str, int)  # node_key, progress

    def __init__(self, image_generator: ImageGenerator, task: ImageGenerationTask):
        super().__init__()
        self.image_generator = image_generator
        self.task = task
        self._is_cancelled = False

    def run(self):
        try:
            result = self.image_generator.generate_image(
                self.task.prompt,
                self.task.save_path
            )
            if not self._is_cancelled:
                self.generation_complete.emit(
                    self.task.node_key,
                    result if result else "",
                    bool(result)
                )
        except Exception as e:
            logging.error(f"Error generating image for {self.task.node_key}: {e}")
            if not self._is_cancelled:
                self.generation_complete.emit(self.task.node_key, "", False)

    def cancel(self):
        """Cancel the current generation task."""
        self._is_cancelled = True

class ImageManager:
    """Manages image generation, caching, and loading."""
    
    def __init__(self, main_window):
        ensure_qt_application()
        self.main_window = main_window
        self.image_generator = ImageGenerator()
        self.image_cache: Dict[str, str] = {}
        self.generation_queue: Set[str] = set()
        self.active_workers: Dict[str, ImageGenerationWorker] = {}
        self.thread_pool = ThreadPoolExecutor(max_workers=2)
        self._generation_callbacks: Dict[str, list] = {}
        
        # Register with error handler
        self._register_error_handlers()

    def _register_error_handlers(self):
        """Register image-specific error handlers."""
        self.main_window.error_handler.register_handler(
            IOError,
            self._handle_io_error
        )
        self.main_window.error_handler.register_handler(
            Image.DecompressionBombError,
            self._handle_image_size_error
        )

    async def initialize_story_images(
        self,
        story_path: str,
        story_image_folder: str,
        image_prompts: Dict[str, str]
    ):
        """Initialize and generate missing images for a story."""
        try:
            os.makedirs(story_image_folder, exist_ok=True)
            logging.info(f"Ensuring image folder: {story_image_folder}")
            
            # Find missing images
            missing_images = []
            for node_key, prompt in image_prompts.items():
                image_path = os.path.join(story_image_folder, f"{node_key}.png")
                if not os.path.exists(image_path) or not self._verify_image(image_path):
                    missing_images.append(
                        ImageGenerationTask(
                            node_key=node_key,
                            prompt=prompt,
                            save_path=image_path
                        )
                    )

            if missing_images:
                await self._generate_missing_images(missing_images)
                
        except Exception as e:
            self._handle_initialization_error(e)

    def request_image(
        self,
        node_key: str,
        prompt: str,
        callback: Optional[Callable[[str, bool], None]] = None
    ):
        """Request an image generation with optional callback."""
        try:
            if node_key in self.image_cache:
                if callback:
                    callback(self.image_cache[node_key], True)
                return

            if node_key in self.generation_queue:
                if callback:
                    self._generation_callbacks.setdefault(node_key, []).append(callback)
                return

            self.generation_queue.add(node_key)
            if callback:
                self._generation_callbacks.setdefault(node_key, []).append(callback)

            task = ImageGenerationTask(
                node_key=node_key,
                prompt=prompt,
                save_path=os.path.join(
                    self.main_window.story_manager.story_image_folder,
                    f"{node_key}.png"
                )
            )
            
            self._start_generation(task)
            
        except Exception as e:
            self._handle_generation_error(e, node_key)

    def _start_generation(self, task: ImageGenerationTask):
        """Start an image generation worker."""
        try:
            worker = ImageGenerationWorker(self.image_generator, task)
            worker.generation_complete.connect(
                lambda node_key, path, success: self._handle_generation_complete(
                    node_key, path, success
                )
            )
            
            self.active_workers[task.node_key] = worker
            worker.start()
            
        except Exception as e:
            self._handle_worker_error(e, task.node_key)

    def _handle_generation_complete(self, node_key: str, path: str, success: bool):
        """Handle completion of image generation."""
        try:
            if success and os.path.exists(path):
                self.image_cache[node_key] = path
                
            self.generation_queue.discard(node_key)
            
            # Execute callbacks
            callbacks = self._generation_callbacks.pop(node_key, [])
            for callback in callbacks:
                try:
                    callback(path if success else "", success)
                except Exception as e:
                    logging.error(f"Error in image generation callback: {e}")
                    
            # Cleanup worker
            if node_key in self.active_workers:
                self.active_workers[node_key].deleteLater()
                del self.active_workers[node_key]
                
        except Exception as e:
            self._handle_completion_error(e, node_key)

    def cancel_generation(self, node_key: str):
        """Cancel an ongoing image generation."""
        try:
            if worker := self.active_workers.get(node_key):
                worker.cancel()
                worker.wait()
                worker.deleteLater()
                del self.active_workers[node_key]
                
            self.generation_queue.discard(node_key)
            self._generation_callbacks.pop(node_key, None)
            
        except Exception as e:
            logging.error(f"Error cancelling generation for {node_key}: {e}")

    def _verify_image(self, image_path: str) -> bool:
        """Verify an image file is valid."""
        try:
            with Image.open(image_path) as img:
                img.verify()
            return True
        except Exception:
            return False

    async def _generate_missing_images(self, tasks: list[ImageGenerationTask]):
        """Generate missing images with progress tracking."""
        try:
            progress = QProgressDialog(
                "Generating missing story images...",
                "Cancel",
                0,
                len(tasks),
                self.main_window
            )
            progress.setWindowModality(Qt.WindowModal)
            progress.setValue(0)
            
            for i, task in enumerate(tasks):
                if progress.wasCanceled():
                    break

                progress.setLabelText(
                    f"Generating image for: {task.node_key}\n"
                    f"Progress: {i + 1}/{len(tasks)}"
                )
                
                # Generate image
                self.request_image(
                    task.node_key,
                    task.prompt,
                    lambda path, success: self._update_progress(progress, i + 1)
                )
                
                # Allow UI updates
                await asyncio.sleep(0.1)
                
            progress.setValue(len(tasks))
            
        except Exception as e:
            self._handle_bulk_generation_error(e)

    def _update_progress(self, progress: QProgressDialog, value: int):
        """Update progress dialog safely."""
        try:
            if not progress.wasCanceled():
                progress.setValue(value)
        except Exception as e:
            logging.error(f"Error updating progress: {e}")

    def _handle_io_error(self, error: IOError, context):
        """Handle IO-related errors."""
        QMessageBox.warning(
            self.main_window,
            "Image Generation Error",
            f"Failed to access image file: {str(error)}\n"
            "Please check disk space and permissions."
        )

    def _handle_image_size_error(self, error: Image.DecompressionBombError, context):
        """Handle image size-related errors."""
        QMessageBox.warning(
            self.main_window,
            "Image Error",
            "The generated image is too large to process.\n"
            "Please try again with different parameters."
        )

    def _handle_initialization_error(self, error: Exception):
        """Handle initialization errors."""
        context = self.main_window.error_handler.create_context(
            "ImageManager",
            "initialization",
            {},
            ErrorSeverity.HIGH
        )
        self.main_window.error_handler.handle_error(error, context)

    def _handle_generation_error(self, error: Exception, node_key: str):
        """Handle generation errors."""
        context = self.main_window.error_handler.create_context(
            "ImageManager",
            "generation",
            {'node_key': node_key},
            ErrorSeverity.MEDIUM
        )
        self.main_window.error_handler.handle_error(error, context)

    def _handle_worker_error(self, error: Exception, node_key: str):
        """Handle worker thread errors."""
        context = self.main_window.error_handler.create_context(
            "ImageManager",
            "worker",
            {'node_key': node_key},
            ErrorSeverity.MEDIUM
        )
        self.main_window.error_handler.handle_error(error, context)

    def _handle_completion_error(self, error: Exception, node_key: str):
        """Handle completion callback errors."""
        context = self.main_window.error_handler.create_context(
            "ImageManager",
            "completion",
            {'node_key': node_key},
            ErrorSeverity.LOW
        )
        self.main_window.error_handler.handle_error(error, context)

    def _handle_bulk_generation_error(self, error: Exception):
        """Handle bulk generation errors."""
        context = self.main_window.error_handler.create_context(
            "ImageManager",
            "bulk_generation",
            {},
            ErrorSeverity.HIGH
        )
        self.main_window.error_handler.handle_error(error, context)

    def cleanup(self):
        """Clean up image manager resources."""
        try:
            logging.info("Cleaning up image manager")
            
            # Cancel all active generations
            for node_key in list(self.active_workers.keys()):
                self.cancel_generation(node_key)
                
            # Clear caches
            self.image_cache.clear()
            self.generation_queue.clear()
            self._generation_callbacks.clear()
            
            # Shutdown thread pool
            self.thread_pool.shutdown(wait=False)
            
        except Exception as e:
            logging.error(f"Error during image manager cleanup: {e}")