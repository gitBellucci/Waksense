#!/usr/bin/env python3
"""
Wakfu Iop Class Resource Tracker - Full Screen Overlay System
Full-screen transparent overlay with draggable icons anywhere on screen
Tracks Concentration and Courroux resources in real-time from chat logs
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
from PyQt6.QtWidgets import QGraphicsOpacityEffect

class LogMonitorThread(QThread):
    """Thread for monitoring log file"""
    log_updated = pyqtSignal(str)
    
    def __init__(self, log_file_path):
        super().__init__()
        self.log_file = Path(log_file_path)
        self.monitoring = True
        self.last_position = 0
        
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
                                    # Debug: Log when we emit a line
                                    if "lance le sort" in line:
                                        timestamp = time.strftime("%H:%M:%S")
                                        print(f"DEBUG [{timestamp}]: LogMonitor emitting spell line: {line[:80]}...")
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
    
    def get_resource_color(self, text):
        """Get color based on resource type"""
        if "PA" in text:
            return QColor(0, 150, 255)  # Bright blue for PA
        elif "PM" in text:
            return QColor(0, 128, 0)   # Green for PM
        elif "PW" in text:
            return QColor(0, 206, 209) # Turquoise for PW
        else:
            return QColor(255, 255, 255)  # Default white
    
    def paintEvent(self, event):
        """Custom paint event to draw outlined text with colored resource types"""
        if not self.text_to_draw:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Parse text to separate number from resource type
        text = self.text_to_draw
        number_part = ""
        resource_part = ""
        
        # Extract number and resource type (e.g., "1PA" -> "1" and "PA")
        for i, char in enumerate(text):
            if char.isdigit():
                number_part += char
            else:
                resource_part = text[i:]
                break
        
        # Font sizes - make them closer in size for better alignment
        font_size_large = 9  # Larger font for numbers
        font_size_small = 8  # Smaller font for resource types (increased from 7)
        font_large = QFont('Segoe UI', font_size_large, QFont.Weight.Bold)
        font_small = QFont('Segoe UI', font_size_small, QFont.Weight.Bold)
        
        # Calculate metrics for both fonts
        painter.setFont(font_large)
        metrics_large = painter.fontMetrics()
        painter.setFont(font_small)
        metrics_small = painter.fontMetrics()
        
        # Calculate total width of the entire text
        number_width = metrics_large.boundingRect(number_part).width() if number_part else 0
        resource_width = metrics_small.boundingRect(resource_part).width() if resource_part else 0
        total_width = number_width + resource_width
        
        # Center the entire text block
        start_x = (self.width() - total_width) // 2
        y = (self.height() + metrics_large.height()) // 2
        
        # Draw number part (larger font)
        if number_part:
            painter.setFont(font_large)
            current_x = start_x
            
            # Draw black outline for number
            painter.setPen(QPen(QColor(0, 0, 0, 255), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx != 0 or dy != 0:
                        painter.drawText(current_x + dx, y + dy, number_part)
            
            # Draw number in white
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.drawText(current_x, y, number_part)
        
        # Draw resource part (smaller font) - positioned right after the number with small gap
        if resource_part:
            painter.setFont(font_small)
            # Position resource part right after the number with a small gap for clarity
            resource_x = start_x + number_width + 1  # Add 1 pixel gap
            
            # Draw black outline for resource
            painter.setPen(QPen(QColor(0, 0, 0, 255), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx != 0 or dy != 0:
                        painter.drawText(resource_x + dx, y + dy, resource_part)
            
            # Draw resource part in appropriate color
            resource_color = self.get_resource_color(resource_part)
            painter.setPen(QPen(resource_color, 1))
            painter.drawText(resource_x, y, resource_part)


class ComboStepWidget(OutlinedLabel):
    """Widget for individual combo step with animation support - uses OutlinedLabel styling"""
    
    def __init__(self, resource_type, parent=None):
        super().__init__(parent)
        self.resource_type = resource_type
        self.is_completed = False
        self.is_next_step = False
        self.animation_alpha = 0.0
        self.pulse_animation = 0.0
        self.fade_alpha = 1.0
        self.slide_offset = 0
        self.is_animating_out = False
        
        self.setFixedSize(32, 32)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                background-color: rgba(50, 50, 50, 100);
                border: 1px solid rgba(100, 100, 100, 150);
                border-radius: 3px;
            }
        """)
        
        # Set the text to display (this will trigger the OutlinedLabel paintEvent)
        self.setText(resource_type)
    
    def set_completed(self, completed=True):
        """Mark step as completed with animation"""
        self.is_completed = completed
        if completed:
            self.setStyleSheet("""
                QLabel {
                    background-color: rgba(0, 200, 0, 200);
                    border: 2px solid rgba(0, 255, 0, 255);
                    border-radius: 3px;
                }
            """)
        else:
            self.setStyleSheet("""
                QLabel {
                    background-color: rgba(50, 50, 50, 100);
                    border: 1px solid rgba(100, 100, 100, 150);
                    border-radius: 3px;
                }
            """)
    
    def set_next_step(self, is_next=True):
        """Mark as next step with pulsing animation"""
        self.is_next_step = is_next
        if is_next:
            self.setStyleSheet("""
                QLabel {
                    background-color: rgba(255, 165, 0, 200);
                    border: 2px solid rgba(255, 200, 0, 255);
                    border-radius: 3px;
                }
            """)
        else:
            self.setStyleSheet("""
                QLabel {
                    background-color: rgba(50, 50, 50, 100);
                    border: 1px solid rgba(100, 100, 100, 150);
                    border-radius: 3px;
                }
            """)
    
    def start_fade_out_animation(self):
        """Start fade out and slide up animation"""
        self.is_animating_out = True
        self.fade_alpha = 1.0
        self.slide_offset = 0
    
    def update_animation(self):
        """Update fade out and slide animation"""
        if self.is_animating_out:
            # Fade out
            self.fade_alpha -= 0.15  # Same speed as timeline
            if self.fade_alpha < 0.0:
                self.fade_alpha = 0.0
            
            # Slide up
            self.slide_offset -= 4  # Same speed as timeline
            if self.slide_offset < -20:  # Slide up 20 pixels
                self.slide_offset = -20
            
            # Apply opacity effect
            if not hasattr(self, '_opacity'):
                self._opacity = QGraphicsOpacityEffect()
                self.setGraphicsEffect(self._opacity)
            self._opacity.setOpacity(self.fade_alpha)
            
            # Apply slide offset
            current_pos = self.pos()
            self.move(current_pos.x(), current_pos.y() + self.slide_offset)
            
            # Check if animation is complete
            if self.fade_alpha <= 0.0 and self.slide_offset <= -20:
                self.is_animating_out = False
                self.hide()  # Hide when animation is complete

class ComboColumnWidget(QWidget):
    """Widget for a complete combo column"""
    
    def __init__(self, combo_name, combo_data, parent=None):
        super().__init__(parent)
        self.combo_name = combo_name
        self.combo_data = combo_data
        self.step_widgets = []
        self.current_step = 0
        self.pulse_animation = 0.0
        self.is_ready_to_complete = False
        self.column_slide_offset = 0  # For column sliding up animation
        self.steps_completed_count = 0  # Track how many steps have been completed
        self.reset_slide_offset = 0  # For reset slide-down animation
        self.is_resetting = False  # Flag for reset animation state
        
        self.setFixedSize(40, 160)  # Increased height to accommodate larger step widgets
        
        # Create layout with fixed spacing to ensure alignment
        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)  # Align to top instead of center
        
        # Create combo icon at top - make it square
        self.combo_icon = QLabel()
        self.combo_icon.setFixedSize(36, 36)  # Square instead of rectangle
        self.combo_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.combo_icon.setScaledContents(True)
        
        # Load combo icon
        # Get the directory where the script is located (works for both script and executable)
        if getattr(sys, 'frozen', False):
            # Running as executable - look in the bundled Iop/img folder
            base_dir = Path(sys._MEIPASS) / "Iop"
        else:
            # Running as script
            base_dir = Path(__file__).parent
        icon_path = base_dir / "img" / combo_data["icon"]
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path))
            self.combo_icon.setPixmap(pixmap.scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self.combo_icon.setText(combo_name[:3])  # Fallback text
        
        layout.addWidget(self.combo_icon)
        
        # Create step widgets - all combos have 4 slots for perfect alignment
        # Create exactly 4 step widgets for all combos to ensure alignment
        for i in range(4):
            if i < len(combo_data["steps"]):
                step_widget = ComboStepWidget(combo_data["steps"][i])
            else:
                # Create invisible spacer widget for combos with fewer than 4 steps
                step_widget = QLabel()
                step_widget.setFixedSize(32, 32)  # Same size as step widgets
                step_widget.setStyleSheet("background-color: transparent; border: none;")  # Completely invisible
                step_widget.hide()  # Hide the widget completely
            self.step_widgets.append(step_widget)
            layout.addWidget(step_widget)
        
        self.setLayout(layout)
        
        # Set background
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 30, 30, 150);
                border: 1px solid rgba(100, 100, 100, 100);
                border-radius: 5px;
            }
        """)
    
    def update_progress(self, current_step):
        """Update the visual progress of the combo"""
        # Check if we have new completed steps
        new_completed_count = current_step
        if new_completed_count > self.steps_completed_count:
            # New step completed - trigger column slide up
            self.steps_completed_count = new_completed_count
            self.column_slide_offset = 60  # Start slide animation from 60px offset (more dramatic)
            print(f"DEBUG: Combo column slide animation started - offset: {self.column_slide_offset}")
        
        self.current_step = current_step
        
        # Check if combo is ready to complete (only one step left)
        self.is_ready_to_complete = (current_step == len(self.combo_data["steps"]) - 1)
        
        for i, step_widget in enumerate(self.step_widgets):
            # Only process actual ComboStepWidget instances (not spacer QLabels)
            if isinstance(step_widget, ComboStepWidget) and i < len(self.combo_data["steps"]):
                if i < current_step:
                    # Completed steps - start fade out animation
                    if not step_widget.is_animating_out:
                        step_widget.start_fade_out_animation()
                elif i == current_step:
                    # Next step (highlighted)
                    step_widget.set_completed(False)
                    step_widget.set_next_step(True)
                else:
                    # Future steps
                    step_widget.set_completed(False)
                    step_widget.set_next_step(False)
    
    def update_animation(self):
        """Update pulsing animation for ready-to-complete combos"""
        if self.is_ready_to_complete:
            self.pulse_animation += 0.1
            # Create pulsing glow effect
            pulse_intensity = (math.sin(self.pulse_animation) + 1) / 2  # 0 to 1
            glow_alpha = int(100 + (155 * pulse_intensity))  # 100 to 255
            
            self.setStyleSheet(f"""
                QWidget {{
                    background-color: rgba(30, 30, 30, {glow_alpha});
                    border: 2px solid rgba(255, 215, 0, {glow_alpha});
                    border-radius: 5px;
                }}
            """)
        else:
            # Normal styling when not ready to complete
            self.setStyleSheet("""
                QWidget {
                    background-color: rgba(30, 30, 30, 150);
                    border: 1px solid rgba(100, 100, 100, 100);
                    border-radius: 5px;
                }
            """)
        
        # Update step animations
        for step_widget in self.step_widgets:
            if isinstance(step_widget, ComboStepWidget):
                step_widget.update_animation()
        
        # Update column slide animation with easing
        if self.column_slide_offset > 0:  # Start sliding up from positive offset
            # Easing effect: faster at start, slower at end
            ease_factor = (self.column_slide_offset / 60.0) ** 0.7  # Ease-out curve
            self.column_slide_offset -= 1.8 * ease_factor  # Variable speed with easing
            if self.column_slide_offset <= 0:
                self.column_slide_offset = 0  # Stop at 0 when animation completes
                print(f"DEBUG: Column slide animation completed")
            # Debug output every 20 frames to reduce spam (only when actually animating)
            elif int(self.column_slide_offset) % 20 == 0 and self.column_slide_offset > 20:
                print(f"DEBUG: Column slide animation - offset: {self.column_slide_offset:.1f}")
        
        # Update reset slide-down animation
        if self.is_resetting and self.reset_slide_offset > 0:
            # Easing effect: faster at start, slower at end
            ease_factor = (self.reset_slide_offset / 80.0) ** 0.8  # Ease-out curve for reset
            self.reset_slide_offset -= 2.2 * ease_factor  # Variable speed with easing
            if self.reset_slide_offset < 0:
                self.reset_slide_offset = 0  # Stop at 0 when animation completes
                self.is_resetting = False  # Mark reset animation as complete
                print(f"DEBUG: Reset slide-down animation completed")
            # Debug output every 25 frames to reduce spam (only when actually animating)
            elif int(self.reset_slide_offset) % 25 == 0 and self.reset_slide_offset > 25:
                print(f"DEBUG: Reset slide-down animation - offset: {self.reset_slide_offset:.1f}")
        
        # Apply column slide offset to all visible steps
        if self.column_slide_offset > 0:  # Apply positive offset (steps appear lower initially)
            # Get the base position of this combo column
            base_x, base_y = self.pos().x(), self.pos().y()
            combo_icon_height = 36  # Height of combo icon
            step_spacing = 36  # Height of each step (32px + 4px spacing)
            
            for i, step_widget in enumerate(self.step_widgets):
                if isinstance(step_widget, ComboStepWidget) and i < len(self.combo_data["steps"]):
                    # Only slide up steps that are not animating out
                    if not step_widget.is_animating_out:
                        # Calculate the base Y position for this step (relative to combo column)
                        step_base_y = base_y + combo_icon_height + (i * step_spacing) + 4  # +4 for margins
                        new_y = int(step_base_y + self.column_slide_offset)
                        step_widget.move(base_x + 2, new_y)  # +2 for margins
                        # Debug output for positioning (reduced frequency, only when actually animating)
                        if i == 0 and int(self.column_slide_offset) % 10 == 0 and self.column_slide_offset > 10:
                            print(f"DEBUG: Column slide - step {i} moved to y={new_y} (offset: {self.column_slide_offset:.1f})")
        
        # Apply reset slide-down offset to all visible steps
        elif self.is_resetting and self.reset_slide_offset > 0:
            # Get the base position of this combo column
            base_x, base_y = self.pos().x(), self.pos().y()
            combo_icon_height = 36  # Height of combo icon
            step_spacing = 36  # Height of each step (32px + 4px spacing)
            
            for i, step_widget in enumerate(self.step_widgets):
                if isinstance(step_widget, ComboStepWidget) and i < len(self.combo_data["steps"]):
                    # Calculate the base Y position for this step (relative to combo column)
                    step_base_y = base_y + combo_icon_height + (i * step_spacing) + 4  # +4 for margins
                    # Apply negative offset (steps appear higher initially, then slide down)
                    new_y = int(step_base_y - self.reset_slide_offset)
                    step_widget.move(base_x + 2, new_y)  # +2 for margins
                    # Debug output for positioning (reduced frequency, only when actually animating)
                    if i == 0 and int(self.reset_slide_offset) % 15 == 0 and self.reset_slide_offset > 15:
                        print(f"DEBUG: Reset slide - step {i} moved to y={new_y} (offset: {self.reset_slide_offset:.1f})")
    
    def reset(self):
        """Reset combo progress with slide-down animation"""
        self.current_step = 0
        self.is_ready_to_complete = False
        self.pulse_animation = 0.0
        self.column_slide_offset = 0  # Reset column slide
        self.steps_completed_count = 0  # Reset completed count
        
        # Start slide-down animation for all steps
        self.reset_slide_offset = 80  # Start steps 80px above their normal positions
        self.is_resetting = True  # Flag to indicate reset animation is active
        print(f"DEBUG: Combo column reset slide-down animation started - offset: {self.reset_slide_offset}")
        
        # Reset all step animations
        for step_widget in self.step_widgets:
            if isinstance(step_widget, ComboStepWidget):
                step_widget.is_animating_out = False
                step_widget.fade_alpha = 1.0
                step_widget.slide_offset = 0
                step_widget.show()  # Show all steps again
                if hasattr(step_widget, '_opacity'):
                    step_widget._opacity.setOpacity(1.0)
        
        self.update_progress(0)
        self.update_animation()
    
    def reset_silent(self):
        """Reset combo progress without slide animation"""
        self.current_step = 0
        self.is_ready_to_complete = False
        self.pulse_animation = 0.0
        self.column_slide_offset = 0  # Reset column slide
        self.steps_completed_count = 0  # Reset completed count
        self.reset_slide_offset = 0  # No reset animation
        self.is_resetting = False  # No reset animation
        
        # Reset all step animations
        for step_widget in self.step_widgets:
            if isinstance(step_widget, ComboStepWidget):
                step_widget.is_animating_out = False
                step_widget.fade_alpha = 1.0
                step_widget.slide_offset = 0
                step_widget.show()  # Show all steps again
                if hasattr(step_widget, '_opacity'):
                    step_widget._opacity.setOpacity(1.0)
        
        self.update_progress(0)
        self.update_animation()

class EgareIcon(QLabel):
    """Custom égaré icon with fade animation support"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.fade_alpha = 0.0
        self._pixmap = None
    
    def setFadeAlpha(self, alpha):
        """Set the fade alpha value (0.0 to 1.0)"""
        self.fade_alpha = max(0.0, min(1.0, alpha))
        self.update()  # Trigger repaint
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Set opacity based on fade alpha
        painter.setOpacity(self.fade_alpha)
        
        # Draw the icon itself
        if self._pixmap:
            painter.drawPixmap(3, 3, self._pixmap)
        
        painter.end()
    
    def setPixmap(self, pixmap):
        """Override to store pixmap for custom drawing"""
        self._pixmap = pixmap
        super().setPixmap(pixmap)


class PreparationIcon(QLabel):
    """Custom préparation icon with fade animation support"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.fade_alpha = 0.0
        self._pixmap = None
    
    def setFadeAlpha(self, alpha):
        """Set the fade alpha value (0.0 to 1.0)"""
        self.fade_alpha = max(0.0, min(1.0, alpha))
        self.update()  # Trigger repaint
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Set opacity based on fade alpha
        painter.setOpacity(self.fade_alpha)
        
        # Draw the icon itself
        if self._pixmap:
            painter.drawPixmap(3, 3, self._pixmap)
        
        painter.end()
    
    def setPixmap(self, pixmap):
        """Override to store pixmap for custom drawing"""
        self._pixmap = pixmap
        super().setPixmap(pixmap)


class ConcentrationProgressBar(QProgressBar):
    """Custom progress bar for Concentration with modern animated gradient"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.decimal_value = 0
        self.target_value = 0
        self.smooth_value = 0
        self.smooth_transitions = True
        self.animation_frame = 0
        self.showing_red = False
        self.red_animation_frames = 0
        
        # Smooth transition variables
        self.transition_speed = 0.12  # How fast the bar moves toward target (smooth for high FPS)
        self.is_transitioning = False
        
        # Separate high-frequency timer for progress bar only
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.update_animation)
        self.progress_timer.start(16)  # ~60 FPS for smooth progress bar only
        
        # Animation variables for gradient progression
        self.gradient_animation_speed = 0.02
        self.gradient_offset = 0
        self.gradient_phase = 0
        
        self.setFixedHeight(24)
        self.setFixedWidth(250)
        self.setRange(0, 100)
        self.setValue(0)
        
        # Hide default text
        self.setTextVisible(False)
        
        # Ultra minimal styling (like Crâ)
        self.setStyleSheet(self.get_minimal_style())
        
    def setValue(self, value):
        """Override setValue to handle decimal values and red animation"""
        self.target_value = float(value)
        self.is_transitioning = True
        
        # Check if we're reaching 100 (should trigger red animation)
        if self.target_value >= 100 and not self.showing_red:
            self.showing_red = True
            self.red_animation_frames = 30  # Show red for 30 frames
        
        super().setValue(int(self.target_value))
    
    def update_animation(self):
        """Update gradient animation and smooth value transitions"""
        # Update gradient animation (back to original speed)
        self.gradient_phase += self.gradient_animation_speed
        self.gradient_offset = math.sin(self.gradient_phase) * 0.3 + 0.7  # Oscillate between 0.4 and 1.0
        
        # Handle smooth value transitions
        if self.is_transitioning:
            # Calculate the difference between current and target
            difference = self.target_value - self.decimal_value
            
            # If we're close enough to the target, snap to it
            if abs(difference) < 0.1:
                self.decimal_value = self.target_value
                self.is_transitioning = False
            else:
                # Move toward target at the specified speed
                self.decimal_value += difference * self.transition_speed
        
        self.update()
    
    
    def paintEvent(self, event):
        """Custom paint event with modern animated gradient and text"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Calculate progress percentage
        progress = self.decimal_value / 100.0
        bar_width = int(self.width() * progress)
        
        # Create animated gradient based on progress
        gradient = QLinearGradient(0, 0, self.width(), 0)
        
        if progress < 0.3:
            # Low concentration: Cool blue tones
            gradient.setColorAt(0, QColor(64, 181, 246, int(200 * self.gradient_offset)))      # Light blue
            gradient.setColorAt(1, QColor(33, 150, 243, int(255 * self.gradient_offset)))     # Blue
        elif progress < 0.7:
            # Medium concentration: Blue to cyan transition
            gradient.setColorAt(0, QColor(33, 150, 243, int(220 * self.gradient_offset)))     # Blue
            gradient.setColorAt(0.5, QColor(0, 188, 212, int(240 * self.gradient_offset)))    # Cyan
            gradient.setColorAt(1, QColor(0, 172, 193, int(255 * self.gradient_offset)))     # Dark cyan
        else:
            # High concentration: Cyan to electric blue
            gradient.setColorAt(0, QColor(0, 172, 193, int(240 * self.gradient_offset)))     # Dark cyan
            gradient.setColorAt(0.5, QColor(3, 169, 244, int(255 * self.gradient_offset)))   # Electric blue
            gradient.setColorAt(1, QColor(0, 123, 255, int(255 * self.gradient_offset)))     # Bright blue
        
        # Draw background
        painter.fillRect(0, 0, self.width(), self.height(), QColor(0, 0, 0, 77))  # Semi-transparent black
        
        # Draw animated progress bar
        if bar_width > 0:
            painter.fillRect(0, 0, bar_width, self.height(), QBrush(gradient))
        
        # Draw border
        painter.setPen(QPen(QColor(51, 51, 51, 255), 2))
        painter.drawRect(0, 0, self.width()-1, self.height()-1)
        
        # Set font
        font = QFont('Segoe UI', 16, QFont.Weight.Bold)
        painter.setFont(font)
        
        # Get text - use decimal_value for accurate display
        text = f"{round(self.decimal_value)}/100"
        
        # Get text metrics
        metrics = painter.fontMetrics()
        text_rect = metrics.boundingRect(text)
        
        # Center the text
        x = (self.width() - text_rect.width()) // 2
        y = (self.height() + text_rect.height()) // 2 - metrics.descent()
        
        # Draw black outline (border)
        painter.setPen(QPen(QColor(0, 0, 0), 3))
        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                if dx != 0 or dy != 0:
                    painter.drawText(x + dx, y + dy, text)
        
        # Draw white text
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.drawText(x, y, text)
        
        painter.end()
        
    def get_minimal_style(self):
        """Get transparent style since we're using custom painting"""
        return """
            QProgressBar {
                border: none;
                background-color: transparent;
                text-align: center;
            }
        """

class DraggableIcon(QLabel):
    """Draggable icon widget"""
    
    def __init__(self, icon_path, icon_size=64, parent=None):
        super().__init__(parent)
        self.icon_path = icon_path
        self.icon_size = icon_size
        self.is_locked = False
        self.drag_start_position = QPoint()
        
        self.setFixedSize(icon_size, icon_size)
        self.setScaledContents(True)
        
        # Load and set icon
        if Path(icon_path).exists():
            pixmap = QPixmap(icon_path)
            self.setPixmap(pixmap.scaled(icon_size, icon_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            print(f"Warning: Icon not found at {icon_path}")
            # Create a placeholder
            self.setStyleSheet("background-color: rgba(100, 100, 100, 100); border: 2px solid white;")
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Initially hidden
        self.hide()
    
    def mousePressEvent(self, event):
        """Handle mouse press for dragging"""
        if event.button() == Qt.MouseButton.LeftButton and not self.is_locked:
            self.drag_start_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging"""
        if event.buttons() == Qt.MouseButton.LeftButton and not self.is_locked:
            self.move(event.globalPosition().toPoint() - self.drag_start_position)
    
    def show_icon(self):
        """Show the icon"""
        self.show()
    
    def hide_icon(self):
        """Hide the icon"""
        self.hide()

class WakfuIopResourceTracker(QMainWindow):
    """Main window for Iop resource tracker"""
    
    def __init__(self, hidden_mode=False):
        super().__init__()
        
        # Store hidden mode
        self.hidden_mode = hidden_mode
        
        # Resource tracking variables
        self.concentration = 0
        self.courroux = 0
        self.puissance = 0
        self.egare = False
        self.preparation = 0
        self.current_concentration = 0
        self.current_courroux = 0
        self.current_puissance = 0
        self.current_egare = False
        self.current_preparation = 0
        
        # Préparation Damage Confirmation System
        self.pending_preparation_loss = False  # True when waiting for damage confirmation
        self.preparation_loss_caster = None  # Player who cast spell that should remove préparation
        self.preparation_loss_spell = None  # Spell that should remove préparation
        self.in_combat = False
        
        # Player tracking
        self.tracked_player_name = None  # Track the player we're monitoring
        
        # Combat detection
        self.is_sac_patate_combat = False  # Track if we're fighting Sac à patate
        
        # Turn-based visibility system
        self.is_iop_turn = False  # Track if it's currently the Iop's turn
        self.overlay_visible = False  # Track if overlay should be visible
        self.iop_spells = ["Épée céleste", "Fulgur", "Super Iop Punch", "Jugement", "Colère de Iop", 
                          "Ébranler", "Roknocerok", "Fendoir", "Ravage", "Jabs", "Rafale", 
                          "Torgnole", "Tannée", "Épée de Iop", "Bond", "Focus", "Éventrail", "Uppercut",
                          "Amplification", "Duel", "Étendard de bravoure", "Vertu", "Charge"]
        
        # Duplicate prevention system
        self.processed_lines = set()  # Track processed log lines to prevent duplicates
        
        # Turn tracking
        self.last_spell_caster = None  # Track the last player who cast a spell
        self.last_etendard_cast = False  # Track if Étendard de bravoure was just cast
        self.last_bond_cast = False  # Track if Bond was just cast
        self.last_charge_cast = False  # Track if Charge was just cast
        
        # Animation variables
        self.animation_frame = 0
        self.smooth_transitions = False  # Disable smooth transitions for more responsive updates
        
        # Courroux icon animation - realistic bouncing physics
        self.courroux_bounce_offset = 0
        self.courroux_bounce_velocity = 0  # Current velocity (pixels per frame)
        self.courroux_bounce_gravity = 1.2  # Gravity acceleration (faster)
        self.courroux_bounce_damping = 0.7  # Energy loss on bounce (0.7 = loses 30% energy each bounce)
        self.courroux_bounce_min_velocity = 0.3  # Stop bouncing when velocity is very small
        self.courroux_ground_level = 0  # Ground level (normal position)
        
        # Égaré icon animation variables
        self.egare_fade_alpha = 0.0  # Current opacity (0.0 to 1.0)
        self.egare_target_alpha = 0.0  # Target opacity
        # Use separate speeds for fade-in and fade-out for better feel
        self.egare_fade_in_speed = 0.08   # per frame when fading in
        self.egare_fade_out_speed = 0.14  # per frame when fading out (faster)
        self.egare_visible = False  # Track on-screen visibility for debug
        self.egare_slide_offset = 0  # Slide-in offset (pixels)
        self.egare_slide_speed = 2  # Pixels per frame during fade-in (faster)
        self.egare_slide_max = 14  # Start this many pixels above and slide down

        # Préparation icon animation variables
        self.preparation_fade_alpha = 0.0  # Current opacity (0.0 to 1.0)
        self.preparation_target_alpha = 0.0  # Target opacity
        self.preparation_fade_in_speed = 0.08   # per frame when fading in
        self.preparation_fade_out_speed = 0.14  # per frame when fading out (faster)
        self.preparation_visible = False  # Track on-screen visibility for debug
        self.preparation_slide_offset = 0  # Slide-in offset (pixels)
        self.preparation_slide_speed = 2  # Pixels per frame during fade-in (faster)
        self.preparation_slide_max = 14  # Start this many pixels above and slide down

        # Préparation bounce animation variables
        self.preparation_bounce_offset = 0
        self.preparation_bounce_velocity = 0  # Current velocity (pixels per frame)
        self.preparation_bounce_gravity = 2.0  # Gravity acceleration (faster)
        self.preparation_bounce_damping = 0.6  # Energy loss on bounce (0.6 = loses 40% energy each bounce, faster decay)
        self.preparation_bounce_min_velocity = 0.5  # Stop bouncing when velocity is very small (higher threshold)
        self.preparation_bounce_ground_level = 0  # Ground level (normal position)
        self.preparation_bounce_delay = 0  # Delay before bouncing starts (frames)
        self.preparation_bounce_delay_max = 15  # Wait 15 frames (0.25 seconds at 60fps) before bouncing (faster)
        self.preparation_bounce_loop_delay = 0  # Delay between bounce loops (frames)
        self.preparation_bounce_loop_delay_max = 30  # Wait 30 frames (0.5 seconds) between bounce loops (faster)
        self.preparation_bounce_loop_active = False  # Whether continuous bouncing is active

        # Debug state tracking to prevent spam
        self.last_puissance_bars_state = 0  # Track last puissance bars count
        self.last_courroux_state = 0  # Track last courroux state
        self.last_preparation_state = 0  # Track last préparation state
        self.last_puissance_hidden_debug = False  # Track if puissance hidden debug was printed
        self.last_courroux_hidden_debug = False  # Track if courroux hidden debug was printed
        self.last_preparation_hidden_debug = False  # Track if préparation hidden debug was printed

        # Cast timeline (last 5 casts by tracked player)
        self.timeline_max_slots = 5
        self.timeline_entries = []  # list[{ 'spell': str, 'icon': QPixmap, 'cost': str }]
        self.timeline_icon_labels = []
        self.timeline_cost_labels = []
        
        # Combo tracking system
        self.combo_definitions = {
            "Vol de vie": {
                "steps": ["1PM", "3PA", "3PA"],
                "icon": "combo1.png",
                "name": "Vol de vie"
            },
            "Poussée": {
                "steps": ["1PA", "1PA", "2PA"],
                "icon": "combo2.png", 
                "name": "Poussée"
            },
            "Préparation": {
                "steps": ["1PM", "1PM", "1PW"],
                "icon": "combo3.png",
                "name": "Préparation"
            },
            "Dommages supplémentaires": {
                "steps": ["2PA", "1PA", "1PM"],
                "icon": "combo4.png",
                "name": "Dommages supplémentaires"
            },
            "Combo PA": {
                "steps": ["1PW", "3PA", "1PW", "1PA"],
                "icon": "combo5.png",
                "name": "Combo PA"
            }
        }
        
        # Combo progress tracking
        self.combo_progress = {}  # {combo_name: current_step_index}
        self.combo_ui_elements = []  # List of combo column widgets
        self.current_turn_spells = []  # Spells cast in current turn
        self.completed_combos_this_turn = set()  # Combos that have been completed this turn
        
        # Initialize combo progress
        for combo_name in self.combo_definitions.keys():
            self.combo_progress[combo_name] = 0
        # Spell cost map and icon filename stems
        self.spell_cost_map = {
            "Épée céleste": "2 PA",
            "Fulgur": "3 PA",
            "Super Iop Punch": "4 PA",
            "Jugement": "1 PA",
            "Colère de Iop": "6 PA",
            "Ébranler": "2 PA",
            "Roknocerok": "4 PA",
            "Fendoir": "3 PA",
            "Ravage": "5 PA",
            "Jabs": "3 PA",
            "Rafale": "1 PA",
            "Torgnole": "2 PA",
            "Tannée": "4 PA",
            "Épée de Iop": "3 PA",
            "Bond": "4 PA",
            "Focus": "2 PA",
            "Éventrail": "1 PM",
            "Uppercut": "1 PW",
            "Amplification": "2 PM",
            "Duel": "1 PA",
            "Étendard de bravoure": "3 PA",  # Variable: 3PA (invocation), 2PA (teleport/destruction)
            "Vertu": "2 PA",
            "Charge": "1 PA",  # Variable: 1PA (0 cases), 2PA (1 case), 3PA (2 cases), 4PA (3 cases)
        }
        self.spell_icon_stem_map = {
            "Épée céleste": "epeeceleste",
            "Fulgur": "fulgur",
            "Super Iop Punch": "superioppunch",
            "Jugement": "jugement",
            "Colère de Iop": "colere",
            "Ébranler": "ebranler",
            "Roknocerok": "roknocerok",
            "Fendoir": "fendoir",
            "Ravage": "ravage",
            "Jabs": "jabs",
            "Rafale": "rafale",
            "Torgnole": "torgnole",
            "Tannée": "tannee",
            "Épée de Iop": "epeeduiop",
            "Bond": "bond",
            "Focus": "Focus",
            "Éventrail": "eventrail",
            "Uppercut": "uppercut",
            "Amplification": "Amplification",
            "Duel": "Duel",
            "Étendard de bravoure": "Etandard",
            "Vertu": "Vertu",
            "Charge": "charge",
        }
        
        # Paths
        # Get the directory where the script is located (works for both script and executable)
        if getattr(sys, 'frozen', False):
            # Running as executable - look in the bundled Iop folder
            self.base_path = Path(sys._MEIPASS) / "Iop"
        else:
            # Running as script
            self.base_path = Path(__file__).parent
        self.concentration_icon_path = self.base_path / "img" / "concentration.png"
        self.courroux_icon_path = self.base_path / "img" / "Couroux.png"
        self.egare_icon_path = self.base_path / "img" / "égaré.png"
        self.preparation_icon_path = self.base_path / "img" / "preparation.png"
        
        # Log file path
        # Log file path - use default Wakfu logs location
        user_profile = Path.home()
        self.log_file_path = user_profile / "AppData" / "Roaming" / "zaap" / "gamesLogs" / "wakfu" / "logs" / "wakfu_chat.log"
        
        # Position saving
        self.positions_locked = False
        self.config_file = self.base_path / "positions_config.json"
        self.auto_save_timer = None
        self.drag_start_position = QPoint()
        self.dragging_concentration = False
        self.dragging_combos = False
        self.dragging_preparation = False
        self.combo_group_offset_x = 0  # Offset for combo group from concentration bar
        self.combo_group_offset_y = 0
        self.preparation_offset_x = 0  # Offset for preparation icon from concentration bar
        self.preparation_offset_y = 0
        
        self.setup_ui()
        self.setup_log_monitoring()
        self.setup_animations()
        self.setup_shortcuts()
        
        # Load saved positions
        QTimer.singleShot(100, self.load_positions)
        
    
    def setup_ui(self):
        """Setup the user interface"""
        self.setWindowTitle("Wakfu Iop Resource Tracker")
        
        # Set window flags based on hidden mode
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
        
        # Make window full screen
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        self.setGeometry(screen_geometry)
        
        # Main widget (full screen)
        main_widget = QWidget()
        main_widget.setLayout(QVBoxLayout())
        main_widget.layout().setContentsMargins(0, 0, 0, 0)
        
        # Concentration icon (positioned absolutely)
        self.concentration_icon = QLabel()
        self.concentration_icon.setFixedSize(28, 28)
        self.concentration_icon.setScaledContents(True)
        self.concentration_icon.setParent(main_widget)
        
        if self.concentration_icon_path.exists():
            pixmap = QPixmap(str(self.concentration_icon_path))
            self.concentration_icon.setPixmap(pixmap.scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.concentration_icon.setStyleSheet("background-color: transparent;")
        else:
            self.concentration_icon.setText("🧠")
            self.concentration_icon.setStyleSheet("""
                QLabel {
                    color: #64b5f6;
                    font-size: 20px;
                    font-weight: bold;
                    background-color: transparent;
                }
            """)
        
        # Concentration progress bar
        self.concentration_bar = ConcentrationProgressBar()
        self.concentration_bar.setParent(main_widget)
        
        # Courroux icon (positioned absolutely, initially hidden)
        self.courroux_icon = QLabel()
        self.courroux_icon.setFixedSize(28, 28)
        self.courroux_icon.setScaledContents(True)
        self.courroux_icon.setParent(main_widget)
        self.courroux_icon.hide()
        
        if self.courroux_icon_path.exists():
            pixmap = QPixmap(str(self.courroux_icon_path))
            self.courroux_icon.setPixmap(pixmap.scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.courroux_icon.setStyleSheet("background-color: transparent;")
        else:
            self.courroux_icon.setText("⚡")
            self.courroux_icon.setStyleSheet("""
                QLabel {
                    color: #ff6b35;
                    font-size: 20px;
                    font-weight: bold;
                    background-color: transparent;
                }
            """)
        
        # Courroux counter (positioned absolutely, initially hidden)
        self.courroux_counter = OutlinedLabel()
        self.courroux_counter.setFixedSize(28, 28)
        self.courroux_counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.courroux_counter.setParent(main_widget)
        self.courroux_counter.hide()
        
        # Préparation icon (positioned absolutely, initially hidden)
        self.preparation_icon = QLabel()
        self.preparation_icon.setFixedSize(40, 40)
        self.preparation_icon.setScaledContents(True)
        self.preparation_icon.setParent(main_widget)
        self.preparation_icon.hide()
        
        if self.preparation_icon_path.exists():
            pixmap = QPixmap(str(self.preparation_icon_path))
            self.preparation_icon.setPixmap(pixmap.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.preparation_icon.setStyleSheet("background-color: transparent;")
        else:
            self.preparation_icon.setText("📋")
            self.preparation_icon.setStyleSheet("""
                QLabel {
                    color: #ff9800;
                    font-size: 28px;
                    font-weight: bold;
                    background-color: transparent;
                }
            """)
        
        # Préparation counter (positioned absolutely, initially hidden)
        self.preparation_counter = OutlinedLabel()
        self.preparation_counter.setFixedSize(40, 40)
        self.preparation_counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preparation_counter.setParent(main_widget)
        self.preparation_counter.hide()
        
        # Puissance combo bars (5 small bars, initially hidden)
        self.puissance_bars = []
        for i in range(5):
            bar = QFrame()
            bar.setFixedSize(30, 6)  # Small horizontal bars
            bar.setParent(main_widget)
            bar.setStyleSheet("""
                QFrame {
                    background-color: rgba(255, 255, 255, 30);
                    border: 1px solid rgba(255, 255, 255, 50);
                    border-radius: 3px;
                }
            """)
            bar.hide()
            self.puissance_bars.append(bar)
        
        # Égaré icon (positioned above first combo bar, initially hidden)
        self.egare_icon = EgareIcon()
        self.egare_icon.setFixedSize(24, 24)
        self.egare_icon.setScaledContents(True)
        self.egare_icon.setParent(main_widget)
        self.egare_icon.hide()
        
        if self.egare_icon_path.exists():
            pixmap = QPixmap(str(self.egare_icon_path))
            scaled_pixmap = pixmap.scaled(18, 18, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.egare_icon.setPixmap(scaled_pixmap)
        else:
            # Fallback to emoji if image not found
            self.egare_icon.setText("🔥")
            self.egare_icon.setStyleSheet("""
                QLabel {
                    color: #ff6b35;
                    font-size: 16px;
                    font-weight: bold;
                    background-color: transparent;
                }
            """)

        # Create timeline UI elements (icons and cost overlays)
        for _ in range(self.timeline_max_slots):
            # Icon label
            icon_label = QLabel()
            icon_label.setParent(main_widget)
            icon_label.setFixedSize(32, 32)
            icon_label.setScaledContents(True)
            icon_label.setStyleSheet("background-color: transparent;")
            icon_label.hide()
            self.timeline_icon_labels.append(icon_label)

            # Cost label below the icon using outlined white text
            cost_label = OutlinedLabel()
            cost_label.setParent(main_widget)
            cost_label.setFixedSize(32, 16)  # Give it a proper size
            cost_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cost_label.setStyleSheet("background-color: transparent;")
            cost_label.hide()
            self.timeline_cost_labels.append(cost_label)
        
        # Create combo tracking UI elements
        self.create_combo_tracking_ui(main_widget)
        
        # Position elements (will be updated when visible)
        self.position_elements()
        
        # Initially hide all elements since we start out of combat
        self.concentration_icon.hide()
        self.concentration_bar.hide()
        
        self.setCentralWidget(main_widget)
    
    def create_combo_tracking_ui(self, parent):
        """Create the combo tracking UI elements"""
        # Create combo columns directly as children of the main widget (not nested)
        for combo_name, combo_data in self.combo_definitions.items():
            combo_column = ComboColumnWidget(combo_name, combo_data, parent)
            combo_column.hide()  # Initially hidden
            self.combo_ui_elements.append(combo_column)
    
    def check_combo_progress(self, spell_cost):
        """Check if a spell cost matches any combo progression"""
        # Convert spell cost to our format (e.g., "2 PA" -> "2PA")
        compact_cost = spell_cost.replace(" ", "")
        
        # First, check if this spell matches the next step of any combo that's currently in progress
        matching_combos = []
        for combo_name, combo_data in self.combo_definitions.items():
            current_step = self.combo_progress[combo_name]
            
            # Check if this combo is in progress and this spell matches the next step
            if current_step < len(combo_data["steps"]):
                expected_step = combo_data["steps"][current_step]
                
                if compact_cost == expected_step:
                    matching_combos.append(combo_name)
        
        # If we found matching combos, progress them and reset all others
        if matching_combos:
            # Progress all matching combos
            for matching_combo in matching_combos:
                self.combo_progress[matching_combo] += 1
                print(f"DEBUG: Combo '{matching_combo}' progressed to step {self.combo_progress[matching_combo]}")
                
                # Update UI for the progressed combo
                if self.combo_ui_elements:
                    combo_index = list(self.combo_definitions.keys()).index(matching_combo)
                    if combo_index < len(self.combo_ui_elements):
                        self.combo_ui_elements[combo_index].update_progress(self.combo_progress[matching_combo])
                
                # Check if combo is completed
                if self.combo_progress[matching_combo] >= len(self.combo_definitions[matching_combo]["steps"]):
                    self.completed_combos_this_turn.add(matching_combo)
                    print(f"DEBUG: Combo '{matching_combo}' COMPLETED! (added to completed set)")
            
            # Reset ALL other combos that were in progress (except completed ones and matching ones)
            for combo_name, combo_data in self.combo_definitions.items():
                if (combo_name not in matching_combos and 
                    self.combo_progress[combo_name] > 0 and 
                    combo_name not in self.completed_combos_this_turn):
                    self.combo_progress[combo_name] = 0
                    combo_index = list(self.combo_definitions.keys()).index(combo_name)
                    if combo_index < len(self.combo_ui_elements):
                        # Trigger full reset with slide-down animation
                        self.combo_ui_elements[combo_index].reset()
                        print(f"DEBUG: Combo '{combo_name}' reset due to '{matching_combos}' progression")
                elif combo_name in self.completed_combos_this_turn:
                    print(f"DEBUG: Combo '{combo_name}' protected from reset (already completed this turn)")
        
        # If no combo was in progress and matched, check if this spell starts any combo
        else:
            # Check if any combo was in progress (if so, reset them, except completed ones)
            any_in_progress = False
            for combo_name, combo_data in self.combo_definitions.items():
                if (self.combo_progress[combo_name] > 0 and 
                    combo_name not in self.completed_combos_this_turn):
                    any_in_progress = True
                    self.combo_progress[combo_name] = 0
                    combo_index = list(self.combo_definitions.keys()).index(combo_name)
                    if combo_index < len(self.combo_ui_elements):
                        # Trigger full reset with slide-down animation
                        self.combo_ui_elements[combo_index].reset()
                        print(f"DEBUG: Combo '{combo_name}' reset due to non-matching spell '{compact_cost}'")
                elif combo_name in self.completed_combos_this_turn:
                    print(f"DEBUG: Combo '{combo_name}' protected from reset (already completed this turn)")
            
            # Now check if this spell starts any combo (first step, but not completed ones)
            for combo_name, combo_data in self.combo_definitions.items():
                if (len(combo_data["steps"]) > 0 and 
                    compact_cost == combo_data["steps"][0] and 
                    combo_name not in self.completed_combos_this_turn):
                    # Start this combo
                    self.combo_progress[combo_name] = 1
                    print(f"DEBUG: Combo '{combo_name}' started with spell '{compact_cost}'")
                    
                    # Update UI
                    if self.combo_ui_elements:
                        combo_index = list(self.combo_definitions.keys()).index(combo_name)
                        if combo_index < len(self.combo_ui_elements):
                            self.combo_ui_elements[combo_index].update_progress(1)
                    break
                elif combo_name in self.completed_combos_this_turn:
                    print(f"DEBUG: Combo '{combo_name}' cannot be started (already completed this turn)")
    
    def reset_all_combos(self):
        """Reset all combo progress"""
        # Check if any combo was actually in progress before resetting
        any_in_progress = any(progress > 0 for progress in self.combo_progress.values())
        
        # Debug: Show which combos were in progress
        if any_in_progress:
            active_combos = [name for name, progress in self.combo_progress.items() if progress > 0]
            print(f"DEBUG: Resetting combos that were in progress: {active_combos}")
        else:
            print("DEBUG: No combos were in progress - silent reset")
        
        for combo_name in self.combo_progress.keys():
            self.combo_progress[combo_name] = 0
        
        # Clear completed combos set (new turn/combat starts)
        completed_count = len(self.completed_combos_this_turn)
        if completed_count > 0:
            print(f"DEBUG: Clearing {completed_count} completed combos from this turn")
        self.completed_combos_this_turn.clear()
        
        # Update all UI elements - only trigger reset animation if any combo was in progress
        for combo_widget in self.combo_ui_elements:
            if any_in_progress:
                combo_widget.reset()  # This will trigger the slide animation
            else:
                combo_widget.reset_silent()  # Reset without animation
        
        # Clear current turn spells
        spells_count = len(self.current_turn_spells)
        if spells_count > 0:
            print(f"DEBUG: Clearing {spells_count} spells from current turn: {self.current_turn_spells}")
        self.current_turn_spells = []
        
        if any_in_progress:
            print("DEBUG: All combos reset with slide animation")
        else:
            print("DEBUG: All combos reset (no animation needed)")
    
    def position_elements(self):
        """Position all elements on screen"""
        # Get concentration bar position
        base_x = self.concentration_bar.x()
        base_y = self.concentration_bar.y()
        
        # Position concentration icon (left of bar)
        self.concentration_icon.move(base_x - 35, base_y - 2)
        
        # Position courroux icon (right of bar)
        self.courroux_icon.move(base_x + 255, base_y - 2)
        
        # Position courroux counter (on top of courroux icon)
        self.courroux_counter.move(base_x + 255, base_y - 2)
        
        # Position préparation icon (right of courroux + offset)
        self.preparation_icon.move(base_x + 290 + self.preparation_offset_x, base_y - 2 + self.preparation_offset_y)
        
        # Position préparation counter (on top of préparation icon)
        self.preparation_counter.move(base_x + 290 + self.preparation_offset_x, base_y - 2 + self.preparation_offset_y)
        
        # Position Puissance combo bars (on top of concentration bar)
        for i, bar in enumerate(self.puissance_bars):
            bar_x = base_x + (i * 35)  # 35px spacing between bars
            bar_y = base_y - 15  # 15px above the concentration bar
            bar.move(bar_x, bar_y)
        
        # Position égaré icon (well above the first combo bar - 10/50)
        egare_x = base_x  # Same X position as first combo bar
        # Apply slide-in offset during fade-in (start slightly above and slide down)
        slide_offset = getattr(self, 'egare_slide_offset', 0)
        egare_y = base_y - 50 - slide_offset
        self.egare_icon.move(egare_x, egare_y)

        # Position timeline slots relative to concentration bar
        timeline_icon_y = base_y + 30  # icons row
        slot_spacing = 32  # no gap between icons (same as icon width)
        icon_w, icon_h = 32, 32
        for i in range(self.timeline_max_slots):
            icon_x = base_x + (i * slot_spacing)
            # Icon position
            self.timeline_icon_labels[i].move(icon_x, timeline_icon_y)
            # Cost label below icon, centered horizontally
            cost_x = icon_x + (icon_w - 32) // 2  # Center the 32px wide cost label under the 32px icon
            cost_y = timeline_icon_y + icon_h - 2
            self.timeline_cost_labels[i].move(cost_x, cost_y)
        
        # Position combo tracking columns with offset
        combo_y = base_y + 80 + self.combo_group_offset_y  # Below timeline + offset
        combo_spacing = 45  # Space between combo columns
        for i, combo_widget in enumerate(self.combo_ui_elements):
            combo_x = base_x + (i * combo_spacing) + self.combo_group_offset_x
            combo_widget.move(combo_x, combo_y)
    
    def setup_log_monitoring(self):
        """Setup log file monitoring"""
        self.log_monitor = LogMonitorThread(self.log_file_path)
        self.log_monitor.log_updated.connect(self.parse_log_line)
        self.log_monitor.start()
    
    def setup_animations(self):
        """Setup animation timers"""
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animations)
        self.animation_timer.start(50)  # 20 FPS (back to original)
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Close application
        close_action = QAction("Close", self)
        close_action.setShortcut("Ctrl+Q")
        close_action.triggered.connect(self.close)
        self.addAction(close_action)
        
        # Force close
        force_close_action = QAction("Force Close", self)
        force_close_action.setShortcut("Ctrl+Shift+Q")
        force_close_action.triggered.connect(lambda: sys.exit(0))
        self.addAction(force_close_action)
    
    def parse_log_line(self, line):
        """Parse log line for Iop resources"""
        try:
            # Prevent duplicate processing of the same spell cast within a short time window
            # Extract the core content without timestamp for spell lines
            if "lance le sort" in line:
                # Extract player and spell info for duplicate detection
                spell_match = re.search(r'\[Information \(combat\)\] ([^:]+)[:\s]+lance le sort ([^(]+)', line)
                if spell_match:
                    player_name = spell_match.group(1).strip()
                    spell_name = spell_match.group(2).strip()
                    
                    # Use line hash for duplicate detection (same log line = duplicate)
                    line_hash = hash(line.strip())
                    if line_hash in self.processed_lines:
                        print(f"DEBUG: Skipping duplicate log line: {line.strip()[:50]}...")
                        return
                    
                    # Record this log line as processed
                    self.processed_lines.add(line_hash)
                    print(f"DEBUG: Processing new spell cast: {player_name}:{spell_name}")
                else:
                    # Fallback to line hash for non-spell lines
                    line_hash = hash(line.strip())
                    if line_hash in self.processed_lines:
                        print(f"DEBUG: Skipping duplicate line: {line.strip()[:50]}...")
                        return
                    self.processed_lines.add(line_hash)
            else:
                # For non-spell lines, use line hash
                line_hash = hash(line.strip())
                if line_hash in self.processed_lines:
                    print(f"DEBUG: Skipping duplicate line: {line.strip()[:50]}...")
                    return
                self.processed_lines.add(line_hash)
            
            # Keep only the last 1000 processed lines to prevent memory issues
            if len(self.processed_lines) > 1000:
                # Remove oldest entries (this is a simple approach)
                self.processed_lines = set(list(self.processed_lines)[-500:])
            # Check for Sac à patate combat start (check this FIRST - works on any line type)
            if "Sac à patate" in line and ("Quand tu auras fini de me frapper" in line or "abandonner" in line or "Abandonne le combat" in line):
                self.is_sac_patate_combat = True
            
            # Check for combat start and Iop turn detection - CONSOLIDATED SPELL PROCESSING
            if "lance le sort" in line:
                # Extract player name for spell cast lines; supports both "Name: lance le sort" and "Name lance le sort"
                player_spell_match = re.search(r'\[Information \(combat\)\]\s+([^:]+):\s+lance le sort', line)
                if not player_spell_match:
                    player_spell_match = re.search(r'\[Information \(combat\)\]\s+([^:]+)\s+lance le sort', line)

                # Extract spell name for debug purposes
                spell_name_match = re.search(r'lance le sort ([^\(\n]+)', line)
                spell_name = spell_name_match.group(1).strip() if spell_name_match else "?"

                # Extract caster name
                caster_name = None
                if player_spell_match:
                    caster_name = player_spell_match.group(1).strip()
                    # Track the last player who cast a spell (for turn end detection)
                    self.last_spell_caster = caster_name
                
                # Check if this is an Iop spell (regardless of who casts it)
                is_iop_spell = spell_name in self.iop_spells
                
                # Turn-based visibility logic - handle first Iop spell
                if is_iop_spell:
                    # If no tracked player yet, set it to this caster (first Iop spell)
                    if not self.tracked_player_name:
                        self.tracked_player_name = caster_name
                        print(f"DEBUG: Tracked player set to {self.tracked_player_name} on Iop spell '{spell_name}'")
                
                # Determine if this cast is by the tracked player (after potentially setting tracked_player_name)
                is_tracked_caster = False
                if caster_name and self.tracked_player_name:
                    is_tracked_caster = (caster_name.strip() == self.tracked_player_name.strip())
                
                timestamp = time.strftime("%H:%M:%S")
                print(f"DEBUG [{timestamp}]: Spell cast detected - caster='{caster_name}', spell='{spell_name}', tracked='{self.tracked_player_name}', is_tracked={is_tracked_caster}, is_iop_spell={is_iop_spell}")

                # Initialize puissance only once per combat, when transitioning into combat due to the tracked player's first cast
                if not self.in_combat and is_tracked_caster:
                    self.in_combat = True
                    self.puissance = 30
                    self.current_puissance = 30
                    print("DEBUG: Combat started by tracked player; Puissance initialized to 30")
                else:
                    # Still mark combat as active, but do not reinitialize puissance
                    self.in_combat = True
                
                # Show overlay immediately when Iop spell is cast by tracked player
                if is_iop_spell and is_tracked_caster:
                    self.is_iop_turn = True
                    self.overlay_visible = True
                    print(f"DEBUG: Iop turn started - overlay shown for '{spell_name}'")
                
                # Handle specific spell effects for tracked player
                if is_tracked_caster and spell_name:
                    # Track Étendard de bravoure for cost adjustment
                    if spell_name == "Étendard de bravoure":
                        self.last_etendard_cast = True
                        print(f"DEBUG: Étendard de bravoure detected - waiting for next line to determine cost")
                    else:
                        self.last_etendard_cast = False
                    
                    # Track Bond for Impétueux proc detection
                    if spell_name == "Bond":
                        self.last_bond_cast = True
                        print(f"DEBUG: Bond detected - waiting for Impétueux proc to determine cost")
                    elif spell_name != "Bond":
                        # Reset Bond flag for other spells
                        self.last_bond_cast = False
                    
                    # Track Charge for distance-based cost adjustment
                    if spell_name == "Charge":
                        self.last_charge_cast = True
                        # Reset Charge cost to 1PA for each new cast
                        self.spell_cost_map["Charge"] = "1 PA"
                        # Set default cost to 1PA immediately when Charge is cast
                        if self.timeline_entries:
                            self.timeline_entries[-1]['cost'] = "1PA"
                            self.update_timeline_display()  # Refresh timeline display
                        print(f"DEBUG: Charge detected - cost reset to 1PA for new cast, waiting for distance info")
                    elif spell_name != "Charge":
                        # Reset Charge flag for other spells
                        self.last_charge_cast = False
                    
                    # Add spell to timeline
                    self.add_spell_to_timeline(spell_name)
                    
                    # Handle Courroux loss spells (Super Iop Punch, Roknocerok, Tannée)
                    if spell_name in ["Super Iop Punch", "Roknocerok", "Tannée"]:
                        self.courroux = 0  # Lose ALL stacks when using these spells
                        self.current_courroux = self.courroux
                        print(f"DEBUG: Courroux lost due to {spell_name}")
                    
                    # Handle Préparation loss - wait for damage confirmation before removing
                    if self.preparation > 0 and caster_name == self.tracked_player_name:
                        # Set up damage confirmation system
                        self.pending_preparation_loss = True
                        self.preparation_loss_caster = caster_name
                        self.preparation_loss_spell = spell_name
                        print(f"DEBUG: Préparation loss pending - waiting for damage confirmation from {spell_name}")
                    
                    # Handle Égaré gain spells (Fulgur, Colère de Iop)
                    elif spell_name in ["Fulgur", "Colère de Iop"]:
                        print(f"DEBUG: Égaré gained by {caster_name} via {spell_name}")
                        self.egare = True  # Gain égaré buff
                        self.current_egare = self.egare
                
                # Return to prevent further processing of this line
                return
            
            # Combat end detection - improved logic
            combat_ended = False
            
            # Normal combat end: "Combat terminé, cliquez ici pour rouvrir l'écran de fin de combat."
            if "Combat terminé" in line or "Combat terminé, cliquez ici pour rouvrir l'écran de fin de combat." in line:
                combat_ended = True
            
            # Exception: KO/hors-combat only triggers end for Sac à patate combat
            elif (re.search(r'est hors-combat', line) or re.search(r'est KO !', line)) and self.is_sac_patate_combat:
                combat_ended = True
            
            if combat_ended:
                self.in_combat = False
                self.is_sac_patate_combat = False  # Reset Sac à patate flag
                self.is_iop_turn = False  # Reset turn state
                self.overlay_visible = False  # Hide overlay
                # Reset all resources when combat ends
                self.concentration = 0
                self.courroux = 0
                self.puissance = 0
                self.egare = False
                self.preparation = 0
                self.current_concentration = 0
                self.current_courroux = 0
                self.current_puissance = 0
                self.current_egare = False
                self.current_preparation = 0
                # Stop préparation bouncing loop
                self.preparation_bounce_loop_active = False
                self.preparation_bounce_velocity = 0
                self.preparation_bounce_offset = 0
                # Reset damage confirmation system
                self.pending_preparation_loss = False
                self.preparation_loss_caster = None
                self.preparation_loss_spell = None
                # Reset combos when combat ends
                self.reset_all_combos()
                # Clear timeline when combat ends
                self.timeline_entries.clear()
                self.current_turn_spells.clear()
                # Hide all timeline elements immediately
                for i in range(self.timeline_max_slots):
                    self.timeline_icon_labels[i].hide()
                    self.timeline_cost_labels[i].hide()
                print("DEBUG: Combat ended - overlay hidden and timeline cleared")
                return
            
            # Handle Étendard de bravoure cost adjustment based on next line
            if self.last_etendard_cast and "[Information (combat)]" in line:
                if "Invoque un(e) Étendard de Bravoure" in line:
                    # Invocation: 3PA - ensure timeline shows correct cost
                    if self.timeline_entries:
                        self.timeline_entries[-1]['cost'] = "3PA"
                        self.spell_cost_map["Étendard de bravoure"] = "3 PA"
                        self.update_timeline_display()  # Refresh timeline display
                        print(f"DEBUG: Étendard de bravoure invocation detected - cost confirmed as 3PA")
                    self.last_etendard_cast = False
                elif "se téléporte" in line:
                    # Téléportation: 2PA - need to update the last timeline entry
                    if self.timeline_entries:
                        self.timeline_entries[-1]['cost'] = "2PA"
                        self.spell_cost_map["Étendard de bravoure"] = "2 PA"
                        self.update_timeline_display()  # Refresh timeline display
                        print(f"DEBUG: Étendard de bravoure téléportation detected - cost adjusted to 2PA")
                    self.last_etendard_cast = False
                elif "est détruit" in line and "Étendard de Bravoure" in line:
                    # Destruction: 2PA - need to update the last timeline entry
                    if self.timeline_entries:
                        self.timeline_entries[-1]['cost'] = "2PA"
                        self.spell_cost_map["Étendard de bravoure"] = "2 PA"
                        self.update_timeline_display()  # Refresh timeline display
                        print(f"DEBUG: Étendard de bravoure destruction detected - cost adjusted to 2PA")
                    self.last_etendard_cast = False
            
            # Handle Bond cost adjustment based on Impétueux proc
            if self.last_bond_cast and "[Information (combat)]" in line:
                if "Impétueux (+" in line and "(Impétueux)" in line:
                    # Impétueux proc detected - Bond costs 0PA
                    if self.timeline_entries:
                        self.timeline_entries[-1]['cost'] = "0PA"
                        self.spell_cost_map["Bond"] = "0 PA"
                        self.update_timeline_display()  # Refresh timeline display
                        print(f"DEBUG: Bond Impétueux proc detected - cost adjusted to 0PA")
                    self.last_bond_cast = False
                elif "PA" in line and "Impétueux" in line:
                    # Alternative detection for Impétueux proc
                    if self.timeline_entries:
                        self.timeline_entries[-1]['cost'] = "0PA"
                        self.spell_cost_map["Bond"] = "0 PA"
                        self.update_timeline_display()  # Refresh timeline display
                        print(f"DEBUG: Bond Impétueux proc detected (alternative) - cost adjusted to 0PA")
                    self.last_bond_cast = False
            
            # Handle Charge cost adjustment based on distance traveled
            if self.last_charge_cast and "[Information (combat)]" in line:
                if "Se rapproche de 1 case" in line:
                    # 1 case traveled - Charge costs 2PA
                    if self.timeline_entries:
                        self.timeline_entries[-1]['cost'] = "2PA"
                        self.spell_cost_map["Charge"] = "2 PA"
                        self.update_timeline_display()  # Refresh timeline display
                        print(f"DEBUG: Charge 1 case detected - cost adjusted to 2PA")
                    self.last_charge_cast = False
                elif "Se rapproche de 2 cases" in line:
                    # 2 cases traveled - Charge costs 3PA
                    if self.timeline_entries:
                        self.timeline_entries[-1]['cost'] = "3PA"
                        self.spell_cost_map["Charge"] = "3 PA"
                        self.update_timeline_display()  # Refresh timeline display
                        print(f"DEBUG: Charge 2 cases detected - cost adjusted to 3PA")
                    self.last_charge_cast = False
                elif "Se rapproche de 3 cases" in line:
                    # 3 cases traveled - Charge costs 4PA
                    if self.timeline_entries:
                        self.timeline_entries[-1]['cost'] = "4PA"
                        self.spell_cost_map["Charge"] = "4 PA"
                        self.update_timeline_display()  # Refresh timeline display
                        print(f"DEBUG: Charge 3 cases detected - cost adjusted to 4PA")
                    self.last_charge_cast = False
            
            # Only process combat lines
            if "[Information (combat)]" not in line:
                return
            
            # Parse Concentration - actual format: "Concentration (+65 Niv.)"
            concentration_match = re.search(r'Concentration \(\+(\d+) Niv\.\)', line)
            if concentration_match:
                # Extract player name from concentration log
                player_concentration_match = re.search(r'\[Information \(combat\)\] ([^:]+): Concentration', line)
                if player_concentration_match:
                    self.tracked_player_name = player_concentration_match.group(1)
                
                concentration_value = int(concentration_match.group(1))
                
                # Check if concentration reaches 100+ (triggers overflow and égaré loss)
                if concentration_value >= 100:
                    # Wrap around using modulo - e.g., 140 becomes 40
                    self.concentration = concentration_value % 100
                    # Lose égaré buff when concentration overflows
                    if self.egare:
                        self.egare = False
                        self.current_egare = self.egare
                        # Start fade out (animated)
                        self.egare_target_alpha = 0.0
                        if self.egare_visible:
                            print("DEBUG: Égaré removed due to Concentration overflow")
                            self.egare_visible = False
                else:
                    # Normal concentration tracking
                    self.concentration = concentration_value
                return
            
            # Parse Égaré loss - turn passing ("seconde reportée pour le tour suivant" or "secondes reportées pour le tour suivant")
            # This MUST be checked BEFORE courroux loss to avoid early return
            if ("reportée pour le tour suivant" in line) or ("reportées pour le tour suivant" in line):
                print(f"DEBUG: Turn end detected in log: {line.strip()[:80]}...")
                
                # Determine which player's turn is ending
                # Use the last player who cast a spell as the turn owner
                turn_owner = self.last_spell_caster
                print(f"DEBUG: Turn end detected - last spell caster was: '{turn_owner}' (tracked: '{self.tracked_player_name}')")
                
                if turn_owner and self.tracked_player_name and turn_owner == self.tracked_player_name:
                    # The tracked Iop is passing turn - hide overlay
                    self.is_iop_turn = False
                    self.overlay_visible = False
                    
                    # If we were waiting for damage confirmation, cancel it
                    if self.pending_preparation_loss:
                        self.pending_preparation_loss = False
                        self.preparation_loss_caster = None
                        self.preparation_loss_spell = None
                        print(f"DEBUG: Préparation damage confirmation cancelled - turn passed without damage")
                    
                    print(f"DEBUG: Iop turn ended - overlay hidden (turn passed by {turn_owner})")
                elif turn_owner:
                    # Different player is passing turn - overlay remains as is
                    print(f"DEBUG: Turn passed by different player '{turn_owner}' - overlay remains {'visible' if self.overlay_visible else 'hidden'}")
                else:
                    # No recent spell caster - assume it's the tracked player's turn ending
                    print(f"DEBUG: No recent spell caster - assuming tracked player's turn ending")
                    if self.tracked_player_name:
                        self.is_iop_turn = False
                        self.overlay_visible = False
                        
                        # If we were waiting for damage confirmation, cancel it
                        if self.pending_preparation_loss:
                            self.pending_preparation_loss = False
                            self.preparation_loss_caster = None
                            self.preparation_loss_spell = None
                            print(f"DEBUG: Préparation damage confirmation cancelled - assumed turn end without damage")
                        
                        print(f"DEBUG: Iop turn ended - overlay hidden (assumed turn end)")
                    else:
                        print(f"DEBUG: No tracked player set - cannot determine turn owner")
                
                if self.egare:
                    self.egare = False
                    self.current_egare = self.egare
                    # Start fade out (animated)
                    self.egare_target_alpha = 0.0
                    if self.egare_visible:
                        print("DEBUG: Égaré removed due to turn carryover")
                        self.egare_visible = False
                
                # Clear timeline when turn passes
                timeline_count = len(self.timeline_entries)
                if timeline_count > 0:
                    print(f"DEBUG: Clearing {timeline_count} timeline entries due to turn end")
                    self.timeline_entries.clear()
                    # Hide all timeline elements immediately
                    for i in range(self.timeline_max_slots):
                        self.timeline_icon_labels[i].hide()
                        self.timeline_cost_labels[i].hide()
                else:
                    print("DEBUG: Timeline already empty - no clearing needed")
                
                # Reset combos when turn passes
                print("DEBUG: Resetting all combos due to turn end")
                self.reset_all_combos()
                
                # Note: Préparation is NOT reset on turn passed - it persists until spell cast
                print("DEBUG: Préparation persists across turns (only lost on spell cast)")
                
                return
            
            # Parse Puissance - actual format: "Puissance (+50 Niv.)"
            puissance_match = re.search(r'Puissance \(\+(\d+) Niv\.\)', line)
            if puissance_match:
                puissance_value = int(puissance_match.group(1))
                self.puissance = min(puissance_value, 50)  # Cap at 50
                # Force immediate display update
                self.current_puissance = self.puissance
                return
            
            # Parse Puissance loss - "n'est plus sous l'emprise de 'Puissance' (Iop isolé)"
            if "n'est plus sous l'emprise de 'Puissance' (Iop isolé)" in line:
                # Extract player name and only apply to tracked player
                player_puissance_loss_match = re.search(r'\[Information \(combat\)\] ([^:]+): n\'est plus sous l\'emprise de \'Puissance\'', line)
                if player_puissance_loss_match and self.tracked_player_name:
                    player_name = player_puissance_loss_match.group(1)
                    if player_name == self.tracked_player_name:
                        self.puissance = max(0, self.puissance - 10)  # Lose 10 puissance, minimum 0
                        # Force immediate display update
                        self.current_puissance = self.puissance
                return
            
            # Parse Courroux gains - "Courroux (+1 Niv.) (Compulsion)" OR "Courroux (+1 Niv.) (Concentration)"
            # Note: The number in (+X Niv.) is the TOTAL current amount, not the amount gained
            courroux_gain_match = re.search(r'Courroux \(\+(\d+) Niv\.\) \((Compulsion|Concentration)\)', line)
            if courroux_gain_match:
                courroux_total = int(courroux_gain_match.group(1))
                old_courroux = self.courroux
                self.courroux = min(courroux_total, 4)  # Set to the total amount shown in log, max 4 stacks
                # Force immediate display update
                self.current_courroux = self.courroux
                # Trigger bounce animation when gaining courroux (only if it increased)
                if self.courroux > old_courroux:
                    self.trigger_courroux_bounce()
                return
            
            # Parse Courroux loss - "n'est plus sous l'emprise de 'Courroux' (Compulsion)"
            if "n'est plus sous l'emprise de 'Courroux' (Compulsion)" in line:
                # Extract player name and only apply to tracked player
                player_courroux_loss_match = re.search(r'\[Information \(combat\)\] ([^:]+): n\'est plus sous l\'emprise de \'Courroux\'', line)
                if player_courroux_loss_match and self.tracked_player_name:
                    player_name = player_courroux_loss_match.group(1)
                    if player_name == self.tracked_player_name:
                        self.courroux = 0  # Lose ALL stacks
                        # Force immediate display update
                        self.current_courroux = self.courroux
                return
            
            # Note: Spell processing is now consolidated above to prevent duplicate timeline entries
            
            # Parse Courroux loss - damage dealt with (Courroux) tag
            # Pattern: "[Information (combat)] monster: -xx PV (element) (Courroux)"
            if "(Courroux)" in line and "PV" in line:
                courroux_damage_match = re.search(r'\[Information \(combat\)\] .*: -(\d+) PV \([^)]+\) \(Courroux\)', line)
                if courroux_damage_match:
                    self.courroux = 0  # Lose ALL stacks when damage is dealt with courroux
                    # Force immediate display update
                    self.current_courroux = self.courroux
                    return
            
            # Parse Préparation gains - "Belluya: Préparation (+20 Niv.)"
            preparation_gain_match = re.search(r'Préparation \(\+(\d+) Niv\.\)', line)
            if preparation_gain_match:
                preparation_total = int(preparation_gain_match.group(1))
                old_preparation = self.preparation
                self.preparation = preparation_total  # Set to the total amount shown in log
                # Force immediate display update
                self.current_preparation = self.preparation
                # Trigger slide animation when gaining préparation (only if it increased)
                if self.preparation > old_preparation:
                    self.trigger_preparation_slide()
                print(f"DEBUG: Préparation gained: {preparation_total} stacks")
                return
            
            # Parse damage lines - "Sac à patates: -64 PV  (Feu)" or "Sac à patates: -133 PV (Feu) (Courroux)"
            damage_match = re.search(r'\[Information \(combat\)\] ([^:]+):\s*-(\d+)\s*PV', line)
            if damage_match and self.pending_preparation_loss:
                damage_target = damage_match.group(1).strip()
                damage_amount = int(damage_match.group(2))
                
                print(f"DEBUG: Damage detected: {damage_amount} PV to {damage_target} (waiting for: {self.preparation_loss_caster})")
                
                # Check if this damage is from the tracked player's spell
                if self.preparation_loss_caster == self.tracked_player_name:
                    # Damage confirmed - remove Préparation
                    self.preparation = 0
                    self.current_preparation = self.preparation
                    # Stop continuous bouncing loop
                    self.preparation_bounce_loop_active = False
                    self.preparation_bounce_velocity = 0
                    self.preparation_bounce_offset = 0
                    # Reset damage confirmation system
                    self.pending_preparation_loss = False
                    self.preparation_loss_caster = None
                    self.preparation_loss_spell = None
                    print(f"DEBUG: Préparation lost due to confirmed damage: {damage_amount} PV to {damage_target}")
                    return
                else:
                    print(f"DEBUG: Damage detected but not from tracked player - caster: {self.preparation_loss_caster}, tracked: {self.tracked_player_name}")
                
        except Exception as e:
            pass  # Silently handle parsing errors
    
    def update_animations(self):
        """Update animations and visual effects"""
        self.animation_frame += 1
        
        # Show/hide overlay based on turn-based visibility (only during Iop's turn)
        if self.overlay_visible and self.in_combat:
            self.concentration_icon.show()
            self.concentration_bar.show()
            self.position_elements()  # Ensure elements are positioned
            # Show timeline slots that have entries
            self.update_timeline_display()
            # Show combo tracking when it's Iop's turn
            for combo_widget in self.combo_ui_elements:
                combo_widget.show()
        else:
            self.concentration_icon.hide()
            self.concentration_bar.hide()
            self.courroux_icon.hide()
            self.courroux_counter.hide()
            # Hide all Puissance bars when not Iop's turn
            for bar in self.puissance_bars:
                bar.hide()
            # Target fade out for égaré icon, but keep processing fade animation below (no early return)
            self.egare_target_alpha = 0.0
            # Hide timeline when not Iop's turn
            for i in range(self.timeline_max_slots):
                self.timeline_icon_labels[i].hide()
                self.timeline_cost_labels[i].hide()
            # Hide combo tracking when not Iop's turn
            for combo_widget in self.combo_ui_elements:
                combo_widget.hide()
        
        # Direct value updates for responsive display
        self.current_concentration = self.concentration
        self.current_courroux = self.courroux
        self.current_puissance = self.puissance
        self.current_egare = self.egare
        
        # Update concentration bar with smooth transitions
        if self.concentration != self.concentration_bar.target_value:
            self.concentration_bar.setValue(self.current_concentration)
        
        # Progress bar has its own high-frequency timer, no need to update here
        
        # Update Puissance combo bars (show bars based on puissance level) - only when overlay is visible
        if self.overlay_visible and self.in_combat:
            bars_to_show = min(5, self.current_puissance // 10)  # Each bar represents 10 puissance
            if bars_to_show > 0:
                # Only print debug message when state changes
                if bars_to_show != self.last_puissance_bars_state:
                    print(f"DEBUG: Puissance bars showing - puissance: {self.current_puissance}, bars: {bars_to_show}, overlay_visible: {self.overlay_visible}, in_combat: {self.in_combat}")
                    self.last_puissance_bars_state = bars_to_show
                # Reset hidden debug flag when bars become visible
                self.last_puissance_hidden_debug = False
            for i, bar in enumerate(self.puissance_bars):
                if i < bars_to_show:
                    bar.show()
                    # Light up the bar with a bright color
                    bar.setStyleSheet("""
                        QFrame {
                            background-color: rgba(100, 200, 255, 200);
                            border: 1px solid rgba(150, 220, 255, 255);
                            border-radius: 3px;
                        }
                    """)
                else:
                    bar.hide()
        else:
            # Hide all puissance bars when overlay is not visible
            if self.current_puissance > 0 and not self.last_puissance_hidden_debug:
                print(f"DEBUG: Puissance bars hidden despite having puissance - overlay_visible: {self.overlay_visible}, in_combat: {self.in_combat}")
                self.last_puissance_hidden_debug = True
            for bar in self.puissance_bars:
                bar.hide()
            # Reset state tracking when hidden
            self.last_puissance_bars_state = 0
        
        # Update courroux display - only show if we have stacks AND overlay is visible
        if self.current_courroux > 0 and self.overlay_visible and self.in_combat:
            self.courroux_icon.show()
            self.courroux_counter.setText(str(int(self.current_courroux)))
            self.courroux_counter.show()
            # Only print debug message when state changes
            if self.current_courroux != self.last_courroux_state:
                print(f"DEBUG: Courroux showing - stacks: {self.current_courroux}, overlay_visible: {self.overlay_visible}, in_combat: {self.in_combat}")
                self.last_courroux_state = self.current_courroux
            # Reset hidden debug flag when courroux becomes visible
            self.last_courroux_hidden_debug = False
            
            # Realistic bouncing physics for courroux icon
            # Apply gravity to velocity
            self.courroux_bounce_velocity += self.courroux_bounce_gravity
            
            # Update position based on velocity
            self.courroux_bounce_offset += self.courroux_bounce_velocity
            
            # Check for ground collision (bounce)
            if self.courroux_bounce_offset >= self.courroux_ground_level:
                # Hit the ground - reverse velocity and apply damping
                self.courroux_bounce_offset = self.courroux_ground_level
                self.courroux_bounce_velocity = -self.courroux_bounce_velocity * self.courroux_bounce_damping
                
                # Stop bouncing if velocity is too small
                if abs(self.courroux_bounce_velocity) < self.courroux_bounce_min_velocity:
                    self.courroux_bounce_velocity = 0
                    self.courroux_bounce_offset = self.courroux_ground_level
            
            # Apply bounce offset to courroux icon position
            base_x, base_y = self.concentration_bar.pos().x(), self.concentration_bar.pos().y()
            courroux_x = int(base_x + 255)
            courroux_y = int(base_y - 2 + self.courroux_bounce_offset)  # Positive offset = UP from ground level
            
            # Move both icon and counter together
            self.courroux_icon.move(courroux_x, courroux_y)
            self.courroux_counter.move(courroux_x, courroux_y)  # Counter follows the icon
        else:
            self.courroux_icon.hide()
            self.courroux_counter.hide()
            if self.current_courroux > 0 and not self.last_courroux_hidden_debug:
                print(f"DEBUG: Courroux hidden despite having stacks - overlay_visible: {self.overlay_visible}, in_combat: {self.in_combat}")
                self.last_courroux_hidden_debug = True
            # Reset state tracking when hidden
            self.last_courroux_state = 0
        
        # Update préparation display - always show if we have stacks (regardless of turn state)
        if self.current_preparation > 0 and self.in_combat:
            self.preparation_icon.show()
            self.preparation_counter.setText(str(int(self.current_preparation)))
            self.preparation_counter.show()
            # Only print debug message when state changes
            if self.current_preparation != self.last_preparation_state:
                print(f"DEBUG: Préparation showing - stacks: {self.current_preparation}, overlay_visible: {self.overlay_visible}, in_combat: {self.in_combat}")
                self.last_preparation_state = self.current_preparation
            # Reset hidden debug flag when préparation becomes visible
            self.last_preparation_hidden_debug = False
            
            # Apply slide animation for préparation icon (initial slide down)
            if self.preparation_slide_offset > 0:
                # Gradually reduce slide offset (slide down effect)
                self.preparation_slide_offset -= self.preparation_slide_speed
                if self.preparation_slide_offset < 0:
                    self.preparation_slide_offset = 0
            
            # Apply slide offset to préparation icon position
            base_x, base_y = self.concentration_bar.pos().x(), self.concentration_bar.pos().y()
            preparation_x = int(base_x + 290 + self.preparation_offset_x)
            preparation_y = int(base_y - 2 + self.preparation_offset_y - self.preparation_slide_offset + self.preparation_bounce_offset)  # Slide + bounce offset
            
            # Move both icon and counter together
            self.preparation_icon.move(preparation_x, preparation_y)
            self.preparation_counter.move(preparation_x, preparation_y)  # Counter follows the icon
        else:
            self.preparation_icon.hide()
            self.preparation_counter.hide()
            if self.current_preparation > 0 and not self.in_combat and not self.last_preparation_hidden_debug:
                print(f"DEBUG: Préparation hidden due to combat end - stacks: {self.current_preparation}")
                self.last_preparation_hidden_debug = True
            # Reset state tracking when hidden
            self.last_preparation_state = 0
        
        # Apply bounce animation for préparation icon (continuous loop) - ALWAYS runs when préparation exists
        if self.current_preparation > 0 and self.preparation_bounce_loop_active:
            # Only print debug occasionally to avoid spam
            if self.animation_frame % 30 == 0:  # Every 30 frames (0.5 seconds at 60fps)
                print(f"DEBUG: Préparation bouncing active - stacks: {self.current_preparation}, overlay_visible: {self.overlay_visible}, in_combat: {self.in_combat}, loop_delay: {self.preparation_bounce_loop_delay}, bounce_delay: {self.preparation_bounce_delay}, velocity: {self.preparation_bounce_velocity}, offset: {self.preparation_bounce_offset}")
            # Handle delay between bounce loops
            if self.preparation_bounce_loop_delay > 0:
                self.preparation_bounce_loop_delay -= 1
                if self.preparation_bounce_loop_delay == 0:
                    # Start new bounce sequence
                    self.trigger_preparation_bounce()
            # Handle initial delay before first bounce
            elif self.preparation_bounce_delay > 0:
                self.preparation_bounce_delay -= 1
                if self.preparation_bounce_delay == 0:
                    self.trigger_preparation_bounce()
            # Handle active bouncing
            elif self.preparation_bounce_velocity != 0 or self.preparation_bounce_offset != 0:
                # Apply gravity to velocity
                self.preparation_bounce_velocity += self.preparation_bounce_gravity
                
                # Update position based on velocity
                self.preparation_bounce_offset += self.preparation_bounce_velocity
                
                # Check for ground collision (bounce)
                if self.preparation_bounce_offset >= self.preparation_bounce_ground_level:
                    # Hit the ground - reverse velocity and apply damping
                    self.preparation_bounce_offset = self.preparation_bounce_ground_level
                    self.preparation_bounce_velocity = -self.preparation_bounce_velocity * self.preparation_bounce_damping
                    
                    # Stop bouncing if velocity is too small
                    if abs(self.preparation_bounce_velocity) < self.preparation_bounce_min_velocity:
                        self.preparation_bounce_velocity = 0
                        self.preparation_bounce_offset = self.preparation_bounce_ground_level
                        # Start delay for next bounce loop
                        self.preparation_bounce_loop_delay = self.preparation_bounce_loop_delay_max
                        print("DEBUG: Préparation bounce sequence ended - starting loop delay")
            # If none of the above conditions are met, start bouncing immediately
            else:
                print("DEBUG: Préparation bouncing conditions not met - starting bounce immediately")
                self.trigger_preparation_bounce()
            
            # Bounce offset is now applied in the preparation display logic above to avoid duplicate positioning
        
        # Update égaré icon with fade animation (only during Iop's turn)
        if self.current_egare and self.overlay_visible and self.in_combat:
            # Set target alpha to 1.0 for fade in (only when it's Iop's turn)
            self.egare_target_alpha = 1.0
            self.egare_icon.show()
            if not self.egare_visible:
                print("DEBUG: Égaré icon showing (fade in)")
                self.egare_visible = True
                # Initialize slide-in from above
                self.egare_slide_offset = self.egare_slide_max
                # Start fade from 0 to make animation visible
                self.egare_fade_alpha = 0.0
            
            # Position égaré icon well above the first combo bar
            base_x, base_y = self.concentration_bar.pos().x(), self.concentration_bar.pos().y()
            egare_x = base_x  # Same X position as first combo bar
            egare_y = base_y - 50  # Much higher up above the combo bars
            self.egare_icon.move(egare_x, egare_y)
        elif not self.current_egare:
            # Set target alpha to 0.0 for fade out (when égaré is lost)
            self.egare_target_alpha = 0.0
        elif not self.overlay_visible:
            # Set target alpha to 0.0 for fade out when not Iop's turn
            self.egare_target_alpha = 0.0
        
        # Update fade animation (always process, regardless of combat status)
        if self.egare_fade_alpha < self.egare_target_alpha:
            # Fade in
            self.egare_fade_alpha += self.egare_fade_in_speed
            if self.egare_fade_alpha > self.egare_target_alpha:
                self.egare_fade_alpha = self.egare_target_alpha
        elif self.egare_fade_alpha > self.egare_target_alpha:
            # Fade out
            self.egare_fade_alpha -= self.egare_fade_out_speed
            if self.egare_fade_alpha < self.egare_target_alpha:
                self.egare_fade_alpha = self.egare_target_alpha
        
        # Update slide-in offset while fading in
        if self.egare_target_alpha > 0.0 and self.egare_fade_alpha > 0.0 and self.egare_slide_offset > 0:
            self.egare_slide_offset = max(0, self.egare_slide_offset - self.egare_slide_speed)

        # Reposition égaré icon after updating slide offset and fade
        base_x, base_y = self.concentration_bar.pos().x(), self.concentration_bar.pos().y()
        egare_x = base_x
        egare_y = base_y - 50 - self.egare_slide_offset
        self.egare_icon.move(egare_x, egare_y)

        # Apply fade alpha to icon (always process, regardless of combat status)
        self.egare_icon.setFadeAlpha(self.egare_fade_alpha)
        
        # Hide icon when fully faded out (always process, regardless of combat status)
        if self.egare_fade_alpha <= 0.0:
            self.egare_icon.hide()
            if self.egare_visible:
                print("DEBUG: Égaré icon hidden (fully faded out)")
                self.egare_visible = False
                self.egare_slide_offset = 0

        # Animate timeline: increase alpha/slide for newest, fade/slide out overflow if present in buffer
        if self.timeline_entries:
            # Newest entry is at end of list
            newest = self.timeline_entries[-1]
            if newest.get('alpha', 0.0) < 1.0:
                newest['alpha'] = min(1.0, newest.get('alpha', 0.0) + 0.15)
            if newest.get('slide', 0) < 0:
                newest['slide'] = min(0, newest.get('slide', 0) + 4)
            # If we have one extra (overflow), it's the oldest at index 0; animate out
            if len(self.timeline_entries) > self.timeline_max_slots:
                oldest = self.timeline_entries[0]
                oldest['alpha'] = max(0.0, oldest.get('alpha', 1.0) - 0.2)
                # Use positive slide to move right
                oldest['slide'] = oldest.get('slide', 0) + 4
                # When fully faded, drop it
                if oldest['alpha'] <= 0.0:
                    # Remove from buffer
                    self.timeline_entries.pop(0)
            # Refresh display to apply the updated alpha/positions
            self.update_timeline_display()
        
        # Update combo animations only during Iop's turn
        if self.overlay_visible and self.in_combat:
            for combo_widget in self.combo_ui_elements:
                combo_widget.update_animation()

    def add_spell_to_timeline(self, spell_name: str):
        """Add a spell cast to the timeline (tracked player only)."""
        spell_key = spell_name.strip()
        cost = self.spell_cost_map.get(spell_key)
        icon_stem = self.spell_icon_stem_map.get(spell_key)
        if not cost or not icon_stem:
            return  # Unknown spell; ignore
        icon_path = self.base_path / "img" / f"{icon_stem}.png"
        pixmap = QPixmap(str(icon_path)) if icon_path.exists() else None
        # Build entry with animation state
        compact_cost = cost.replace(" ", "")  # e.g., "1 PA" -> "1PA"
        entry = { 'spell': spell_key, 'cost': compact_cost, 'pixmap': pixmap, 'alpha': 0.0, 'slide': -16 }
        # Append and clamp to last N; mark the oldest for fade-out/slide-right if overflow
        overflow_entry = None
        if len(self.timeline_entries) >= self.timeline_max_slots:
            overflow_entry = self.timeline_entries[0]
        self.timeline_entries.append(entry)
        if len(self.timeline_entries) > self.timeline_max_slots:
            # Keep one extra temporarily for animating out the oldest
            self.timeline_entries = self.timeline_entries[-(self.timeline_max_slots + 1):]
        
        # Add to current turn spells and check combo progress
        self.current_turn_spells.append(compact_cost)
        self.check_combo_progress(cost)
        
        # Trigger display refresh
        self.update_timeline_display()

    def update_timeline_display(self):
        """Refresh timeline labels to reflect current entries."""
        # Only update timeline if overlay is visible
        if not (self.overlay_visible and self.in_combat):
            # Hide all timeline elements if overlay is not visible
            for i in range(self.timeline_max_slots):
                self.timeline_icon_labels[i].hide()
                self.timeline_cost_labels[i].hide()
            return
        
        # Ensure positions are up-to-date
        self.position_elements()
        # Fill newest-to-oldest left-to-right (latest cast on the far left)
        for i in range(self.timeline_max_slots):
            entry_index = len(self.timeline_entries) - 1 - i
            if 0 <= entry_index < len(self.timeline_entries):
                entry = self.timeline_entries[entry_index]
                # Set cost text (outlined white, centered)
                self.timeline_cost_labels[i].setText(entry['cost'])
                self.timeline_cost_labels[i].show()
                # Set icon
                if entry['pixmap']:
                    self.timeline_icon_labels[i].setPixmap(entry['pixmap'].scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                else:
                    self.timeline_icon_labels[i].setText("?")
                self.timeline_icon_labels[i].show()
                # Ensure cost overlay stays on top of the icon
                self.timeline_icon_labels[i].raise_()
                self.timeline_cost_labels[i].raise_()
                # Apply opacity and slide based on entry animation state
                # Newest (i == 0) fades in and slides from the left; oldest (if overflow) fades out and slides right
                icon_label = self.timeline_icon_labels[i]
                cost_label = self.timeline_cost_labels[i]
                # Set opacity
                if not hasattr(icon_label, '_opacity'):
                    icon_label._opacity = QGraphicsOpacityEffect()
                    icon_label.setGraphicsEffect(icon_label._opacity)
                if not hasattr(cost_label, '_opacity'):
                    cost_label._opacity = QGraphicsOpacityEffect()
                    cost_label.setGraphicsEffect(cost_label._opacity)
                # Determine target alpha
                is_newest = (i == 0)
                icon_label._opacity.setOpacity(min(1.0, max(0.0, entry.get('alpha', 1.0) if is_newest else 1.0)))
                cost_label._opacity.setOpacity(min(1.0, max(0.0, entry.get('alpha', 1.0) if is_newest else 1.0)))
                # Apply slide offset for newest (both icon and cost move together)
                slide_offset = entry.get('slide', 0) if is_newest else 0
                # Always position cost relative to icon
                base_x, base_y = self.concentration_bar.pos().x(), self.concentration_bar.pos().y()
                timeline_icon_y = base_y + 30
                icon_x = base_x + (i * 32) + slide_offset
                icon_label.move(icon_x, timeline_icon_y)
                # Cost below icon, centered
                cost_x = icon_x + (32 - 32) // 2  # Center the 32px wide cost label under the 32px icon
                cost_y = timeline_icon_y + 32 - 2
                cost_label.move(cost_x, cost_y)
            else:
                self.timeline_icon_labels[i].hide()
                self.timeline_cost_labels[i].hide()
    
    def trigger_courroux_bounce(self):
        """Trigger a bounce animation when courroux is gained"""
        # Set initial upward velocity for the bounce (smaller jump)
        self.courroux_bounce_velocity = -6  # Negative velocity = upward movement (reduced from -12)
        self.courroux_bounce_offset = 0  # Start from ground level
    
    def trigger_preparation_slide(self):
        """Trigger a slide animation when préparation is gained"""
        # Start with slide offset (slide down effect)
        self.preparation_slide_offset = self.preparation_slide_max  # Start this many pixels above
        
        # Start bounce animation immediately (no delay)
        self.preparation_bounce_delay = 0  # No delay - start bouncing immediately
        self.preparation_bounce_velocity = -10  # Start with upward velocity immediately
        self.preparation_bounce_offset = 0  # Start at ground level
        
        # Start continuous bouncing loop
        self.preparation_bounce_loop_active = True
        self.preparation_bounce_loop_delay = 0  # No delay for first bounce
        
        print("DEBUG: Préparation slide and immediate bounce loop triggered")
    
    def trigger_preparation_bounce(self):
        """Trigger the actual bounce animation after delay"""
        # Start with upward velocity (negative = up) - bigger initial jump
        self.preparation_bounce_velocity = -10  # Negative velocity = upward movement (faster than before)
        self.preparation_bounce_offset = 0  # Start from ground level
        self.preparation_bounce_delay = 0  # Clear the delay
        print(f"DEBUG: Préparation bounce animation started - overlay_visible: {self.overlay_visible}")
    
    def save_positions(self):
        """Save current positions to config file"""
        try:
            positions = {
                'concentration_bar': {
                    'x': self.concentration_bar.x(),
                    'y': self.concentration_bar.y()
                },
                'combo_group_offset': {
                    'x': self.combo_group_offset_x,
                    'y': self.combo_group_offset_y
                },
                'preparation_offset': {
                    'x': self.preparation_offset_x,
                    'y': self.preparation_offset_y
                },
                'positions_locked': self.positions_locked
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(positions, f, indent=2)
            pass  # Positions saved silently
        except Exception as e:
            pass  # Silently handle save errors
    
    def load_positions(self):
        """Load positions from config file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    positions = json.load(f)
                
                if 'concentration_bar' in positions:
                    x, y = positions['concentration_bar']['x'], positions['concentration_bar']['y']
                    self.concentration_bar.move(x, y)
                
                if 'combo_group_offset' in positions:
                    self.combo_group_offset_x = positions['combo_group_offset']['x']
                    self.combo_group_offset_y = positions['combo_group_offset']['y']
                
                if 'preparation_offset' in positions:
                    self.preparation_offset_x = positions['preparation_offset']['x']
                    self.preparation_offset_y = positions['preparation_offset']['y']
                
                if 'positions_locked' in positions:
                    self.positions_locked = positions['positions_locked']
        except Exception as e:
            pass  # Silently handle load errors
    
    def mousePressEvent(self, event):
        """Handle mouse press for dragging concentration bar or combo columns separately"""
        if event.button() == Qt.MouseButton.LeftButton and not self.positions_locked:
            click_pos = event.globalPosition().toPoint()
            
            # Check if click is on concentration bar
            concentration_rect = self.concentration_bar.geometry()
            if concentration_rect.contains(click_pos):
                self.drag_start_position = click_pos - self.concentration_bar.frameGeometry().topLeft()
                self.dragging_concentration = True
                self.dragging_combos = False
                print("DEBUG: Started dragging concentration bar")
                return
            
            # Check if click is on any combo column
            for combo_widget in self.combo_ui_elements:
                if combo_widget.isVisible():
                    combo_rect = combo_widget.geometry()
                    if combo_rect.contains(click_pos):
                        # Calculate offset from concentration bar for combo group
                        combo_base_x = self.concentration_bar.x() + self.combo_group_offset_x
                        combo_base_y = self.concentration_bar.y() + 80 + self.combo_group_offset_y
                        self.drag_start_position = click_pos - QPoint(combo_base_x, combo_base_y)
                        self.dragging_concentration = False
                        self.dragging_combos = True
                        self.dragging_preparation = False
                        print("DEBUG: Started dragging combo group")
                        return
            
            # Check if click is on preparation icon
            if self.preparation_icon.isVisible():
                preparation_rect = self.preparation_icon.geometry()
                if preparation_rect.contains(click_pos):
                    # Calculate offset from concentration bar for preparation
                    preparation_base_x = self.concentration_bar.x() + 290 + self.preparation_offset_x
                    preparation_base_y = self.concentration_bar.y() - 2 + self.preparation_offset_y
                    self.drag_start_position = click_pos - QPoint(preparation_base_x, preparation_base_y)
                    self.dragging_concentration = False
                    self.dragging_combos = False
                    self.dragging_preparation = True
                    print("DEBUG: Started dragging preparation icon")
                    return
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging concentration bar or combo columns separately"""
        if event.buttons() == Qt.MouseButton.LeftButton and not self.positions_locked:
            if self.dragging_concentration:
                # Move concentration bar and all other elements
                new_pos = event.globalPosition().toPoint() - self.drag_start_position
                self.concentration_bar.move(new_pos)
                self.position_elements()
                self.auto_save_positions()
                print(f"DEBUG: Moving concentration bar to {new_pos}")
            elif self.dragging_combos:
                # Move only combo columns
                new_pos = event.globalPosition().toPoint() - self.drag_start_position
                combo_base_x = self.concentration_bar.x() + 80  # Default combo position
                combo_base_y = self.concentration_bar.y() + 80
                
                # Calculate new offset from concentration bar
                self.combo_group_offset_x = new_pos.x() - combo_base_x
                self.combo_group_offset_y = new_pos.y() - combo_base_y
                
                # Update combo positions
                self.position_elements()
                self.auto_save_positions()
                print(f"DEBUG: Moving combo group - offset: ({self.combo_group_offset_x}, {self.combo_group_offset_y})")
            elif self.dragging_preparation:
                # Move only preparation icon
                new_pos = event.globalPosition().toPoint() - self.drag_start_position
                preparation_base_x = self.concentration_bar.x() + 290  # Default preparation position
                preparation_base_y = self.concentration_bar.y() - 2
                
                # Calculate new offset from concentration bar
                self.preparation_offset_x = new_pos.x() - preparation_base_x
                self.preparation_offset_y = new_pos.y() - preparation_base_y
                
                # Update preparation position
                self.position_elements()
                self.auto_save_positions()
                print(f"DEBUG: Moving preparation icon - offset: ({self.preparation_offset_x}, {self.preparation_offset_y})")
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release to stop dragging"""
        if event.button() == Qt.MouseButton.LeftButton:
            if self.dragging_concentration:
                print("DEBUG: Stopped dragging concentration bar")
            elif self.dragging_combos:
                print("DEBUG: Stopped dragging combo group")
            elif self.dragging_preparation:
                print("DEBUG: Stopped dragging preparation icon")
            self.dragging_concentration = False
            self.dragging_combos = False
            self.dragging_preparation = False
    
    def auto_save_positions(self):
        """Auto-save positions with a delay to avoid too frequent saves"""
        if self.auto_save_timer:
            self.auto_save_timer.stop()
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.save_positions)
        self.auto_save_timer.setSingleShot(True)
        self.auto_save_timer.start(500)
    
    def closeEvent(self, event):
        """Handle close event"""
        self.save_positions()
        self.log_monitor.stop_monitoring()
        self.log_monitor.wait()
        # Stop progress bar timer
        self.concentration_bar.progress_timer.stop()
        event.accept()

def main():
    """Main function"""
    app = QApplication(sys.argv)
    
    # Check if running in hidden mode (from launcher)
    hidden_mode = "--hidden" in sys.argv
    
    # Set application properties
    app.setApplicationName("Wakfu Iop Resource Tracker")
    app.setApplicationVersion("1.0")
    
    # Create and show main window
    window = WakfuIopResourceTracker(hidden_mode=hidden_mode)
    
    # Only show window if not in hidden mode
    if not hidden_mode:
        window.show()
    else:
        # In hidden mode, show window but minimize it
        window.show()
        window.showMinimized()
    
    # Start event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
