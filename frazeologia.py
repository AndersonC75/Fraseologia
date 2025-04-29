# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
import uuid
import sys
import traceback

# --- Constantes ---
ARQUIVO_FRASES = "frases.json"
ICON_FILE = "icone.ico"
PHRASES_KEY = "_phrases_"
ORDER_KEY = "__category_order__" # Chave para a ordem das categorias

# --- Configuração de Caminhos ---
def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except Exception: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

icon_path = resource_path(ICON_FILE)
if getattr(sys, 'frozen', False): application_path = os.path.dirname(sys.executable)
else: application_path = os.path.dirname(os.path.abspath(__file__))
arquivo_frases_path = os.path.join(application_path, ARQUIVO_FRASES)
log_filename = os.path.join(application_path, "frazeologia_error_log.txt")

# --- Globais ---
frases = {} # Dicionário com os dados das categorias
category_order = [] # Lista que define a ordem das abas
widgets_por_categoria = {}
current_theme = "light"
app = None # Será definido no bloco principal
abas = None
label_sem_categorias = None
context_menu = None

# --- Theme Colors ---
themes = {
    "light": {"bg": "#f0f0f0", "fg": "#000000", "button_bg": "#e0e0e0", "button_fg": "#000000", "button_active_bg": "#cccccc", "tree_bg": "#ffffff", "tree_fg": "#000000", "tree_select_bg": "#0078d7", "tree_select_fg": "#ffffff", "disabled_fg": "#aaaaaa", "tab_active_bg": "#e0e0e0", "tab_inactive_bg": "#f0f0f0", "heading_bg": "#e0e0e0", "heading_fg": "#000000"},
    "dark": {"bg": "#2b2b2b", "fg": "#ffffff", "button_bg": "#555555", "button_fg": "#ffffff", "button_active_bg": "#666666", "tree_bg": "#3c3c3c", "tree_fg": "#ffffff", "tree_select_bg": "#005f87", "tree_select_fg": "#ffffff", "disabled_fg": "#777777", "tab_active_bg": "#444444", "tab_inactive_bg": "#2b2b2b", "heading_bg": "#555555", "heading_fg": "#ffffff"}
}

# --- Data Handling ---
def carregar_frases():
    global frases, category_order # Modifica globais
    print(f"Carregando de: {arquivo_frases_path}")
    if os.path.exists(arquivo_frases_path):
        try:
            with open(arquivo_frases_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Carrega os dados das frases (categorias)
            temp_frases = {}
            ok = True
            for cat, content in data.items():
                if cat == ORDER_KEY: continue # Pula a chave da ordem
                if isinstance(content, list): temp_frases[cat] = {PHRASES_KEY: content} # Migra estrutura antiga
                elif isinstance(content, dict): temp_frases[cat] = content
                else: print(f"Aviso: Ignorando inválido '{cat}'"); ok = False
            frases = temp_frases # Atualiza o global de frases

            # Carrega ou define a ordem das categorias
            if ORDER_KEY in data and isinstance(data[ORDER_KEY], list):
                loaded_order = data[ORDER_KEY]
                # Sanitiza a ordem: mantém apenas categorias que realmente existem em 'frases'
                # e garante que todas as categorias existentes estejam na ordem (novas vão pro fim)
                existing_cats = set(frases.keys())
                sanitized_order = [cat for cat in loaded_order if cat in existing_cats]
                for cat in existing_cats:
                    if cat not in sanitized_order:
                        sanitized_order.append(cat)
                category_order = sanitized_order
                print(f"Ordem carregada e sanitizada: {category_order}")
            else:
                # Se não há ordem salva, cria uma ordem alfabética inicial
                category_order = sorted(frases.keys())
                print(f"Ordem não encontrada, criada ordem padrão: {category_order}")

            if ok: print("Dados carregados.")
            return # Retorna implicitamente None, pois os globais foram atualizados

        except (json.JSONDecodeError, IOError) as e:
            print(f"!!! ERRO ao carregar {ARQUIVO_FRASES}: {e}")
            messagebox.showerror("Erro Carregar", f"Erro ao ler {ARQUIVO_FRASES}:\n{e}\n\nIniciando com dados vazios.")
            frases = {}
            category_order = []
            return
    else:
        print(f"{ARQUIVO_FRASES} não encontrado. Iniciando vazio.");
        frases = {}
        category_order = []
        return

def salvar_frases():
    global frases, category_order # Usa globais
    print(f"Salvando em: {arquivo_frases_path}")
    # Cria o dicionário completo para salvar, incluindo a ordem
    data_to_save = {ORDER_KEY: category_order}
    data_to_save.update(frases) # Adiciona os dados das categorias

    try:
        with open(arquivo_frases_path, "w", encoding="utf-8") as f:
             json.dump(data_to_save, f, indent=4, ensure_ascii=False, sort_keys=False) # Não ordena chaves principais
        print("Dados salvos.")
    except IOError as e:
        print(f"!!! ERRO ao salvar {ARQUIVO_FRASES}: {e}")
        messagebox.showerror("Erro Salvar", f"Erro ao salvar {ARQUIVO_FRASES}:\n{e}")

# --- Helper Functions (get_node_data, etc. - sem mudanças) ---
def get_node_data(path):
    # (Código idêntico ao anterior)
    if not path: return None
    main_key = path[0]
    if main_key not in frases: return None
    level = frases[main_key]
    for step in path[1:]:
        if isinstance(level, dict) and step in level: level = level[step]
        else: return None
    return level

def get_parent_node_data(path):
    # (Código idêntico ao anterior)
    if not path: return None, None;
    if len(path) == 1: return frases, path[0]
    parent_path = path[:-1]; node_key = path[-1]; parent_node = get_node_data(parent_path)
    return parent_node, node_key

def get_path_from_iid(tree, iid):
    # (Código idêntico ao anterior)
    path = []; curr = iid
    while curr: path.insert(0, tree.item(curr, 'text')); curr = tree.parent(curr)
    return path

# --- Context Menu & Copy Functions (sem mudanças) ---
def copiar_texto_para_clipboard(text):
    global app
    if text:
        try: app.clipboard_clear(); app.clipboard_append(text); print(f"Copiado: '{text}'")
        except Exception as e: print(f"Erro copiar ctx/dbl: {e}")

def show_context_menu(event):
    global context_menu
    tree = event.widget; iid = tree.identify_row(event.y)
    if iid:
        tree.selection_set(iid); tree.focus_set()
        item_text = tree.item(iid, 'text')
        context_menu.delete(0, 'end')
        context_menu.add_command(label="Copiar", command=lambda t=item_text: copiar_texto_para_clipboard(t))
        try: context_menu.tk_popup(event.x_root, event.y_root)
        finally: context_menu.grab_release()
    else: pass

def on_treeview_double_click_copy(event, categoria_principal):
    try:
        tree = event.widget; iid = tree.identify_row(event.y)
        if not iid: return
        tree.selection_set(iid); tree.focus_set()
        item_text = tree.item(iid, 'text')
        copiar_texto_para_clipboard(item_text)
    except Exception as e: print(f"Erro dblclick: {e}")

def copiar_selecao_global(event=None):
    global abas, widgets_por_categoria
    try:
        tab_id = abas.select();
        if not tab_id: return
        cat = abas.tab(tab_id, "text")
        if cat in widgets_por_categoria:
            tree = widgets_por_categoria[cat]['tree']; sel = tree.selection()
            if not sel: return
            iid = sel[0]; text = tree.item(iid, 'text')
            copiar_texto_para_clipboard(text)
        else: pass
    except tk.TclError: pass
    except Exception as e: print(f"Erro copiar global: {e}")

# --- Category/Item Actions (Atualizadas para 'category_order') ---
def adicionar_categoria_principal():
    global frases, category_order, app # Modifica globais
    nome = simpledialog.askstring("Nova Categoria Principal", "Nome:", parent=app)
    if nome and nome.strip():
        nome = nome.strip()
        if nome in frases: messagebox.showerror("Erro", f"Categoria '{nome}' já existe.", parent=app); return
        if nome == ORDER_KEY: messagebox.showerror("Erro", f"Nome '{ORDER_KEY}' é reservado.", parent=app); return

        frases[nome] = {}
        category_order.append(nome) # Adiciona ao FIM da ordem
        criar_abas_e_conteudo()
        salvar_frases()
        try: abas.select(abas.tabs()[-1]) # Tenta selecionar a última aba adicionada
        except (ValueError, IndexError, tk.TclError): pass
    elif nome is not None: messagebox.showwarning("Aviso", "Nome vazio.", parent=app)

def remover_categoria_principal():
    global frases, category_order, app # Modifica globais
    if not category_order: messagebox.showinfo("Remover", "Nenhuma categoria.", parent=app); return

    # Ideal: usar combobox/listbox
    nome = simpledialog.askstring("Remover Categoria Principal", "Nome:", parent=app)
    if nome and nome in frases:
        if messagebox.askyesno("Confirmar", f"Remover '{nome}' e TODO seu conteúdo?", parent=app):
            del frases[nome]
            if nome in category_order: category_order.remove(nome) # Remove da ordem
            criar_abas_e_conteudo()
            salvar_frases()
    elif nome: messagebox.showerror("Erro", f"Categoria '{nome}' não encontrada.", parent=app)

def editar_categoria_principal():
    global frases, category_order, app # Modifica globais
    if not category_order: messagebox.showinfo("Renomear", "Nenhuma categoria.", parent=app); return

    nome_antigo = simpledialog.askstring("Renomear Categoria Principal", "Nome atual:", parent=app)
    if nome_antigo and nome_antigo in frases:
        novo_nome = simpledialog.askstring("Novo Nome", f"Novo nome para '{nome_antigo}':", parent=app)
        if novo_nome and novo_nome.strip() and novo_nome.strip() != nome_antigo:
            novo_nome = novo_nome.strip()
            if novo_nome == ORDER_KEY: messagebox.showerror("Erro", f"Nome '{ORDER_KEY}' reservado.", parent=app); return
            if novo_nome in frases: messagebox.showerror("Erro", f"Nome '{novo_nome}' já existe.", parent=app); return

            # Atualiza dados e ordem
            frases[novo_nome] = frases.pop(nome_antigo)
            try:
                index = category_order.index(nome_antigo)
                category_order[index] = novo_nome # Atualiza na lista de ordem
            except ValueError: # Se não estava na lista por algum motivo, adiciona no fim
                 category_order.append(novo_nome)

            criar_abas_e_conteudo()
            salvar_frases()
            try: # Tenta re-selecionar a aba renomeada
                idx_new = category_order.index(novo_nome)
                abas.select(abas.tabs()[idx_new])
            except (ValueError, IndexError, tk.TclError): pass
        elif novo_nome is not None and not novo_nome.strip(): messagebox.showwarning("Aviso", "Nome vazio.", parent=app)
    elif nome_antigo: messagebox.showerror("Erro", f"Categoria '{nome_antigo}' não encontrada.", parent=app)

# --- NOVAS FUNÇÕES PARA REORDENAR ABAS ---
def mover_categoria_esquerda():
    global category_order, app, abas
    try:
        current_tab_id = abas.select()
        if not current_tab_id: messagebox.showwarning("Mover", "Selecione uma aba para mover.", parent=app); return
        current_cat = abas.tab(current_tab_id, "text")

        if current_cat in category_order:
            index = category_order.index(current_cat)
            if index > 0: # Só pode mover se não for a primeira
                # Troca com o item à esquerda
                category_order[index], category_order[index - 1] = category_order[index - 1], category_order[index]
                print(f"Nova ordem: {category_order}")
                salvar_frases()
                criar_abas_e_conteudo()
                # Re-seleciona a aba movida (agora no novo índice)
                try: abas.select(abas.tabs()[index - 1])
                except (IndexError, tk.TclError): pass
            else:
                print("Já é a primeira aba.")
        else:
             messagebox.showerror("Erro Ordem", f"Categoria '{current_cat}' não encontrada na ordem interna.", parent=app)
    except tk.TclError: messagebox.showwarning("Mover", "Nenhuma aba selecionada.", parent=app)
    except Exception as e: messagebox.showerror("Erro Mover", f"Erro ao mover aba: {e}", parent=app)

def mover_categoria_direita():
    global category_order, app, abas
    try:
        current_tab_id = abas.select()
        if not current_tab_id: messagebox.showwarning("Mover", "Selecione uma aba para mover.", parent=app); return
        current_cat = abas.tab(current_tab_id, "text")

        if current_cat in category_order:
            index = category_order.index(current_cat)
            if index < len(category_order) - 1: # Só pode mover se não for a última
                # Troca com o item à direita
                category_order[index], category_order[index + 1] = category_order[index + 1], category_order[index]
                print(f"Nova ordem: {category_order}")
                salvar_frases()
                criar_abas_e_conteudo()
                # Re-seleciona a aba movida (agora no novo índice)
                try: abas.select(abas.tabs()[index + 1])
                except (IndexError, tk.TclError): pass
            else:
                print("Já é a última aba.")
        else:
             messagebox.showerror("Erro Ordem", f"Categoria '{current_cat}' não encontrada na ordem interna.", parent=app)
    except tk.TclError: messagebox.showwarning("Mover", "Nenhuma aba selecionada.", parent=app)
    except Exception as e: messagebox.showerror("Erro Mover", f"Erro ao mover aba: {e}", parent=app)

# --- Treeview Item Actions (adicionar_subcategoria, adicionar_frase_tree, etc. - sem mudanças) ---
def get_selected_tree_info(cat_princ):
    global widgets_por_categoria
    if cat_princ not in widgets_por_categoria: return None, None, None, None
    info = widgets_por_categoria[cat_princ]; tree = info['tree']; sel = tree.selection()
    if not sel: return tree, None, None, None
    iid = sel[0]; tags = tree.item(iid, 'tags'); type_ = 'phrase' if 'phrase' in tags else 'category'
    path = get_path_from_iid(tree, iid); return tree, iid, type_, path

def adicionar_subcategoria(cat_princ):
    global app
    tree, _, _, _ = get_selected_tree_info(cat_princ);
    if not tree: return
    parent_iid = ''; parent_data_path = [cat_princ]
    parent_node = get_node_data(parent_data_path)
    if parent_node is None or not isinstance(parent_node, dict): messagebox.showerror("Erro Interno", f"Nó pai não encontrado p/ '{cat_princ}'.", parent=app); return
    nome_sub = simpledialog.askstring("Nova Subcategoria", f"Nome (em '{cat_princ}'):", parent=app)
    if nome_sub and nome_sub.strip():
        nome_sub = nome_sub.strip()
        if nome_sub == PHRASES_KEY or nome_sub == ORDER_KEY: messagebox.showerror("Erro", f"'{nome_sub}' reservado.", parent=app); return
        if nome_sub in parent_node: messagebox.showerror("Erro", f"Item '{nome_sub}' já existe.", parent=app); return
        parent_node[nome_sub] = {}; new_iid = tree.insert(parent_iid, 'end', text=nome_sub, open=True, tags=('category',))
        tree.selection_set(new_iid); tree.focus(new_iid); salvar_frases(); update_button_states(cat_princ, tree)
    elif nome_sub is not None: messagebox.showwarning("Aviso", "Nome vazio.", parent=app)

def adicionar_frase_tree(cat_princ):
    global app
    tree, sel_iid, sel_type, sel_path = get_selected_tree_info(cat_princ)
    if not tree: return
    parent_iid = ''; parent_data_path = [cat_princ]
    if sel_iid:
        if sel_type == 'category': parent_iid = sel_iid; parent_data_path.extend(sel_path)
        elif sel_type == 'phrase':
            parent_iid = tree.parent(sel_iid)
            if len(sel_path) > 1: parent_data_path.extend(sel_path[:-1])
    parent_node = get_node_data(parent_data_path)
    if parent_node is None or not isinstance(parent_node, dict): messagebox.showerror("Erro Interno", f"Nó pai não encontrado p/ add frase.\nPath: {parent_data_path}", parent=app); return
    nova_frase = simpledialog.askstring("Nova Frase", "Digite:", parent=app)
    if nova_frase and nova_frase.strip():
        nova_frase = nova_frase.strip()
        if PHRASES_KEY not in parent_node: parent_node[PHRASES_KEY] = []
        elif not isinstance(parent_node[PHRASES_KEY], list): messagebox.showerror("Erro Dados", f"Inválido p/ frases em {parent_data_path}.", parent=app); parent_node[PHRASES_KEY] = []
        if nova_frase in parent_node[PHRASES_KEY]: messagebox.showwarning("Aviso", "Frase já existe.", parent=app); return
        parent_node[PHRASES_KEY].append(nova_frase); parent_node[PHRASES_KEY].sort()
        ph_uuid = str(uuid.uuid4()); new_iid = tree.insert(parent_iid, 'end', text=nova_frase, iid=ph_uuid, tags=('phrase',))
        tree.selection_set(new_iid); tree.focus(new_iid); salvar_frases(); update_button_states(cat_princ, tree)
    elif nova_frase is not None: messagebox.showwarning("Aviso", "Frase vazia.", parent=app)

def editar_item_tree(cat_princ):
    global app
    tree, sel_iid, sel_type, sel_path = get_selected_tree_info(cat_princ)
    if not tree or not sel_iid: messagebox.showwarning("Editar", "Selecione item.", parent=app); return
    item_atual = tree.item(sel_iid, 'text'); data_path = [cat_princ] + sel_path
    parent_node, node_key = get_parent_node_data(data_path)
    if parent_node is None: messagebox.showerror("Erro Interno", f"Nó pai não encontrado p/ editar.\nPath Pai: {data_path[:-1]}", parent=app); return
    if sel_type == 'category':
        novo_nome = simpledialog.askstring("Renomear Subcategoria", "Novo nome:", initialvalue=item_atual, parent=app)
        if novo_nome and novo_nome.strip() and novo_nome.strip() != item_atual:
            novo_nome = novo_nome.strip()
            if novo_nome == PHRASES_KEY or novo_nome == ORDER_KEY: messagebox.showerror("Erro", f"'{novo_nome}' reservado.", parent=app); return
            if novo_nome in parent_node: messagebox.showerror("Erro", f"Item '{novo_nome}' já existe.", parent=app); return
            if item_atual in parent_node and isinstance(parent_node[item_atual], dict):
                parent_node[novo_nome] = parent_node.pop(item_atual); tree.item(sel_iid, text=novo_nome); salvar_frases()
            else: messagebox.showerror("Erro Dados", f"Subcat. '{item_atual}' não encontrada/inválida.", parent=app)
        elif novo_nome is not None and not novo_nome.strip(): messagebox.showwarning("Aviso", "Nome vazio.", parent=app)
    elif sel_type == 'phrase':
        if not isinstance(parent_node, dict) or PHRASES_KEY not in parent_node or \
           not isinstance(parent_node[PHRASES_KEY], list) or item_atual not in parent_node[PHRASES_KEY]:
             messagebox.showerror("Erro Dados", f"Frase '{item_atual}' ou estrutura pai não encontrada.", parent=app); return
        nova_frase = simpledialog.askstring("Editar Frase", "Altere:", initialvalue=item_atual, parent=app)
        if nova_frase and nova_frase.strip() and nova_frase.strip() != item_atual:
            nova_frase = nova_frase.strip()
            temp_list = [p for p in parent_node[PHRASES_KEY] if p != item_atual]
            if nova_frase in temp_list: messagebox.showwarning("Aviso", "Essa frase já existe.", parent=app); return
            try:
                idx = parent_node[PHRASES_KEY].index(item_atual); parent_node[PHRASES_KEY][idx] = nova_frase
                parent_node[PHRASES_KEY].sort(); tree.item(sel_iid, text=nova_frase); salvar_frases()
            except ValueError: messagebox.showerror("Erro Dados", "Frase original não encontrada.", parent=app)
        elif nova_frase is not None and not nova_frase.strip(): messagebox.showwarning("Aviso", "Frase vazia.", parent=app)

def remover_item_tree(cat_princ):
    global app
    tree, sel_iid, sel_type, sel_path = get_selected_tree_info(cat_princ)
    if not tree or not sel_iid: messagebox.showwarning("Remover", "Selecione item.", parent=app); return
    item_texto = tree.item(sel_iid, 'text'); data_path = [cat_princ] + sel_path
    confirm_msg = f"Remover '{item_texto}'?"
    if sel_type == 'category' and tree.get_children(sel_iid): confirm_msg += "\n\nATENÇÃO: Conteúdo interno perdido!"
    if messagebox.askyesno("Confirmar Remoção", confirm_msg, parent=app):
        parent_node, node_key = get_parent_node_data(data_path)
        if parent_node is None: messagebox.showerror("Erro Interno", f"Nó pai não encontrado p/ '{item_texto}'.", parent=app); return
        item_rem = item_texto
        try:
            if sel_type == 'category':
                 if isinstance(parent_node, dict) and item_rem in parent_node: del parent_node[item_rem]
                 else: raise KeyError(f"Subcat. '{item_rem}' não nos dados pai ({type(parent_node).__name__}).")
            else: # phrase
                 if isinstance(parent_node, dict) and PHRASES_KEY in parent_node and \
                    isinstance(parent_node[PHRASES_KEY], list) and item_rem in parent_node[PHRASES_KEY]:
                     parent_node[PHRASES_KEY].remove(item_rem)
                     if not parent_node[PHRASES_KEY]: del parent_node[PHRASES_KEY]
                 else: raise ValueError(f"Frase '{item_rem}' não na lista '{PHRASES_KEY}' ou estrutura inválida.")
            tree.delete(sel_iid); salvar_frases(); update_button_states(cat_princ, tree)
        except (KeyError, ValueError) as e: messagebox.showerror("Erro Dados", f"Não removeu '{item_rem}'.\n\n{e}", parent=app)

# --- UI Update Functions ---
def aplicar_tema(nome_tema):
    global current_theme, style, app, menu, menu_arquivo, menu_editar, menu_organizar, menu_tema, context_menu
    current_theme = nome_tema; colors = themes[current_theme]; style.theme_use('clam')
    style.configure('.', background=colors['bg'], foreground=colors['fg'], fieldbackground=colors['tree_bg'], insertcolor=colors['fg'])
    style.configure('TFrame', background=colors['bg']); style.configure('TLabel', background=colors['bg'], foreground=colors['fg'])
    style.configure('TButton', background=colors['button_bg'], foreground=colors['button_fg'], bordercolor=colors['fg'], padding=(8, 4))
    style.map('TButton', background=[('active', colors['button_active_bg']), ('disabled', colors['bg'])], foreground=[('disabled', colors['disabled_fg'])])
    style.configure('TNotebook', background=colors['bg'], borderwidth=0)
    style.configure('TNotebook.Tab', background=colors['tab_inactive_bg'], foreground=colors['fg'], padding=(10, 5), borderwidth=1)
    style.map('TNotebook.Tab', background=[('selected', colors['tab_active_bg'])], expand=[('selected', [1, 1, 1, 0])])
    style.configure('Treeview', background=colors['tree_bg'], foreground=colors['tree_fg'], fieldbackground=colors['tree_bg'], rowheight=25)
    style.map('Treeview', background=[('selected', colors['tree_select_bg'])], foreground=[('selected', colors['tree_select_fg'])])
    style.configure("Treeview.Heading", background=colors['heading_bg'], foreground=colors['heading_fg'], relief="flat", padding=(5,5))
    style.map("Treeview.Heading", background=[('active', colors['button_active_bg'])])
    app.config(bg=colors['bg']); menu.config(bg=colors['bg'], fg=colors['fg'], activebackground=colors['button_active_bg'], activeforeground=colors['button_fg'])
    menu_arquivo.config(bg=colors['bg'], fg=colors['fg'], activebackground=colors['button_active_bg'], activeforeground=colors['button_fg'])
    if 'menu_editar' in globals(): menu_editar.config(bg=colors['bg'], fg=colors['fg'], activebackground=colors['button_active_bg'], activeforeground=colors['button_fg'])
    if 'menu_organizar' in globals(): menu_organizar.config(bg=colors['bg'], fg=colors['fg'], activebackground=colors['button_active_bg'], activeforeground=colors['button_fg']) # Estiliza novo menu
    menu_tema.config(bg=colors['bg'], fg=colors['fg'], activebackground=colors['button_active_bg'], activeforeground=colors['button_fg'])
    context_menu.config(bg=colors['bg'], fg=colors['fg'], activebackground=colors['button_active_bg'], activeforeground=colors['button_fg'])
    criar_abas_e_conteudo() # Recria UI

def ativar_modo_claro(): aplicar_tema("light")
def ativar_modo_escuro(): aplicar_tema("dark")

def update_button_states(cat_princ, tree):
    global widgets_por_categoria
    if cat_princ not in widgets_por_categoria: return
    buttons = widgets_por_categoria[cat_princ]['buttons']; has_sel = bool(tree.selection())
    buttons['add_sub'].config(state='normal'); buttons['add_phrase'].config(state='normal')
    edit_rem_state = 'normal' if has_sel else 'disabled'
    buttons['edit'].config(state=edit_rem_state); buttons['remove'].config(state=edit_rem_state)

def on_treeview_select(event, categoria_principal):
    tree = event.widget
    update_button_states(categoria_principal, tree)
    tree.focus_set()

def populate_tree(tree, parent_iid, data_node):
    # (Código idêntico ao anterior)
    if not isinstance(data_node, dict): return
    category_keys = sorted([k for k, v in data_node.items() if k != PHRASES_KEY and isinstance(v, dict)])
    phrase_list = sorted(data_node.get(PHRASES_KEY, []))
    for key in category_keys:
        value = data_node[key]
        child_iid = tree.insert(parent_iid, 'end', text=key, open=False, tags=('category',))
        populate_tree(tree, child_iid, value)
    if phrase_list:
        for phrase_text in phrase_list:
             ph_uuid = str(uuid.uuid4()); tree.insert(parent_iid, 'end', text=phrase_text, iid=ph_uuid, tags=('phrase',))

def criar_abas_e_conteudo():
    global abas, widgets_por_categoria, label_sem_categorias, category_order, frases # Usa globais
    # Limpa abas antigas
    if abas: # Verifica se 'abas' já foi criado
        for tab_id in abas.tabs(): abas.forget(tab_id)
    widgets_por_categoria.clear()

    # Mostra/esconde mensagem ou notebook
    if not category_order: # Verifica pela lista de ordem agora
        if 'label_sem_categorias' in globals() and label_sem_categorias.winfo_exists(): label_sem_categorias.pack(expand=True, fill="both", padx=20, pady=50)
        if 'abas' in globals() and abas.winfo_exists(): abas.pack_forget();
        return
    else:
        if 'label_sem_categorias' in globals() and label_sem_categorias.winfo_exists(): label_sem_categorias.pack_forget();
        if 'abas' in globals() and abas.winfo_exists(): abas.pack(expand=True, fill="both", padx=5, pady=5)

    # Cria abas na ordem definida por category_order
    for cat_princ in category_order:
        if cat_princ not in frases: # Segurança: pula se categoria na ordem não existe mais
            print(f"Aviso: Categoria '{cat_princ}' na ordem não encontrada nos dados. Pulando.")
            continue

        data_root = frases[cat_princ]
        tab_frame = ttk.Frame(abas, style='TFrame', padding=(5, 5))
        abas.add(tab_frame, text=cat_princ) # Adiciona na ordem da lista

        # --- Resto da criação da UI da aba (Treeview, Botões) ---
        tree_frame = ttk.Frame(tab_frame, style='TFrame'); tree_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        tree = ttk.Treeview(tree_frame, style='Treeview', selectmode="browse"); tree.heading("#0", text="Itens", anchor='w')
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview); hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set); vsb.pack(side='right', fill='y'); hsb.pack(side='bottom', fill='x'); tree.pack(side='left', fill='both', expand=True)

        tree.bind('<Double-1>', lambda event, cp=cat_princ: on_treeview_double_click_copy(event, cp))
        tree.bind('<Button-3>', show_context_menu)
        tree.bind('<<TreeviewSelect>>', lambda event, cp=cat_princ: on_treeview_select(event, cp))

        populate_tree(tree, '', data_root)
        botoes_frame = ttk.Frame(tab_frame, style='TFrame'); botoes_frame.pack(side="right", fill="y", padx=(5, 0))
        btn_add_sub = ttk.Button(botoes_frame, text="+ Subcategoria", style='TButton', command=lambda cp=cat_princ: adicionar_subcategoria(cp))
        btn_add_phrase = ttk.Button(botoes_frame, text="+ Frase", style='TButton', command=lambda cp=cat_princ: adicionar_frase_tree(cp))
        btn_edit = ttk.Button(botoes_frame, text="Editar Item", style='TButton', state='disabled', command=lambda cp=cat_princ: editar_item_tree(cp))
        btn_remove = ttk.Button(botoes_frame, text="Remover Item", style='TButton', state='disabled', command=lambda cp=cat_princ: remover_item_tree(cp))
        btn_add_sub.pack(pady=3, fill="x"); btn_add_phrase.pack(pady=3, fill="x"); btn_edit.pack(pady=3, fill="x"); btn_remove.pack(pady=(3, 10), fill="x")
        widgets_por_categoria[cat_princ] = {'tree': tree, 'buttons': {'add_sub': btn_add_sub, 'add_phrase': btn_add_phrase, 'edit': btn_edit, 'remove': btn_remove }}
        update_button_states(cat_princ, tree)

# --- Fim das Definições de Funções ---

# --- Bloco Principal de Execução com Captura de Erro ---
initialization_error = None

try:
    print("--- Iniciando Configuração Principal ---")
    app = tk.Tk() # Define app global aqui
    print("1. Janela Tk() criada.")

    app.title("Frazeologia Pro"); app.geometry("800x550")
    print("2. Título e Geometria definidos.")

    try:
        if os.path.exists(icon_path): app.iconbitmap(icon_path); print(f"3. Ícone definido: {icon_path}")
        else: print(f"3. Aviso: Ícone não encontrado em {icon_path}.")
    except Exception as e_icon: print(f"3. ERRO ao definir ícone: {e_icon}")

    style = ttk.Style(app); print("4. Estilo ttk inicializado.")
    menu = tk.Menu(app); app.config(menu=menu)
    print("5. Menu principal criado.")

    context_menu = tk.Menu(app, tearoff=0); print("6. Menu de contexto inicializado.") # Define context_menu global aqui

    # --- Menus Principais (com Organizar adicionado) ---
    menu_arquivo = tk.Menu(menu, tearoff=0); menu.add_cascade(label="Categorias", menu=menu_arquivo) # Renomeado para Categorias
    menu_arquivo.add_command(label="Nova", command=adicionar_categoria_principal); menu_arquivo.add_command(label="Renomear", command=editar_categoria_principal)
    menu_arquivo.add_command(label="Remover", command=remover_categoria_principal); menu_arquivo.add_separator(); menu_arquivo.add_command(label="Sair", command=app.quit)

    menu_editar = tk.Menu(menu, tearoff=0); menu.add_cascade(label="Editar", menu=menu_editar)
    menu_editar.add_command(label="Copiar Seleção", command=copiar_selecao_global)

    # NOVO MENU ORGANIZAR
    menu_organizar = tk.Menu(menu, tearoff=0); menu.add_cascade(label="Organizar Abas", menu=menu_organizar)
    menu_organizar.add_command(label="Mover Aba para Esquerda", command=mover_categoria_esquerda)
    menu_organizar.add_command(label="Mover Aba para Direita", command=mover_categoria_direita)

    menu_tema = tk.Menu(menu, tearoff=0); menu.add_cascade(label="Tema", menu=menu_tema)
    menu_tema.add_command(label="Modo Claro", command=ativar_modo_claro); menu_tema.add_command(label="Modo Escuro", command=ativar_modo_escuro)
    print("7. Menus da barra adicionados (incluindo Organizar).")
    # --- Fim Menus ---

    main_frame = ttk.Frame(app, padding=5); main_frame.pack(expand=True, fill="both")
    label_sem_categorias = ttk.Label(main_frame, text="Nenhuma categoria.\nUse o menu para adicionar.", font=("Segoe UI", 12), justify="center", anchor="center", style='TLabel') # Define global
    abas = ttk.Notebook(main_frame, style='TNotebook') # Define global
    print("8. Widgets principais (frame, label, notebook) criados.")

    print("9. Carregando frases e ordem...")
    carregar_frases() # Carrega nos globais 'frases' e 'category_order'
    print(f"10. Dados carregados ({len(category_order)} categorias na ordem: {category_order}).")

    print("11. Aplicando tema e criando abas/conteúdo inicial...")
    aplicar_tema(current_theme)
    print("12. Tema aplicado e conteúdo inicial criado.")

    print("--- Configuração Principal Concluída. Entrando no mainloop... ---")
    app.mainloop()
    print("--- Mainloop finalizado (Janela Fechada Normalmente) ---")

except Exception as e_init:
    print(f"\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print(f"!!! ERRO FATAL DURANTE A INICIALIZAÇÃO !!!")
    print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
    initialization_error = e_init
    traceback.print_exc()
    try:
        with open(log_filename, "w", encoding="utf-8") as f_err:
            f_err.write("--- ERRO FATAL NA INICIALIZAÇÃO ---\n"); f_err.write(f"Erro: {type(e_init).__name__}: {e_init}\n\n")
            f_err.write("--- Traceback Completo: ---\n"); traceback.print_exc(file=f_err)
        print(f"\n---> Erro detalhado gravado em: {os.path.abspath(log_filename)}")
    except Exception as e_log: print(f"\n---> ATENÇÃO: Falha ao gravar log de erro: {e_log}")
    try:
        if app is not None and isinstance(app, tk.Tk) and app.winfo_exists():
             messagebox.showerror("Erro Fatal na Inicialização", f"Erro grave ao iniciar:\n\n{type(e_init).__name__}: {e_init}\n\nConsulte '{os.path.basename(log_filename)}' ou o console.")
    except Exception as e_msg: print(f"Falha ao mostrar messagebox de erro: {e_msg}")
    if os.name == 'nt': input("\nERRO FATAL. Pressione Enter para sair...")