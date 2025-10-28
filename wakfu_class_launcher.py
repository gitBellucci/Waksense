#!/usr/bin/env python3
"""
Wakfu Class Launcher - Main Application
Detects Cra and Iop players in combat and provides a menu to launch appropriate trackers
"""

import sys
import threading
import time
import re
import subprocess
import json
import math
import platform
from pathlib import Path
from log_deduplicator import LogDeduplicator
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QFrame, QMenu, 
                            QListWidget, QListWidgetItem, QMessageBox, QScrollArea,
                            QFileDialog, QDialog, QFormLayout, QLineEdit, QProgressBar)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QPoint, QRect, QSize, QStandardPaths
from PyQt6.QtGui import QFont, QPalette, QColor, QPainter, QPixmap, QAction, QLinearGradient, QBrush

# Windows-specific imports for window detection
try:
    import win32gui
    import win32process
    WINDOWS_DETECTION_AVAILABLE = True
except ImportError:
    WINDOWS_DETECTION_AVAILABLE = False
    print("DEBUG: win32gui not available, window detection disabled")

class LogMonitorThread(QThread):
    """Thread for monitoring log file with deduplication"""
    class_detected = pyqtSignal(str, str)  # class_name, player_name
    combat_started = pyqtSignal()
    combat_ended = pyqtSignal()
    
    def __init__(self, log_file_path, enable_deduplication=True):
        super().__init__()
        self.log_file = Path(log_file_path)
        self.monitoring = True
        self.last_position = 0
        self.detected_classes = {}  # Store detected classes and players
        self.in_combat = False
        
        # Système de déduplication
        self.enable_deduplication = enable_deduplication
        if enable_deduplication:
            self.deduplicator = LogDeduplicator(duplicate_window_ms=100)  # 100ms de fenêtre
            self.deduplicator.set_debug_mode(True)  # Activer le debug par défaut
            print("DEBUG: Déduplication activée pour le launcher avec debug")
        else:
            self.deduplicator = None
            print("DEBUG: Déduplication désactivée pour le launcher")
        
        # Initialize position to end of file to ignore existing content
        self.initialize_position_to_end()
    
    def initialize_position_to_end(self):
        """Set the file position to the end to ignore existing content"""
        try:
            if self.log_file.exists():
                with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(0, 2)  # Seek to end of file
                    self.last_position = f.tell()
                print(f"DEBUG: Log monitor initialized at position {self.last_position} (end of file)")
            else:
                print("DEBUG: Log file doesn't exist yet, will start from beginning when created")
        except Exception as e:
            print(f"DEBUG: Error initializing log position: {e}")
            self.last_position = 0
        
    def run(self):
        """Monitor log file for changes"""
        consecutive_errors = 0
        max_errors = 5
        
        while self.monitoring:
            try:
                if self.log_file.exists():
                    with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        f.seek(self.last_position)
                        new_lines = f.readlines()
                        self.last_position = f.tell()
                        
                        if new_lines:
                            for line in new_lines:
                                line = line.strip()
                                if line:
                                    # Vérifier la déduplication si activée
                                    if self.enable_deduplication and self.deduplicator:
                                        if not self.deduplicator.should_process_line(line):
                                            continue  # Ignorer les doublons
                                    
                                    # Traiter la ligne normalement
                                    self.process_line(line)
                            
                            consecutive_errors = 0
                        else:
                            time.sleep(0.1)
                else:
                    time.sleep(1)
                    consecutive_errors = 0
                
            except Exception as e:
                consecutive_errors += 1
                print(f"Error monitoring log file: {e}")
                
                if consecutive_errors >= max_errors:
                    print(f"Too many consecutive errors, stopping monitoring")
                    break
                
                sleep_time = min(1 * (2 ** consecutive_errors), 10)
                time.sleep(sleep_time)
    
    def process_line(self, line):
        """Process a log line for class detection"""
        # Check for combat start
        if "[Information (combat)]" in line and "lance le sort" in line:
            if not self.in_combat:
                self.in_combat = True
                self.combat_started.emit()
                print(f"DEBUG: Combat started")
        
        # Check for combat end
        if "Combat terminé, cliquez ici pour rouvrir l'écran de fin de combat." in line:
            if self.in_combat:
                self.in_combat = False
                self.combat_ended.emit()
                print(f"DEBUG: Combat ended")
                return
        
        # Only process combat lines for class detection
        if "[Information (combat)]" not in line or "lance le sort" not in line:
            return
        
        # Extract player and spell info
        spell_match = re.search(r'\[Information \(combat\)\] ([^:]+)[:\s]+lance le sort ([^(]+)', line)
        if not spell_match:
            return
        
        player_name = spell_match.group(1).strip()
        spell_name = spell_match.group(2).strip()
        
        # Detect class based on spells
        detected_class = self.detect_class(spell_name)
        if detected_class and detected_class not in self.detected_classes:
            self.detected_classes[detected_class] = player_name
            print(f"DEBUG: {detected_class} detected: {player_name}")
            self.class_detected.emit(detected_class, player_name)
    
    def detect_class(self, spell_name):
        """Detect class based on spell name"""
        # Iop spells
        iop_spells = [
            "Épée céleste", "Fulgur", "Super Iop Punch", "Jugement", "Colère de Iop", 
            "Ébranler", "Roknocerok", "Fendoir", "Ravage", "Jabs", "Rafale", 
            "Torgnole", "Tannée", "Épée de Iop", "Bond", "Focus", "Éventrail", "Uppercut"
        ]
        
        # Cra spells
        cra_spells = [
            "Flèche criblante", "Flèche fulminante", "Flèche d'immolation", 
            "Flèche enflammée", "Flèche Ardente", "Flèche explosive", 
            "Flèche cinglante", "Flèche perçante", "Flèche destructrice", 
            "Flèche chercheuse", "Flèche de recul", "Flèche tempête", 
            "Flèche harcelante", "Flèche statique", "Balise de destruction", 
            "Balise d'alignement", "Balise de contact", "Tir précis", "Débalisage", "Eclaireur",
            "Flèche lumineuse", "Pluie de flèches", "Roulade"
        ]
        
        if any(iop_spell in spell_name for iop_spell in iop_spells):
            return "Iop"
        elif any(cra_spell in spell_name for cra_spell in cra_spells):
            return "Cra"
        
        return None
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False
    
    def set_deduplication_debug(self, enabled):
        """Active le debug de déduplication"""
        if self.deduplicator:
            self.deduplicator.set_debug_mode(enabled)
    
    def get_deduplication_stats(self):
        """Retourne les stats de déduplication"""
        if self.deduplicator:
            return self.deduplicator.get_stats()
        return None
    
    def reset_deduplication_stats(self):
        """Remet à zéro les statistiques de déduplication"""
        if self.deduplicator:
            self.deduplicator.reset_stats()

class GradientBackgroundWidget(QWidget):
    """Custom widget with animated gradient background"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.gradient_phase = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_gradient)
        self.timer.start(30)  # Higher FPS for ultra-smooth animation
        
    def update_gradient(self):
        """Update gradient animation"""
        self.gradient_phase += 0.01  # Slower animation for ultra-smooth effect
        if self.gradient_phase >= 2 * 3.14159:  # Reset after full cycle
            self.gradient_phase = 0
        self.update()
        
    def paintEvent(self, event):
        """Paint animated gradient background with ultra-smooth transitions"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Create animated gradient with many color stops for ultra-smooth transitions
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        
        # Base colors with animation
        pulse = (1 + math.sin(self.gradient_phase)) / 2  # 0 to 1
        
        # Ultra-smooth gradient with many color stops
        color1 = QColor(6, 6, 5)  # Base dark color
        color2 = QColor(8 + int(pulse * 2), 8 + int(pulse * 2), 6 + int(pulse * 1))  # Very subtle transition
        color3 = QColor(10 + int(pulse * 3), 10 + int(pulse * 3), 8 + int(pulse * 2))  # Another subtle transition
        color4 = QColor(12 + int(pulse * 4), 12 + int(pulse * 4), 10 + int(pulse * 3))  # Another transition
        color5 = QColor(14 + int(pulse * 5), 14 + int(pulse * 5), 12 + int(pulse * 4))  # Another transition
        color6 = QColor(16 + int(pulse * 6), 16 + int(pulse * 6), 14 + int(pulse * 5))  # Another transition
        color7 = QColor(18 + int(pulse * 7), 18 + int(pulse * 7), 16 + int(pulse * 6))  # Another transition
        color8 = QColor(20 + int(pulse * 8), 20 + int(pulse * 8), 18 + int(pulse * 7))  # Another transition
        color9 = QColor(22 + int(pulse * 9), 22 + int(pulse * 9), 20 + int(pulse * 8))  # Another transition
        color10 = QColor(24 + int(pulse * 10), 24 + int(pulse * 10), 22 + int(pulse * 9))  # Final transition
        
        # Many color stops for ultra-smooth gradient
        gradient.setColorAt(0.0, color1)
        gradient.setColorAt(0.1, color2)
        gradient.setColorAt(0.2, color3)
        gradient.setColorAt(0.3, color4)
        gradient.setColorAt(0.4, color5)
        gradient.setColorAt(0.5, color6)
        gradient.setColorAt(0.6, color7)
        gradient.setColorAt(0.7, color8)
        gradient.setColorAt(0.8, color9)
        gradient.setColorAt(0.9, color10)
        gradient.setColorAt(1.0, color10)
        
        painter.fillRect(self.rect(), QBrush(gradient))

class DetectionOverlay(QWidget):
    """Compact overlay for character detection"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.detected_classes = {}  # {class_name: player_name}
        self.is_collapsed = False
        self.is_interacting = False  # Track if user is interacting with overlay
        
        # Window properties for overlay
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(300, 200)
        
        # Position in top-right corner - flèche collée au bord droit
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 300, 20)
        
        # Setup UI
        self.setup_ui()
        
        # Track mouse events
        self.setMouseTracking(True)
        
        # Initially hidden
        self.hide()
    
    def enterEvent(self, event):
        """Called when mouse enters overlay"""
        self.is_interacting = True
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Called when mouse leaves overlay"""
        self.is_interacting = False
        super().leaveEvent(event)
    
    def setup_ui(self):
        """Setup the overlay UI"""
        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Content container
        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setSpacing(5)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        
                # No title - removed completely
        
        # Classes container
        self.classes_container = QWidget()
        self.classes_layout = QVBoxLayout(self.classes_container)
        self.classes_layout.setSpacing(2)  # Reduced spacing between characters
        self.classes_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.addWidget(self.classes_container)
        
        # Collapse button
        self.collapse_button = QPushButton("◀")
        self.collapse_button.setFixedSize(20, 200)
        self.collapse_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 0.7);
                color: #ffffff;
                border: none;
                border-left: 1px solid rgba(255, 255, 255, 0.3);
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.9);
            }
        """)
        self.collapse_button.clicked.connect(self.toggle_collapse)
        
        # Add to main layout
        main_layout.addWidget(self.content_container)
        main_layout.addWidget(self.collapse_button)
        
        # Background styling
        self.setStyleSheet("""
            DetectionOverlay {
                background-color: rgba(20, 20, 20, 0.9);
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 12px;
            }
        """)
    
    def toggle_collapse(self):
        """Toggle overlay collapse state"""
        self.is_collapsed = not self.is_collapsed
        
        # Get screen dimensions to keep arrow at right edge
        screen = QApplication.primaryScreen().geometry()
        
        if self.is_collapsed:
            # Collapse: hide content, show only button
            self.content_container.hide()
            self.collapse_button.setText("▶")
            self.collapse_button.setFixedSize(20, 150)  # Reduced height
            self.setFixedSize(20, 150)  # Reduced height
            # Keep arrow at right edge of screen
            self.move(screen.width() - 20, 20)
        else:
            # Expand: show content, change button
            self.content_container.show()
            self.collapse_button.setText("◀")
            self.collapse_button.setFixedSize(20, 150)  # Reduced height
            self.setFixedSize(250, 150)  # Reduced width and height
            # Move back to original position
            self.move(screen.width() - 250, 20)
    
    def add_detected_class(self, class_name, player_name):
        """Add a detected class to the overlay"""
        button_key = f"{class_name}_{player_name}"
        
        if button_key not in self.detected_classes:
            self.detected_classes[button_key] = (class_name, player_name)
            
            # Create horizontal layout for icon + name + delete button
            container = QWidget()
            container_layout = QHBoxLayout(container)
            container_layout.setSpacing(3)  # Reduced spacing
            container_layout.setContentsMargins(2, 2, 2, 2)  # Minimal margins
            
            # Load class icon
            if getattr(sys, 'frozen', False):
                base_dir = Path(sys._MEIPASS)
            else:
                base_dir = Path(__file__).parent
            icon_path = base_dir / "img" / "breedsicons"
            
            if class_name == "Iop":
                icon_file = icon_path / "iopicon.png"
            elif class_name == "Cra":
                icon_file = icon_path / "craicon.png"
            else:
                icon_file = None
            
            # Create icon label - taille réduite
            icon_label = QLabel()
            if icon_file and icon_file.exists():
                from PyQt6.QtGui import QPixmap
                pixmap = QPixmap(str(icon_file))
                scaled_pixmap = pixmap.scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                icon_label.setPixmap(scaled_pixmap)
            else:
                # Fallback icon based on class
                if class_name == "Iop":
                    icon_label.setText("⚔")
                elif class_name == "Cra":
                    icon_label.setText("🏹")
                icon_label.setStyleSheet("font-size: 16px; color: #ffffff;")
            
            # Create name label - responsive container sans background noir
            name_label = QLabel(player_name)
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Style responsive basé sur la classe - ÉTAT INACTIF par défaut, taille réduite
            if class_name == "Iop":
                name_label.setStyleSheet("""
                    QLabel {
                        font-size: 11px;
                        color: #ffffff;
                        font-weight: bold;
                        font-family: 'Segoe UI', Arial, sans-serif;
                        padding: 3px 8px;
                        background-color: rgba(255, 107, 53, 0.4);
                        border-radius: 6px;
                        border: 1px solid rgba(255, 107, 53, 0.6);
                    }
                """)
            elif class_name == "Cra":
                name_label.setStyleSheet("""
                    QLabel {
                        font-size: 11px;
                        color: #ffffff;
                        font-weight: bold;
                        font-family: 'Segoe UI', Arial, sans-serif;
                        padding: 3px 8px;
                        background-color: rgba(74, 158, 255, 0.4);
                        border-radius: 6px;
                        border: 1px solid rgba(74, 158, 255, 0.6);
                    }
                """)
            
            # Add to container - pseudo plus près de la flèche
            container_layout.addStretch()  # Push content to the right
            container_layout.addWidget(icon_label)
            container_layout.addWidget(name_label)
            
            # Create delete button
            delete_button = QPushButton("×")
            delete_button.setFixedSize(16, 16)
            delete_button.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 0, 0, 0.3);
                    border: 1px solid rgba(255, 0, 0, 0.6);
                    border-radius: 8px;
                    color: #ffffff;
                    font-weight: bold;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 0, 0, 0.6);
                    border: 1px solid rgba(255, 0, 0, 1.0);
                }
                QPushButton:pressed {
                    background-color: rgba(255, 0, 0, 0.8);
                }
            """)
            
            # Connect delete button
            delete_button.clicked.connect(lambda: self.remove_detected_class(class_name, player_name))
            
            container_layout.addWidget(delete_button)
            
            # Create clickable button with custom layout - taille réduite
            button = QPushButton()
            button.setMinimumSize(200, 25)  # Reduced size
            
            # Set the container as the button's content
            button_layout = QHBoxLayout(button)
            button_layout.setContentsMargins(0, 0, 0, 0)
            button_layout.addWidget(container)
            
            # Style based on class - plus transparent pour laisser voir le container coloré
            if class_name == "Iop":
                button.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        border: none;
                        padding: 0px;
                    }
                    QPushButton:hover {
                        background-color: rgba(255, 107, 53, 0.1);
                    }
                    QPushButton:pressed {
                        background-color: rgba(255, 107, 53, 0.2);
                    }
                """)
            elif class_name == "Cra":
                button.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        border: none;
                        padding: 0px;
                    }
                    QPushButton:hover {
                        background-color: rgba(74, 158, 255, 0.1);
                    }
                    QPushButton:pressed {
                        background-color: rgba(74, 158, 255, 0.2);
                    }
                """)
            
            # Connect click to main window's class button
            button.clicked.connect(lambda checked, cn=class_name, pn=player_name: self.launch_tracker(cn, pn))
            
            # Store reference to button and name_label for state updates
            button.name_label = name_label
            button.class_name = class_name
            button.player_name = player_name
            
            self.classes_layout.addWidget(button)
            
            # Show overlay if hidden
            if not self.isVisible():
                self.show()
    
    def launch_tracker(self, class_name, player_name):
        """Launch tracker for the detected class"""
        # Find the corresponding button in main window and trigger it
        button_key = f"{class_name}_{player_name}"
        if button_key in self.main_window.class_buttons:
            self.main_window.class_buttons[button_key].toggle_tracker()
            # Update visual state in overlay
            self.update_button_state(class_name, player_name)
    
    def update_button_state(self, class_name, player_name):
        """Update visual state of overlay button based on tracker status"""
        try:
            button_key = f"{class_name}_{player_name}"
            if button_key in self.main_window.class_buttons:
                is_active = self.main_window.class_buttons[button_key].is_active
                
                # Find the overlay button
                for i in range(self.classes_layout.count()):
                    widget = self.classes_layout.itemAt(i).widget()
                    if hasattr(widget, 'class_name') and hasattr(widget, 'player_name'):
                        if widget.class_name == class_name and widget.player_name == player_name:
                            # Update name_label style based on active state
                            if is_active:
                                # Active state - more opaque and brighter
                                if class_name == "Iop":
                                    widget.name_label.setStyleSheet("""
                                        QLabel {
                                            font-size: 11px;
                                            color: #ffffff;
                                            font-weight: bold;
                                            font-family: 'Segoe UI', Arial, sans-serif;
                                            padding: 3px 8px;
                                            background-color: rgba(255, 107, 53, 1.0);
                                            border-radius: 6px;
                                            border: 2px solid rgba(255, 107, 53, 1.0);
                                        }
                                    """)
                                elif class_name == "Cra":
                                    widget.name_label.setStyleSheet("""
                                        QLabel {
                                            font-size: 11px;
                                            color: #ffffff;
                                            font-weight: bold;
                                            font-family: 'Segoe UI', Arial, sans-serif;
                                            padding: 3px 8px;
                                            background-color: rgba(74, 158, 255, 1.0);
                                            border-radius: 6px;
                                            border: 2px solid rgba(74, 158, 255, 1.0);
                                        }
                                    """)
                            else:
                                # Inactive state - more transparent
                                if class_name == "Iop":
                                    widget.name_label.setStyleSheet("""
                                        QLabel {
                                            font-size: 11px;
                                            color: #ffffff;
                                            font-weight: bold;
                                            font-family: 'Segoe UI', Arial, sans-serif;
                                            padding: 3px 8px;
                                            background-color: rgba(255, 107, 53, 0.4);
                                            border-radius: 6px;
                                            border: 1px solid rgba(255, 107, 53, 0.6);
                                        }
                                    """)
                                elif class_name == "Cra":
                                    widget.name_label.setStyleSheet("""
                                        QLabel {
                                            font-size: 11px;
                                            color: #ffffff;
                                            font-weight: bold;
                                            font-family: 'Segoe UI', Arial, sans-serif;
                                            padding: 3px 8px;
                                            background-color: rgba(74, 158, 255, 0.4);
                                            border-radius: 6px;
                                            border: 1px solid rgba(74, 158, 255, 0.6);
                                        }
                                    """)
                            break
        except Exception as e:
            print(f"DEBUG: Error updating button state: {e}")
    
    def remove_detected_class(self, class_name, player_name):
        """Remove a detected class from the overlay"""
        button_key = f"{class_name}_{player_name}"
        
        if button_key in self.detected_classes:
            # Find and remove the button from layout
            for i in range(self.classes_layout.count()):
                item = self.classes_layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    if hasattr(widget, 'class_name') and hasattr(widget, 'player_name'):
                        if widget.class_name == class_name and widget.player_name == player_name:
                            self.classes_layout.removeWidget(widget)
                            widget.deleteLater()
                            break
            
            # Remove from detected classes
            del self.detected_classes[button_key]
            
            # Hide overlay if no more classes
            if not self.detected_classes:
                self.hide()
            
            print(f"DEBUG: Personnage {player_name} ({class_name}) supprimé de l'overlay")
    
    def clear_classes(self):
        """Clear all detected classes"""
        while self.classes_layout.count():
            child = self.classes_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.detected_classes.clear()
        self.hide()

class ClassButton(QPushButton):
    """Custom button for class selection"""
    
    def __init__(self, class_name, player_name, parent=None, from_saved=False, main_window=None):
        super().__init__(parent)
        self.class_name = class_name
        self.player_name = player_name
        self.tracker_process = None
        self.is_active = False
        self.from_saved = from_saved  # Track if this button was loaded from saved data
        self.main_window = main_window  # Reference to main window for save_character method
        
        # Setup button
        self.setup_button()
        
    def setup_button(self):
        """Setup the button appearance and text"""
        self.setMinimumSize(150, 30)  # Ultra-compact size
        
        # Load class icon
        # Get the directory where the script is located (works for both script and executable)
        if getattr(sys, 'frozen', False):
            # Running as executable - look in the bundled img folder
            base_dir = Path(sys._MEIPASS)
        else:
            # Running as script
            base_dir = Path(__file__).parent
        icon_path = base_dir / "img" / "breedsicons"
        if self.class_name == "Iop":
            icon_file = icon_path / "iopicon.png"
        elif self.class_name == "Cra":
            icon_file = icon_path / "craicon.png"
        else:
            icon_file = None
        
        # Set text - just player name, status icon will be updated separately
        self.setText(self.player_name)
        
        # Set icon if available
        if icon_file and icon_file.exists():
            from PyQt6.QtGui import QIcon
            from PyQt6.QtCore import QSize
            icon = QIcon(str(icon_file))
            self.setIcon(icon)
            # Set smaller icon size
            self.setIconSize(QSize(16, 16))  # Ultra-compact icon size
        
        # Dark theme styling with smaller buttons
        if self.class_name == "Iop":
            self.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 107, 53, 0.15);
                    color: #ff6b35;
                    font-size: 11px;
                    font-weight: 500;
                    border: 1px solid rgba(255, 107, 53, 0.4);
                    border-radius: 6px;
                    padding: 4px 8px;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: rgba(255, 107, 53, 0.25);
                    border: 1px solid rgba(255, 107, 53, 0.6);
                }
                QPushButton:pressed {
                    background-color: rgba(255, 107, 53, 0.35);
                }
            """)
        elif self.class_name == "Cra":
            self.setStyleSheet("""
                QPushButton {
                    background-color: rgba(74, 158, 255, 0.15);
                    color: #4a9eff;
                    font-size: 11px;
                    font-weight: 500;
                    border: 1px solid rgba(74, 158, 255, 0.4);
                    border-radius: 6px;
                    padding: 4px 8px;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: rgba(74, 158, 255, 0.25);
                    border: 1px solid rgba(74, 158, 255, 0.6);
                }
                QPushButton:pressed {
                    background-color: rgba(74, 158, 255, 0.35);
                }
            """)
        
        # Connect click event
        self.clicked.connect(self.toggle_tracker)
        
        # Enable context menu for deleting characters
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        # Add tooltip to indicate right-click functionality
        self.setToolTip(f"Clic gauche: Démarrer/Arrêter le tracker\nClic droit: Supprimer {self.player_name} ({self.class_name})")
    
    def toggle_tracker(self):
        """Toggle tracker on/off"""
        if self.is_active:
            self.stop_tracker()
        else:
            self.start_tracker()
    
    def start_tracker(self):
        """Start the appropriate tracker"""
        try:
            # Check if we're running as an executable (frozen)
            if getattr(sys, 'frozen', False):
                # Running as executable - launch the same executable with different arguments
                if self.class_name == "Iop":
                    # Launch Waksense.exe with --iop argument
                    self.tracker_process = subprocess.Popen([sys.executable, "--iop"])
                elif self.class_name == "Cra":
                    # Launch Waksense.exe with --cra argument
                    self.tracker_process = subprocess.Popen([sys.executable, "--cra"])
                else:
                    return
            else:
                # Running as Python script - look for Python files
                if self.class_name == "Iop":
                    script_path = Path("Iop/wakfu_iop_resource_tracker.py")
                elif self.class_name == "Cra":
                    script_path = Path("Cra/wakfu_resource_tracker_fullscreen.py")
                else:
                    return
                
                if script_path.exists():
                    self.tracker_process = subprocess.Popen([sys.executable, str(script_path)])
                else:
                    QMessageBox.warning(self, "Erreur", f"Script de tracker non trouvé: {script_path}")
                    return
            
            self.is_active = True
            self.update_button_text()
            
            # Save this character to the saved characters file
            if self.main_window:
                self.main_window.save_character(self.class_name, self.player_name)
            
            # Update overlay state
            if hasattr(self.main_window, 'detection_overlay'):
                self.main_window.detection_overlay.update_button_state(self.class_name, self.player_name)
            
            print(f"DEBUG: Tracker {self.class_name} démarré pour {self.player_name}")
                
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Échec du démarrage du tracker: {e}")
    
    def stop_tracker(self):
        """Stop the tracker"""
        try:
            if self.tracker_process:
                self.tracker_process.terminate()
                self.tracker_process.wait(timeout=5)
                self.tracker_process = None
                self.is_active = False
                self.update_button_text()
                
                # Update overlay state
                if hasattr(self.main_window, 'detection_overlay'):
                    self.main_window.detection_overlay.update_button_state(self.class_name, self.player_name)
                
                print(f"DEBUG: Tracker {self.class_name} arrêté pour {self.player_name}")
        except Exception as e:
            print(f"DEBUG: Erreur lors de l'arrêt du tracker: {e}")
    
    def update_button_text(self):
        """Update button text based on active state"""
        # Just show player name, status will be indicated by button styling
        self.setText(self.player_name)
        
        # Update button styling based on active state
        if self.class_name == "Iop":
            if self.is_active:
                self.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(255, 107, 53, 0.3);
                        color: #ff6b35;
                        font-size: 11px;
                        font-weight: 600;
                        border: 2px solid rgba(255, 107, 53, 0.8);
                        border-radius: 6px;
                        padding: 4px 8px;
                        text-align: left;
                    }
                    QPushButton:hover {
                        background-color: rgba(255, 107, 53, 0.4);
                        border: 2px solid rgba(255, 107, 53, 1.0);
                    }
                    QPushButton:pressed {
                        background-color: rgba(255, 107, 53, 0.5);
                    }
                """)
            else:
                self.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(255, 107, 53, 0.15);
                        color: #ff6b35;
                        font-size: 11px;
                        font-weight: 500;
                        border: 1px solid rgba(255, 107, 53, 0.4);
                        border-radius: 6px;
                        padding: 4px 8px;
                        text-align: left;
                    }
                    QPushButton:hover {
                        background-color: rgba(255, 107, 53, 0.25);
                        border: 1px solid rgba(255, 107, 53, 0.6);
                    }
                    QPushButton:pressed {
                        background-color: rgba(255, 107, 53, 0.35);
                    }
                """)
        elif self.class_name == "Cra":
            if self.is_active:
                self.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(74, 158, 255, 0.3);
                        color: #4a9eff;
                        font-size: 11px;
                        font-weight: 600;
                        border: 2px solid rgba(74, 158, 255, 0.8);
                        border-radius: 6px;
                        padding: 4px 8px;
                        text-align: left;
                    }
                    QPushButton:hover {
                        background-color: rgba(74, 158, 255, 0.4);
                        border: 2px solid rgba(74, 158, 255, 1.0);
                    }
                    QPushButton:pressed {
                        background-color: rgba(74, 158, 255, 0.5);
                    }
                """)
            else:
                self.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(74, 158, 255, 0.15);
                        color: #4a9eff;
                        font-size: 11px;
                        font-weight: 500;
                        border: 1px solid rgba(74, 158, 255, 0.4);
                        border-radius: 6px;
                        padding: 4px 8px;
                        text-align: left;
                    }
                    QPushButton:hover {
                        background-color: rgba(74, 158, 255, 0.25);
                        border: 1px solid rgba(74, 158, 255, 0.6);
                    }
                    QPushButton:pressed {
                        background-color: rgba(74, 158, 255, 0.35);
                    }
                """)
    
    def show_context_menu(self, position):
        """Show context menu for character deletion"""
        menu = QMenu(self)
        
        # Delete character action
        delete_action = QAction("🗑️ Supprimer le personnage", self)
        delete_action.triggered.connect(self.delete_character)
        menu.addAction(delete_action)
        
        # Show menu at cursor position
        menu.exec(self.mapToGlobal(position))
    
    def delete_character(self):
        """Delete this character from the saved list"""
        try:
            # Show confirmation dialog
            reply = QMessageBox.question(
                self, 
                "Supprimer le personnage", 
                f"Êtes-vous sûr de vouloir supprimer {self.player_name} ({self.class_name}) ?\n\nCela les retirera de votre liste de personnages sauvegardés.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
                
            if self.main_window:
                # Remove from saved characters
                if (self.class_name in self.main_window.saved_characters and 
                    self.player_name in self.main_window.saved_characters[self.class_name]):
                    self.main_window.saved_characters[self.class_name].remove(self.player_name)
                    
                    # If no more characters of this class, remove the class entry
                    if not self.main_window.saved_characters[self.class_name]:
                        del self.main_window.saved_characters[self.class_name]
                    
                    # Save updated list to internal storage
                    self.main_window.settings['saved_characters'] = self.main_window.saved_characters
                    
                    # Remove button from UI
                    button_key = f"{self.class_name}_{self.player_name}"
                    if button_key in self.main_window.class_buttons:
                        del self.main_window.class_buttons[button_key]
                    
                    # Remove button from layout
                    self.setParent(None)
                    self.deleteLater()
                    
                    print(f"DEBUG: Personnage supprimé {self.player_name} ({self.class_name})")
                    
                    # Update status
                    total_saved = len([name for names in self.main_window.saved_characters.values() for name in names])
                    if total_saved > 0:
                        self.main_window.status_label.setText(f"{total_saved} personnages sauvegardés restants")
                    else:
                        self.main_window.status_label.setText("Aucun personnage sauvegardé - surveillance des nouvelles classes...")
                        
        except Exception as e:
            print(f"DEBUG: Erreur lors de la suppression du personnage: {e}")
            QMessageBox.warning(self, "Erreur", f"Échec de la suppression du personnage: {e}")

class WakfuClassLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Window properties
        self.setWindowTitle("Waksense")
        self.setMinimumSize(400, 300)  # Ultra-compact minimum size
        self.resize(450, 350)  # Ultra-compact initial size
        
        # Set window background - will be handled by gradient widget
        self.setStyleSheet("""
            QMainWindow {
                color: #ffffff;
            }
        """)
        
        # Set window icon
        # Get the directory where the script is located (works for both script and executable)
        if getattr(sys, 'frozen', False):
            # Running as executable - look in the bundled files
            base_dir = Path(sys._MEIPASS)
        else:
            # Running as script
            base_dir = Path(__file__).parent
        icon_path = base_dir / "Waksense.ico"
        if icon_path.exists():
            from PyQt6.QtGui import QIcon
            self.setWindowIcon(QIcon(str(icon_path)))
            print(f"DEBUG: Icône de fenêtre définie sur {icon_path}")
        else:
            print(f"DEBUG: Fichier d'icône non trouvé: {icon_path}")
        
        # Internal storage (no external files)
        self.settings = {}  # Store settings internally
        self.saved_characters = {}  # {class_name: [player_names]}
        
        # Setup persistent app settings
        self.setup_app_settings()
        
        # Load settings and set log file path
        self.load_settings()
        
        # Class buttons storage
        self.class_buttons = {}
        
        # Create detection overlay
        self.detection_overlay = DetectionOverlay(self)
        
        # Setup UI
        self.setup_ui()
        
        # Load saved characters first
        self.load_saved_characters()
        
        # Start monitoring
        self.start_monitoring()
        
        # Setup window focus detection timer
        self.setup_focus_detection()
    
    def setup_ui(self):
        """Setup the user interface"""
        # Create gradient background widget
        gradient_widget = GradientBackgroundWidget()
        self.setCentralWidget(gradient_widget)
        
        # Main layout - ultra minimaliste
        layout = QVBoxLayout(gradient_widget)
        layout.setSpacing(8)  # Ultra-compact spacing
        layout.setContentsMargins(10, 10, 10, 10)  # Ultra-compact margins
        
        # Waksense icon instead of text
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Get the directory where the script is located (works for both script and executable)
        if getattr(sys, 'frozen', False):
            # Running as executable - look in the bundled files
            base_dir = Path(sys._MEIPASS)
        else:
            # Running as script
            base_dir = Path(__file__).parent
        icon_path = base_dir / "Waksense.ico"
        if icon_path.exists():
            from PyQt6.QtGui import QIcon, QPixmap
            pixmap = QPixmap(str(icon_path))
            # Scale the icon to ultra-small size for minimal design
            scaled_pixmap = pixmap.scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            icon_label.setPixmap(scaled_pixmap)
            icon_label.setStyleSheet("""
                QLabel {
                    margin-bottom: 5px;
                    background-color: transparent;
                }
            """)
        else:
            # Fallback to text if icon not found
            icon_label.setText("Waksense")
            icon_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                    font-weight: 300;
                    color: #ffffff;
                margin-bottom: 5px;
                    background-color: transparent;
                }
            """)
        layout.addWidget(icon_label)
        
        # Wakfu path configuration section (initially hidden)
        self.path_config_container = QWidget()
        self.path_config_layout = QVBoxLayout(self.path_config_container)
        self.path_config_layout.setSpacing(5)  # Ultra-compact spacing
        
        # Path label
        self.path_label = QLabel("Indiquez le chemin vers le dossier des logs Wakfu")
        self.path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.path_label.setWordWrap(True)  # Enable word wrapping
        self.path_label.setMinimumHeight(20)  # Ultra-compact height
        self.path_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #ffffff;
                font-weight: 500;
                margin: 10px 0px;
                padding: 5px 10px;
                background-color: transparent;
            }
        """)
        self.path_config_layout.addWidget(self.path_label)
        
        # Path input field removed - user will select path through file dialog only
        
        # Button layout for Auto-Scan and Manual
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)  # Ultra-compact spacing
        
        # Auto-Scan button
        self.auto_scan_button = QPushButton("🔍 Scan Automatique")
        self.auto_scan_button.setMinimumSize(100, 30)  # Ultra-compact size
        self.auto_scan_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 107, 53, 0.3);
                color: #ff6b35;
                border: 1px solid rgba(255, 107, 53, 0.6);
                border-radius: 6px;
                font-size: 12px;
                font-weight: 500;
                padding: 8px 16px;
                margin: 5px 0px;
            }
            QPushButton:hover {
                background-color: rgba(255, 107, 53, 0.4);
                border: 1px solid rgba(255, 107, 53, 0.8);
            }
            QPushButton:pressed {
                background-color: rgba(255, 107, 53, 0.5);
            }
        """)
        self.auto_scan_button.clicked.connect(self.auto_scan_wakfu)
        button_layout.addWidget(self.auto_scan_button)
        
        # Manual button
        self.manual_button = QPushButton("📁 Manuel")
        self.manual_button.setMinimumSize(100, 30)  # Ultra-compact size
        self.manual_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(74, 158, 255, 0.3);
                color: #4a9eff;
                border: 1px solid rgba(74, 158, 255, 0.6);
                border-radius: 6px;
                font-size: 12px;
                font-weight: 500;
                padding: 8px 16px;
                margin: 5px 0px;
            }
            QPushButton:hover {
                background-color: rgba(74, 158, 255, 0.4);
                border: 1px solid rgba(74, 158, 255, 0.8);
            }
            QPushButton:pressed {
                background-color: rgba(74, 158, 255, 0.5);
            }
        """)
        self.manual_button.clicked.connect(self.manual_browse_wakfu)
        button_layout.addWidget(self.manual_button)
        
        self.path_config_layout.addLayout(button_layout)
        
        # Add path config container to main layout
        layout.addWidget(self.path_config_container)
        
        # Status label with modern styling
        self.status_label = QLabel("Chargement des personnages sauvegardés...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)  # Enable word wrapping
        self.status_label.setMinimumHeight(20)  # Ultra-compact height
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #cccccc;
                margin: 5px 0px;
                padding: 6px 10px;
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 6px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
        layout.addWidget(self.status_label)
        
        # Check if log path is already saved and start auto-scan
        self.check_saved_log_path()
        
        # Create horizontal layout for columns
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(15)  # Space between IOP and CRA columns
        
        # Iop scrollable area
        iop_scroll = QScrollArea()
        iop_scroll.setWidgetResizable(True)
        iop_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        iop_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        iop_scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background-color: rgba(255, 255, 255, 0.1);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(255, 255, 255, 0.3);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: rgba(255, 255, 255, 0.5);
            }
        """)
        
        # Iop buttons container (no background)
        self.iop_buttons_container = QWidget()
        self.iop_buttons_container.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
        """)
        self.iop_buttons_layout = QVBoxLayout(self.iop_buttons_container)
        self.iop_buttons_layout.setSpacing(3)  # Small spacing between buttons
        self.iop_buttons_layout.setContentsMargins(5, 5, 5, 5)  # Small margins
        
        iop_scroll.setWidget(self.iop_buttons_container)
        iop_scroll.setMinimumSize(180, 150)  # Responsive minimum size
        iop_scroll.setMaximumWidth(220)  # Maximum width constraint
        columns_layout.addWidget(iop_scroll)
        
        # Cra scrollable area
        cra_scroll = QScrollArea()
        cra_scroll.setWidgetResizable(True)
        cra_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        cra_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        cra_scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background-color: rgba(255, 255, 255, 0.1);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(255, 255, 255, 0.3);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: rgba(255, 255, 255, 0.5);
            }
        """)
        
        # Cra buttons container (no background)
        self.cra_buttons_container = QWidget()
        self.cra_buttons_container.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
        """)
        self.cra_buttons_layout = QVBoxLayout(self.cra_buttons_container)
        self.cra_buttons_layout.setSpacing(3)  # Small spacing between buttons
        self.cra_buttons_layout.setContentsMargins(5, 5, 5, 5)  # Small margins
        
        cra_scroll.setWidget(self.cra_buttons_container)
        cra_scroll.setMinimumSize(180, 150)  # Responsive minimum size
        cra_scroll.setMaximumWidth(220)  # Maximum width constraint
        columns_layout.addWidget(cra_scroll)
        
        layout.addLayout(columns_layout)
        
        # Add stretch to push everything to top
        layout.addStretch()
        
        # Instructions with modern styling
        instructions = QLabel("Clic gauche: Démarrer/Arrêter le tracker | Clic droit: Supprimer le personnage")
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instructions.setWordWrap(True)  # Enable word wrapping
        instructions.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #aaaaaa;
                font-style: italic;
                margin: 15px 0px 10px 0px;
                padding: 8px;
                background-color: transparent;
            }
        """)
        layout.addWidget(instructions)
        
        # Load current path into input field
        self.load_current_path()
        
        # Initialize loading system
        self.setup_loading_system()
        
        # Check if we need to show path configuration
        self.check_path_configuration()
    
    def load_current_path(self):
        """Load current Wakfu path - no longer needed since input field is removed"""
        pass
    
    def setup_loading_system(self):
        """Setup the loading progress bar system"""
        # Create progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 8px;
                text-align: center;
                background-color: rgba(255, 255, 255, 0.1);
                color: #ffffff;
                font-size: 12px;
                font-weight: 500;
                height: 25px;
                margin: 10px 0px;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4a9eff, stop:1 #ff6b35);
                border-radius: 6px;
            }
        """)
        
        # Initially hide the progress bar
        self.progress_bar.hide()
        
        # Add progress bar to the main layout (after status label)
        central_widget = self.centralWidget()
        if central_widget:
            layout = central_widget.layout()
            if layout:
                # Insert after status label (index 2: icon, path_config, status_label)
                layout.insertWidget(3, self.progress_bar)
        
        # Create loading timer for sequence
        self.loading_timer = QTimer()
        self.loading_timer.timeout.connect(self.update_loading_sequence)
        self.loading_step = 0
        self.loading_messages = [
            "Localisation du fichier de chat...",
            "Fichier de chat localisé", 
            "Surveillance des classes, veuillez commencer un combat et lancer un sort avec les classes ciblées"
        ]
        
        # Smooth progress animation
        self.current_progress = 0
        self.target_progress = 0
        self.progress_speed = 2  # Progress per frame for smooth animation
        
        # Loading state tracking
        self.loading_active = False
        self.classes_found = False
    
    def start_loading_sequence(self):
        """Start the loading sequence with progress bar"""
        # Ensure loading system is initialized
        if not hasattr(self, 'progress_bar'):
            self.setup_loading_system()
        
        # Reset loading state
        self.loading_active = True
        self.loading_step = 0
        self.current_progress = 0
        self.target_progress = 0
        self.classes_found = False
        
        # Show progress bar
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        
        # Start timer with faster updates for smooth animation
        self.loading_timer.start(50)  # Update every 50ms for smooth animation
        
        # Show first message immediately
        self.update_loading_sequence()
    
    def update_loading_sequence(self):
        """Update the loading sequence message and progress with smooth animation"""
        if not self.loading_active:
            return
        
        # Smooth progress animation
        if self.current_progress < self.target_progress:
            self.current_progress = min(self.current_progress + self.progress_speed, self.target_progress)
            self.progress_bar.setValue(int(self.current_progress))
            
        if self.loading_step < len(self.loading_messages):
            message = self.loading_messages[self.loading_step]
            self.status_label.setText(message)
            
            # Set target progress for smooth animation
            if self.loading_step == 0:
                self.target_progress = 30
            elif self.loading_step == 1:
                self.target_progress = 70
            elif self.loading_step == 2:
                self.target_progress = 100
            
            self.progress_bar.setFormat(f"{int(self.current_progress)}% - {message}")
            
            # Move to next step after a delay
            if self.current_progress >= self.target_progress:
                self.loading_step += 1
        else:
            # After all messages, keep showing the last message until classes are found
            if not self.classes_found:
                # Keep cycling the last message to show it's still monitoring
                self.status_label.setText("Surveillance des classes, veuillez commencer un combat et lancer un sort avec les classes ciblées")
                if self.current_progress < 100:
                    self.current_progress = min(self.current_progress + self.progress_speed, 100)
                    self.progress_bar.setValue(int(self.current_progress))
                self.progress_bar.setFormat("100% - Surveillance des classes...")
                # Stop the timer since we're now in monitoring mode
                self.loading_timer.stop()
            else:
                # Classes found, stop loading
                self.stop_loading_sequence()
    
    def stop_loading_sequence(self):
        """Stop the loading sequence and hide progress bar"""
        self.loading_active = False
        self.loading_timer.stop()
        self.progress_bar.hide()
        
        # Set final status message
        self.status_label.setText("Logs Wakfu configurés - surveillance des personnages...")
        
        # Show overlay but keep main window visible for user interaction
        self.detection_overlay.show()
    
    def check_path_configuration(self):
        """Check if path is configured and show/hide path configuration accordingly"""
        try:
            has_valid_path = False
            
            # Check internal settings
            wakfu_path = self.settings.get('wakfu_path', '')
            if wakfu_path and wakfu_path.strip():
                # Check if the path actually exists and is valid
                path_obj = Path(wakfu_path)
                if path_obj.exists():
                    has_valid_path = True
            
            if has_valid_path:
                # Hide path configuration, show main app
                self.path_config_container.hide()
                self.status_label.show()
                self.status_label.setText("Logs Wakfu configurés - surveillance des personnages...")
            else:
                # Show path configuration, hide main app
                self.path_config_container.show()
                self.status_label.hide()
                # Hide character containers
                if hasattr(self, 'iop_buttons_container'):
                    self.iop_buttons_container.hide()
                if hasattr(self, 'cra_buttons_container'):
                    self.cra_buttons_container.hide()
                
        except Exception as e:
            print(f"DEBUG: Error checking path configuration: {e}")
            # On error, show path configuration
            self.path_config_container.show()
    
    def auto_scan_wakfu(self):
        """Automatically scan for Wakfu chat logs folder"""
        try:
            # Get user's AppData folder
            user_profile = Path.home()
            
            # Look for chat logs in the standard location
            logs_path = user_profile / "AppData" / "Roaming" / "zaap" / "gamesLogs" / "wakfu" / "logs"
            
            if logs_path.exists():
                # Validate the found path
                if self.validate_wakfu_path(str(logs_path)):
                    self.save_wakfu_path(str(logs_path))
                    self.start_loading_sequence()
                    return
                else:
                    self.status_label.setText("Dossier logs trouvé mais fichier chat manquant - utilisez 'Manually'")
                    QMessageBox.warning(
                        self, 
                        "Fichier Chat Manquant", 
                        f"Dossier logs trouvé à: {logs_path}\n\n"
                        f"Mais le fichier 'wakfu_chat.log' n'a pas été trouvé.\n\n"
                        f"Veuillez utiliser 'Manually' pour sélectionner le bon dossier."
                    )
                    return
            
            # If not found in standard location, try alternative locations
            alternative_paths = [
                user_profile / "AppData" / "Local" / "zaap" / "gamesLogs" / "wakfu" / "logs",
                Path("C:/Users/Shadow/AppData/Roaming/zaap/gamesLogs/wakfu/logs"),  # Hardcoded fallback
            ]
            
            found_path = None
            for path in alternative_paths:
                if path.exists():
                    found_path = path
                    break
            
            if found_path:
                # Validate the found path
                if self.validate_wakfu_path(str(found_path)):
                    self.save_wakfu_path(str(found_path))
                    self.start_loading_sequence()
                else:
                    self.status_label.setText("Dossier logs trouvé mais fichier chat manquant - utilisez 'Manually'")
                    QMessageBox.warning(
                        self, 
                        "Fichier Chat Manquant", 
                        f"Dossier logs trouvé à: {found_path}\n\n"
                        f"Mais le fichier 'wakfu_chat.log' n'a pas été trouvé.\n\n"
                        f"Veuillez utiliser 'Manually' pour sélectionner le bon dossier."
                    )
            else:
                self.status_label.setText("Logs Wakfu non trouvés automatiquement - utilisez 'Manually'")
                QMessageBox.warning(
                    self, 
                    "Scan Échoué", 
                    "Impossible de trouver automatiquement le dossier des logs Wakfu.\n\n"
                    "Chemin recherché: AppData\\Roaming\\zaap\\gamesLogs\\wakfu\\logs\n\n"
                    "Veuillez utiliser 'Manually' pour sélectionner le dossier."
                )
                
        except Exception as e:
            self.status_label.setText("Erreur lors du scan automatique")
            QMessageBox.critical(
                self, 
                "Erreur de Scan", 
                f"Erreur lors du scan: {e}\n\nVeuillez utiliser 'Manually' pour sélectionner le dossier."
            )
    
    def manual_browse_wakfu(self):
        """Open folder browser dialog for manual selection of logs directory"""
        try:
            folder_path = QFileDialog.getExistingDirectory(
                self, 
                "Sélectionner le dossier des logs Wakfu",
                str(Path.home()),  # Start from user's home directory
                QFileDialog.Option.ShowDirsOnly
            )
            
            if folder_path:
                # Validate the selected path by checking for chat log
                if self.validate_wakfu_path(folder_path):
                    self.save_wakfu_path(folder_path)
                    self.start_loading_sequence()
                else:
                    # Show error message for invalid path
                    QMessageBox.warning(
                        self, 
                        "Chemin Invalide", 
                        f"Le chemin sélectionné ne contient pas le fichier 'wakfu_chat.log'.\n\n"
                        f"Chemin sélectionné: {folder_path}\n\n"
                        f"Veuillez sélectionner le dossier contenant les logs Wakfu et réessayer.\n\n"
                        f"Le dossier doit contenir le fichier 'wakfu_chat.log'."
                    )
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la sélection: {e}")
    
    def validate_wakfu_path(self, logs_path):
        """Validate if the selected path contains Wakfu chat logs"""
        try:
            path_obj = Path(logs_path)
            
            # Check if the path exists
            if not path_obj.exists():
                print(f"DEBUG: Le chemin n'existe pas: {logs_path}")
                return False
            
            # Check for chat log file
            chat_log_file = path_obj / "wakfu_chat.log"
            if not chat_log_file.exists():
                print(f"DEBUG: Fichier de chat non trouvé à: {chat_log_file}")
                return False
            
            print(f"DEBUG: Chemin de logs valide trouvé: {logs_path}")
            return True
            
        except Exception as e:
            print(f"DEBUG: Erreur lors de la validation du chemin: {e}")
            return False
    
    def save_wakfu_path(self, wakfu_path):
        """Save Wakfu path to internal storage and restart monitoring"""
        try:
            # Save to internal settings
            self.settings['wakfu_path'] = wakfu_path
            
            # Also save to app_settings for persistence
            self.app_settings['log_path'] = wakfu_path
            self.save_app_settings()  # Save to file immediately
            
            # Update log file path
            self.log_file = self.get_log_file_path(wakfu_path)
            
            # Restart monitoring with new path
            self.restart_monitoring()
            
            # Switch to main app interface
            self.switch_to_main_app()
            
            print(f"DEBUG: Chemin Wakfu sauvegardé en interne: {wakfu_path}")
        except Exception as e:
            print(f"DEBUG: Erreur lors de la sauvegarde du chemin: {e}")
            QMessageBox.warning(self, "Erreur", "Impossible de sauvegarder le chemin")
    
    def switch_to_main_app(self):
        """Switch from path configuration to main app interface"""
        # Hide path configuration
        self.path_config_container.hide()
        
        # Show main app elements
        self.status_label.show()
        self.status_label.setText("Logs Wakfu configurés - surveillance des personnages...")
        
        # Show character containers
        if hasattr(self, 'iop_buttons_container'):
            self.iop_buttons_container.show()
        if hasattr(self, 'cra_buttons_container'):
            self.cra_buttons_container.show()
        
        # Load and show saved characters
        self.load_saved_characters()
    
    def is_wakfu_window_active(self):
        """Check if Wakfu game window is currently active"""
        if not WINDOWS_DETECTION_AVAILABLE or platform.system() != "Windows":
            # On non-Windows or if win32gui is not available, always return True
            return True
        
        try:
            # Get the handle of the foreground (active) window
            foreground_window = win32gui.GetForegroundWindow()
            
            if foreground_window == 0:
                return False
            
            # Get the window text (title)
            window_text = win32gui.GetWindowText(foreground_window)
            
            # Check if it's a Wakfu window by checking for the specific format: "CharacterName - WAKFU"
            # This is the standard format for Wakfu game windows
            if " - WAKFU" in window_text or " - Wakfu" in window_text:
                return True
            
            # Also check by process name
            try:
                _, pid = win32process.GetWindowThreadProcessId(foreground_window)
                import psutil
                try:
                    process = psutil.Process(pid)
                    process_name = process.name().lower()
                    if "wakfu" in process_name or "ankama" in process_name:
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            except Exception:
                pass
            
            return False
        except Exception as e:
            # On error, return True to keep overlay visible
            return True
    
    def setup_focus_detection(self):
        """Setup window focus detection timer for detection overlay"""
        self.focus_timer = QTimer()
        self.focus_timer.timeout.connect(self.update_overlay_visibility)
        self.focus_timer.start(100)  # Check every 100ms
    
    def update_overlay_visibility(self):
        """Update detection overlay visibility"""
        # Always show overlay when there are detected classes
        if self.detection_overlay.detected_classes:
            if not self.detection_overlay.isVisible():
                self.detection_overlay.show()
    
    def setup_app_settings(self):
        """Setup persistent app settings storage"""
        try:
            # Get app data directory
            app_data_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
            app_data_path = Path(app_data_dir)
            
            # Create app directory if it doesn't exist
            app_data_path.mkdir(parents=True, exist_ok=True)
            
            # Define settings file path
            self.settings_file = app_data_path / "Waksense" / "app.settings.json"
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing settings
            self.app_settings = self.load_app_settings()
            
            print(f"DEBUG: App settings file: {self.settings_file}")
            
        except Exception as e:
            print(f"DEBUG: Error setting up app settings: {e}")
            self.app_settings = {}
            self.settings_file = None
    
    def load_app_settings(self):
        """Load app settings from file"""
        try:
            if self.settings_file and self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    print(f"DEBUG: Loaded app settings: {settings}")
                    return settings
            else:
                print("DEBUG: No existing app settings file found")
                return {}
        except Exception as e:
            print(f"DEBUG: Error loading app settings: {e}")
            return {}
    
    def save_app_settings(self):
        """Save app settings to file"""
        try:
            if self.settings_file:
                with open(self.settings_file, 'w', encoding='utf-8') as f:
                    json.dump(self.app_settings, f, indent=2)
                    print(f"DEBUG: Saved app settings: {self.app_settings}")
        except Exception as e:
            print(f"DEBUG: Error saving app settings: {e}")
    
    def load_settings(self):
        """Load app settings from internal storage"""
        try:
            # Initialize with default settings
            self.settings = {
                'wakfu_path': '',
                'saved_characters': {}
            }
            
            # Set log file path based on settings
            self.log_file = self.get_log_file_path(self.settings.get('wakfu_path', ''))
            
        except Exception as e:
            print(f"DEBUG: Error loading settings: {e}")
            # Fallback to default path
            self.log_file = self.get_log_file_path('')
    
    def get_log_file_path(self, logs_path):
        """Get the chat log file path from the logs directory"""
        if not logs_path:
            # Fallback to default path if no logs path provided
            user_profile = Path.home()
            return user_profile / "AppData" / "Roaming" / "zaap" / "gamesLogs" / "wakfu" / "logs" / "wakfu_chat.log"
        
        # Return the chat log file in the specified logs directory
        return Path(logs_path) / "wakfu_chat.log"
    
    
    
    def restart_monitoring(self):
        """Restart the monitoring thread with new settings"""
        try:
            # Stop current monitoring
            if hasattr(self, 'monitor_thread'):
                self.monitor_thread.stop_monitoring()
                self.monitor_thread.wait()
            
            # Start new monitoring with updated path
            self.start_monitoring()
            
        except Exception as e:
            print(f"DEBUG: Error restarting monitoring: {e}")
    
    def start_monitoring(self):
        """Start the monitoring thread"""
        self.monitor_thread = LogMonitorThread(str(self.log_file))
        self.monitor_thread.class_detected.connect(self.on_class_detected)
        self.monitor_thread.combat_started.connect(self.on_combat_started)
        self.monitor_thread.combat_ended.connect(self.on_combat_ended)
        self.monitor_thread.start()
    
    def on_class_detected(self, class_name, player_name):
        """Handle class detection"""
        button_key = f"{class_name}_{player_name}"
        
        # Check if we already have a button for this exact class+player combination
        if button_key not in self.class_buttons:
            # Check if this character is already saved
            is_saved = (class_name in self.saved_characters and 
                       player_name in self.saved_characters[class_name])
            
            # Create horizontal container for button + delete button
            container = QWidget()
            container_layout = QHBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(3)
            
            # Create new button for this class
            button = ClassButton(class_name, player_name, self, from_saved=is_saved, main_window=self)
            self.class_buttons[button_key] = button
            
            # Add main button to container
            container_layout.addWidget(button)
            
            # Add delete button if this is a saved character
            if is_saved:
                delete_button = QPushButton("×")
                delete_button.setFixedSize(20, 20)
                delete_button.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(255, 0, 0, 0.3);
                        border: 2px solid rgba(255, 0, 0, 0.5);
                                border-radius: 10px;
                        color: white;
                                font-size: 12px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: rgba(255, 0, 0, 0.5);
                        border-color: rgba(255, 0, 0, 0.7);
                    }
                    QPushButton:pressed {
                        background-color: rgba(255, 0, 0, 0.7);
                    }
                """)
                delete_button.setToolTip(f"Supprimer {player_name}")
                delete_button.clicked.connect(lambda checked, cn=class_name, pn=player_name: self.delete_character(cn, pn))
                container_layout.addWidget(delete_button)
            
            # Add container to appropriate column
            if class_name == "Iop":
                self.iop_buttons_layout.addWidget(container)
                self.iop_buttons_container.show()  # Ensure container is visible
            elif class_name == "Cra":
                self.cra_buttons_layout.addWidget(container)
                self.cra_buttons_container.show()  # Ensure container is visible
            
            # Add to detection overlay
            self.detection_overlay.add_detected_class(class_name, player_name)
            
            # Update status
            if self.status_label.isVisible():
                if is_saved:
                    self.status_label.setText(f"Personnage sauvegardé détecté: {class_name} ({player_name})")
                else:
                    self.status_label.setText(f"Nouveau détecté: {class_name} ({player_name})")
            print(f"DEBUG: Bouton {class_name} ajouté pour {player_name} (sauvegardé: {is_saved})")
            
            # Stop loading sequence when first class is detected
            if self.loading_active and not self.classes_found:
                self.classes_found = True
                self.stop_loading_sequence()
    
    def on_combat_started(self):
        """Handle combat start"""
        if self.status_label.isVisible():
            self.status_label.setText("Combat démarré - surveillance des classes...")
        print("DEBUG: Combat démarré")
    
    def on_combat_ended(self):
        """Handle combat end"""
        if self.status_label.isVisible():
            self.status_label.setText("Combat terminé - classes détectées:")
        print("DEBUG: Combat terminé")
    
    def save_character(self, class_name, player_name):
        """Save a character to internal storage"""
        try:
            if class_name not in self.saved_characters:
                self.saved_characters[class_name] = []
            
            # Check if character already exists (prevent duplicates)
            if player_name not in self.saved_characters[class_name]:
                self.saved_characters[class_name].append(player_name)
                
                # Save to internal settings
                self.settings['saved_characters'] = self.saved_characters
                
                print(f"DEBUG: Personnage sauvegardé {player_name} ({class_name}) en interne")
        except Exception as e:
            print(f"DEBUG: Erreur lors de la sauvegarde du personnage: {e}")
    
    def load_saved_characters(self):
        """Load saved characters from internal storage and create buttons"""
        try:
            # Load from internal settings
            self.saved_characters = self.settings.get('saved_characters', {})
            
            # Create buttons for saved characters
            for class_name, player_names in self.saved_characters.items():
                for player_name in player_names:
                    # Create horizontal container for button + delete button
                    container = QWidget()
                    container_layout = QHBoxLayout(container)
                    container_layout.setContentsMargins(0, 0, 0, 0)
                    container_layout.setSpacing(3)
                    
                    # Create main button
                    button = ClassButton(class_name, player_name, self, from_saved=True, main_window=self)
                    self.class_buttons[f"{class_name}_{player_name}"] = button
                        
                    # Create delete button
                    delete_button = QPushButton("×")
                    delete_button.setFixedSize(20, 20)
                    delete_button.setStyleSheet("""
                        QPushButton {
                            background-color: rgba(255, 0, 0, 0.3);
                            border: 2px solid rgba(255, 0, 0, 0.5);
                                border-radius: 10px;
                            color: white;
                                font-size: 12px;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background-color: rgba(255, 0, 0, 0.5);
                            border-color: rgba(255, 0, 0, 0.7);
                        }
                        QPushButton:pressed {
                            background-color: rgba(255, 0, 0, 0.7);
                        }
                    """)
                    delete_button.setToolTip(f"Supprimer {player_name}")
                    delete_button.clicked.connect(lambda checked, cn=class_name, pn=player_name: self.delete_character(cn, pn))
                    
                    # Add buttons to container
                    container_layout.addWidget(button)
                    container_layout.addWidget(delete_button)
                    
                    # Add container to appropriate column
                    if class_name == "Iop":
                        self.iop_buttons_layout.addWidget(container)
                    elif class_name == "Cra":
                        self.cra_buttons_layout.addWidget(container)
                        
                    print(f"DEBUG: Personnage sauvegardé chargé {player_name} ({class_name})")
                
                if self.saved_characters:
                    saved_count = len([name for names in self.saved_characters.values() for name in names])
                    if self.status_label.isVisible():
                        self.status_label.setText(f"Chargé {saved_count} personnages sauvegardés")
            else:
                print("DEBUG: Aucun personnage sauvegardé trouvé")
                if self.status_label.isVisible():
                    self.status_label.setText("Aucun personnage sauvegardé - surveillance des nouvelles classes...")
        except Exception as e:
            print(f"DEBUG: Erreur lors du chargement des personnages sauvegardés: {e}")
            if self.status_label.isVisible():
                self.status_label.setText("Erreur lors du chargement des personnages sauvegardés...")
    
    def check_saved_log_path(self):
        """Check if log path is saved and start auto-scan if available"""
        try:
            saved_log_path = self.app_settings.get('log_path')
            if saved_log_path and Path(saved_log_path).exists():
                # Use saved path and start auto-scan immediately
                self.log_path = Path(saved_log_path)
                self.path_label.setText(f"📁 {self.log_path}")
                self.path_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
                self.status_label.setText("✅ Chemin des logs trouvé - Démarrage automatique...")
                self.status_label.setStyleSheet("""
                    QLabel {
                        font-size: 11px;
                        color: #4CAF50;
                        margin: 5px 0px;
                        padding: 6px 10px;
                        background-color: rgba(76, 175, 80, 0.2);
                        border-radius: 6px;
                        border: 1px solid rgba(76, 175, 80, 0.5);
                    }
                """)
                # Start auto-scan immediately
                QTimer.singleShot(1000, self.auto_scan_wakfu)
            else:
                # Show manual path selection
                self.status_label.setText("📁 Sélectionnez le chemin des logs Wakfu")
                self.status_label.setStyleSheet("""
                    QLabel {
                        font-size: 11px;
                        color: #2196F3;
                        margin: 5px 0px;
                        padding: 6px 10px;
                        background-color: rgba(33, 150, 243, 0.2);
                        border-radius: 6px;
                        border: 1px solid rgba(33, 150, 243, 0.5);
                    }
                """)
        except Exception as e:
            print(f"DEBUG: Error checking saved log path: {e}")
    
    def delete_character(self, class_name, player_name):
        """Delete a character from the saved list"""
        try:
            # Show confirmation dialog
            reply = QMessageBox.question(
                self, 
                "Supprimer le personnage", 
                f"Êtes-vous sûr de vouloir supprimer {player_name} ({class_name}) ?\n\nCela les retirera de votre liste de personnages sauvegardés.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
                
            # Remove from saved characters
            if (class_name in self.saved_characters and 
                player_name in self.saved_characters[class_name]):
                self.saved_characters[class_name].remove(player_name)
                
                # If no more characters of this class, remove the class entry
                if not self.saved_characters[class_name]:
                    del self.saved_characters[class_name]
                
                # Save updated list to internal storage
                self.settings['saved_characters'] = self.saved_characters
                
                # Remove button from UI
                button_key = f"{class_name}_{player_name}"
                if button_key in self.class_buttons:
                    del self.class_buttons[button_key]
                
                # Refresh the UI by clearing and reloading
                self.clear_character_buttons()
                self.load_saved_characters()
                
                print(f"DEBUG: Personnage supprimé {player_name} ({class_name})")
                
        except Exception as e:
            print(f"DEBUG: Erreur lors de la suppression du personnage: {e}")
    
    def clear_character_buttons(self):
        """Clear all character buttons from the UI"""
        # Clear IOP buttons
        while self.iop_buttons_layout.count():
            child = self.iop_buttons_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Clear CRA buttons
        while self.cra_buttons_layout.count():
            child = self.cra_buttons_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Clear button references
        self.class_buttons.clear()
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Stop all active trackers
        for button in self.class_buttons.values():
            if button.is_active:
                button.stop_tracker()
        
        # Stop monitoring
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.stop_monitoring()
            self.monitor_thread.wait()
        
        # Close detection overlay
        if hasattr(self, 'detection_overlay'):
            self.detection_overlay.close()
        
        # Save app settings before closing
        self.save_app_settings()
        
        event.accept()

def main():
    # Check command line arguments for tracker mode
    if len(sys.argv) > 1:
        if "--iop" in sys.argv:
            # Launch IOP tracker directly
            from Iop.wakfu_iop_resource_tracker import main as iop_main
            iop_main()
            return
        elif "--cra" in sys.argv:
            # Launch CRA tracker directly
            from Cra.wakfu_resource_tracker_fullscreen import main as cra_main
            cra_main()
            return
    
    # Normal launcher mode
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Set application properties
    app.setApplicationName("Waksense")
    app.setApplicationDisplayName("Waksense")
    
    # Set application icon
    # Get the directory where the script is located (works for both script and executable)
    if getattr(sys, 'frozen', False):
        # Running as executable - look in the bundled files
        base_dir = Path(sys._MEIPASS)
    else:
        # Running as script
        base_dir = Path(__file__).parent
    icon_path = base_dir / "Waksense.ico"
    if icon_path.exists():
        from PyQt6.QtGui import QIcon
        app.setWindowIcon(QIcon(str(icon_path)))
        print(f"DEBUG: Icône d'application définie sur {icon_path}")
    else:
        print(f"DEBUG: Fichier d'icône non trouvé: {icon_path}")
    
    # Create and show window
    window = WakfuClassLauncher()
    window.show()
    
    # Run application
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
