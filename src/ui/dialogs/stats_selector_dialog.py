import tkinter as tk
from tkinter import ttk, messagebox
from src.utils.logger import log_message
from src.config.settings import save_config

def show_stats_selector_dialog(parent, config):
    """Muestra un diálogo para seleccionar qué estadísticas mostrar"""
    # Extraer configuración actual
    stats_seleccionadas = config.get("stats_seleccionadas", {})
    stats_order = config.get("stats_order", list(stats_seleccionadas.keys()))
    
    # Crear ventana
    dialog = tk.Toplevel(parent)
    dialog.title("Seleccionar Estadísticas")
    dialog.geometry("600x500")
    dialog.minsize(500, 400)
    dialog.transient(parent)
    dialog.grab_set()
    
    # Frame principal con scroll
    main_frame = ttk.Frame(dialog, padding=10)
    main_frame.pack(fill="both", expand=True)
    
    # Canvas con scrollbar
    canvas = tk.Canvas(main_frame)
    scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
    scroll_frame = ttk.Frame(canvas)
    
    scroll_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # Título e instrucciones
    ttk.Label(scroll_frame, text="Selecciona las estadísticas a mostrar:", 
              font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", padx=5, pady=10)
    
    ttk.Label(scroll_frame, text="Puedes arrastrar para cambiar el orden", 
              font=("Arial", 10)).grid(row=1, column=0, columnspan=3, sticky="w", padx=5, pady=5)
    
    # Mapeo de nombres legibles
    stat_names = {
        "vpip": "VPIP (Voluntarily Put Money In Pot)",
        "pfr": "PFR (Pre-Flop Raise)",
        "three_bet": "3-Bet Preflop",
        "fold_to_3bet_pct": "Fold to 3-Bet",
        "wtsd": "WTSD (Went To Showdown)",
        "wsd": "WSD (Won at Showdown)",
        "cbet_flop": "C-Bet Flop",
        "cbet_turn": "C-Bet Turn",
        "fold_to_flop_cbet_pct": "Fold to Flop C-Bet",
        "fold_to_turn_cbet_pct": "Fold to Turn C-Bet", 
        "limp_pct": "Limp %",
        "limp_raise_pct": "Limp-Raise %",
        "four_bet_preflop_pct": "4-Bet Preflop",
        "fold_to_4bet_pct": "Fold to 4-Bet",
        "probe_bet_turn_pct": "Probe Bet Turn",
        "bet_river_pct": "Bet River",
        "fold_to_river_bet_pct": "Fold to River Bet",
        "overbet_turn_pct": "Overbet Turn",
        "overbet_river_pct": "Overbet River",
        "wsdwbr_pct": "WSD w/ Bet River"
    }
    
    # Variables para checkboxes
    checkbox_vars = {}
    checkboxes = {}
    
    # Crear checkboxes para cada estadística
    row = 2
    for stat_key in stats_order:
        if stat_key in stat_names:
            checkbox_vars[stat_key] = tk.BooleanVar(value=stats_seleccionadas.get(stat_key, False))
            cb = ttk.Checkbutton(
                scroll_frame, 
                text=stat_names[stat_key], 
                variable=checkbox_vars[stat_key],
                padding=5
            )
            cb.grid(row=row, column=0, sticky="w", padx=5, pady=2)
            checkboxes[stat_key] = cb
            
            # Botones para mover arriba/abajo
            ttk.Button(scroll_frame, text="↑", width=3,
                      command=lambda k=stat_key: move_stat_up(k)).grid(row=row, column=1, padx=2)
            ttk.Button(scroll_frame, text="↓", width=3,
                      command=lambda k=stat_key: move_stat_down(k)).grid(row=row, column=2, padx=2)
            
            row += 1
    
    # Funciones para mover estadísticas arriba/abajo
    def move_stat_up(stat_key):
        idx = stats_order.index(stat_key)
        if idx > 0:
            # Intercambiar con el elemento anterior
            stats_order[idx], stats_order[idx-1] = stats_order[idx-1], stats_order[idx]
            update_ui_order()
    
    def move_stat_down(stat_key):
        idx = stats_order.index(stat_key)
        if idx < len(stats_order) - 1:
            # Intercambiar con el elemento siguiente
            stats_order[idx], stats_order[idx+1] = stats_order[idx+1], stats_order[idx]
            update_ui_order()
    
    def update_ui_order():
        """Actualiza la interfaz para reflejar el nuevo orden"""
        # Ocultar todos los widgets
        for child in scroll_frame.winfo_children():
            child.grid_forget()
        
        # Volver a mostrar título e instrucciones
        ttk.Label(scroll_frame, text="Selecciona las estadísticas a mostrar:", 
                 font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", padx=5, pady=10)
        
        ttk.Label(scroll_frame, text="Puedes arrastrar para cambiar el orden", 
                 font=("Arial", 10)).grid(row=1, column=0, columnspan=3, sticky="w", padx=5, pady=5)
        
        # Volver a posicionar en el nuevo orden
        row = 2
        for stat_key in stats_order:
            if stat_key in stat_names:
                checkboxes[stat_key].grid(row=row, column=0, sticky="w", padx=5, pady=2)
                
                # Botones para mover arriba/abajo
                ttk.Button(scroll_frame, text="↑", width=3,
                          command=lambda k=stat_key: move_stat_up(k)).grid(row=row, column=1, padx=2)
                ttk.Button(scroll_frame, text="↓", width=3,
                          command=lambda k=stat_key: move_stat_down(k)).grid(row=row, column=2, padx=2)
                
                row += 1
    
    # Frame para botones de acción
    button_frame = ttk.Frame(dialog, padding=10)
    button_frame.pack(fill="x")
    
    # Función para guardar cambios
    def save_changes():
        try:
            # Actualizar selección
            for stat_key, var in checkbox_vars.items():
                stats_seleccionadas[stat_key] = var.get()
            
            # Actualizar configuración
            config["stats_seleccionadas"] = stats_seleccionadas
            config["stats_order"] = stats_order
            
            # Guardar configuración
            if save_config(config):
                messagebox.showinfo("Éxito", "Preferencias de estadísticas guardadas correctamente")
                dialog.destroy()
            else:
                messagebox.showerror("Error", "No se pudo guardar la configuración")
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar preferencias: {e}")
            log_message(f"Error al guardar preferencias de estadísticas: {e}", level='error')
    
    # Botones de acción
    ttk.Button(button_frame, text="Guardar Cambios", command=save_changes).pack(side="right", padx=5)
    ttk.Button(button_frame, text="Cancelar", command=dialog.destroy).pack(side="right", padx=5)
    ttk.Button(button_frame, text="Seleccionar Todo", 
              command=lambda: [var.set(True) for var in checkbox_vars.values()]).pack(side="left", padx=5)
    ttk.Button(button_frame, text="Deseleccionar Todo", 
              command=lambda: [var.set(False) for var in checkbox_vars.values()]).pack(side="left", padx=5)
    
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
    
    # Hacer modal
    parent.wait_window(dialog)