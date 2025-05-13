import time
import threading
import pyperclip
import pyautogui
import win32gui
from datetime import datetime

from src.utils.logger import log_message
from src.utils.windows import focus_window, get_window_under_cursor
from src.core.ocr_engine import capture_and_read_nick
from src.core.api_client import get_player_stats
from src.core.gpt_client import analyze_stats
from src.core.history_manager import add_to_history, load_history
from src.utils.image_utils import generate_image_hash

# Caché de nicks y hashes
nick_cache = {}
last_nick_data = {}

def clear_nick_cache():
    """Limpia la caché de nicks detectados"""
    global nick_cache, last_nick_data
    nick_cache = {}
    last_nick_data = {}
    log_message("Caché de nicks limpiada")
    return True

def paste_to_poker(text):
    """Pega texto en la ventana activa de poker"""
    try:
        pyperclip.copy(text)
        time.sleep(0.2)
        pyautogui.hotkey("ctrl", "v")
        pyautogui.press("enter")
        log_message("Texto pegado en ventana de poker")
        return True
    except Exception as e:
        log_message(f"Error al pegar texto: {e}", level='error')
        return False

def format_stats_summary(data, config):
    """Formatea las estadísticas principales en formato corto según la selección del usuario"""
    try:
        # Obtener estadísticas seleccionadas y su orden
        selected_stats = config.get("stats_seleccionadas", {})
        stats_order = config.get("stats_order", list(selected_stats.keys()))
        stats_format = config.get("stats_format", {})
        
        # Filtrar el orden para incluir solo las estadísticas seleccionadas
        filtered_order = [stat for stat in stats_order if selected_stats.get(stat, False)]
        
        # Si no hay estadísticas seleccionadas, usar algunas por defecto
        if not filtered_order:
            default_stats = ["vpip", "pfr", "three_bet", "fold_to_3bet_pct", "wtsd", "wsd", "cbet_flop", "cbet_turn"]
            filtered_order = [stat for stat in default_stats if stat in data]
        
        # Formatear estadísticas seleccionadas en el orden especificado
        stats_parts = []
        for stat_key in filtered_order:
            if stat_key in data:
                # Obtener el formato para esta estadística
                format_str = stats_format.get(stat_key, f"{stat_key.upper()}:{{value}}")
                
                try:
                    # Intentar formatear como entero para la mayoría de estadísticas porcentuales
                    if stat_key in ['bb_100', 'win_usd']:
                        value = float(data[stat_key])
                        formatted_value = format_str.format(value=value)
                    else:
                        value = int(float(data[stat_key]))
                        formatted_value = format_str.format(value=value)
                    
                    stats_parts.append(formatted_value)
                except (ValueError, TypeError):
                    # Si no se puede convertir, mostrar como está
                    formatted_value = format_str.format(value=data[stat_key])
                    stats_parts.append(formatted_value)
        
        # Si no se pudo formatear ninguna estadística, usar formato antiguo
        if not stats_parts:
            return (f"VPIP:{int(float(data['vpip']))} PFR:{int(float(data['pfr']))} "
                    f"3B:{int(float(data['three_bet']))} F3B:{int(float(data['fold_to_3bet_pct']))} "
                    f"WTSD:{int(float(data['wtsd']))} WSD:{int(float(data['wsd']))} "
                    f"CB:{int(float(data['cbet_flop']))}/{int(float(data['cbet_turn']))}")
        
        return " ".join(stats_parts)
    except Exception as e:
        log_message(f"Error al formatear stats: {e}", level='error')
        import traceback
        log_message(traceback.format_exc(), level='error')
        return "Error al formatear stats"

def analyze_table(hwnd, config, manual_nick=None, force_new_capture=False):
    """Función principal para analizar una mesa de poker"""
    global nick_cache, last_nick_data
    
    try:
        log_message("Iniciando análisis de mesa")
        
        # 1. Determinar el nick del jugador
        if manual_nick:
            # Usar nick manual proporcionado
            nick = manual_nick
            log_message(f"Usando nick manual: '{nick}'")
        else:
            # Decidir si usar caché o capturar de nuevo
            use_cache = not force_new_capture and hwnd in nick_cache and (time.time() - nick_cache[hwnd]["timestamp"]) < 300
            
            if use_cache:
                # Verificar si el jugador cambió mediante hash de la imagen
                left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                coords = config["ocr_coords"]
                region = (left + coords["x"], top + coords["y"], coords["w"], coords["h"])
                
                # Capturar imagen para comparación
                img = pyautogui.screenshot(region=region)
                img_hash = generate_image_hash(img)
                
                # Comparar con hash anterior si existe
                if hwnd in last_nick_data and "img_hash" in last_nick_data[hwnd]:
                    if img_hash != last_nick_data[hwnd]["img_hash"]:
                        log_message("Detectado cambio de jugador en la misma ventana")
                        use_cache = False  # Forzar nueva captura
                
                if use_cache:
                    nick = nick_cache[hwnd]["nick"]
                    log_message(f"Nick recuperado de caché: '{nick}'")
                else:
                    log_message("La ventana cambió, obteniendo nuevo nick...")
            
            # Si no usamos caché, capturar nuevo nick
            if not use_cache:
                # Activar ventana y capturar nick
                original_hwnd, current_hwnd = focus_window(hwnd)
                
                # Leer nick usando OCR
                log_message("Leyendo nick...")
                nick = capture_and_read_nick(hwnd, config["ocr_coords"])
                
                if not nick:
                    log_message("No se detectó ningún nick", level='warning')
                    return False
                
                # Actualizar caché
                nick_cache[hwnd] = {
                    "nick": nick,
                    "timestamp": time.time()
                }
                
                # Actualizar hash de imagen
                left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                coords = config["ocr_coords"]
                region = (left + coords["x"], top + coords["y"], coords["w"], coords["h"])
                img = pyautogui.screenshot(region=region)
                img_hash = generate_image_hash(img)
                
                # Actualizar último nick y hash
                if "img_hash" in locals():
                    last_nick_data[hwnd] = {
                        "nick": nick,
                        "img_hash": img_hash
                    }
                
                log_message(f"Nick detectado: '{nick}'")
        
        # 2. Obtener estadísticas del jugador
        try:
            stats_data = get_player_stats(nick, config["sala_default"], config["token"], config["server_url"])
            
            # Añadir nick a los datos
            stats_data["player_name"] = nick
            
            # 3. Formatear estadísticas y generar análisis
            stats_summary = format_stats_summary(stats_data, config)
            analysis = analyze_stats(stats_data, config["openai_api_key"], nick)
            
            log_message(f"Stats: {stats_summary}")
            log_message(f"Análisis: {analysis[:100]}...")  # Primeros 100 caracteres
            
            # Verificar si se debe mostrar el diálogo de copia
            show_copy_dialog = config.get("mostrar_dialogo_copia", False)
            
            if show_copy_dialog:
                # Programar la ventana de diálogo en el hilo principal
                from src.ui.main_window import root
                if root and root.winfo_exists():
                    # Usar el evento after para ejecutar en el hilo de Tkinter
                    root.after(100, lambda: show_copy_options_dialog(root, stats_summary, analysis, hwnd, config))
                    log_message("Diálogo de copia programado")
                else:
                    log_message("No se pudo mostrar diálogo de copia (root no disponible)", level='warning')
                    # Continuar con la operación normal
                    paste_results(stats_summary, analysis, hwnd, config)
            else:
                # Operación normal: pegar resultados en la mesa
                paste_results(stats_summary, analysis, hwnd, config)
            
            # 6. Guardar en historial
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            history_entry = {
                "timestamp": timestamp,
                "nick": nick,
                "stats": stats_summary,
                "analisis": analysis,
                "sala": config["sala_default"]
            }
            
            # Añadir al historial
            add_to_history(history_entry)
            
            # 7. Actualizar UI del historial de manera segura
            try:
                # Usar root.after para programar la actualización en el hilo principal de Tkinter
                from src.ui.main_window import root, update_history_ui
                if root and root.winfo_exists():
                    # Programar la actualización para que se ejecute en el hilo principal
                    root.after(100, update_history_ui)
                    log_message("Actualización de historial UI programada")
            except Exception as ui_error:
                log_message(f"Error al programar actualización de UI del historial: {ui_error}", level='warning')
            
            log_message("Análisis completado con éxito")
            return True
            
        except Exception as e:
            log_message(f"Error al obtener/analizar stats: {e}", level='error')
            
            # Limpiar caché en caso de error
            if hwnd in nick_cache:
                del nick_cache[hwnd]
            if hwnd in last_nick_data:
                del last_nick_data[hwnd]
                
            return False
        
    except Exception as e:
        log_message(f"Error en análisis de mesa: {e}", level='error')
        import traceback
        log_message(traceback.format_exc(), level='error')
        return False

def paste_results(stats_summary, analysis, hwnd, config):
    """Pega los resultados en la ventana de poker según la configuración"""
    # Preparar resultado final
    result = ""
    if config["mostrar_stats"]:
        result += f"{stats_summary}\n"
    if config["mostrar_analisis"]:
        result += f"{analysis}"
    
    if not result:
        log_message("No hay contenido para mostrar según la configuración")
        return False
    
    # Pegar resultado en la mesa
    return paste_to_poker(result)

def show_copy_options_dialog(parent_window, stats, analysis, hwnd, config):
    """Muestra un diálogo con opciones para copiar stats o análisis"""
    try:
        import tkinter as tk
        from tkinter import ttk
        
        dialog = tk.Toplevel(parent_window)
        dialog.title("Opciones de Copia")
        dialog.geometry("300x200")
        dialog.minsize(300, 200)
        dialog.transient(parent_window)
        dialog.grab_set()
        
        # Frame principal
        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill="both", expand=True)
        
        ttk.Label(frame, text="¿Qué quieres hacer con el resultado?", 
                 font=("Arial", 10, "bold")).pack(pady=5)
        
        # Funciones para acciones
        def copy_stats():
            import pyperclip
            pyperclip.copy(stats)
            log_message("Stats copiadas al portapapeles")
            dialog.destroy()
        
        def copy_analysis():
            import pyperclip
            pyperclip.copy(analysis)
            log_message("Análisis copiado al portapapeles")
            dialog.destroy()
        
        def copy_both():
            import pyperclip
            pyperclip.copy(f"{stats}\n{analysis}")
            log_message("Stats y análisis copiados al portapapeles")
            dialog.destroy()
        
        def paste_to_window():
            dialog.destroy()
            # Pegar el contenido según configuración
            paste_results(stats, analysis, hwnd, config)
        
        def do_nothing():
            dialog.destroy()
        
        # Botones de acción
        ttk.Button(frame, text="Copiar Stats", command=copy_stats).pack(fill="x", pady=2)
        ttk.Button(frame, text="Copiar Análisis", command=copy_analysis).pack(fill="x", pady=2)
        ttk.Button(frame, text="Copiar Ambos", command=copy_both).pack(fill="x", pady=2)
        ttk.Button(frame, text="Pegar en Mesa", command=paste_to_window).pack(fill="x", pady=2)
        ttk.Button(frame, text="Cancelar", command=do_nothing).pack(fill="x", pady=2)
        
        # Centrar ventana
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Intentar añadir ícono
        try:
            dialog.iconbitmap("assets/icon.ico")
        except:
            pass
            
    except Exception as e:
        log_message(f"Error al mostrar diálogo de copia: {e}", level='error')
        import traceback
        log_message(traceback.format_exc(), level='error')
        
        # Si hay error en el diálogo, simplemente realizar acción predeterminada
        paste_results(stats, analysis, hwnd, config)

def get_last_analysis_results():
    """Obtiene los resultados del último análisis realizado"""
    history = load_history()
    if not history:
        return None, None
    
    last_entry = history[-1]
    stats = last_entry.get("stats", "")
    analysis = last_entry.get("analisis", "")
    return stats, analysis

def copy_last_stats_to_clipboard():
    """Copia las estadísticas del último análisis al portapapeles"""
    stats, _ = get_last_analysis_results()
    if stats:
        pyperclip.copy(stats)
        log_message("Últimas estadísticas copiadas al portapapeles")
        return True
    return False

def copy_last_analysis_to_clipboard():
    """Copia el análisis del último análisis al portapapeles"""
    _, analysis = get_last_analysis_results()
    if analysis:
        pyperclip.copy(analysis)
        log_message("Último análisis copiado al portapapeles")
        return True
    return False

def copy_last_results_to_clipboard():
    """Copia ambos resultados del último análisis al portapapeles"""
    stats, analysis = get_last_analysis_results()
    if stats or analysis:
        combined = ""
        if stats:
            combined += stats + "\n"
        if analysis:
            combined += analysis
        
        if combined:
            pyperclip.copy(combined)
            log_message("Últimos resultados copiados al portapapeles")
            return True
    return False