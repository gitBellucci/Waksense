#!/usr/bin/env python3
"""
Log Deduplicator - Gestionnaire de déduplication des logs basé sur le timing
Gère les doublons causés par plusieurs instances Wakfu qui écrivent dans le même fichier de log
"""

import time
import re
from collections import deque

class LogDeduplicator:
    """Gestionnaire de déduplication des logs basé sur le timing"""
    
    def __init__(self, duplicate_window_ms=100, max_history=1000):
        """
        Args:
            duplicate_window_ms: Fenêtre temporelle pour considérer un message comme doublon (ms)
            max_history: Nombre maximum de messages à garder en mémoire
        """
        self.duplicate_window_ms = duplicate_window_ms
        self.max_history = max_history
        self.message_history = deque(maxlen=max_history)
        self.debug_mode = False
        self.duplicates_detected = 0
        self.total_messages = 0
        
    def should_process_line(self, line):
        """
        Détermine si une ligne doit être traitée ou si c'est un doublon
        
        Args:
            line: Ligne de log complète avec timestamp
            
        Returns:
            bool: True si la ligne doit être traitée, False si c'est un doublon
        """
        self.total_messages += 1
        
        # Extraire le timestamp et le contenu du message
        timestamp, content = self._parse_log_line(line)
        
        if timestamp is None or content is None:
            # Si on ne peut pas parser, traiter quand même pour éviter de perdre des données
            if self.debug_mode:
                print(f"DEBUG: Impossible de parser la ligne, traitement forcé: {line[:50]}...")
            return True
            
        current_time_ms = self._timestamp_to_ms(timestamp)
        
        # Vérifier les doublons dans la fenêtre temporelle
        for entry in self.message_history:
            if (abs(current_time_ms - entry['timestamp_ms']) <= self.duplicate_window_ms and
                entry['content'] == content):
                
                self.duplicates_detected += 1
                if self.debug_mode:
                    time_diff = abs(current_time_ms - entry['timestamp_ms'])
                    print(f"DEBUG: 🚫 DOUBLON IGNORÉ (diff: {time_diff}ms) - {content[:60]}...")
                return False
        
        # Ajouter à l'historique
        self.message_history.append({
            'timestamp_ms': current_time_ms,
            'content': content,
            'full_line': line
        })
        
        if self.debug_mode:
            print(f"DEBUG: ✅ MESSAGE TRAITÉ - {content[:60]}...")
        
        return True
    
    def _parse_log_line(self, line):
        """
        Parse une ligne de log pour extraire timestamp et contenu
        
        Format attendu: "20:34:53,813 - [Information (combat)] Belluzu lance le sort Jugement"
        """
        try:
            # Regex pour extraire timestamp et contenu
            match = re.match(r'^(\d{2}:\d{2}:\d{2},\d{3})\s*-\s*(.+)$', line.strip())
            if match:
                timestamp = match.group(1)
                content = match.group(2)
                return timestamp, content
        except Exception as e:
            if self.debug_mode:
                print(f"DEBUG: Erreur parsing ligne: {e}")
        
        return None, None
    
    def _timestamp_to_ms(self, timestamp_str):
        """
        Convertit un timestamp "HH:MM:SS,mmm" en millisecondes depuis minuit
        """
        try:
            # Parser le timestamp
            time_part, ms_part = timestamp_str.split(',')
            h, m, s = map(int, time_part.split(':'))
            ms = int(ms_part)
            
            # Convertir en millisecondes depuis minuit
            total_ms = (h * 3600 + m * 60 + s) * 1000 + ms
            return total_ms
            
        except Exception as e:
            if self.debug_mode:
                print(f"DEBUG: Erreur conversion timestamp: {e}")
            return 0
    
    def set_debug_mode(self, enabled):
        """Active/désactive le mode debug"""
        self.debug_mode = enabled
        print(f"DEBUG: Mode debug déduplication {'activé' if enabled else 'désactivé'}")
    
    def get_stats(self):
        """Retourne les statistiques de déduplication"""
        return {
            'total_messages': self.total_messages,
            'duplicates_detected': self.duplicates_detected,
            'messages_processed': len(self.message_history),
            'duplicate_window_ms': self.duplicate_window_ms,
            'duplicate_rate': (self.duplicates_detected / self.total_messages * 100) if self.total_messages > 0 else 0
        }
    
    def reset_stats(self):
        """Remet à zéro les statistiques"""
        self.duplicates_detected = 0
        self.total_messages = 0
        self.message_history.clear()
        print("DEBUG: Statistiques de déduplication remises à zéro")
