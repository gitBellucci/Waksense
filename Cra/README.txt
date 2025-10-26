# Wakfu Crâ Resource Tracker - Technical Documentation

## 📋 **Overview**
The Wakfu Crâ Resource Tracker is a real-time overlay application that monitors and displays resource levels for the Crâ (Archer) class in Wakfu. It reads combat logs and provides visual feedback similar to World of Warcraft WeakAuras.

## 🏗️ **Architecture**

### **Core Components**
1. **Main Application Class**: `WakfuResourceTracker`
2. **GUI Framework**: Tkinter with PIL for image handling
3. **File Monitoring**: Threaded log file watcher
4. **Resource Parser**: Regex-based log line analysis
5. **Visual System**: Animated bars and overlay images

## 🔄 **How It Works**

### **1. Initialization Process**
```python
def __init__(self):
    # Create main window (300x120px, always on top, semi-transparent)
    # Load resource images from img/ folder
    # Initialize resource tracking variables
    # Start background monitoring thread
```

### **2. File Monitoring System**
```python
def monitor_log_file(self):
    # Continuously watches: C:\Users\Shadow\AppData\Roaming\zaap\gamesLogs\wakfu\logs\wakfu_chat.log
    # Uses file position tracking to read only new lines
    # Processes combat lines in real-time
    # Updates GUI on main thread via root.after()
```

### **3. Log Parsing Engine**
The parser identifies specific patterns in combat logs:

#### **Resource Detection**
- **Affûtage**: `Affûtage \(\+(\d+) Niv\.\)` → Extracts current level
- **Précision**: `Précision \(\+(\d+) Niv\.\)` → Extracts current level
- **Combat State**: `lance le sort` → Combat start, `est KO !` → Combat end

#### **Buff Management**
- **Pointe affûtée**: Automatically gained when Affûtage reaches 100+
- **Tir précis**: `Tir précis (Niv.` → Buff active, `n'est plus sous l'emprise` → Buff removed

#### **Spell Consumption Logic**
When Tir précis is active, spells consume Précision:
```python
spell_costs = {
    "Flèche criblante": 60,
    "Flèche fulminante": 45,
    "Flèche d'immolation": 30,
    # ... etc
}
```

### **4. Resource Management Logic**

#### **Affûtage System**
```python
if new_affutage >= 100:
    stacks_gained = new_affutage // 100  # Calculate stacks
    self.pointe_affutee_stacks += min(stacks_gained, 3)  # Max 3 stacks
    self.affutage = new_affutage % 100  # Carry over remainder
```

**Example**: 80 + 60 = 140 → Gain 1 stack, Affûtage becomes 40

#### **Précision System**
- **Normal**: Builds from 0-300
- **With Tir précis**: Consumes based on spell cast
- **Maximum**: Caps at 300 with "Valeur maximale" message

### **5. Visual System**

#### **Resource Bars**
- **Affûtage**: Orange gradient bar (0-100)
- **Précision**: Blue gradient bar (0-300)
- **Borders**: Golden glow when buffs active
- **Text**: White/golden based on buff state

#### **Overlay Images**
- **Pointe.png**: Center-top when stacks > 0
- **précis.png**: Center when Tir précis active
- **Animation**: Pulsing size effect (64px ± 4px)

#### **Icons**
- **Affûtage.png**: Left of Affûtage bar
- **Précision.png**: Left of Précision bar

## 🧵 **Threading Model**

### **Main Thread**
- GUI updates and user interactions
- Image rendering and animations
- Event handling (drag, right-click menu)

### **Background Thread**
- File monitoring
- Log parsing
- Resource calculations
- GUI updates via `root.after()`

## 📁 **File Structure**
```
C:\Users\Shadow\Desktop\WAKFU WEAKAURA\Crâ\
├── wakfu_resource_tracker.py    # Main application
└── img\
    ├── Affûtage.png            # Resource icon
    ├── Précision.png          # Resource icon
    ├── Pointe.png             # Stack overlay
    └── précis.png             # Buff overlay
```

## 🔧 **Key Features**

### **Real-time Monitoring**
- **File Watcher**: Monitors log file changes every 100ms
- **Incremental Reading**: Only processes new lines
- **Error Recovery**: Exponential backoff on file errors

### **Resource Tracking**
- **Accurate Parsing**: Regex patterns match exact log format
- **Carry-over Logic**: Proper stack management for Affûtage
- **Spell Costs**: Precise Précision consumption per spell

### **Visual Feedback**
- **Animated Bars**: Gradient effects and pulsing borders
- **Overlay Images**: Prominent buff indicators
- **Combat Status**: Visual combat state indicator

### **User Interface**
- **Draggable**: Click and drag to reposition
- **Context Menu**: Right-click for options
- **Debug Mode**: Detailed console logging
- **Test Functions**: Manual resource testing

## 🎮 **Usage Flow**

1. **Start**: Application loads images and starts monitoring
2. **Combat**: Detects spell casting, begins resource tracking
3. **Building**: Affûtage/Précision increase from spells
4. **Stacking**: Affûtage → Pointe affûtée stacks at 100+
5. **Consumption**: Tir précis → Précision spent on spells
6. **Reset**: Resources reset to 0 when combat ends

## 🐛 **Debug Features**

### **Debug Mode**
- **Console Output**: Detailed parsing information
- **Status Display**: Current resource values
- **Test Functions**: Manual resource manipulation

### **Error Handling**
- **File Access**: Graceful handling of missing logs
- **Image Loading**: Fallback to text labels
- **Parsing Errors**: Continues operation on malformed lines

## 🔄 **Performance Optimizations**

1. **Incremental File Reading**: Only processes new content
2. **Conditional GUI Updates**: Updates only when data changes
3. **Image Caching**: Avoids constant image reloading
4. **Sleep Intervals**: Reduces CPU usage during idle periods
5. **Error Limits**: Stops monitoring after repeated failures

## 📊 **Data Flow**

```
Log File → File Monitor → Parser → Resource Manager → GUI Updater → Visual Display
    ↓           ↓          ↓           ↓              ↓            ↓
Combat Log → New Lines → Regex → State Changes → Animation → User Interface
```

This architecture ensures real-time responsiveness while maintaining low resource usage and providing accurate resource tracking for optimal gameplay experience.