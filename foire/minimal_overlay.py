import cv2
import numpy as np
import customtkinter as ctk
import tkinter as tk
import threading
import time
import pyautogui
import os
import sys
from PIL import ImageGrab, Image
import mss
import glob
from datetime import datetime
import json
import re
import win32gui
import win32con
from pynput import mouse

class MinimalWakfuOverlay:
    def __init__(self):
        try:
            # Resolve base directories (supports PyInstaller onefile)
            self.base_dir = getattr(sys, '_MEIPASS', os.path.dirname(__file__))
            # Writable app data dir for persistent files (sequences, etc.)
            self.appdata_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'GYard')
            if not os.path.exists(self.appdata_dir):
                try:
                    os.makedirs(self.appdata_dir, exist_ok=True)
                except Exception:
                    pass
            
            # Configure CustomTkinter
            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("blue")
            
            self.root = ctk.CTk()
            self.root.title("Wakfu Bot")
            # Window dimensions used across the app
            self.window_width = 340
            self.window_height = 170
            self.root.geometry(f"{self.window_width}x{self.window_height}")
            self.root.resizable(True, True)
            self.root.minsize(300, 140)
            
            # Configure window properties
            self.root.attributes('-topmost', True)
            self.root.attributes('-alpha', 0.9)
            self.root.overrideredirect(True)
            
            # Drag and drop variables
            self.drag_start_x = 0
            self.drag_start_y = 0
            self.is_dragging = False
            
            # Bot state
            self.is_monitoring = False
            self.is_recording = False
            self.is_sequence_selection_mode = False
            self.confidence_threshold = 0.7
            self.selected_sequence_id = None
            
            # Automation workflow state
            self.current_main_step = 1
            self.current_sub_step = 1
            self.log_trigger_found = False
            
            # Game state tracking (OUTSIDE, SAS, MINIGAME, UNKNOWN)
            self.game_state = "UNKNOWN"
            self.last_state_check_time = 0
            self.state_check_interval = 5.0
            self.state_checked_this_cycle = False
            
            # Periodic safety check timer
            self.last_periodic_check_time = 0
            self.periodic_check_interval = 60.0
            
            # Recording state
            self.recording_sequence = []
            self.recording_start_time = None
            self.recording_timer_detected = False
            self.mouse_listener = None
            self.screen_center_x = None
            self.screen_center_y = None
            
            # Debug tracking for recording
            self.debug_npc_interaction_detected = False
            self.debug_door_opened_detected = False
            self.last_recorded_action_index = -1  # Track last displayed action
            self.dialogue2_ready_for_click = False  # Flag: dialogue2 detected, waiting for user click
            self.recording_kamas_loss_detected = False  # Flag: kamas loss detected during recording
            self.recording_log_file_position = None  # Track log file position during recording
            self.recording_log_file_path = None  # Cached log file path during recording
            
            # Mini-game state
            self.mini_game_active = False
            self.mini_game_start_time = None
            self.mini_game_duration = 60.0
            
            # Statistics tracking (per sequence)
            self.current_run_resources = {}
            self.current_sequence_id = None
        
            # Sequences storage (in AppData so it's writable when packaged)
            self.sequences_dir = os.path.join(self.appdata_dir, 'sequences')
            self.sequences_file = os.path.join(self.sequences_dir, "sequences.json")
            self.sequences = {}  # {id: {name, clicks, runs, total_boissons, avg_boissons, created_at, runs_data}}
            self.load_sequences()
            
            # Load template images for debug detection
            self.templates = {}
            self.load_templates()
            
            # Log monitoring - auto-detect path
            self.log_path = self.auto_detect_log_path()
            if not self.log_path:
                print("[DEBUG] Warning: Could not auto-detect Wakfu log path. Will try to find log file manually.")
            self.kamas_loss_pattern = r"Vous avez perdu\s+(\d+)\s+kamas"
            # Detect leaving mini-game via ticket loss
            self.ticket_loss_pattern = r"\[Information \(jeu\)\] Vous avez perdu\s+\d+x\s+Ticket du"
            self.resource_log_pattern = r"\[Information \(jeu\)\] Vous avez ramassé (\d+)x (.+) \."
            self.log_monitoring = False
            self.log_file_position = None
            self.left_minigame_detected = False
            # Live stats: total Boisson de Frayeur since app start
            self.total_frayeur_since_start = 0
            
            # Create UI
            self.create_minimal_ui()
            
            # Position overlay
            self.position_overlay()
            
            # Start F12 monitoring
            self.start_f12_monitoring()
            
            # Start the application
            self.root.mainloop()
        except Exception as e:
            import traceback
            print(f"Error initializing application: {e}")
            traceback.print_exc()
            input("Press Enter to exit...")
    
    def load_sequences(self):
        """Load all sequences from file"""
        try:
            print(f"[DEBUG] Sequences directory: {self.sequences_dir}")
            print(f"[DEBUG] Sequences file: {self.sequences_file}")
            
            if not os.path.exists(self.sequences_dir):
                os.makedirs(self.sequences_dir)
            
            if os.path.exists(self.sequences_file):
                with open(self.sequences_file, 'r', encoding='utf-8') as f:
                    self.sequences = json.load(f)
                print(f"[DEBUG] Loaded {len(self.sequences)} sequence(s) from: {self.sequences_file}")
                for seq_id, seq_data in self.sequences.items():
                    print(f"[DEBUG]   - Sequence ID: {seq_id}, Name: '{seq_data.get('name', 'unknown')}', Clicks: {len(seq_data.get('clicks', []))}")
            else:
                self.sequences = {}
                print(f"[DEBUG] No sequences file found at: {self.sequences_file}")
        except Exception as e:
            print(f"Error loading sequences: {e}")
            self.sequences = {}
    
    def save_sequences(self):
        """Save all sequences to file"""
        try:
            if not os.path.exists(self.sequences_dir):
                os.makedirs(self.sequences_dir)
            
            with open(self.sequences_file, 'w', encoding='utf-8') as f:
                json.dump(self.sequences, f, indent=2, ensure_ascii=False)
            print(f"[DEBUG] Saved {len(self.sequences)} sequence(s) to: {self.sequences_file}")
        except Exception as e:
            print(f"Error saving sequences: {e}")
    
    def load_templates(self):
        """Load template images for debug detection"""
        base_path = os.path.join(self.base_dir, "images")
        template_paths = {
            'pnj': {
                'day': os.path.join(base_path, "Screenshots.png"),
                'night': os.path.join(base_path, "Screenshots_nuit.png") if os.path.exists(os.path.join(base_path, "Screenshots_nuit.png")) else None
            },
            'dialogue1': {
                'day': os.path.join(base_path, "dialogue1.png"),
                'night': os.path.join(base_path, "dialogue1_nuit.png") if os.path.exists(os.path.join(base_path, "dialogue1_nuit.png")) else None
            },
            'dialogue2': {
                'day': os.path.join(base_path, "dialogue2.png"),
                'night': os.path.join(base_path, "dialogue2_nuit.png") if os.path.exists(os.path.join(base_path, "dialogue2_nuit.png")) else None
            },
            'porte': {
                'day': os.path.join(base_path, "porte.png"),
                'night': os.path.join(base_path, "porte_nuit.png") if os.path.exists(os.path.join(base_path, "porte_nuit.png")) else None
            },
            'porte2': os.path.join(base_path, "porte2.png"),
            'porte3': os.path.join(base_path, "porte3.png"),
            'maptoggle': os.path.join(base_path, "maptoggle.png"),
            'maptoggle2': os.path.join(base_path, "maptoggle2.png"),
            'maptoggle3': os.path.join(base_path, "maptoggle3.png"),
            'maphint1': os.path.join(base_path, "maphint1.png")
        }
        
        for name, variants in template_paths.items():
            self.templates[name] = {}
            if isinstance(variants, dict):
                for time_of_day, path in variants.items():
                    if path and os.path.exists(path):
                        try:
                            template = cv2.imread(path, cv2.IMREAD_COLOR)
                            if template is not None:
                                self.templates[name][time_of_day] = template
                        except Exception as e:
                            print(f"Error loading {name} ({time_of_day}): {e}")
            else:
                # Single variant template (porte2, porte3)
                if os.path.exists(variants):
                    try:
                        template = cv2.imread(variants, cv2.IMREAD_COLOR)
                        if template is not None:
                            self.templates[name]['day'] = template  # Default to day
                    except Exception as e:
                        print(f"Error loading {name}: {e}")
    
    def detect_template_dual(self, img, template_name):
        """Detect template using both day and night variants"""
        if template_name not in self.templates:
            return False, 0, None, None
        
        best_confidence = 0
        best_location = None
        best_template = None
        
        # Try both day and night variants
        template_data = self.templates[template_name]
        if isinstance(template_data, dict):
            for time_of_day in ['day', 'night']:
                if time_of_day in template_data:
                    try:
                        template = template_data[time_of_day]
                        result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
                        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                        
                        if max_val > best_confidence:
                            best_confidence = max_val
                            best_location = max_loc
                            best_template = template
                    except Exception as e:
                        pass
        
        is_detected = best_confidence >= self.confidence_threshold
        return is_detected, best_confidence, best_location, best_template
    
    def detect_maptoggle_variants(self, img):
        """Detect maptoggle using available variants"""
        best_confidence = 0
        best_location = None
        best_template = None
        
        maptoggle_variants = ['maptoggle', 'maptoggle2', 'maptoggle3']
        
        for toggle_name in maptoggle_variants:
            if toggle_name in self.templates:
                template_data = self.templates[toggle_name]
                if isinstance(template_data, dict):
                    for key in template_data:
                        try:
                            template = template_data[key]
                            result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
                            _, max_val, _, max_loc = cv2.minMaxLoc(result)
                            
                            if max_val > best_confidence:
                                best_confidence = max_val
                                best_location = max_loc
                                best_template = template
                        except Exception:
                            pass
        is_detected = best_confidence >= self.confidence_threshold
        return is_detected, best_confidence, best_location, best_template
    
    def get_game_state(self):
        """
        Determine game state (OUTSIDE, SAS, MINIGAME) using the maptoggle tooltip.
        Returns: "OUTSIDE", "SAS", "MINIGAME", or "UNKNOWN"
        """
        try:
            if not self.is_monitoring:
                return "UNKNOWN"
            
            img = self.capture_screen()
            if img is None:
                self.game_state = "UNKNOWN"
                return "UNKNOWN"
            
            detected, confidence, max_loc, template = self.detect_maptoggle_variants(img)
            if not detected or max_loc is None or template is None:
                print(f"[STATE] Maptoggle not found (confidence {confidence:.2f if confidence else 0:.2f})")
                self.game_state = "UNKNOWN"
                return "UNKNOWN"
            
            template_h, template_w = template.shape[:2]
            hover_x = int(max_loc[0] + template_w // 2)
            hover_y = int(max_loc[1] + template_h // 2)
            
            if not self.is_monitoring:
                return "UNKNOWN"
            
            # Preserve current cursor position to restore later
            try:
                current_pos = pyautogui.position()
            except Exception:
                current_pos = None
            
            try:
                pyautogui.moveTo(hover_x, hover_y)
                time.sleep(0.8)
                
                if not self.is_monitoring:
                    return "UNKNOWN"
                
                img_after = self.capture_screen()
                if img_after is None:
                    self.game_state = "UNKNOWN"
                    return "UNKNOWN"
            finally:
                if current_pos is not None:
                    try:
                        pyautogui.moveTo(current_pos.x, current_pos.y)
                    except Exception:
                        pass
            
            tooltip_detected = False
            if 'maphint1' in self.templates:
                hint_data = self.templates['maphint1']
                if isinstance(hint_data, dict):
                    hint_template = hint_data.get('day')
                    if hint_template is not None:
                        try:
                            result = cv2.matchTemplate(img_after, hint_template, cv2.TM_CCOEFF_NORMED)
                            _, hint_conf, _, _ = cv2.minMaxLoc(result)
                            tooltip_detected = hint_conf >= self.confidence_threshold
                        except Exception:
                            pass
            
            if tooltip_detected:
                state = "MINIGAME" if self.mini_game_active else "SAS"
            else:
                state = "OUTSIDE"
            
            self.game_state = state
            print(f"[STATE] {state} (tooltip {'detected' if tooltip_detected else 'not detected'}, maptoggle confidence {confidence:.2f})")
            return state
        except Exception as e:
            print(f"[STATE] Error determining game state: {e}")
            self.game_state = "UNKNOWN"
            return "UNKNOWN"
    
    def detect_door_variants(self, img):
        """Detect door using all available variants"""
        best_confidence = 0
        best_location = None
        best_template = None
        
        door_variants = ['porte', 'porte2', 'porte3']
        
        for door_name in door_variants:
            if door_name in self.templates:
                template_data = self.templates[door_name]
                if isinstance(template_data, dict):
                    for time_of_day in ['day', 'night']:
                        if time_of_day in template_data:
                            try:
                                template = template_data[time_of_day]
                                result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
                                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                                
                                if max_val > best_confidence:
                                    best_confidence = max_val
                                    best_location = max_loc
                                    best_template = template
                            except Exception as e:
                                pass
        
        is_detected = best_confidence >= self.confidence_threshold
        return is_detected, best_confidence, best_location, best_template
    
    def position_overlay(self):
        """Position overlay in top-right corner of Wakfu window"""
        try:
            def enum_windows_callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    window_title = win32gui.GetWindowText(hwnd)
                    if "wakfu" in window_title.lower():
                        windows.append(hwnd)
                return True
            
            windows = []
            win32gui.EnumWindows(enum_windows_callback, windows)
            
            if windows:
                wakfu_hwnd = windows[0]
                rect = win32gui.GetWindowRect(wakfu_hwnd)
                x = rect[2] - (self.window_width + 20)
                y = rect[1] + 10
                self.root.geometry(f"{self.window_width}x{self.window_height}+{x}+{y}")
            else:
                screen_width = self.root.winfo_screenwidth()
                self.root.geometry(f"{self.window_width}x{self.window_height}+{screen_width-(self.window_width+20)}+10")
        except Exception as e:
            screen_width = self.root.winfo_screenwidth()
            self.root.geometry(f"{self.window_width}x{self.window_height}+{screen_width-(self.window_width+20)}+10")
    
    def start_f12_monitoring(self):
        """Start monitoring F12 key for toggle"""
        def monitor_f12():
            from pynput import keyboard
            
            def on_key_press(key):
                try:
                    if key == keyboard.Key.f12:
                        self.toggle_monitoring()
                except Exception as e:
                    pass
            
            listener = keyboard.Listener(on_press=on_key_press)
            listener.start()
            
            while True:
                time.sleep(0.1)
        
        f12_thread = threading.Thread(target=monitor_f12, daemon=True)
        f12_thread.start()
    
    def create_minimal_ui(self):
        """Create minimal overlay UI"""
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Ultra-minimal container (fully transparent, no border)
        main_frame = ctk.CTkFrame(
            self.root,
            fg_color="transparent",
            corner_radius=0,
            border_width=0
        )
        main_frame.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        main_frame.grid_rowconfigure(2, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        # Remove duplicate large status text to keep minimalism
        self.status_label = None
        
        # (Removed old loaded sequence label to save vertical space)
        
        # Step label
        self.step_label = ctk.CTkLabel(
            main_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#00ff88"
        )
        self.step_label.grid(row=99, column=0, pady=(0, 2), sticky="ew")
        # Hidden by default; shown only while running/recording
        self.step_label.grid_remove()
        
        # Recording countdown label (hidden by default)
        self.countdown_label = ctk.CTkLabel(
            main_frame,
            text="",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#ffaa00"
        )
        self.countdown_label.grid(row=1, column=0, pady=(0, 2), sticky="ew")
        self.countdown_label.grid_remove()  # Hidden by default
        
        # Recording action label (hidden by default)
        self.action_label = ctk.CTkLabel(
            main_frame,
            text="",
            font=ctk.CTkFont(size=10),
            text_color="#00ff88"
        )
        self.action_label.grid(row=2, column=0, pady=(0, 2), sticky="ew")
        self.action_label.grid_remove()  # Hidden by default
        
        # Live Frayeur counter
        stats_frame = ctk.CTkFrame(main_frame, fg_color="transparent", corner_radius=0)
        # Place stats below buttons with minimal spacing
        stats_frame.grid(row=2, column=0, pady=(2, 0), sticky="ew", padx=4)
        stats_frame.grid_columnconfigure(0, weight=0)
        stats_frame.grid_columnconfigure(1, weight=1)
        stats_frame.grid_rowconfigure(0, weight=1)

        # Try to load frayeur icon
        frayeur_path = os.path.join(self.base_dir, "images", "frayeur.png")
        self.frayeur_icon = None
        self.frayeur_pil_image = None
        try:
            if os.path.exists(frayeur_path):
                self.frayeur_pil_image = Image.open(frayeur_path)
                # Slightly smaller default than before; will resize responsively
                self.frayeur_icon = ctk.CTkImage(light_image=self.frayeur_pil_image, dark_image=self.frayeur_pil_image, size=(56, 56))
        except Exception:
            self.frayeur_icon = None

        if self.frayeur_icon:
            self.frayeur_icon_label = ctk.CTkLabel(stats_frame, image=self.frayeur_icon, text="")
            # Keep tight padding and center vertically in the row
            self.frayeur_icon_label.grid(row=0, column=0, padx=(4, 4), pady=0, sticky="w")
        else:
            # Fallback to text if image missing
            self.frayeur_icon_label = ctk.CTkLabel(stats_frame, text="🧪", font=ctk.CTkFont(size=14))
            self.frayeur_icon_label.grid(row=0, column=0, padx=(6, 6), pady=4, sticky="w")

        # Horizontal row: value and caption to the right of the icon
        text_row = ctk.CTkFrame(stats_frame, fg_color="transparent")
        text_row.grid(row=0, column=1, sticky="w")
        text_row.grid_columnconfigure(0, weight=0)
        text_row.grid_columnconfigure(1, weight=0)
        self.frayeur_value_label = ctk.CTkLabel(
            text_row,
            text="0",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#ffd166"
        )
        self.frayeur_value_label.grid(row=0, column=0, sticky="w")
        self.frayeur_caption_label = ctk.CTkLabel(
            text_row,
            text="from start",
            font=ctk.CTkFont(size=11),
            text_color="#9aa4b2"
        )
        self.frayeur_caption_label.grid(row=0, column=1, sticky="w", padx=(4, 0))

        # Responsive: adjust icon sizes when the window resizes
        try:
            self.root.bind('<Configure>', self.on_window_resize)
        except Exception:
            pass
        
        # Control buttons
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        # Put buttons at the top
        button_frame.grid(row=0, column=0, pady=(0, 0), sticky="ew", padx=4)
        button_frame.grid_columnconfigure(0, weight=1, uniform="buttons")
        button_frame.grid_columnconfigure(1, weight=1, uniform="buttons")
        button_frame.grid_columnconfigure(2, weight=1, uniform="buttons")
        # Row 0: status pill (top-left), spacer, run name (top-right)
        self.status_pill = ctk.CTkFrame(button_frame, fg_color="#2a2f36", corner_radius=999)
        self.status_pill.grid(row=0, column=0, sticky="w")
        self.status_pill_label = ctk.CTkLabel(
            self.status_pill,
            text="Ready",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#cbd5e1"
        )
        self.status_pill_label.pack(padx=6, pady=2)
        spacer1 = ctk.CTkLabel(button_frame, text="")
        spacer1.grid(row=0, column=1, sticky="ew")

        # Start button (behaves like F12 when stopped)
        self.start_button = ctk.CTkButton(
            button_frame,
            text="▶ F12",
            command=self.on_start_click,
            font=ctk.CTkFont(size=13, weight="bold"),
            height=30,
            fg_color="#00ff88",
            hover_color="#00cc66",
            text_color="#000000"
        )
        self.start_button.grid(row=1, column=0, padx=(0, 4), sticky="ew")

        # Stop button (behaves like F12 when running)
        self.stop_button = ctk.CTkButton(
            button_frame,
            text="⏹ F12",
            command=self.on_stop_click,
            font=ctk.CTkFont(size=13, weight="bold"),
            height=30,
            fg_color="#ff4444",
            hover_color="#cc3333",
            text_color="#ffffff"
        )
        self.stop_button.grid(row=1, column=1, padx=4, sticky="ew")

        # Load button (opens sequences selection)
        # Right column: put the run name directly in row 0 so the entire row pushes all buttons
        self.loaded_sequence_mini_label = ctk.CTkLabel(
            button_frame,
            text="No run selected",
            font=ctk.CTkFont(size=11),
            text_color="#9aa4b2"
        )
        self.loaded_sequence_mini_label.grid(row=0, column=2, sticky="e", pady=(0, 2), padx=(4, 0))
        self.load_button = ctk.CTkButton(
            button_frame,
            text="📂 Load",
            command=self.on_load_click,
            font=ctk.CTkFont(size=12, weight="bold"),
            height=30,
            fg_color="#444444",
            hover_color="#555555",
            text_color="#ffffff"
        )
        self.load_button.grid(row=1, column=2, sticky="ew", padx=(4, 0))

        # Initialize control state
        self.update_controls_state()
        
        # Enable drag and drop for the overlay
        self.setup_drag_and_drop(main_frame)
    
    def setup_drag_and_drop(self, widget):
        """Setup drag and drop functionality for the overlay"""
        def is_button_widget(widget):
            """Check if widget is a button or contains a button"""
            if isinstance(widget, ctk.CTkButton):
                return True
            # Check if widget has button as child
            try:
                for child in widget.winfo_children():
                    if isinstance(child, ctk.CTkButton):
                        return True
            except:
                pass
            return False
        
        def start_drag(event):
            # Don't start drag if clicking on a button
            try:
                clicked_widget = event.widget
                if is_button_widget(clicked_widget):
                    # Check if we're actually clicking the button itself
                    # Get widget type from the clicked widget
                    widget_class = clicked_widget.winfo_class()
                    if 'Button' in str(type(clicked_widget)) or 'Button' in widget_class:
                        return  # Don't drag if clicking button
            except:
                pass
            
            self.is_dragging = True
            self.drag_start_x = event.x_root
            self.drag_start_y = event.y_root
        
        def on_drag(event):
            if self.is_dragging:
                # Calculate how much the mouse moved
                dx = event.x_root - self.drag_start_x
                dy = event.y_root - self.drag_start_y
                
                # Get current window position
                x = self.root.winfo_x() + dx
                y = self.root.winfo_y() + dy
                
                # Update window position
                self.root.geometry(f"+{x}+{y}")
                
                # Update drag start position for next movement
                self.drag_start_x = event.x_root
                self.drag_start_y = event.y_root
        
        def stop_drag(event):
            self.is_dragging = False
        
        # Bind to main frame
        widget.bind("<Button-1>", start_drag)
        widget.bind("<B1-Motion>", on_drag)
        widget.bind("<ButtonRelease-1>", stop_drag)
        
        # Bind to labels and frames (but not buttons - they handle their own clicks)
        def bind_non_button_children(parent):
            for child in parent.winfo_children():
                if isinstance(child, (ctk.CTkLabel, ctk.CTkFrame)):
                    child.bind("<Button-1>", start_drag)
                    child.bind("<B1-Motion>", on_drag)
                    child.bind("<ButtonRelease-1>", stop_drag)
                    # Recursively bind to children
                    bind_non_button_children(child)
                elif isinstance(child, ctk.CTkScrollableFrame):
                    child.bind("<Button-1>", start_drag)
                    child.bind("<B1-Motion>", on_drag)
                    child.bind("<ButtonRelease-1>", stop_drag)
                    bind_non_button_children(child)
                # Skip CTkButton widgets - they need to handle clicks normally
        
        bind_non_button_children(widget)
    
    def update_status(self, message):
        """Update status message"""
        # Minimalistic: only the colored pill reflects state
        try:
            self.set_status_pill_from_message(message)
        except Exception:
            pass
        # Keep controls state in sync
        self.update_controls_state()

    def set_status_pill_from_message(self, message):
        """Derive pill color/text from a status message for quick visual feedback."""
        text = message.lower()
        # Defaults
        pill_color = "#2a2f36"
        pill_text = message if len(message) <= 24 else message[:24] + "…"
        text_color = "#cbd5e1"
        if any(w in text for w in ["running", "🚀", "mini-game active", "playing"]):
            pill_color = "#00a86b"  # green
            text_color = "#041b10"
            pill_text = "Running"
        elif any(w in text for w in ["stopped", "⏹", "error", "failed", "❌"]):
            pill_color = "#b4232c"  # red
            text_color = "#fff5f5"
            pill_text = "Stopped"
        elif any(w in text for w in ["recording", "🎬", "⏱"]):
            pill_color = "#e39a1c"  # amber
            text_color = "#1f1300"
            pill_text = "Recording"
        elif any(w in text for w in ["ready", "loaded", "✅"]):
            pill_color = "#384454"
            text_color = "#cbd5e1"
            pill_text = "Ready"
        # Apply
        try:
            self.status_pill.configure(fg_color=pill_color)
            self.status_pill_label.configure(text=pill_text, text_color=text_color)
        except Exception:
            pass
    
    def toggle_monitoring(self):
        """Toggle monitoring on/off (for F12 key)"""
        if not self.is_monitoring:
            # Check if we have a loaded sequence
            if not self.selected_sequence_id or self.selected_sequence_id not in self.sequences:
                # No sequence loaded - show selection UI
                if len(self.sequences) == 0:
                    self.show_sequence_selection()
                else:
                    self.show_sequence_selection()
            else:
                # Sequence loaded - start automation
                self.start_monitoring()
        else:
            self.stop_monitoring()
        # Sync buttons after toggle
        self.update_controls_state()

    def on_start_click(self):
        """Start button: behaves like F12 when stopped"""
        if not self.is_monitoring:
            # Same behavior as F12 when stopped
            if not self.selected_sequence_id or self.selected_sequence_id not in self.sequences:
                self.show_sequence_selection()
            else:
                self.start_monitoring()
        self.update_controls_state()

    def on_stop_click(self):
        """Stop button: behaves like F12 when running"""
        if self.is_monitoring:
            self.stop_monitoring()
        self.update_controls_state()

    def on_load_click(self):
        """Open the sequence selection window"""
        self.show_sequence_selection()
        self.update_controls_state()

    def update_controls_state(self):
        """Enable/disable Start/Stop based on current state"""
        try:
            if self.is_monitoring:
                # Running: disable Start, enable Stop
                self.start_button.configure(state="disabled")
                self.stop_button.configure(state="normal")
            else:
                # Stopped: enable Start, disable Stop
                self.start_button.configure(state="normal")
                self.stop_button.configure(state="disabled")
            # Load is always allowed
            self.load_button.configure(state="normal")
        except Exception:
            pass
    
    def show_sequence_selection(self):
        """Show sequence selection overlay in center of screen"""
        self.is_sequence_selection_mode = True
        
        # Create selection window
        self.selection_window = ctk.CTkToplevel(self.root)
        self.selection_window.title("Select Sequence")
        self.selection_window.attributes('-topmost', True)
        self.selection_window.attributes('-alpha', 0.95)
        
        # Center window on screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = 600
        window_height = 500
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.selection_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Configure grid
        self.selection_window.grid_rowconfigure(1, weight=1)
        self.selection_window.grid_columnconfigure(0, weight=1)
        
        # Title
        title_label = ctk.CTkLabel(
            self.selection_window,
            text="Select Sequence to Play",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#ffffff"
        )
        title_label.grid(row=0, column=0, pady=15)
        
        # Scrollable frame for sequences
        scroll_frame = ctk.CTkScrollableFrame(self.selection_window, fg_color="#2a2a2a")
        scroll_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        scroll_frame.grid_columnconfigure(0, weight=1)
        
        # Get sorted sequences by efficiency
        sorted_sequences = self.get_sorted_sequences()
        
        if len(sorted_sequences) == 0:
            # No sequences - show record button
            record_btn = ctk.CTkButton(
                scroll_frame,
                text="🎬 Record New Sequence",
                command=self.start_recording_mode,
                font=ctk.CTkFont(size=16, weight="bold"),
                height=60,
                fg_color="#00ff88",
                hover_color="#00cc66",
                text_color="#000000"
            )
            record_btn.grid(row=0, column=0, pady=20, sticky="ew")
            
            info_label = ctk.CTkLabel(
                scroll_frame,
                text="No sequences recorded yet.\nClick above to record your first sequence!",
                font=ctk.CTkFont(size=12),
                text_color="#aaaaaa"
            )
            info_label.grid(row=1, column=0, pady=10)
        else:
            # Display sequences
            for idx, (seq_id, seq_data) in enumerate(sorted_sequences[:5]):  # Max 5 sequences
                self.create_sequence_item(scroll_frame, seq_id, seq_data, idx)
            
            # Add record button if less than 5 sequences
            if len(sorted_sequences) < 5:
                record_btn = ctk.CTkButton(
                    scroll_frame,
                    text="➕ Record New Sequence",
                    command=self.start_recording_mode,
                    font=ctk.CTkFont(size=14),
                    height=40,
                    fg_color="#444444",
                    hover_color="#555555"
                )
                record_btn.grid(row=len(sorted_sequences), column=0, pady=10, sticky="ew")
        
        # Close button
        close_btn = ctk.CTkButton(
            self.selection_window,
            text="Cancel",
            command=self.close_sequence_selection,
            font=ctk.CTkFont(size=12),
            height=35,
            fg_color="#444444",
            hover_color="#555555"
        )
        close_btn.grid(row=2, column=0, pady=15)
    
    def create_sequence_item(self, parent, seq_id, seq_data, rank):
        """Create a sequence item in the selection list"""
        item_frame = ctk.CTkFrame(parent, fg_color="#333333", corner_radius=5)
        item_frame.grid(row=rank, column=0, pady=5, sticky="ew", padx=5)
        item_frame.grid_columnconfigure(0, weight=1)
        
        # Left side - info
        info_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        info_frame.grid(row=0, column=0, sticky="w", padx=10, pady=8)
        
        # Rank and name
        rank_color = "#00ff88" if rank == 0 else "#ffaa00" if rank == 1 else "#ffffff"
        rank_label = ctk.CTkLabel(
            info_frame,
            text=f"#{rank + 1}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=rank_color,
            width=30
        )
        rank_label.grid(row=0, column=0, sticky="w")
        
        name_label = ctk.CTkLabel(
            info_frame,
            text=seq_data['name'],
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ffffff"
        )
        name_label.grid(row=0, column=1, sticky="w", padx=(5, 15))
        
        # Stats
        runs = seq_data.get('runs', 0)
        avg_boissons = seq_data.get('avg_boissons', 0.0)
        total_boissons = seq_data.get('total_boissons', 0)
        efficiency_pct = self.calculate_efficiency_percentage(seq_data, rank)
        
        stats_text = f"Runs: {runs} | Avg: {avg_boissons:.1f} | Total: {total_boissons}"
        if efficiency_pct > 0:
            stats_text += f" | +{efficiency_pct:.0f}%"
        
        stats_label = ctk.CTkLabel(
            info_frame,
            text=stats_text,
            font=ctk.CTkFont(size=11),
            text_color="#aaaaaa"
        )
        stats_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 0))
        
        # Right side - buttons
        button_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        button_frame.grid(row=0, column=1, sticky="e", padx=10)
        
        # Load button
        select_btn = ctk.CTkButton(
            button_frame,
            text="Load sequence",
            command=lambda: self.select_sequence(seq_id),
            font=ctk.CTkFont(size=12, weight="bold"),
            width=120,
            height=35,
            fg_color="#00ff88",
            hover_color="#00cc66",
            text_color="#000000"
        )
        select_btn.grid(row=0, column=0, padx=5)
        
        # Delete button
        delete_btn = ctk.CTkButton(
            button_frame,
            text="🗑",
            command=lambda: self.delete_sequence_confirm(seq_id),
            font=ctk.CTkFont(size=14),
            width=35,
            height=35,
            fg_color="#ff4444",
            hover_color="#cc3333"
        )
        delete_btn.grid(row=0, column=1)
    
    def get_sorted_sequences(self):
        """Get sequences sorted by efficiency (avg boissons per run)"""
        seq_list = [(seq_id, data) for seq_id, data in self.sequences.items()]
        seq_list.sort(key=lambda x: x[1].get('avg_boissons', 0), reverse=True)
        return seq_list
    
    def calculate_efficiency_percentage(self, seq_data, rank):
        """Calculate percentage better than worst sequence"""
        if rank == 0 or len(self.sequences) < 2:
            return 0
        
        sorted_seqs = self.get_sorted_sequences()
        if len(sorted_seqs) < 2:
            return 0
        
        worst_avg = sorted_seqs[-1][1].get('avg_boissons', 0)
        current_avg = seq_data.get('avg_boissons', 0)
        
        if worst_avg == 0:
            return 0
        
        return ((current_avg - worst_avg) / worst_avg) * 100
    
    def close_sequence_selection(self):
        """Close sequence selection window"""
        if hasattr(self, 'selection_window'):
            self.selection_window.destroy()
        self.is_sequence_selection_mode = False
    
    def select_sequence(self, seq_id):
        """Load a sequence (don't start playing yet)"""
        self.selected_sequence_id = seq_id
        self.current_sequence_id = seq_id
        self.close_sequence_selection()
        
        # Update loaded sequence display (compact label above Load button)
        seq_name = self.sequences[seq_id]['name']
        try:
            self.loaded_sequence_mini_label.configure(text=seq_name, text_color="#00ff88")
        except Exception:
            pass
        
        self.update_status(f"Sequence loaded: {seq_name}")
        self.step_label.configure(text="Ready")
        print(f"[INFO] Sequence loaded: {seq_name}")
        # Keep controls in sync
        self.update_controls_state()
    
    def delete_sequence_confirm(self, seq_id):
        """Confirm and delete a sequence"""
        seq_name = self.sequences[seq_id]['name']
        
        parent = self.selection_window if hasattr(self, 'selection_window') and self.selection_window.winfo_exists() else self.root
        confirm_window = ctk.CTkToplevel(parent)
        confirm_window.title("Delete Sequence")
        confirm_window.attributes('-topmost', True)
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 350) // 2
        y = (screen_height - 180) // 2
        confirm_window.geometry(f"350x180+{x}+{y}")
        confirm_window.lift()
        confirm_window.grab_set()
        confirm_window.focus_force()
        
        msg_label = ctk.CTkLabel(
            confirm_window,
            text=f"Delete sequence:\n{seq_name}?",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ff4444",
            justify="center"
        )
        msg_label.pack(pady=20)
        
        def confirm_delete():
            del self.sequences[seq_id]
            self.save_sequences()
            confirm_window.destroy()
            # Refresh selection window
            if hasattr(self, 'selection_window'):
                self.selection_window.destroy()
            self.show_sequence_selection()
        
        def cancel():
            confirm_window.destroy()
        
        btn_frame = ctk.CTkFrame(confirm_window, fg_color="transparent")
        btn_frame.pack(pady=10)
        
        ctk.CTkButton(
            btn_frame,
            text="Delete",
            command=confirm_delete,
            width=100,
            fg_color="#ff4444",
            hover_color="#cc3333"
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=cancel,
            width=100,
            fg_color="#444444",
            hover_color="#555555"
        ).pack(side="left", padx=5)
    
    def show_input_dialog(self, title, prompt):
        """Show input dialog and return result"""
        result = [None]
        
        dialog = ctk.CTkToplevel(self.root)
        dialog.title(title)
        dialog.attributes('-topmost', True)
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 350) // 2
        y = (screen_height - 150) // 2
        dialog.geometry(f"350x150+{x}+{y}")
        
        label = ctk.CTkLabel(dialog, text=prompt, font=ctk.CTkFont(size=12))
        label.pack(pady=15)
        
        entry = ctk.CTkEntry(dialog, width=250)
        entry.pack(pady=10)
        entry.focus()
        
        def confirm():
            result[0] = entry.get()
            dialog.destroy()
        
        def cancel():
            dialog.destroy()
        
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=10)
        
        ctk.CTkButton(
            btn_frame,
            text="OK",
            command=confirm,
            width=80,
            fg_color="#00ff88",
            hover_color="#00cc66"
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=cancel,
            width=80,
            fg_color="#444444",
            hover_color="#555555"
        ).pack(side="left", padx=5)
        
        entry.bind('<Return>', lambda e: confirm())
        dialog.grab_set()
        dialog.wait_window()
        
        return result[0]
    
    def start_recording_mode(self):
        """Start recording a new sequence"""
        self.close_sequence_selection()
        
        # Check if we have max 5 sequences
        if len(self.sequences) >= 5:
            error_window = ctk.CTkToplevel(self.root)
            error_window.title("Error")
            error_window.attributes('-topmost', True)
            error_window.geometry("300x100")
            ctk.CTkLabel(
                error_window,
                text="Maximum 5 sequences allowed!\nPlease delete one first.",
                justify="center"
            ).pack(pady=30)
            ctk.CTkButton(
                error_window,
                text="OK",
                command=error_window.destroy
            ).pack()
            return
        
        # Ask for sequence name
        sequence_name = self.show_input_dialog("Record Sequence", "Enter sequence name:")
        
        if not sequence_name:
            return
        
        # Store sequence name for later
        self.recording_sequence_name = sequence_name
        
        # Reset debug tracking
        self.debug_npc_interaction_detected = False
        self.debug_door_opened_detected = False
        self.dialogue2_ready_for_click = False
        self.recording_kamas_loss_detected = False
        self.recording_log_file_position = None
        self.recording_log_file_path = None
        
        # Reset UI labels
        self.countdown_label.grid_remove()
        self.action_label.grid_remove()
        self.step_label.grid()
        
        self.is_recording = True
        self.recording_sequence = []
        self.recording_start_time = None
        self.recording_timer_detected = False
        
        print(f"[DEBUG] Recording started for sequence: {sequence_name}")
        print("[DEBUG] Waiting for NPC interaction, door opening, and timer start...")
        
        # Get screen center for relative coordinates
        screen_width, screen_height = pyautogui.size()
        self.screen_center_x = screen_width // 2
        self.screen_center_y = screen_height // 2
        
        # Start mouse listener
        self.start_mouse_recording()
        
        # Start timer detection
        self.update_status("🎬 Recording... Waiting for timer")
        self.step_label.configure(text="Enter mini-game and start timer")
        
        # Start monitoring for timer
        recording_thread = threading.Thread(target=self.monitor_recording, daemon=True)
        recording_thread.start()
    
    def start_mouse_recording(self):
        """Start recording mouse clicks"""
        def on_click(x, y, button, pressed):
            if not self.is_recording:
                return False
            
            # Check if dialogue2 was detected and we're waiting for user to click it
            if self.dialogue2_ready_for_click and not self.recording_timer_detected:
                if pressed:
                    # User clicked after dialogue2 appeared - START RECORDING NOW
                    self.recording_timer_detected = True
                    self.recording_start_time = time.time()
                    self.recording_sequence = []  # Reset sequence
                    self.last_recorded_action_index = -1
                    self.dialogue2_ready_for_click = False  # Clear flag
                    
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    sequence_name = getattr(self, 'recording_sequence_name', 'Unknown')
                    print(f"[DEBUG] {timestamp} - User clicked dialogue2 - RECORDING STARTED for sequence: '{sequence_name}'")
                    print(f"[DEBUG] ⏺️ All mouse clicks will now be recorded (recording_start_time = {self.recording_start_time})")
                    
                    # Update UI
                    self.root.after(0, self.update_status, f"Recording \"{sequence_name}\" sequence")
                    self.root.after(0, self.step_label.grid_remove)
                    self.root.after(0, self.countdown_label.grid)
                    self.root.after(0, self.action_label.grid)
                    self.root.after(0, self.action_label.configure, {"text": "Waiting for actions..."})
                    
                    # Start countdown update thread
                    countdown_thread = threading.Thread(target=self.update_countdown_display, daemon=True)
                    countdown_thread.start()
                    
                    # This click was on dialogue2, don't record it - recording starts AFTER this click
                    return True
            
            # Only record clicks AFTER recording has actually started
            if not self.recording_timer_detected:
                return True  # Don't record yet, but keep listener active
            
            if pressed:
                # Calculate relative coordinates
                rel_x = x - self.screen_center_x
                rel_y = y - self.screen_center_y
                
                current_time = time.time()
                # Calculate timestamp relative to recording start
                if self.recording_start_time is not None:
                    timestamp = current_time - self.recording_start_time
                else:
                    timestamp = 0.0
                
                button_str = 'right' if button == mouse.Button.right else 'left'
                
                self.recording_sequence.append({
                    'relative_x': rel_x,
                    'relative_y': rel_y,
                    'button': button_str,
                    'timestamp': timestamp
                })
                
                # Debug output
                print(f"[DEBUG] Click recorded: {button_str} @ ({rel_x:+d}, {rel_y:+d}) - {timestamp:.2f}s")
        
        # Stop existing listener if any
        if self.mouse_listener:
            try:
                self.mouse_listener.stop()
            except:
                pass
        
        self.mouse_listener = mouse.Listener(on_click=on_click)
        self.mouse_listener.start()
    
    def update_countdown_display(self):
        """Update countdown display every second"""
        while self.is_recording and self.recording_timer_detected:
            try:
                if self.recording_start_time is not None:
                    elapsed = time.time() - self.recording_start_time
                    remaining = max(0, 60.0 - elapsed)
                    
                    # Update countdown label
                    self.root.after(0, self.countdown_label.configure, 
                                   {"text": f"⏱ {int(remaining)}s"})
                    
                    # Change color as time runs out
                    if remaining <= 10:
                        self.root.after(0, self.countdown_label.configure,
                                       {"text_color": "#ff4444"})
                    elif remaining <= 20:
                        self.root.after(0, self.countdown_label.configure,
                                       {"text_color": "#ffaa00"})
                    else:
                        self.root.after(0, self.countdown_label.configure,
                                       {"text_color": "#ffaa00"})
                
                time.sleep(0.1)  # Update every 100ms for smooth countdown
            except:
                break
    
    def update_action_display(self):
        """Update action display with latest recorded actions"""
        try:
            # Check if new actions were added
            current_length = len(self.recording_sequence)
            if current_length > self.last_recorded_action_index + 1:
                # Show the latest action
                latest_action = self.recording_sequence[-1]
                button_icon = "🖱️ R" if latest_action['button'] == 'right' else "🖱️ L"
                action_text = f"{button_icon} @ ({latest_action['relative_x']:+d}, {latest_action['relative_y']:+d}) - {latest_action['timestamp']:.1f}s"
                
                self.root.after(0, self.action_label.configure, {"text": action_text})
                self.last_recorded_action_index = current_length - 1
                
                # Also show total actions count
                total_text = f"Actions recorded: {current_length}"
        except:
            pass
    
    def detect_timer(self, img):
        """Detect timer countdown in top-left corner of screen"""
        try:
            # Crop top-left region (approximately where timer would be)
            # Assuming timer is in first 100x50 pixels
            h, w = img.shape[:2]
            timer_region = img[0:min(100, h), 0:min(200, w)]
            
            # Convert to grayscale
            gray = cv2.cvtColor(timer_region, cv2.COLOR_BGR2GRAY)
            
            # Simple detection: look for white/bright pixels (timer text is usually bright)
            # This is a basic approach - could be improved with OCR
            white_pixels = np.sum(gray > 200)
            total_pixels = gray.size
            
            # If we see a lot of white pixels, timer might be visible
            # More sophisticated: use template matching for numbers or OCR
            if white_pixels > total_pixels * 0.1:
                # Check if we can detect "60" or numbers
                # For now, simple heuristic: if user just started, assume timer starts at 60
                return True, 60
            
            return False, None
        except:
            return False, None
    
    def monitor_recording(self):
        """Monitor for timer start and end during recording"""
        while self.is_recording:
            try:
                img = self.capture_screen()
                if img is None:
                    time.sleep(0.5)
                    continue
                
                # Debug: Detect NPC interaction (dialogue1 bubble)
                if not self.debug_npc_interaction_detected:
                    is_detected, confidence, location, template = self.detect_template_dual(img, 'dialogue1')
                    if is_detected:
                        self.debug_npc_interaction_detected = True
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        print(f"[DEBUG] {timestamp} - NPC interaction detected! (Entered cemetery)")
                        print(f"  Confidence: {confidence:.2f}, Location: {location}")
                        self.update_status(f"NPC detected - Waiting for kamas loss...")
                        
                        # Initialize log file monitoring position when dialogue1 is detected
                        # Cache the log file path to avoid calling find_log_file() every iteration
                        if self.recording_log_file_path is None:
                            self.recording_log_file_path = self.find_log_file()
                        
                        if self.recording_log_file_path and os.path.exists(self.recording_log_file_path):
                            try:
                                with open(self.recording_log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    f.seek(0, 2)  # Seek to end of file
                                    self.recording_log_file_position = f.tell()
                                print(f"[DEBUG] Started monitoring log file from position: {self.recording_log_file_position}")
                            except Exception as e:
                                print(f"[DEBUG] Error initializing log position: {e}")
                                self.recording_log_file_position = None
                
                # Monitor log file for kamas loss after dialogue1 is detected
                if self.debug_npc_interaction_detected and not self.recording_kamas_loss_detected:
                    # Use cached log file path instead of calling find_log_file() every iteration
                    if self.recording_log_file_path and os.path.exists(self.recording_log_file_path) and self.recording_log_file_position is not None:
                        try:
                            with open(self.recording_log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                f.seek(self.recording_log_file_position)
                                line = f.readline()
                                
                                if line:
                                    self.recording_log_file_position = f.tell()
                                    # Check for kamas loss pattern
                                    match = re.search(self.kamas_loss_pattern, line, re.IGNORECASE)
                                    if match:
                                        self.recording_kamas_loss_detected = True
                                        try:
                                            lost_amount = int(match.group(1)) if match.lastindex and match.group(1) else None
                                        except Exception:
                                            lost_amount = None
                                        if lost_amount is not None:
                                            timestamp = datetime.now().strftime("%H:%M:%S")
                                            print(f"[DEBUG] {timestamp} - ✅ Kamas loss detected during recording: -{lost_amount} kamas")
                                            self.update_status(f"✅ Kamas loss detected: {lost_amount} - Waiting for door...")
                                        else:
                                            timestamp = datetime.now().strftime("%H:%M:%S")
                                            print(f"[DEBUG] {timestamp} - ✅ Kamas loss detected during recording")
                                            self.update_status("✅ Kamas loss detected - Waiting for door...")
                        except Exception as e:
                            # Log file might be locked or changed, continue monitoring
                            pass
                
                # Debug: Detect door interaction (dialogue2 bubble) - Only after kamas loss is detected
                if not self.debug_door_opened_detected and self.debug_npc_interaction_detected and self.recording_kamas_loss_detected:
                    is_detected, confidence, location, template = self.detect_template_dual(img, 'dialogue2')
                    if is_detected:
                        self.debug_door_opened_detected = True
                        self.dialogue2_ready_for_click = True  # Set flag - waiting for user to click dialogue2
                        
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        sequence_name = getattr(self, 'recording_sequence_name', 'Unknown')
                        print(f"[DEBUG] {timestamp} - Dialogue2 bubble detected! (Ready for mini-game)")
                        print(f"  Confidence: {confidence:.2f}, Location: {location}")
                        print(f"[DEBUG] ⏸️ Waiting for you to click the dialogue2 bubble to start recording...")
                        print(f"[DEBUG] ⏸️ Recording will start AFTER you click dialogue2")
                        
                        # Update UI - prompt user to click
                        self.root.after(0, self.update_status, f"Click dialogue2 to start recording: '{sequence_name}'")
                        self.root.after(0, self.step_label.grid_remove)  # Hide step label
                
                # Also check door variants for detection - Only after kamas loss is detected
                if not self.debug_door_opened_detected and self.debug_npc_interaction_detected and self.recording_kamas_loss_detected:
                    is_detected, confidence, location, template = self.detect_door_variants(img)
                    if is_detected:
                        # Door template detected, but we need dialogue2 to confirm it was opened
                        # Just log for info
                        pass
                
                # Update action display during recording
                if self.recording_timer_detected:
                    self.update_action_display()
                
                # Detect timer (for debug only, recording already started when user clicked dialogue2)
                timer_detected, timer_value = self.detect_timer(img)
                if timer_detected and self.recording_timer_detected:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"[DEBUG] {timestamp} - Timer detected: {timer_value}s (already recording)")
                
                if self.recording_timer_detected:
                    # Check if timer ended (reached 60 seconds)
                    elapsed = time.time() - self.recording_start_time
                    
                    # Only end if 60 seconds have passed (don't rely on timer_value detection)
                    if elapsed >= 60.0:
                        # Recording complete
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        print(f"[DEBUG] {timestamp} - Timer ended! Recording complete (elapsed: {elapsed:.2f}s)")
                        print(f"[DEBUG] Total clicks recorded: {len(self.recording_sequence)}")
                        
                        # Hide countdown and action labels
                        self.root.after(0, self.countdown_label.grid_remove)
                        self.root.after(0, self.action_label.grid_remove)
                        self.root.after(0, self.step_label.grid)  # Show step label again
                        
                        self.finish_recording()
                        break
                
                time.sleep(0.1)
            except Exception as e:
                print(f"[DEBUG] Error in monitor_recording: {e}")
                time.sleep(0.5)
    
    def finish_recording(self):
        """Finish recording and save sequence"""
        self.is_recording = False
        
        if self.mouse_listener:
            self.mouse_listener.stop()
            self.mouse_listener = None
        
        if len(self.recording_sequence) == 0:
            self.update_status("❌ Recording failed - no clicks recorded")
            self.step_label.configure(text="Press F12 to try again")
            return
            
        # Get sequence name (should have been set)
        # Create sequence ID
        seq_id = f"seq_{int(time.time())}"
        
        # Get sequence name (stored during start)
        sequence_name = getattr(self, 'recording_sequence_name', f"Sequence {len(self.sequences) + 1}")
        
        # Save sequence
        self.sequences[seq_id] = {
            'name': sequence_name,
            'clicks': self.recording_sequence,
            'runs': 0,
            'total_boissons': 0,
            'avg_boissons': 0.0,
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'runs_data': []
        }
        
        self.save_sequences()
        
        self.update_status("✅ Sequence recorded!")
        try:
            self.step_label.configure(text=f"Saved: {self.sequences[seq_id]['name']}")
        except Exception:
            pass
        
        # Reset
        self.recording_sequence = []
        self.recording_start_time = None
        self.recording_timer_detected = False
        self.dialogue2_ready_for_click = False
    
    def capture_screen(self):
        """Capture screen using MSS or PIL as fallback"""
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                screenshot = sct.grab(monitor)
                img = np.array(screenshot)
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                return img
        except:
            try:
                screenshot = ImageGrab.grab()
                img = np.array(screenshot)
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                return img
            except:
                return None
    
    def start_monitoring(self):
        """Start playing selected sequence"""
        if not self.selected_sequence_id or self.selected_sequence_id not in self.sequences:
            self.update_status("❌ No sequence selected")
            return
        
        self.is_monitoring = True
        self.update_status("🚀 Running...")
        self.update_controls_state()
        try:
            self.step_label.grid()  # Show step/phase only while running
        except Exception:
            pass
        
        # Reset stats and automation state
        self.current_run_resources = {}
        self.mini_game_active = False
        self.mini_game_start_time = None
        self.current_main_step = 1
        self.current_sub_step = 1
        self.log_trigger_found = False
        self.left_minigame_detected = False
        self.game_state = "UNKNOWN"
        self.state_checked_this_cycle = False
        self.last_state_check_time = 0
        self.last_periodic_check_time = 0
        
        # Start log monitoring
        self.log_monitoring = True
        self.log_file_position = None
        log_thread = threading.Thread(target=self.monitor_logs, daemon=True)
        log_thread.start()
        
        # Start monitoring thread (automation flow: NPC -> Door -> Play sequence)
        self.monitor_thread = threading.Thread(target=self.monitor_playback, daemon=True)
        self.monitor_thread.start()
    
    def monitor_playback(self):
        """Monitor screen and automate entry to mini-game, then play sequence"""
        while self.is_monitoring:
            try:
                img = self.capture_screen()
                if img is None:
                    time.sleep(1)
                    continue
                
                current_time = time.time()
                if current_time - self.last_periodic_check_time >= self.periodic_check_interval:
                    self.last_periodic_check_time = current_time
                    print("[SAFETY] Periodic maptoggle check...")
                    safety_state = self.get_game_state()
                    print(f"[SAFETY] Current state: {safety_state}")
                    
                    if safety_state == "UNKNOWN":
                        self.update_status("⚠️ State unknown - restarting")
                        self.restart_cycle()
                        continue
                    
                    if self.current_main_step == 1:
                        if safety_state == "MINIGAME":
                            self.update_status("⚠️ Desync detected - syncing with mini-game")
                            self.current_main_step = 2
                            self.current_sub_step = 1
                            self.mini_game_active = True
                            self.game_state = "MINIGAME"
                            if not self.mini_game_start_time:
                                self.mini_game_start_time = time.time()
                            continue
                        if safety_state == "OUTSIDE" and self.current_sub_step >= 4:
                            self.update_status("↩️ Outside detected - restarting NPC search")
                            self.current_sub_step = 1
                            self.game_state = "OUTSIDE"
                            self.state_checked_this_cycle = False
                            if hasattr(self, 'kamas_wait_start'):
                                delattr(self, 'kamas_wait_start')
                            if hasattr(self, 'log_delay_started'):
                                delattr(self, 'log_delay_started')
                            continue
                        if safety_state == "SAS" and self.current_sub_step < 4:
                            self.update_status("➡️ Already in SAS - moving to door")
                            self.current_sub_step = 4
                            self.game_state = "SAS"
                            if hasattr(self, 'kamas_wait_start'):
                                delattr(self, 'kamas_wait_start')
                            if hasattr(self, 'log_delay_started'):
                                delattr(self, 'log_delay_started')
                            continue
                
                # Update UI
                self.root.after(0, self.update_step, self.current_main_step, self.current_sub_step)
                
                # Main workflow: Step 1 = Enter mini-game, Step 2 = Play sequence
                if self.current_main_step == 1:
                    self.handle_step1_enter_minigame(img)
                elif self.current_main_step == 2:
                    self.handle_step2_play_sequence(img)
                
                time.sleep(0.1)
            except Exception as e:
                print(f"[ERROR] Error in monitor_playback: {e}")
                time.sleep(1)
    
    def handle_step1_enter_minigame(self, img):
        """Handle Step 1: Automate entry to mini-game"""
        if not self.is_monitoring:
            return
        
        if self.current_sub_step == 1 and not self.state_checked_this_cycle:
            current_time = time.time()
            if current_time - self.last_state_check_time >= self.state_check_interval:
                state = self.get_game_state()
                self.last_state_check_time = current_time
                self.state_checked_this_cycle = True
                
                if state == "SAS":
                    self.update_status("➡️ Already in SAS - searching for door")
                    self.current_sub_step = 4
                    self.game_state = "SAS"
                    return
                if state == "MINIGAME":
                    self.update_status("🎮 Mini-game already active - syncing")
                    self.current_main_step = 2
                    self.current_sub_step = 1
                    self.mini_game_active = True
                    if not self.mini_game_start_time:
                        self.mini_game_start_time = time.time()
                    if self.selected_sequence_id in self.sequences:
                        time.sleep(0.2)
                        self.play_sequence(self.selected_sequence_id)
                    return
                if state == "UNKNOWN":
                    self.update_status("⚠️ Unable to detect state - waiting")
                    return
                # If OUTSIDE, continue with normal flow
        
        if self.current_sub_step == 1:
            # Find PNJ and click
            if 'pnj' in self.templates:
                is_detected, confidence, max_loc, template = self.detect_template_dual(img, 'pnj')
                
                if is_detected:
                    template_h, template_w = template.shape[:2]
                    click_x = max_loc[0] + template_w // 2
                    click_y = max_loc[1] + template_h // 2
                    
                    self.perform_click(click_x, click_y, 'right', '(PNJ - Step 1.1)')
                    self.current_sub_step = 2
        
        elif self.current_sub_step == 2:
            # Click on dialogue bubble
            if 'dialogue1' in self.templates:
                is_detected, confidence, max_loc, template = self.detect_template_dual(img, 'dialogue1')
                
                if is_detected:
                    template_h, template_w = template.shape[:2]
                    click_x = max_loc[0] + template_w // 2
                    click_y = max_loc[1] + template_h // 2
                    
                    self.perform_click(click_x, click_y, 'left', '(Dialogue1 - Step 1.2)')
                    self.current_sub_step = 3
                    # Start timer to wait for kamas loss; if it takes too long, retry step 1
                    self.kamas_wait_start = time.time()
        
        elif self.current_sub_step == 3:
            # Wait for kamas loss
            # If we have waited more than 5 seconds without detecting kamas loss, restart step 1
            if not self.log_trigger_found and hasattr(self, 'kamas_wait_start'):
                if time.time() - self.kamas_wait_start > 5.0:
                    # Retry from the beginning of step 1
                    self.update_status("↩️ No kamas loss after 5s - retrying NPC interaction")
                    self.current_sub_step = 1
                    self.state_checked_this_cycle = False
                    delattr(self, 'kamas_wait_start')
                    return
            
            if self.log_trigger_found:
                if not hasattr(self, 'log_delay_started'):
                    self.log_delay_started = time.time()
                
                if time.time() - self.log_delay_started >= 3.0:
                    self.current_sub_step = 4
                    delattr(self, 'log_delay_started')
                    if hasattr(self, 'kamas_wait_start'):
                        delattr(self, 'kamas_wait_start')
                    self.game_state = "SAS"
                    # Immediately verify that we're really in the SAS before proceeding to the door
                    state_after_entry = self.get_game_state()
                    if state_after_entry == "SAS":
                        self.game_state = "SAS"
                        print("[STATE] ✔ SAS confirmed right after kamas loss")
                    elif state_after_entry == "MINIGAME":
                        print("[STATE] ⚠ Detected mini-game already active after kamas loss – syncing")
                        self.game_state = "MINIGAME"
                        self.current_main_step = 2
                        self.current_sub_step = 1
                        self.mini_game_active = True
                        if not self.mini_game_start_time:
                            self.mini_game_start_time = time.time()
                        return
                    elif state_after_entry == "OUTSIDE":
                        print("[STATE] ⚠ Still outside after kamas loss – restarting NPC search")
                        self.game_state = "OUTSIDE"
                        self.current_sub_step = 1
                        self.state_checked_this_cycle = False
                        return
                    else:
                        print("[STATE] ⚠ Unable to confirm SAS after kamas loss (state unknown)")
        
        elif self.current_sub_step == 4:
            # Find door and click
            is_detected, confidence, max_loc, template = self.detect_door_variants(img)
            
            if is_detected:
                template_h, template_w = template.shape[:2]
                click_x = max_loc[0] + template_w // 2
                click_y = max_loc[1] + template_h // 2
                
                self.perform_click(click_x, click_y, 'right', '(Door - Step 1.4)')
                self.current_sub_step = 5
        
        elif self.current_sub_step == 5:
            # Click on door dialogue bubble
            if 'dialogue2' in self.templates:
                is_detected, confidence, max_loc, template = self.detect_template_dual(img, 'dialogue2')
                
                if is_detected:
                    template_h, template_w = template.shape[:2]
                    click_x = max_loc[0] + template_w // 2
                    click_y = max_loc[1] + template_h // 2
                    
                    self.perform_click(click_x, click_y, 'left', '(Dialogue2 - Step 1.5)')
                    
                    # Enter mini-game phase - START PLAYING SEQUENCE
                    # IMPORTANT: Set mini_game_start_time FIRST, then set mini_game_active
                    # This prevents handle_step2_play_sequence from ending immediately
                    current_time = time.time()
                    self.mini_game_start_time = current_time
                    self.mini_game_active = True
                    self.current_main_step = 2
                    self.current_sub_step = 1
                    self.game_state = "MINIGAME"
                    
                    print(f"[DEBUG] Mini-game started at {current_time}")
                    
                    self.update_status("🎮 Mini-game active!")
                    seq_name = self.sequences[self.selected_sequence_id]['name']
                    self.step_label.configure(text=f"Playing: {seq_name}")
                    
                    # Small delay to ensure state is set before sequence starts
                    time.sleep(0.2)
                    
                    # Play loaded sequence
                    if self.selected_sequence_id in self.sequences:
                        self.play_sequence(self.selected_sequence_id)
    
    def handle_step2_play_sequence(self, img):
        """Handle Step 2: Mini-game phase - sequence is already playing"""
        # Early exit if ticket loss detected in logs (we left the mini-game)
        # Only process if mini-game is actually active (avoid false positives from old logs)
        if self.left_minigame_detected and self.mini_game_active and self.mini_game_start_time:
            print(f"[DEBUG] Ticket loss detected during active mini-game - exiting")
            self.mini_game_active = False
            self.update_status("🎟️ Ticket loss detected - exited mini-game")
            time.sleep(1)
            self.save_run_statistics()
            time.sleep(0.5)
            # left_minigame_detected will be reset in restart_cycle
            self.restart_cycle()
            return
        
        # Check if timer ended (60 seconds)
        # Only check if we have a valid start time and mini_game is actually active
        if self.mini_game_active and self.mini_game_start_time:
            elapsed = time.time() - self.mini_game_start_time
            if elapsed >= 60.0:
                # Mini-game ended
                print(f"[DEBUG] Mini-game timer ended: {elapsed:.2f}s elapsed")
                self.mini_game_active = False
                self.update_status("⏰ Mini-game ended")
                
                # Wait a bit then save stats
                time.sleep(2)
                self.save_run_statistics()
                time.sleep(1)
                
                # Restart cycle
                self.restart_cycle()
    
    def perform_click(self, x, y, button='left', context=''):
        """Perform click at given coordinates (automation clicks)"""
        try:
            click_type = "RIGHT" if button == 'right' else "LEFT"
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[DEBUG] 🖱️ AUTOMATION CLICK [{timestamp}] {click_type} @ ({int(x)}, {int(y)}) {context}")
            
            if button == 'right':
                pyautogui.rightClick(x, y)
            else:
                pyautogui.click(x, y)
        except Exception as e:
            print(f"[DEBUG] ❌ Click failed: {e}")
    
    def update_step(self, main_step, sub_step):
        """Update step display"""
        step_names = {
            (1, 1): "Finding PNJ",
            (1, 2): "Clicking Dialogue",
            (1, 3): "Waiting for Kamas Loss",
            (1, 4): "Finding Door",
            (1, 5): "Opening Door",
            (2, 1): "Mini-game Active",
        }
        
        step_name = step_names.get((main_step, sub_step), f"Step {main_step}.{sub_step}")
        self.step_label.configure(text=f"Step: {main_step}.{sub_step} - {step_name}")
    
    def play_sequence(self, seq_id):
        """Play a saved sequence"""
        if seq_id not in self.sequences:
            return
        
        sequence = self.sequences[seq_id]['clicks']
        
        def execute_sequence():
            screen_width, screen_height = pyautogui.size()
            center_x = screen_width // 2
            center_y = screen_height // 2
            
            start_time = time.time()
            seq_name = self.sequences[seq_id]['name']
            print(f"[DEBUG] 🎬 Starting sequence playback: '{seq_name}' ({len(sequence)} clicks)")
            
            # Debug: Show first action details
            if len(sequence) > 0:
                first_action = sequence[0]
                print(f"[DEBUG] 🎬 First action in sequence: {first_action.get('button', 'unknown')} @ relative ({first_action.get('relative_x', 0)}, {first_action.get('relative_y', 0)}), timestamp: {first_action.get('timestamp', 0):.3f}s")
            
            while self.is_monitoring and self.mini_game_active:
                for i, action in enumerate(sequence):
                    if not self.is_monitoring or not self.mini_game_active:
                        break
                    
                    # Calculate absolute coordinates
                    abs_x = center_x + action['relative_x']
                    abs_y = center_y + action['relative_y']
                    
                    # Wait exactly the recorded delay between actions
                    if i == 0:
                        # First action: wait for its timestamp (usually very small, but respect it)
                        if action.get('timestamp', 0) > 0:
                            time.sleep(action['timestamp'])
                    else:
                        # Subsequent actions: wait for the delay since previous action
                        delay = action['timestamp'] - sequence[i-1]['timestamp']
                        if delay > 0:
                            time.sleep(delay)
                    
                    # Perform click from sequence
                    click_type = "RIGHT" if action['button'] == 'right' else "LEFT"
                    rel_x = action['relative_x']
                    rel_y = action['relative_y']
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    action_timestamp = action.get('timestamp', 0.0)
                    print(f"[DEBUG] 🎬 SEQUENCE CLICK [{timestamp}] {click_type} @ ({int(abs_x)}, {int(abs_y)}) [relative: ({rel_x:+d}, {rel_y:+d}), action #{i+1}/{len(sequence)}, recorded at {action_timestamp:.2f}s]")
                    
                    if action['button'] == 'left':
                        pyautogui.click(abs_x, abs_y)
                    else:
                        pyautogui.rightClick(abs_x, abs_y)
        
        sequence_thread = threading.Thread(target=execute_sequence, daemon=True)
        sequence_thread.start()
    
    def auto_detect_log_path(self):
        """Automatically detect Wakfu chat logs folder (same logic as wakfu_class_launcher.py)"""
        try:
            # Get user's home directory
            user_profile = os.path.expanduser('~')
            
            # Standard location - try first
            logs_path = os.path.join(user_profile, "AppData", "Roaming", "zaap", "gamesLogs", "wakfu", "logs")
            if self.validate_wakfu_path(logs_path):
                print(f"[DEBUG] Found log path at standard location: {logs_path}")
                return logs_path
            
            # Try alternative locations
            alternative_paths = [
                os.path.join(user_profile, "AppData", "Local", "zaap", "gamesLogs", "wakfu", "logs"),
            ]
            
            # Try alternative paths
            for path in alternative_paths:
                if self.validate_wakfu_path(path):
                    print(f"[DEBUG] Found log path at alternative location: {path}")
                    return path
            
            print(f"[DEBUG] Could not auto-detect Wakfu log path. Tried:")
            print(f"[DEBUG]   - {logs_path}")
            for path in alternative_paths:
                print(f"[DEBUG]   - {path}")
            
            return None
        except Exception as e:
            print(f"[DEBUG] Error in auto_detect_log_path: {e}")
            return None
    
    def validate_wakfu_path(self, logs_path):
        """Validate if the path contains Wakfu chat logs (same logic as wakfu_class_launcher.py)"""
        try:
            if not os.path.exists(logs_path):
                return False
            
            # Check for chat log file (try different possible names)
            possible_names = [
                "wakfu_chat.log",  # Primary name used by Wakfu
                "wakfu_chat",      # No extension variant
                "wakfu_chat.txt"   # Alternative extension
            ]
            
            for filename in possible_names:
                chat_log_file = os.path.join(logs_path, filename)
                if os.path.exists(chat_log_file):
                    print(f"[DEBUG] Validated Wakfu path: {logs_path} (found {filename})")
                    return True
            
            return False
        except Exception as e:
            print(f"[DEBUG] Error validating Wakfu path: {e}")
            return False
    
    def find_log_file(self):
        """Find the chat log file (wakfu_chat, wakfu_chat.log, or wakfu_chat.txt)"""
        try:
            # If no log_path detected, try to auto-detect again
            if not self.log_path or not os.path.exists(self.log_path):
                self.log_path = self.auto_detect_log_path()
            
            if not self.log_path:
                return None
            
            # Try different possible file names (matching wakfu_class_launcher.py logic)
            possible_names = [
                "wakfu_chat.log",  # What wakfu_class_launcher.py uses
                "wakfu_chat",      # No extension (what file explorer shows)
                "wakfu_chat.txt"   # Alternative extension
            ]
            
            for filename in possible_names:
                log_file = os.path.join(self.log_path, filename)
                if os.path.exists(log_file):
                    print(f"[DEBUG] Found log file: {log_file}")
                    return log_file
            
            # Debug: list available files if not found
            if os.path.exists(self.log_path):
                try:
                    files = [f for f in os.listdir(self.log_path) if 'chat' in f.lower()]
                    if files:
                        print(f"[DEBUG] Chat-related files found: {files}")
                except:
                    pass
            
            return None
        except Exception as e:
            print(f"[DEBUG] Error in find_log_file: {e}")
            return None
    
    def monitor_logs(self):
        """Monitor Wakfu logs for kamas loss and resource collection"""
        import re
        
        try:
            log_file = self.find_log_file()
            if not log_file:
                print(f"[DEBUG] Log file not found. Checked: {os.path.join(self.log_path, 'wakfu_chat.log')}, {os.path.join(self.log_path, 'wakfu_chat')}, and {os.path.join(self.log_path, 'wakfu_chat.txt')}")
                return
            
            print(f"[DEBUG] Monitoring log file: {log_file}")
            
            # Always start from the end of the file to ignore previous runs
            # If log_file_position is None, reset to end of file (this happens on restart_cycle)
            if self.log_file_position is None:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(0, 2)  # Go to end of file
                    self.log_file_position = f.tell()
                    print(f"[DEBUG] Starting log monitoring from position: {self.log_file_position} (end of file - fresh start)")
            
            # Reopen file for reading from current position
            # Note: We reopen the file in each iteration to handle position resets
            while self.log_monitoring:
                # Check if position was reset (None means start from end)
                if self.log_file_position is None:
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        f.seek(0, 2)  # Go to end of file
                        self.log_file_position = f.tell()
                        print(f"[DEBUG] Log position reset - now at: {self.log_file_position} (end of file)")
                
                # Open file for reading from current position
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(self.log_file_position)
                    line = f.readline()
                    
                    if line:
                        # Update position after reading
                        self.log_file_position = f.tell()
                        # Check for kamas loss (entry to cemetery) - use pattern match for flexibility
                        match = re.search(self.kamas_loss_pattern, line, re.IGNORECASE)
                        if match:
                            if not self.log_trigger_found:
                                self.log_trigger_found = True
                                # Extract amount if the regex captured it
                                try:
                                    lost_amount = int(match.group(1)) if match.lastindex and match.group(1) else None
                                except Exception:
                                    lost_amount = None
                                if lost_amount is not None:
                                    print(f"[DEBUG] ✅ Kamas loss detected: -{lost_amount} | Line: {line.strip()}")
                                    # Reflect the amount in the overlay status for quick visual confirmation
                                    self.root.after(0, self.update_status, f"✅ Kamas loss: {lost_amount} kamas - Entered cemetery")
                                else:
                                    print(f"[DEBUG] ✅ Kamas loss detected! Line: {line.strip()}")
                                    self.root.after(0, self.update_status, "✅ Kamas loss detected - Entered cemetery")

                        # Detect leaving the mini-game by ticket loss
                        # ONLY detect if mini-game is actually active (to avoid old log entries)
                        ticket_match = re.search(self.ticket_loss_pattern, line, re.IGNORECASE)
                        if ticket_match and self.mini_game_active and not self.left_minigame_detected:
                            self.left_minigame_detected = True
                            print(f"[DEBUG] 🎟️ Ticket loss detected (leaving mini-game): {line.strip()}")
                            self.root.after(0, self.update_status, "🎟️ Ticket loss detected - exiting mini-game")
                        
                        # Check for resource collection
                        if self.mini_game_active:
                            resource_match = re.search(self.resource_log_pattern, line)
                            if resource_match:
                                quantity = int(resource_match.group(1))
                                resource_name = resource_match.group(2)
                                
                                if resource_name in self.current_run_resources:
                                    self.current_run_resources[resource_name] += quantity
                                else:
                                    self.current_run_resources[resource_name] = quantity
                                
                                # Live update for Boisson de Frayeur
                                if "Boisson de Frayeur" in resource_name:
                                    self.total_frayeur_since_start += quantity
                                    self.root.after(0, self.update_live_frayeur_display)
                    else:
                        # No new line - update position and wait
                        self.log_file_position = f.tell()
                        time.sleep(0.1)  # Reduced sleep time for faster detection
        except Exception as e:
            print(f"[DEBUG] Error in monitor_logs: {e}")
            import traceback
            traceback.print_exc()
    
    def save_run_statistics(self):
        """Save statistics for completed run"""
        if not self.current_sequence_id or self.current_sequence_id not in self.sequences:
            return
        
        seq_data = self.sequences[self.current_sequence_id]
        
        # Count boissons
        run_boissons = self.current_run_resources.get("Boisson de Frayeur", 0)
        
        # Update sequence stats
        seq_data['runs'] = seq_data.get('runs', 0) + 1
        seq_data['total_boissons'] = seq_data.get('total_boissons', 0) + run_boissons
        
        if seq_data['runs'] > 0:
            seq_data['avg_boissons'] = seq_data['total_boissons'] / seq_data['runs']
        
        # Save run data
        if 'runs_data' not in seq_data:
            seq_data['runs_data'] = []
        
        seq_data['runs_data'].append({
            'run_number': seq_data['runs'],
            'boissons_frayeur': run_boissons,
            'resources': self.current_run_resources.copy(),
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        self.save_sequences()
        
        # Update live UI counter as well (in case resources were counted at end)
        try:
            self.update_live_frayeur_display()
        except Exception:
            pass
            
        print(f"Run completed - Sequence: {seq_data['name']}, Boissons: {run_boissons}")
    
    def update_live_frayeur_display(self):
        """Update the live Boisson de Frayeur counter display"""
        try:
            # Only update the big value label
            if hasattr(self, 'frayeur_value_label'):
                self.frayeur_value_label.configure(text=f"{self.total_frayeur_since_start}")
        except Exception:
            pass

    def on_window_resize(self, event):
        """Dynamically resize icons to keep UI responsive"""
        try:
            # Derive a target size from current window height; clamp to sane bounds
            h = max(1, self.root.winfo_height())
            target = int(max(24, min(64, h * 0.22)))  # scale with window height, 24..64px
            if self.frayeur_icon is not None:
                self.frayeur_icon.configure(size=(target, target))
        except Exception:
            pass
    
    def restart_cycle(self):
        """Restart the cycle"""
        print(f"[DEBUG] Restarting cycle - resetting state")
        
        # Reset all state - IMPORTANT: reset mini_game_active FIRST
        self.mini_game_active = False
        self.mini_game_start_time = None
        self.current_run_resources = {}
        self.current_main_step = 1
        self.current_sub_step = 1
        self.log_trigger_found = False
        self.left_minigame_detected = False  # Reset ticket loss detection
        self.game_state = "UNKNOWN"
        self.state_checked_this_cycle = False
        self.last_state_check_time = 0
        self.last_periodic_check_time = 0
        
        # Reset log file position for next run - this will make monitor_logs restart from end of file
        old_position = self.log_file_position
        self.log_file_position = None
        
        # Stop any running sequence
        if hasattr(self, 'sequence_playing'):
            self.sequence_playing = False
        
        print(f"[DEBUG] State reset - mini_game_active={self.mini_game_active}, start_time={self.mini_game_start_time}, left_minigame_detected={self.left_minigame_detected}")
        print(f"[DEBUG] Log file position reset from {old_position} to None (will restart from end of file)")
        
        self.update_status("🔄 Restarting...")
        time.sleep(1)
        self.update_status("🚀 Running...")
        self.step_label.configure(text="Step: 1.1 - Finding PNJ")
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.is_monitoring = False
        self.log_monitoring = False
        self.mini_game_active = False
        self.game_state = "UNKNOWN"
        self.state_checked_this_cycle = False
        self.last_state_check_time = 0
        self.last_periodic_check_time = 0
        
        self.update_status("⏹ Stopped")
        # Hide step label when not running to avoid duplicate state text
        try:
            self.step_label.grid_remove()
        except Exception:
            pass
        
        self.update_controls_state()


if __name__ == "__main__":
    try:
        app = MinimalWakfuOverlay()
        # mainloop is already called in __init__
    except Exception as e:
        import traceback
        print(f"Error starting application: {e}")
        traceback.print_exc()
        input("Press Enter to exit...")
