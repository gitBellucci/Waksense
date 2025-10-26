#!/usr/bin/env python3
"""
Wakfu Cra Class Resource Tracker - Full Screen Overlay System
Full-screen transparent overlay with draggable icons anywhere on screen
Tracks Affûtage and Précision resources in real-time from chat logs
"""

import sys
import threading
import time
import re
import math
import json
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QProgressBar, QFrame, QMenu)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QPoint, QRect
from PyQt6.QtGui import QFont, QPalette, QColor, QPainter, QLinearGradient, QBrush, QPixmap, QPen, QAction

class LogMonitorThread(QThread):
    """Thread for monitoring log file"""
    log_updated = pyqtSignal(str)
    
    def __init__(self, log_file_path):
        super().__init__()
        self.log_file = Path(log_file_path)
        self.monitoring = True
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
                                    self.log_updated.emit(line)
                            
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
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False

class OutlinedLabel(QLabel):
    """QLabel with outlined text (white text with black border)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.text_to_draw = ""
    
    def setText(self, text):
        """Override setText to store text and trigger repaint"""
        self.text_to_draw = text
        super().setText(text)
        self.update()
    
    def paintEvent(self, event):
        """Custom paint event to draw outlined text"""
        if not self.text_to_draw:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Set font size based on widget size
        font_size = max(16, int(self.width() * 0.4))  # Smaller font, scale with widget size
        font = QFont('Segoe UI', font_size, QFont.Weight.Bold)
        painter.setFont(font)
        
        # Calculate text position
        metrics = painter.fontMetrics()
        text_rect = metrics.boundingRect(self.text_to_draw)
        x = (self.width() - text_rect.width()) // 2
        y = (self.height() + text_rect.height()) // 2 - metrics.descent()
        
        # Draw black outline (8 directions)
        outline_pen = QPen(QColor(0, 0, 0), 2)
        painter.setPen(outline_pen)
        for dx in [-2, 0, 2]:
            for dy in [-2, 0, 2]:
                if dx != 0 or dy != 0:
                    painter.drawText(x + dx, y + dy, self.text_to_draw)
        
        # Draw white text on top
        text_pen = QPen(QColor(255, 255, 255), 1)
        painter.setPen(text_pen)
        painter.drawText(x, y, self.text_to_draw)

class DraggableIcon(QWidget):
    """Draggable icon widget that can be moved anywhere on screen"""
    
    def __init__(self, icon_path, icon_name, parent=None, centered_count=False, icon_size=80):
        super().__init__(parent)
        self.icon_path = icon_path
        self.icon_name = icon_name
        self.drag_position = QPoint()
        self.is_dragging = False
        self.is_locked = False
        self.parent_overlay = parent
        self.centered_count = centered_count  # If True, show count in center of icon
        self.icon_size = icon_size  # Size of the icon widget
        
        # Animation properties
        self.bounce_offset = 0
        self.bounce_direction = 1
        self.bounce_speed = 0.3
        self.stack_count = 0
        self.show_stack_count = False
        
        # Setup UI
        self.setup_ui()
        
        # Initially hidden
        self.hide()
    
    def setup_ui(self):
        """Setup the draggable icon"""
        self.setFixedSize(self.icon_size, self.icon_size)  # Use custom size
        
        # Make widget transparent
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Stack count label (on top or centered)
        if self.centered_count:
            # Use OutlinedLabel for centered display (white text with black border)
            self.stack_count_label = OutlinedLabel(self)
            self.stack_count_label.setFixedSize(64, 64)
            self.stack_count_label.setStyleSheet("background-color: transparent;")
        else:
            # Top label (original style)
            self.stack_count_label = QLabel("")
            self.stack_count_label.setFixedSize(80, 20)
            self.stack_count_label.setStyleSheet("""
                QLabel {
                    color: #ffffff;
                    font-size: 14px;
                    font-weight: bold;
                    font-family: 'Segoe UI', 'Roboto', 'Open Sans', sans-serif;
                    background-color: rgba(255, 0, 0, 0.8);
                    border-radius: 10px;
                    border: 2px solid #ffffff;
                }
            """)
        self.stack_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stack_count_label.hide()
        
        # Load icon
        if self.icon_path.exists():
            self.icon_label = QLabel()
            pixmap = QPixmap(str(self.icon_path))
            self.icon_label.setPixmap(pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            # Set icon label to exact image size (64x64) for proper border
            self.icon_label.setFixedSize(64, 64)
            self.icon_label.setStyleSheet("background-color: transparent;")
        else:
            # Fallback emoji based on icon name
            emoji_map = {
                "Affûtage": "⚡",
                "Précision": "🎯", 
                "Pointe": "🔸",
                "Précis": "🎯"
            }
            emoji = emoji_map.get(self.icon_name, "📌")
            self.icon_label = QLabel(emoji)
            # Set icon label to exact size (64x64) for proper border
            self.icon_label.setFixedSize(64, 64)
            self.icon_label.setStyleSheet(f"""
                QLabel {{
                    color: #ffd700;
                    font-size: 48px;
                    font-weight: bold;
                    background-color: transparent;
                }}
            """)
        
        if self.centered_count:
            # For centered mode, overlay the count on top of the icon
            layout.addWidget(self.icon_label)
            layout.setAlignment(self.icon_label, Qt.AlignmentFlag.AlignCenter)
            # Position count label on top of icon using absolute positioning
            self.stack_count_label.setParent(self)
            self.stack_count_label.move(8, 8)  # Center it on the 64x64 icon (80-64)/2 = 8
            self.stack_count_label.raise_()
        else:
            # Original layout: count on top, icon below
            layout.addWidget(self.stack_count_label)
            layout.addWidget(self.icon_label)
            layout.setAlignment(self.icon_label, Qt.AlignmentFlag.AlignCenter)
    
    def mousePressEvent(self, event):
        """Handle mouse press for dragging"""
        if event.button() == Qt.MouseButton.LeftButton and not self.is_locked:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.is_dragging = True
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self.show_context_menu(event.globalPosition().toPoint())
            event.accept()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging"""
        if self.is_dragging and event.buttons() == Qt.MouseButton.LeftButton and not self.is_locked:
            new_pos = event.globalPosition().toPoint() - self.drag_position
            self.move(new_pos)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            event.accept()
    
    def show_context_menu(self, position):
        """Show context menu for lock/unlock"""
        menu = QMenu(self)
        
        lock_action = QAction("🔒 Lock Position" if not self.is_locked else "🔓 Unlock Position", self)
        lock_action.triggered.connect(self.toggle_lock)
        menu.addAction(lock_action)
        
        hide_action = QAction("👁️ Hide Icon", self)
        hide_action.triggered.connect(self.hide)
        menu.addAction(hide_action)
        
        menu.exec(position)
    
    def toggle_lock(self):
        """Toggle lock state"""
        self.is_locked = not self.is_locked
        if self.is_locked:
            self.setStyleSheet("border: 2px solid #ff0000; border-radius: 8px;")
        else:
            self.setStyleSheet("border: none;")
    
    def show_icon(self):
        """Show the icon"""
        self.show()
        self.raise_()
    
    def hide_icon(self):
        """Hide the icon"""
        self.hide()
    
    def update_stack_count(self, count):
        """Update the stack count display"""
        self.stack_count = count
        if count > 0:
            if self.centered_count:
                # Show just the number for centered display
                self.stack_count_label.setText(f"{count}")
            else:
                # Show ×number for top display
                self.stack_count_label.setText(f"×{count}")
            self.stack_count_label.show()
            self.show_stack_count = True
            # Trigger repaint for custom text rendering if centered
            if self.centered_count:
                self.update()
        else:
            self.stack_count_label.hide()
            self.show_stack_count = False
    
    def update_bounce_animation(self):
        """Update bounce animation"""
        if self.show_stack_count and self.stack_count > 0:
            # Bounce animation
            self.bounce_offset += self.bounce_direction * self.bounce_speed
            
            # Reverse direction at bounce limits
            if self.bounce_offset >= 5:
                self.bounce_direction = -1
            elif self.bounce_offset <= -5:
                self.bounce_direction = 1
            
            # Apply bounce offset to position
            current_pos = self.pos()
            self.move(current_pos.x(), current_pos.y() + int(self.bounce_offset))
    
    def set_icon_border(self, active, pulse_alpha=255):
        """Set border styling on the icon label instead of the entire widget"""
        if active:
            # Apply border to the icon label (64x64) instead of the widget (80x80)
            self.icon_label.setStyleSheet(f"""
                QLabel {{
                    background-color: transparent;
                    border: 3px solid rgba(255, 215, 0, {pulse_alpha/255});
                    border-radius: 8px;
                }}
            """)
        else:
            # Remove border from icon label
            self.icon_label.setStyleSheet("background-color: transparent;")

class MinimalProgressBar(QProgressBar):
    """Ultra minimalistic progress bar with custom text rendering"""
    
    def __init__(self, color_scheme="yellow"):
        super().__init__()
        self.color_scheme = color_scheme
        self.setFixedHeight(24)
        self.setFixedWidth(250)
        self.setRange(0, 100)
        self.setValue(0)
        self.decimal_value = 0.0
        self.max_value = 100
        
        # Hide default text
        self.setTextVisible(False)
        
        # Ultra minimal styling
        self.setStyleSheet(self.get_minimal_style())
    
    def setMaxValue(self, max_val):
        """Set maximum value for percentage calculation"""
        self.max_value = max_val
        self.setRange(0, max_val)
    
    def setDecimalValue(self, value):
        """Set decimal value and update display"""
        self.decimal_value = value
        self.setValue(int(value))
        self.update()  # Trigger repaint
    
    def paintEvent(self, event):
        """Custom paint event to draw text with black borders"""
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Set font
        font = QFont('Segoe UI', 16, QFont.Weight.Bold)
        painter.setFont(font)
        
        # Get text - use round() instead of int() to fix the "1 less point" issue
        # Use dynamic max_value instead of hardcoded values
        text = f"{round(self.decimal_value)}/{self.max_value}"
        
        # Get text metrics
        metrics = painter.fontMetrics()
        text_rect = metrics.boundingRect(text)
        
        # Center the text
        x = (self.width() - text_rect.width()) // 2
        y = (self.height() + text_rect.height()) // 2 - metrics.descent()
        
        # Draw black outline (border)
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx != 0 or dy != 0:
                    painter.drawText(x + dx, y + dy, text)
        
        # Draw white text
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.drawText(x, y, text)
        
        painter.end()
        
    def get_minimal_style(self):
        """Get ultra minimal style with white text"""
        if self.color_scheme == "yellow":
            return """
                QProgressBar {
                    border: 2px solid #333333;
                    background-color: rgba(0, 0, 0, 0.3);
                    text-align: center;
                    font-weight: bold;
                    font-size: 16px;
                    font-family: 'Segoe UI', 'Roboto', 'Open Sans', sans-serif;
                    color: #ffffff;
                    border-radius: 12px;
                }
                QProgressBar::chunk {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #ffd700, stop:0.5 #ffed4e, stop:1 #ffff00);
                    border-radius: 10px;
                    margin: 1px;
                }
            """
        else:  # blue
            return """
                QProgressBar {
                    border: 2px solid #333333;
                    background-color: rgba(0, 0, 0, 0.3);
                    text-align: center;
                    font-weight: bold;
                    font-size: 16px;
                    font-family: 'Segoe UI', 'Roboto', 'Open Sans', sans-serif;
                    color: #ffffff;
                    border-radius: 12px;
                }
                QProgressBar::chunk {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #4a9eff, stop:0.5 #6bb6ff, stop:1 #2196f3);
                    border-radius: 10px;
                    margin: 1px;
                }
            """
    
    def set_glow_effect(self, active=False, pulse_intensity=1.0):
        """Add subtle glow effect when active - keeps rectangular shape"""
        if active:
            if self.color_scheme == "yellow":
                # Calculate pulsing border color
                pulse_alpha = int(255 * pulse_intensity)
                glow_style = f"""
                    QProgressBar {{
                        border: 3px solid rgba(255, 215, 0, {pulse_alpha});
                        background-color: rgba(255, 215, 0, {int(0.2 * pulse_intensity)});
                        text-align: center;
                        font-weight: bold;
                        font-size: 16px;
                        font-family: 'Segoe UI', 'Roboto', 'Open Sans', sans-serif;
                        color: #ffffff;
                        border-radius: 12px;
                    }}
                    QProgressBar::chunk {{
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 #ffd700, stop:0.5 #ffed4e, stop:1 #ffff00);
                        border-radius: 9px;
                        margin: 1px;
                    }}
                """
            else:  # blue
                # Calculate pulsing border color for Tir précis
                pulse_alpha = int(255 * pulse_intensity)
                glow_style = f"""
                    QProgressBar {{
                        border: 3px solid rgba(255, 215, 0, {pulse_alpha});
                        background-color: rgba(255, 215, 0, {int(0.2 * pulse_intensity)});
                        text-align: center;
                        font-weight: bold;
                        font-size: 16px;
                        font-family: 'Segoe UI', 'Roboto', 'Open Sans', sans-serif;
                        color: #ffffff;
                        border-radius: 12px;
                    }}
                    QProgressBar::chunk {{
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 #00a8ff, stop:0.5 #4fc3f7, stop:1 #00bcd4);
                        border-radius: 9px;
                        margin: 1px;
                    }}
                """
            self.setStyleSheet(glow_style)
        else:
            self.setStyleSheet(self.get_minimal_style())

class WakfuResourceTrackerFullscreen(QMainWindow):
    def __init__(self, hidden_mode=False):
        super().__init__()
        
        # Store hidden mode
        self.hidden_mode = hidden_mode
        
        # Resource values
        self.affutage = 0
        self.precision = 0
        self.pointe_affutee_stacks = 0
        self.balise_affutee_stacks = 0
        self.tir_precis_active = False
        self.has_esprit_affute = False  # Track if player has "Esprit affûté" talent
        self.in_combat = False
        self.debug_mode = False
        
        # Turn-based visibility system
        self.tracked_player_name = None  # Track the player we're monitoring
        self.is_cra_turn = False  # Track if it's the Cra's turn
        self.overlay_visible = False  # Track if overlay should be visible
        self.last_spell_caster = None  # Track the last player who cast a spell
        
        # Cra spells list for turn detection
        self.cra_spells = [
            "Flèche criblante", "Flèche fulminante", "Flèche d'immolation", 
            "Flèche enflammée", "Flèche Ardente", "Flèche explosive", 
            "Flèche cinglante", "Flèche perçante", "Flèche destructrice", 
            "Flèche chercheuse", "Flèche de recul", "Flèche tempête", 
            "Flèche harcelante", "Flèche statique", "Balise de destruction", 
            "Balise d'alignement", "Balise de contact", "Tir précis", "Débalisage", "Eclaireur",
            "Flèche lumineuse", "Pluie de flèches", "Roulade"
        ]
        
        # Combat detection
        self.is_sac_patate_combat = False  # Track if we're fighting Sac à patate
        
        # Position locking and saving system
        self.positions_locked = False
        # Get the directory where the script is located (works for both script and executable)
        if getattr(sys, 'frozen', False):
            # Running as executable - look in the bundled Cra folder
            base_dir = Path(sys._MEIPASS) / "Cra"
        else:
            # Running as script
            base_dir = Path(__file__).parent
        self.config_file = base_dir / "positions_config.json"
        self.positions_loaded = False  # Track if positions have been loaded
        self.auto_save_timer = None  # Timer for auto-saving positions
        
        # Animation
        self.animation_frame = 0
        self.smooth_transitions = True
        self.current_affutage = 0
        self.current_precision = 0
        
        # Queue system for Balise and Pointe icons
        # Position 1: Right edge of Précision bar (281px) - for Balise (priority)
        # Position 2: Left of position 1 (281 - 40 = 241px) - for Pointe (secondary)
        # But we need to ensure both fit in container (300px max)
        # So: Position 1 = 260px (max), Position 2 = 220px
        self.queue_positions = {
            'balise': {'x': 220, 'y': 5},  # Position 2 (left, secondary)
            'pointe': {'x': 260, 'y': 5}   # Position 1 (right, priority)
        }
        self.current_positions = {
            'balise': {'x': 220, 'y': 5},
            'pointe': {'x': 260, 'y': 5}
        }
        self.animation_speed = 0.2  # Speed of slide animation
        
        # Bounce animation for Pointe affûtée
        self.pointe_bounce_offset = 0
        self.pointe_bounce_direction = 1
        self.pointe_bounce_speed = 0.3
        self.pointe_bounce_amplitude = 3  # Max bounce height in pixels
        
        # Drag functionality
        self.drag_position = QPoint()
        
        # Precision gain tracking for talent detection
        self.recent_precision_gains = []  # Store recent precision gains
        self.max_recent_gains = 5  # Keep only last 5 gains
        
        # Log file path - use default Wakfu logs location
        user_profile = Path.home()
        self.log_file = user_profile / "AppData" / "Roaming" / "zaap" / "gamesLogs" / "wakfu" / "logs" / "wakfu_chat.log"
        
        # Icon paths
        # Get the directory where the script is located (works for both script and executable)
        if getattr(sys, 'frozen', False):
            # Running as executable - look in the bundled Cra folder
            base_dir = Path(sys._MEIPASS) / "Cra"
        else:
            # Running as script
            base_dir = Path(__file__).parent
        self.icon_path = base_dir / "img"
        
        # Setup full-screen overlay
        self.setup_fullscreen_overlay()
        self.setup_animations()
        self.setup_shortcuts()
        
        # Start monitoring
        self.start_monitoring()
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        from PyQt6.QtGui import QShortcut, QKeySequence
        
        # Ctrl+Q to quit
        quit_shortcut = QShortcut(QKeySequence("Ctrl+Q"), self)
        quit_shortcut.activated.connect(self.close_application)
        
        # Ctrl+Shift+Q to force quit
        force_quit_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Q"), self)
        force_quit_shortcut.activated.connect(self.force_quit)
        
        # Ctrl+L to toggle position lock
        lock_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        lock_shortcut.activated.connect(self.toggle_positions_lock)
    
    def close_application(self):
        """Close application gracefully"""
        self.close()
    
    def force_quit(self):
        """Force quit application"""
        sys.exit(0)
    
    def save_positions(self):
        """Save current positions to config file"""
        try:
            positions = {
                'resource_container': {
                    'x': self.resource_container.x(),
                    'y': self.resource_container.y()
                },
                'precis_icon': {
                    'x': self.precis_icon.x(),
                    'y': self.precis_icon.y()
                },
                'positions_locked': self.positions_locked
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(positions, f, indent=2)
            
            print(f"DEBUG: Positions auto-saved to {self.config_file}")
                
        except Exception as e:
            print(f"DEBUG: Error saving positions: {e}")
    
    def load_positions(self):
        """Load positions from config file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    positions = json.load(f)
                
                print(f"DEBUG: Loading positions from {self.config_file}")
                print(f"DEBUG: Positions data: {positions}")
                
                # Don't load resource container position here - it's handled by load_container_position()
                
                # Load icon positions only if icons are visible (in combat)
                if 'precis_icon' in positions and self.precis_icon.isVisible():
                    x, y = positions['precis_icon']['x'], positions['precis_icon']['y']
                    self.precis_icon.move(x, y)
                    print(f"DEBUG: Moved precis_icon to ({x}, {y})")
                
                # Load lock state
                if 'positions_locked' in positions:
                    self.positions_locked = positions['positions_locked']
                    print(f"DEBUG: Positions locked: {self.positions_locked}")
                
                print("DEBUG: Positions loaded successfully!")
                    
        except Exception as e:
            print(f"DEBUG: Error loading positions: {e}")
    
    def toggle_positions_lock(self):
        """Toggle positions lock state"""
        self.positions_locked = not self.positions_locked
        self.save_positions()  # Save the lock state
        
        if self.debug_mode:
            print(f"DEBUG: Positions locked: {self.positions_locked}")
    
    def load_container_position(self):
        """Load only the resource container position"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    positions = json.load(f)
                
                # Load resource container position
                if 'resource_container' in positions:
                    x, y = positions['resource_container']['x'], positions['resource_container']['y']
                    print(f"DEBUG: Loading container position: ({x}, {y})")
                    print(f"DEBUG: Container current position: ({self.resource_container.x()}, {self.resource_container.y()})")
                    self.resource_container.move(x, y)
                    print(f"DEBUG: Container moved to: ({self.resource_container.x()}, {self.resource_container.y()})")
                    
        except Exception as e:
            print(f"DEBUG: Error loading container position: {e}")
    
    def auto_save_positions(self):
        """Auto-save positions with a delay to avoid too frequent saves"""
        if self.auto_save_timer:
            self.auto_save_timer.stop()
        
        # Save after 500ms delay to avoid too frequent saves
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.save_positions)
        self.auto_save_timer.setSingleShot(True)
        self.auto_save_timer.start(500)
    
    def show_resource_context_menu(self, position):
        """Show context menu for resource bars"""
        menu = QMenu(self)
        
        # Quit options
        quit_action = QAction("🚪 Quit Application", self)
        quit_action.triggered.connect(self.close_application)
        menu.addAction(quit_action)
        
        force_quit_action = QAction("💀 Force Quit", self)
        force_quit_action.triggered.connect(self.force_quit)
        menu.addAction(force_quit_action)
        
        menu.addSeparator()
        
        # Debug info
        debug_action = QAction(f"📊 Debug Info", self)
        debug_action.triggered.connect(self.show_debug_info)
        menu.addAction(debug_action)
        
        # Show menu at cursor position
        menu.exec(self.mapToGlobal(position))
    
    def show_debug_info(self):
        """Show debug information"""
        debug_text = f"""
Wakfu Cra Resource Tracker - Debug Info
=====================================
Affûtage: {self.affutage}/100
Précision: {self.precision}/300
Pointe affûtée stacks: {self.pointe_affutee_stacks}
Balise affûtée stacks: {self.balise_affutee_stacks}
Tir précis actif: {self.tir_precis_active}
En combat: {self.in_combat}
Fichier log: {self.log_file}
        """
        print(debug_text)
    
    def setup_fullscreen_overlay(self):
        """Setup full-screen transparent overlay"""
        # Get screen dimensions
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        
        # Set window to full screen
        self.setWindowTitle("Wakfu Cra Resource Tracker - Full Screen Overlay")
        self.setGeometry(screen_geometry)
        
        # Make window transparent, always on top, but visible in taskbar
        if self.hidden_mode:
            # In hidden mode, use flags that hide from taskbar
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint | 
                Qt.WindowType.WindowStaysOnTopHint |
                Qt.WindowType.Tool |
                Qt.WindowType.X11BypassWindowManagerHint
            )
        else:
            # Normal mode
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint | 
                Qt.WindowType.WindowStaysOnTopHint |
                Qt.WindowType.Tool
            )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        
        # Main widget - completely transparent
        main_widget = QWidget()
        main_widget.setStyleSheet("background-color: transparent;")
        
        # Main layout
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create resource bars container (top-left corner)
        self.resource_container = QWidget()
        self.resource_container.setFixedSize(320, 70)  # Increased width to accommodate bars properly
        self.resource_container.setStyleSheet("background-color: transparent;")
        
        # Resource bars layout
        resource_layout = QVBoxLayout(self.resource_container)
        resource_layout.setSpacing(10)
        resource_layout.setContentsMargins(0, 0, 0, 0)
        
        # Affûtage section
        affutage_layout = QHBoxLayout()
        affutage_layout.setContentsMargins(0, 0, 0, 0)
        
        # Load Affûtage icon
        affutage_icon_path = self.icon_path / "Affûtage.png"
        if affutage_icon_path.exists():
            affutage_icon = QLabel()
            pixmap = QPixmap(str(affutage_icon_path))
            affutage_icon.setPixmap(pixmap.scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            affutage_icon.setStyleSheet("background-color: transparent;")
        else:
            affutage_icon = QLabel("⚡")
            affutage_icon.setStyleSheet("""
                QLabel {
                    color: #ff6b35;
                    font-size: 20px;
                    font-weight: bold;
                    background-color: transparent;
                }
            """)
        
        # Affûtage progress bar
        self.affutage_bar = MinimalProgressBar("yellow")
        self.affutage_bar.setMaxValue(100)
        # Enable right-click context menu
        self.affutage_bar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.affutage_bar.customContextMenuRequested.connect(self.show_resource_context_menu)
        
        # Stack indicator
        self.stack_label = QLabel("")
        self.stack_label.setStyleSheet("""
            QLabel {
                color: #ffd700;
                font-size: 16px;
                font-weight: bold;
                font-family: 'Segoe UI', 'Roboto', 'Open Sans', sans-serif;
                background-color: transparent;
                min-width: 20px;
            }
        """)
        
        affutage_layout.addWidget(affutage_icon)
        affutage_layout.addSpacing(3)
        affutage_layout.addWidget(self.affutage_bar)
        affutage_layout.addWidget(self.stack_label)
        
        # Create Balise affûtée icon as child of resource_container
        balise_icon_path = self.icon_path / "Balise.png"
        if balise_icon_path.exists():
            self.balise_container_icon = QLabel(self.resource_container)
            pixmap = QPixmap(str(balise_icon_path))
            self.balise_container_icon.setPixmap(pixmap.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.balise_container_icon.setFixedSize(40, 40)
            self.balise_container_icon.setStyleSheet("background-color: transparent;")
            
            # Create centered count label for Balise
            self.balise_count_label = OutlinedLabel(self.resource_container)
            self.balise_count_label.setFixedSize(40, 40)
            self.balise_count_label.setStyleSheet("background-color: transparent;")
            self.balise_count_label.hide()
            
            # Position just to the right of Affûtage bar, within container bounds
            # Bar starts at ~31px (icon 28 + spacing 3), bar is 250px wide
            # So right edge is at 31 + 250 = 281, place icon just to the right
            # Bar height is 24px, icon is 40px, so center vertically: (24-40)/2 = -8
            # Container is 300px wide, so position at 260px to fit (260 + 40 = 300)
            # Adjust Y position to be within container bounds (container height is 70px)
            self.balise_container_icon.move(260, 5)  # Within container bounds, centered vertically
            self.balise_count_label.move(260, 5)
            # Raise both widgets to ensure they appear on top of progress bar
            self.balise_container_icon.raise_()
            self.balise_count_label.raise_()
            
            self.balise_container_icon.hide()
        else:
            self.balise_container_icon = None
            self.balise_count_label = None
        
        # Create Pointe affûtée icon as child of resource_container (for queue system)
        pointe_icon_path = self.icon_path / "Pointe.png"
        if pointe_icon_path.exists():
            self.pointe_container_icon = QLabel(self.resource_container)
            pixmap = QPixmap(str(pointe_icon_path))
            self.pointe_container_icon.setPixmap(pixmap.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.pointe_container_icon.setFixedSize(40, 40)
            self.pointe_container_icon.setStyleSheet("background-color: transparent;")
            
            # Create centered count label for Pointe
            self.pointe_count_label = OutlinedLabel(self.resource_container)
            self.pointe_count_label.setFixedSize(40, 40)
            self.pointe_count_label.setStyleSheet("background-color: transparent;")
            self.pointe_count_label.hide()
            
            # Position will be managed by queue system
            # Adjust Y position to be within container bounds (container height is 70px)
            self.pointe_container_icon.move(220, 5)  # Initial position (left of Balise)
            self.pointe_count_label.move(220, 5)
            # Raise both widgets to ensure they appear on top of progress bar
            self.pointe_container_icon.raise_()
            self.pointe_count_label.raise_()
            
            self.pointe_container_icon.hide()
        else:
            self.pointe_container_icon = None
            self.pointe_count_label = None
        
        # Précision section
        precision_layout = QHBoxLayout()
        precision_layout.setContentsMargins(0, 0, 0, 0)
        
        # Load Précision icon
        precision_icon_path = self.icon_path / "Précision.png"
        if precision_icon_path.exists():
            precision_icon = QLabel()
            pixmap = QPixmap(str(precision_icon_path))
            precision_icon.setPixmap(pixmap.scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            precision_icon.setStyleSheet("background-color: transparent;")
        else:
            precision_icon = QLabel("🎯")
            precision_icon.setStyleSheet("""
                QLabel {
                    color: #4a9eff;
                    font-size: 20px;
                    font-weight: bold;
                    background-color: transparent;
                }
            """)
        
        # Précision progress bar
        self.precision_bar = MinimalProgressBar("blue")
        self.precision_bar.setMaxValue(300)
        # Enable right-click context menu
        self.precision_bar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.precision_bar.customContextMenuRequested.connect(self.show_resource_context_menu)
        
        precision_layout.addWidget(precision_icon)
        precision_layout.addSpacing(3)
        precision_layout.addWidget(self.precision_bar)
        
        # Add invisible spacer to align with affutage layout (which has stack_label)
        precision_spacer = QLabel("")
        precision_spacer.setFixedWidth(20)  # Same width as stack_label
        precision_spacer.setStyleSheet("background-color: transparent;")
        precision_layout.addWidget(precision_spacer)
        
        # Add to resource layout
        resource_layout.addLayout(affutage_layout)
        resource_layout.addLayout(precision_layout)
        
        # Position resource container absolutely (not in layout)
        self.resource_container.setParent(main_widget)
        self.resource_container.move(0, 0)  # Initial position
        
        # Initially hide overlay since we start out of combat
        self.resource_container.hide()
        
        self.setCentralWidget(main_widget)
        
        # Create draggable icons
        self.create_draggable_icons()
    
    def create_draggable_icons(self):
        """Create draggable icons for different resources"""
        # Tir précis icon only (Pointe is handled by queue system)
        precis_icon_path = self.icon_path / "Précis.png"
        self.precis_icon = DraggableIcon(precis_icon_path, "Précis", self)
        
        # Position icon initially (center of screen)
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        center_x = screen_geometry.width() // 2
        center_y = screen_geometry.height() // 2
        
        self.precis_icon.move(center_x + 100, center_y)
        
        # Initially hide icon since we start out of combat
        self.precis_icon.hide_icon()
        
        # Load saved positions after a short delay to ensure widgets are ready
        QTimer.singleShot(100, self.load_positions)
    
    def setup_animations(self):
        """Setup animation timer"""
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animations)
        self.animation_timer.start(16)  # ~60 FPS
    
    def update_pointe_bounce_animation(self):
        """Update bounce animation for Pointe affûtée icon"""
        if self.pointe_affutee_stacks > 0:
            # Update bounce offset
            self.pointe_bounce_offset += self.pointe_bounce_direction * self.pointe_bounce_speed
            
            # Reverse direction when reaching amplitude limits
            if self.pointe_bounce_offset >= self.pointe_bounce_amplitude:
                self.pointe_bounce_offset = self.pointe_bounce_amplitude
                self.pointe_bounce_direction = -1
            elif self.pointe_bounce_offset <= -self.pointe_bounce_amplitude:
                self.pointe_bounce_offset = -self.pointe_bounce_amplitude
                self.pointe_bounce_direction = 1
        else:
            # Reset bounce when no stacks
            self.pointe_bounce_offset = 0
            self.pointe_bounce_direction = 1

    def update_queue_animation(self):
        """Update queue system animation for Balise and Pointe icons"""
        if not (self.balise_container_icon and self.pointe_container_icon):
            return
        
        # Determine target positions based on priority
        pointe_active = self.pointe_affutee_stacks > 0
        balise_active = self.balise_affutee_stacks > 0
        
        # Calculate target positions - Balise has priority over Pointe
        if pointe_active and balise_active:
            # Both active: Balise at position 1 (260px), Pointe at position 2 (220px)
            target_balise_x = self.queue_positions['pointe']['x']  # 260px (position 1)
            target_pointe_x = self.queue_positions['balise']['x']  # 220px (position 2)
        elif balise_active:
            # Only Balise active: takes position 1
            target_balise_x = self.queue_positions['pointe']['x']  # 260px
            target_pointe_x = self.queue_positions['balise']['x']  # 220px (hidden)
        elif pointe_active:
            # Only Pointe active: takes position 1 (moves to right)
            target_balise_x = self.queue_positions['balise']['x']  # 220px (hidden)
            target_pointe_x = self.queue_positions['pointe']['x']  # 260px (moves to position 1)
        else:
            # Neither active: reset to default positions
            target_balise_x = self.queue_positions['balise']['x']  # 220px
            target_pointe_x = self.queue_positions['pointe']['x']  # 260px
        
        # Smooth animation to target positions
        if pointe_active:
            # Animate Pointe to target position
            self.current_positions['pointe']['x'] = self.smooth_value(
                self.current_positions['pointe']['x'], target_pointe_x, self.animation_speed
            )
            # Apply bounce animation to Y position
            bounce_y = int(self.current_positions['pointe']['y'] + self.pointe_bounce_offset)
            self.pointe_container_icon.move(int(self.current_positions['pointe']['x']), bounce_y)
            self.pointe_count_label.move(int(self.current_positions['pointe']['x']), bounce_y)
        
        if balise_active:
            # Animate Balise to target position
            self.current_positions['balise']['x'] = self.smooth_value(
                self.current_positions['balise']['x'], target_balise_x, self.animation_speed
            )
            self.balise_container_icon.move(int(self.current_positions['balise']['x']), int(self.current_positions['balise']['y']))
            self.balise_count_label.move(int(self.current_positions['balise']['x']), int(self.current_positions['balise']['y']))
    
    def update_animations(self):
        """Update animations and visual effects"""
        self.animation_frame += 1
        
        # Show/hide overlay based on turn-based visibility and combat status
        if self.overlay_visible and self.in_combat:
            if not self.resource_container.isVisible():
                # Load saved positions BEFORE showing overlay
                self.load_container_position()
                # Force update to ensure position is applied
                self.resource_container.update()
                self.resource_container.show()
            else:
                # Already visible, just ensure it's shown
                self.resource_container.show()
            # Show draggable icons when overlay is visible
            self.precis_icon.show_icon()
        else:
            self.resource_container.hide()
            # Hide draggable icons when overlay is not visible
            self.precis_icon.hide_icon()
            self.precis_icon.set_icon_border(False)
            return  # Don't update anything else when overlay is not visible
        
        # Smooth transitions for values
        if self.smooth_transitions:
            self.current_affutage = self.smooth_value(self.current_affutage, self.affutage, 0.15)
            self.current_precision = self.smooth_value(self.current_precision, self.precision, 0.15)
        else:
            self.current_affutage = self.affutage
            self.current_precision = self.precision
        
        # Update progress bars with decimal values
        self.affutage_bar.setDecimalValue(self.current_affutage)
        self.precision_bar.setDecimalValue(self.current_precision)
        
        # Update bounce animation for Pointe affûtée
        self.update_pointe_bounce_animation()
        
        # Update queue animation first
        self.update_queue_animation()
        
        # Update Pointe affûtée icon (static, positioned in queue)
        if self.pointe_container_icon and self.pointe_count_label:
            if self.pointe_affutee_stacks > 0:
                self.pointe_container_icon.show()
                self.pointe_container_icon.raise_()  # Ensure icon is on top
                self.pointe_count_label.setText(f"{self.pointe_affutee_stacks}")
                self.pointe_count_label.show()
                self.pointe_count_label.raise_()  # Ensure label is on top
            else:
                self.pointe_container_icon.hide()
                self.pointe_count_label.hide()
        
        # Update Balise affûtée icon (static, positioned in queue)
        if self.balise_container_icon and self.balise_count_label:
            if self.balise_affutee_stacks > 0:
                self.balise_container_icon.show()
                self.balise_container_icon.raise_()  # Ensure icon is on top
                self.balise_count_label.setText(f"{self.balise_affutee_stacks}")
                self.balise_count_label.show()
                self.balise_count_label.raise_()  # Ensure label is on top
            else:
                self.balise_container_icon.hide()
                self.balise_count_label.hide()
        
        # Update bounce animations for draggable icons (Tir précis only)
        self.precis_icon.update_bounce_animation()
        
        # Add glow effect to precision bar when tir precis is active
        if self.tir_precis_active:
            pulse_intensity = 0.6 + 0.4 * abs(math.sin(self.animation_frame * 0.2))
            self.precision_bar.set_glow_effect(True, pulse_intensity)
            # Show Tir précis icon with pulsing border
            self.precis_icon.show_icon()
            # Create pulsing border effect on the icon itself
            pulse_alpha = int(128 + 127 * abs(math.sin(self.animation_frame * 0.3)))
            self.precis_icon.set_icon_border(True, pulse_alpha)
        else:
            self.precision_bar.set_glow_effect(False)
            # Hide Tir précis icon and remove border
            self.precis_icon.hide_icon()
            self.precis_icon.set_icon_border(False)
    
    def smooth_value(self, current, target, factor):
        """Smooth interpolation between current and target values"""
        return current + (target - current) * factor
    
    def mousePressEvent(self, event):
        """Handle mouse press for dragging the resource container"""
        if event.button() == Qt.MouseButton.LeftButton and not self.positions_locked:
            self.drag_position = event.globalPosition().toPoint() - self.resource_container.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging the resource container"""
        if event.buttons() == Qt.MouseButton.LeftButton and not self.positions_locked:
            new_pos = event.globalPosition().toPoint() - self.drag_position
            self.resource_container.move(new_pos)
            # Auto-save position when dragging
            self.auto_save_positions()
            event.accept()
    
    def parse_log_line(self, line):
        """Parse a log line and extract resource information"""
        # Debug mode - print parsed lines
        if self.debug_mode:
            print(f"DEBUG: Parsing line: {line.strip()}")
        
        # Check for Sac à patate combat start (check this FIRST - works on any line type)
        if "Sac à patate" in line and ("Quand tu auras fini de me frapper" in line or "abandonner" in line or "Abandonne le combat" in line):
            self.is_sac_patate_combat = True
            if self.debug_mode:
                print("DEBUG: Sac à patate combat detected")
        
        # Check if it's a combat line for other processing
        if "[Information (combat)]" not in line:
            return
        
        # Check for combat start
        if "lance le sort" in line:
            self.in_combat = True
            
            # Extract player and spell info for turn-based visibility
            spell_match = re.search(r'\[Information \(combat\)\] ([^:]+)[:\s]+lance le sort ([^(]+)', line)
            if spell_match:
                caster_name = spell_match.group(1).strip()
                spell_name = spell_match.group(2).strip()
                
                # Track the last spell caster for turn end detection
                self.last_spell_caster = caster_name
                
                # Check if this is a Cra spell
                is_cra_spell = any(cra_spell in spell_name for cra_spell in self.cra_spells)
                
                if is_cra_spell:
                    # Set tracked player on first Cra spell cast
                    if self.tracked_player_name is None:
                        self.tracked_player_name = caster_name
                        print(f"DEBUG: Cra player tracked: {caster_name}")
                    
                    # Show overlay if the tracked Cra casts a spell
                    if caster_name == self.tracked_player_name:
                        self.is_cra_turn = True
                        self.overlay_visible = True
                        print(f"DEBUG: Cra turn started - overlay shown for '{spell_name}'")
                else:
                    # Check if this is the tracked player casting a non-Cra spell
                    if caster_name == self.tracked_player_name:
                        print(f"DEBUG: Tracked Cra '{caster_name}' cast non-Cra spell '{spell_name}' - overlay remains visible")
        
        # Turn end detection
        if "secondes reportées pour le tour suivant" in line:
            print(f"DEBUG: Turn end detected in log: {line.strip()}")
            
            # Determine which player's turn is ending
            turn_owner = self.last_spell_caster
            print(f"DEBUG: Turn end detected - last spell caster was: '{turn_owner}' (tracked: '{self.tracked_player_name}')")
            
            if turn_owner and self.tracked_player_name and turn_owner == self.tracked_player_name:
                # The tracked Cra is passing turn - hide overlay
                self.is_cra_turn = False
                self.overlay_visible = False
                print(f"DEBUG: Cra turn ended - overlay hidden (turn passed by {turn_owner})")
            elif turn_owner:
                # Different player is passing turn - overlay remains as is
                print(f"DEBUG: Turn passed by different player '{turn_owner}' - overlay remains {'visible' if self.overlay_visible else 'hidden'}")
            else:
                # No recent spell caster - assume it's the tracked player's turn ending
                print(f"DEBUG: No recent spell caster - assuming tracked Cra's turn ending")
                if self.tracked_player_name:
                    self.is_cra_turn = False
                    self.overlay_visible = False
                    print(f"DEBUG: Cra turn ended - overlay hidden (assumed turn end)")
                else:
                    print(f"DEBUG: No tracked player set - cannot determine turn owner")
        
        # Combat end detection - improved logic
        combat_ended = False
        
        # Normal combat end: "Combat terminé, cliquez ici pour rouvrir l'écran de fin de combat."
        if "Combat terminé, cliquez ici pour rouvrir l'écran de fin de combat." in line:
            combat_ended = True
            if self.debug_mode:
                print("DEBUG: Normal combat ended (Combat terminé, cliquez ici...)")
        
        # Exception: KO/hors-combat only triggers end for Sac à patate combat
        elif (re.search(r'est hors-combat', line) or re.search(r'est KO !', line)) and self.is_sac_patate_combat:
            combat_ended = True
            if self.debug_mode:
                print("DEBUG: Sac à patate combat ended (KO/hors-combat)")
        
        # Debug KO detection
        if self.debug_mode and ("est hors-combat" in line or "est KO !" in line):
            print(f"DEBUG: KO detected in line: {line.strip()}")
            print(f"DEBUG: is_sac_patate_combat = {self.is_sac_patate_combat}")
            print(f"DEBUG: in_combat = {self.in_combat}")
        
        if combat_ended:
            self.in_combat = False
            self.is_sac_patate_combat = False  # Reset Sac à patate flag
            # Reset turn-based visibility system
            self.is_cra_turn = False
            self.overlay_visible = False
            self.tracked_player_name = None
            self.last_spell_caster = None
            # Reset resources when combat ends
            self.affutage = 0
            self.precision = 0
            self.pointe_affutee_stacks = 0
            self.balise_affutee_stacks = 0  # Reset Balise affûtée stacks
            self.tir_precis_active = False
            if self.debug_mode:
                print("DEBUG: Combat ended, resources reset")
        
        # Parse Affûtage current value
        affutage_match = re.search(r'Affûtage \(\+(\d+) Niv\.\)', line)
        if affutage_match:
            new_affutage = int(affutage_match.group(1))
            if self.debug_mode:
                print(f"DEBUG: Affûtage changed from {self.affutage} to {new_affutage}")
            
            # Handle Affûtage reaching 100+ - gain stacks and carry over excess
            if new_affutage >= 100:
                stacks_gained = new_affutage // 100
                if self.pointe_affutee_stacks < 3:
                    stacks_to_add = min(stacks_gained, 3 - self.pointe_affutee_stacks)
                    self.pointe_affutee_stacks += stacks_to_add
                    if self.debug_mode:
                        print(f"DEBUG: Affûtage reached {new_affutage}, gained {stacks_to_add} Pointe affûtée stack(s), total: {self.pointe_affutee_stacks}")
                
                # Add Balise affûtée stacks (same as Pointe affûtée, max 3)
                if stacks_gained > 0:
                    if self.balise_affutee_stacks < 3:
                        stacks_to_add = min(stacks_gained, 3 - self.balise_affutee_stacks)
                        self.balise_affutee_stacks += stacks_to_add
                        if self.debug_mode:
                            print(f"DEBUG: Affûtage reached {new_affutage}, gained {stacks_to_add} Balise affûtée stack(s), total: {self.balise_affutee_stacks}")
                
                self.affutage = new_affutage % 100
                if self.debug_mode:
                    print(f"DEBUG: Affûtage set to {self.affutage} (remainder after gaining stacks)")
            else:
                self.affutage = new_affutage
        
        # Parse Précision current value
        precision_match = re.search(r'Précision \(\+(\d+) Niv\.\)', line)
        if precision_match:
            new_precision = int(precision_match.group(1))
            if self.debug_mode:
                print(f"DEBUG: Précision changed from {self.precision} to {new_precision}")
            self.precision = new_precision
        
        # Parse Pointe affûtée consumption
        if "Consomme Pointe affûtée" in line:
            if self.pointe_affutee_stacks > 0:
                self.pointe_affutee_stacks -= 1
                if self.debug_mode:
                    print(f"DEBUG: Consumed Pointe affûtée stack, remaining: {self.pointe_affutee_stacks}")
        
        # Parse Balise affûtée consumption (specific spells)
        if "lance le sort" in line:
            if "Balise de destruction" in line or "Balise d'alignement" in line or "Balise de contact" in line:
                if self.balise_affutee_stacks > 0:
                    self.balise_affutee_stacks -= 1
                    if self.debug_mode:
                        print(f"DEBUG: Consumed Balise affûtée stack (Balise spell cast), remaining: {self.balise_affutee_stacks}")
        
        # Parse Tir précis buff activation
        if "Tir précis (Niv." in line:
            self.tir_precis_active = True
            if self.debug_mode:
                print("DEBUG: Tir précis buff activated")
        
        # Parse Tir précis buff removal
        elif "n'est plus sous l'emprise de 'Tir précis'" in line:
            self.tir_precis_active = False
            if self.debug_mode:
                print("DEBUG: Tir précis buff removed")
        
        # Parse Précision buff removal - reset precision to 0
        if "n'est plus sous l'emprise de 'Précision'" in line:
            self.precision = 0
            # Reset bar maximum back to 300 for normal operation
            self.precision_bar.setMaxValue(300)
            if self.debug_mode:
                print("DEBUG: Précision buff removed - precision reset to 0")
        
        # Parse spell consumption with Tir précis active
        if self.tir_precis_active and "lance le sort" in line and "Tir précis" not in line:
            spell_consumption = 0
            
            if "Flèche criblante" in line:
                spell_consumption = 60
            elif "Flèche fulminante" in line:
                spell_consumption = 45
            elif "Flèche d'immolation" in line:
                spell_consumption = 30
            elif "Flèche enflammée" in line:
                spell_consumption = 60
            elif "Flèche Ardente" in line:
                spell_consumption = 30
            elif "Flèche explosive" in line:
                spell_consumption = 90
            elif "Flèche cinglante" in line:
                spell_consumption = 45
            elif "Flèche perçante" in line:
                spell_consumption = 75
            elif "Flèche destructrice" in line:
                spell_consumption = 105
            elif "Flèche chercheuse" in line:
                spell_consumption = 30
            elif "Flèche de recul" in line:
                spell_consumption = 60
            elif "Flèche tempête" in line:
                spell_consumption = 45
            elif "Flèche harcelante" in line:
                spell_consumption = 45
            elif "Flèche statique" in line:
                spell_consumption = 90
            else:
                spell_consumption = 30
            
            if spell_consumption > 0:
                self.precision = max(self.precision - spell_consumption, 0)
                if self.debug_mode:
                    print(f"DEBUG: Consumed {spell_consumption} Précision with Tir précis, remaining: {self.precision}")
        
        # Handle maximum precision reached - detect talent "Esprit affûté"
        # Only cap at 200 if the precision gain was NOT +300 (normal case)
        if "Valeur maximale de Précision atteinte !" in line and self.precision > 200:
            # Check if this was after a +300 gain (normal case - don't cap)
            # We need to look at recent precision gains to determine this
            if not self._was_recent_300_gain():
                # Player has "Esprit affûté" talent - cap precision at 200
                self.precision = 200
                self.precision_bar.setMaxValue(200)
                self.precision_bar.setValue(200)  # Force display to 200/200
                self.has_esprit_affute = True  # Mark that player has this talent
                if self.debug_mode:
                    print(f"DEBUG: Talent 'Esprit affûté' détecté - Précision limitée à 200")
            else:
                if self.debug_mode:
                    print(f"DEBUG: Gain de +300 normal détecté - pas de limitation à 200")
        
        # Track precision gains for talent detection
        if "Précision" in line and "+" in line:
            # Extract precision gain value
            precision_match = re.search(r'Précision.*?(\+?\d+)', line)
            if precision_match:
                try:
                    precision_gain = int(precision_match.group(1))
                    # Store recent precision gain for talent detection
                    self._store_precision_gain(precision_gain)
                    
                    if precision_gain > 200 and "Valeur maximale de Précision atteinte !" not in line:
                        # Player gained > 200 precision without cap message - talent might be removed
                        if self.has_esprit_affute:
                            self.has_esprit_affute = False
                            self.precision_bar.setMaxValue(300)  # Reset to normal max
                            if self.debug_mode:
                                print(f"DEBUG: Talent 'Esprit affûté' semble retiré - limite Précision remise à 300")
                except ValueError:
                    pass
    
    def _store_precision_gain(self, gain_value):
        """Store recent precision gain for talent detection"""
        self.recent_precision_gains.append(gain_value)
        # Keep only the last N gains
        if len(self.recent_precision_gains) > self.max_recent_gains:
            self.recent_precision_gains.pop(0)
    
    def _was_recent_300_gain(self):
        """Check if the most recent precision gain was +300"""
        if not self.recent_precision_gains:
            return False
        return self.recent_precision_gains[-1] == 300
    
    def start_monitoring(self):
        """Start the monitoring thread"""
        self.monitor_thread = LogMonitorThread(str(self.log_file))
        self.monitor_thread.log_updated.connect(self.parse_log_line)
        self.monitor_thread.start()
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Save positions before closing
        self.save_positions()
        
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.stop_monitoring()
            self.monitor_thread.wait()
        event.accept()

def main():
    app = QApplication(sys.argv)
    
    # Check if running in hidden mode (from launcher)
    hidden_mode = "--hidden" in sys.argv
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show window
    window = WakfuResourceTrackerFullscreen(hidden_mode=hidden_mode)
    
    # Only show window if not in hidden mode
    if not hidden_mode:
        window.show()
    else:
        # In hidden mode, show window but minimize it
        window.show()
        window.showMinimized()
    
    # Run application
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
