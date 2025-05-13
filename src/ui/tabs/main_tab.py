import tkinter as tk
from tkinter import ttk, messagebox
import threading

from src.utils.logger import log_message
from src.utils.windows import get_window_under_cursor, find_poker_tables
from src.core.poker_analyzer import analyze_table, copy_last_stats_to_clipboard, copy_last_analysis_to_clipboard, copy_last_results_to_clipboard

def create_main_tab(parent, config):
    """Crea la pestaña principal de la aplicación"""
    tab = ttk.Frame(parent)
    tab.name = "main_tab"
    
    # Marco para búsqueda manual
    create_search_frame(tab, config)
    
    # Marco para acciones rápidas (NUEVO)
    create_quick_actions_frame(tab, config)
    
    # Marco para opciones de salida
    create_output_options_frame(tab, config)
    
    # Marco para estado del modo automático
    create_status_frame(tab, config)
    
    # Marco para mesas detectadas
    create_tables_frame(tab, config)
    
    return tab

def create_search_frame(parent, config):
    """Crea el marco para búsqueda manual"""
    frame = ttk.Frame(parent, padding=10)
    frame.pack(fill="x", padx=10, pady=5)
    frame.name = "search_frame"
    
    # Campo de búsqueda
    ttk.Label(frame, text="Buscar nick:").grid(row=0, column=0, padx=5, pady=5)
    entry_nick = ttk.Entry(frame, width=30)
    entry_nick.grid(row=0, column=1, padx=5, pady=5)
    
    # Selector de sala
    sala_var = tk.StringVar(value=config["sala_default"])
    ttk.Label(frame, text="Sala:").grid(row=0, column=2, padx=5, pady=5)
    combo_sala = ttk.Combobox(frame, textvariable=sala_var, values=["XPK", "PS", "GG", "WPN", "888"], width=5)
    combo_sala.grid(row=0, column=3, padx=5, pady=5)
    
    # Botón de búsqueda
    def search_manual():
        nick = entry_nick.get().strip()
        if not nick:
            messagebox.showwarning("Campo vacío", "Ingresa un nick para buscar")
            return
            
        # Actualizar sala predeterminada
        config["sala_default"] = sala_var.get()
        from src.config.settings import save_config
        save_config(config)
        
        # Obtener ventana bajo el cursor
        hwnd, _ = get_window_under_cursor()
        if hwnd:
            threading.Thread(target=analyze_table, args=(hwnd, config, nick, True)).start()
        else:
            # Sin mesa específica, buscar la primera disponible
            tables = find_poker_tables()
            if tables:
                hwnd, _ = tables[0]
                threading.Thread(target=analyze_table, args=(hwnd, config, nick, True)).start()
            else:
                log_message("No se encontró una mesa activa para la búsqueda manual", level="warning")
                messagebox.showwarning("Sin mesa", "No se encontró una mesa de poker activa")
    
    ttk.Button(frame, text="Buscar", command=search_manual).grid(row=0, column=4, padx=5, pady=5)
    
    # Hacer que el Enter en el campo de búsqueda active la búsqueda
    entry_nick.bind("<Return>", lambda event: search_manual())
    
    return frame

def create_quick_actions_frame(parent, config):
    """Crea el marco para acciones rápidas (NUEVO)"""
    frame = ttk.LabelFrame(parent, text="Acciones Rápidas", padding=10)
    frame.pack(fill="x", padx=10, pady=5)
    frame.name = "quick_actions_frame"
    
    # Botones para copiar última búsqueda
    def copy_last_stats():
        """Copia al portapapeles las estadísticas de la última búsqueda"""
        if copy_last_stats_to_clipboard():
            messagebox.showinfo("Copiado", "Estadísticas copiadas al portapapeles")
        else:
            messagebox.showinfo("Sin datos", "No hay búsquedas previas")

    def copy_last_analysis():
        """Copia al portapapeles el análisis de la última búsqueda"""
        if copy_last_analysis_to_clipboard():
            messagebox.showinfo("Copiado", "Análisis copiado al portapapeles")
        else:
            messagebox.showinfo("Sin datos", "No hay análisis previo disponible")

    def copy_both():
        """Copia al portapapeles las estadísticas y el análisis de la última búsqueda"""
        if copy_last_results_to_clipboard():
            messagebox.showinfo("Copiado", "Estadísticas y análisis copiados al portapapeles")
        else:
            messagebox.showinfo("Sin datos", "No hay búsquedas previas")
    
    # Botón para seleccionar estadísticas a mostrar
    def open_stats_selector():
        try:
            from src.ui.dialogs.stats_selector_dialog import show_stats_selector_dialog
            show_stats_selector_dialog(parent, config)
        except Exception as e:
            log_message(f"Error al abrir selector de estadísticas: {e}", level='error')
            messagebox.showerror("Error", f"No se pudo abrir el selector de estadísticas: {e}")
    
    # Opciones para la última búsqueda
    ttk.Label(frame, text="Última búsqueda:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
    ttk.Button(frame, text="Copiar Stats", command=copy_last_stats, width=12).grid(row=0, column=1, padx=5, pady=5)
    ttk.Button(frame, text="Copiar Análisis", command=copy_last_analysis, width=12).grid(row=0, column=2, padx=5, pady=5)
    ttk.Button(frame, text="Copiar Ambos", command=copy_both, width=12).grid(row=0, column=3, padx=5, pady=5)
    
    # Opciones de configuración rápida
    ttk.Label(frame, text="Configuración:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
    ttk.Button(frame, text="Seleccionar Stats", command=open_stats_selector, width=16).grid(row=1, column=1, padx=5, pady=5, columnspan=2)
    
    return frame

def create_output_options_frame(parent, config):
    """Crea el marco para opciones de salida"""
    frame = ttk.Frame(parent, padding=10)
    frame.pack(fill="x", padx=10, pady=5)
    frame.name = "options_frame"
    
    ttk.Label(frame, text="Incluir en la salida:").grid(row=0, column=0, padx=5, pady=5)
    
    # Opciones de visualización
    mostrar_stats_var = tk.BooleanVar(value=config["mostrar_stats"])
    mostrar_analisis_var = tk.BooleanVar(value=config["mostrar_analisis"])
    
    def toggle_stats():
        config["mostrar_stats"] = mostrar_stats_var.get()
        from src.config.settings import save_config
        save_config(config)
    
    def toggle_analisis():
        config["mostrar_analisis"] = mostrar_analisis_var.get()
        from src.config.settings import save_config
        save_config(config)
    
    check_stats = ttk.Checkbutton(frame, text="Estadísticas", variable=mostrar_stats_var, command=toggle_stats)
    check_stats.grid(row=0, column=1, padx=5, pady=5)
    
    check_analisis = ttk.Checkbutton(frame, text="Análisis", variable=mostrar_analisis_var, command=toggle_analisis)
    check_analisis.grid(row=0, column=2, padx=5, pady=5)
    
    # Opción de mostrar diálogo de copia
    mostrar_dialogo_var = tk.BooleanVar(value=config.get("mostrar_dialogo_copia", False))
    
    def toggle_dialogo():
        config["mostrar_dialogo_copia"] = mostrar_dialogo_var.get()
        from src.config.settings import save_config
        save_config(config)
    
    check_dialogo = ttk.Checkbutton(frame, text="Mostrar diálogo de copia", variable=mostrar_dialogo_var, command=toggle_dialogo)
    check_dialogo.grid(row=0, column=3, padx=5, pady=5)
    
    return frame

def create_status_frame(parent, config):
    """Crea el marco para el estado del modo automático"""
    frame = ttk.Frame(parent, padding=10)
    frame.pack(fill="x", padx=10, pady=5)
    frame.name = "status_frame"
    
    ttk.Label(frame, text="Estado:").grid(row=0, column=0, padx=5, pady=5)
    
    from src.ui.main_window import auto_running, start_auto_mode, stop_auto_mode
    estado_label = ttk.Label(frame, text="Inactivo", foreground="red")
    estado_label.grid(row=0, column=1, padx=5, pady=5)
    
    # Botón para modo automático
    if auto_running:
        btn_auto = ttk.Button(frame, text="Detener modo automático", command=stop_auto_mode)
    else:
        btn_auto = ttk.Button(frame, text="Iniciar modo automático", 
                             command=lambda: start_auto_mode(config))
    
    btn_auto.grid(row=0, column=2, padx=5, pady=5)
    
    return frame

def create_tables_frame(parent, config):
    """Crea el marco para mesas detectadas"""
    frame = ttk.LabelFrame(parent, text="Mesas Detectadas", padding=10)
    frame.pack(fill="both", expand=True, padx=10, pady=5)
    frame.name = "tables_frame"
    
    # Lista de mesas
    columns = ("id", "titulo")
    tree = ttk.Treeview(frame, columns=columns, show="headings", height=10)
    tree.heading("id", text="ID")
    tree.heading("titulo", text="Título")
    tree.column("id", width=50)
    tree.column("titulo", width=400)
    tree.pack(fill="both", expand=True, padx=5, pady=5)
    
    # Añadir scrollbar
    scrollbar = ttk.Scrollbar(tree, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    
    # Botón para refrescar mesas
    def refresh_tables():
        # Limpiar treeview
        for item in tree.get_children():
            tree.delete(item)
        
        # Buscar mesas
        tables = find_poker_tables()
        
        # Añadir a la vista
        for hwnd, title in tables:
            tree.insert("", "end", values=(hwnd, title))
        
        if not tables:
            log_message("No se encontraron mesas de poker activas", level="warning")
            tree.insert("", "end", values=("", "No se encontraron mesas de poker activas"))
    
    # Frame para botones
    button_frame = ttk.Frame(frame)
    button_frame.pack(fill="x", padx=5, pady=5)
    
    ttk.Button(button_frame, text="Refrescar Mesas", command=refresh_tables).pack(side="left", padx=5, pady=5)
    
    # Botón para analizar mesa seleccionada
    def analyze_selected_table():
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("Sin selección", "Selecciona una mesa para analizar")
            return
        
        item = tree.item(selection[0])
        if not item["values"] or not item["values"][0]:
            messagebox.showwarning("Selección inválida", "Selecciona una mesa válida para analizar")
            return
            
        hwnd = int(item["values"][0])
        threading.Thread(target=analyze_table, args=(hwnd, config)).start()
    
    ttk.Button(button_frame, text="Analizar Mesa Seleccionada", command=analyze_selected_table).pack(side="left", padx=5, pady=5)
    
    # Botón para analizar mesa bajo cursor
    def analyze_table_under_cursor():
        hwnd, _ = get_window_under_cursor()
        if hwnd:
            threading.Thread(target=analyze_table, args=(hwnd, config)).start()
        else:
            messagebox.showwarning("Sin ventana", "No se encontró una mesa bajo el cursor")
    
    ttk.Button(button_frame, text="Analizar Mesa Bajo Cursor", command=analyze_table_under_cursor).pack(side="left", padx=5, pady=5)
    
    # Botón para limpiar caché
    def clear_cache():
        from src.core.poker_analyzer import clear_nick_cache
        clear_nick_cache()
        messagebox.showinfo("Caché limpiada", "Se ha limpiado la caché de nicks correctamente")
    
    ttk.Button(button_frame, text="Limpiar Caché de Nicks", command=clear_cache).pack(side="right", padx=5, pady=5)
    
    # Inic