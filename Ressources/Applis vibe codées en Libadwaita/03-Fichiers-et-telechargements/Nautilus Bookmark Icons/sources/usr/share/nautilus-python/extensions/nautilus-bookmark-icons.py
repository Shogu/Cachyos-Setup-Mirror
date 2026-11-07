# SPDX-License-Identifier: MIT
# Nautilus Bookmark Icons - extracted/adapted from nautilus-my-computer
# Original bookmark icon implementation Copyright (c) 2026 Yann Masoch.

import os
import gi

gi.require_version('Gdk','4.0')
gi.require_version('Gio','2.0')
gi.require_version('GLib','2.0')
gi.require_version('Gtk','4.0')
gi.require_version('Adw','1')
# Do NOT call gi.require_version() for Nautilus here: nautilus-python has
# already loaded the matching typelib (Nautilus 4.1 on Nautilus 50).
from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk, Nautilus

SCHEMA_ID='io.github.ogu.nautilus-bookmark-icons'
COLS, ROWS, CELL, SPACING = 6, 5, 36, 4

def all_widgets(w):
    if not w: return
    yield w
    c=w.get_first_child()
    while c:
        yield from all_widgets(c); c=c.get_next_sibling()

def bookmarks():
    path=os.path.join(GLib.get_user_config_dir(),'gtk-3.0','bookmarks'); out=set()
    try:
        with open(path, encoding='utf-8') as f:
            for line in f:
                line=line.strip()
                if line: out.add(line.split(maxsplit=1)[0].rstrip('/'))
    except OSError: pass
    return out

def menu_section(model, action):
    st=GLib.VariantType.new('s')
    for i in range(model.get_n_items()):
        sec=model.get_item_link(i,Gio.MENU_LINK_SECTION)
        if sec:
            for j in range(sec.get_n_items()):
                av=sec.get_item_attribute_value(j,'action',st)
                if av is not None and av.get_string()==action: return sec
    return None

def start_image(row):
    for w in all_widgets(row):
        if not isinstance(w,Gtk.Image): continue
        p=w.get_parent(); in_button=False
        while p and p is not row:
            if isinstance(p,Gtk.Button): in_button=True; break
            p=p.get_parent()
        if not in_button: return w
    return None

def pin(img,name):
    img._nbi_name=name; img.set_from_icon_name(name); img.set_visible(True)
    if getattr(img,'_nbi_pinned',False): return
    img._nbi_pinned=True; img._nbi_restoring=False
    def changed(image,_pspec):
        if image._nbi_restoring: return
        target=getattr(image,'_nbi_name',None)
        if target is None: return
        if image.get_storage_type()!=Gtk.ImageType.ICON_NAME or image.get_icon_name()!=target or not image.get_visible():
            image._nbi_restoring=True; image.set_from_icon_name(target); image.set_visible(True); image._nbi_restoring=False
    for sig in ('notify::icon-name','notify::gicon','notify::paintable','notify::storage-type','notify::visible'):
        img.connect(sig,changed)

def icons(settings): return settings.get_value('custom-bookmark-icons').unpack()
def save(settings,uri,name):
    d=icons(settings); d[uri.rstrip('/')]=name; settings.set_value('custom-bookmark-icons',GLib.Variant('a{ss}',d))
def clear(settings,uri):
    d=icons(settings)
    if d.pop(uri.rstrip('/'),None) is not None: settings.set_value('custom-bookmark-icons',GLib.Variant('a{ss}',d))

def apply(row,name):
    img=start_image(row)
    if not img: return
    theme=Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
    if not theme.has_icon(name): return
    if not hasattr(row,'_nbi_native'): row._nbi_native=row.get_property('start-icon')
    row.set_property('start-icon',Gio.ThemedIcon.new(name)); pin(img,name)

def reset(row):
    img=start_image(row)
    if img: img._nbi_name=None
    native=getattr(row,'_nbi_native',None)
    if native is not None: row.set_property('start-icon',native); del row._nbi_native

def is_nautilus_window(win):
    try:
        if type(win).__name__ in ("NautilusWindow", "NautilusFileChooser"):
            return True
        bid = win.get_buildable_id() if hasattr(win, "get_buildable_id") else None
        if bid == "NautilusWindow":
            return True
        if hasattr(win, "has_css_class") and win.has_css_class("nautilus-window"):
            return True
        return any(isinstance(w, Adw.OverlaySplitView) for w in all_widgets(win))
    except Exception:
        return False

def find_listbox(win):
    # Nautilus 50: use the same structural path as nautilus-my-computer:
    # OverlaySplitView -> sidebar ToolbarView -> native NautilusSidebar.
    split = next((w for w in all_widgets(win) if isinstance(w, Adw.OverlaySplitView)), None)
    toolbar = split.get_sidebar() if split else None
    sidebar = toolbar.get_content() if isinstance(toolbar, Adw.ToolbarView) else None
    if sidebar is None:
        return None, None

    places = None
    for w in all_widgets(sidebar):
        bid = w.get_buildable_id() if hasattr(w, "get_buildable_id") else None
        name = w.get_name() if hasattr(w, "get_name") else None
        if bid == "places_sidebar" or name == "places_sidebar" or type(w).__name__ == "NautilusSidebar":
            places = w
            break
    root = places or sidebar
    boxes = [w for w in all_widgets(root) if isinstance(w, Gtk.ListBox)]
    for css in ("navigation-sidebar", "places-sidebar-list"):
        for lb in boxes:
            if lb.has_css_class(css):
                return sidebar, lb
    return (sidebar, boxes[0]) if boxes else (sidebar, None)

class BookmarkIconsExtension(GObject.GObject, Nautilus.MenuProvider):
    def __init__(self):
        super().__init__(); self.settings=Gio.Settings.new(SCHEMA_ID); self.states={}
        self.settings.connect('changed::custom-bookmark-icons',lambda *_: GLib.idle_add(self.rescan_all))
        GLib.idle_add(self._late_init)

    def _late_init(self):
        self.scan_windows()
        app = Gtk.Application.get_default()
        if app is not None:
            app.connect("window-added", lambda _app, _win: GLib.timeout_add(150, self.scan_windows_once))
        # Keep a low-frequency fallback for sidebar rebuilds/window discovery.
        GLib.timeout_add_seconds(2, self.scan_windows)
        return GLib.SOURCE_REMOVE

    def scan_windows_once(self):
        self.scan_windows()
        return GLib.SOURCE_REMOVE

    def scan_windows(self):
        for win in Gtk.Window.list_toplevels():
            if not is_nautilus_window(win): continue
            sidebar,lb=find_listbox(win)
            if lb is None: continue
            st=self.states.get(win)
            if st is None or st['lb'] is not lb:
                if st and st.get('model') and st.get('handler'):
                    try: st['model'].disconnect(st['handler'])
                    except Exception: pass
                model=lb.observe_children()
                handler=model.connect('items-changed',lambda *_a,w=win: GLib.idle_add(self.rescan_window,w))
                self.states[win]={'sidebar':sidebar,'lb':lb,'model':model,'handler':handler}
            self.rescan_window(win)
        return GLib.SOURCE_CONTINUE

    def rescan_all(self):
        for win in list(self.states): self.rescan_window(win)
        return GLib.SOURCE_REMOVE

    def rescan_window(self,win):
        st=self.states.get(win)
        if not st: return GLib.SOURCE_REMOVE
        lb=st['lb']; wanted=bookmarks(); custom=icons(self.settings); i=0
        while (row:=lb.get_row_at_index(i)) is not None:
            i+=1
            try: uri=row.get_property('uri')
            except Exception: uri=None
            if not uri or uri.rstrip('/') not in wanted: continue
            name=custom.get(uri.rstrip('/'))
            if name: apply(row,name)
            if getattr(row,'_nbi_menu',False): continue
            try: label=row.get_property('label') or uri
            except Exception: label=uri
            gesture=Gtk.GestureClick(); gesture.set_button(3); gesture.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
            gesture.connect('released',lambda _g,_n,_x,_y,u=uri,l=label,w=win,r=row: GLib.idle_add(self.inject,w,u,l,r))
            row.add_controller(gesture); row._nbi_menu=True
        return GLib.SOURCE_REMOVE

    def inject(self,win,uri,label,row):
        st=self.states.get(win)
        if not st: return GLib.SOURCE_REMOVE
        pop=None
        for w in all_widgets(st['sidebar']):
            if isinstance(w,Gtk.PopoverMenu) and w.get_mapped(): pop=w
        if not pop or getattr(pop,'_nbi_injected',False): return GLib.SOURCE_REMOVE
        model=pop.get_menu_model()
        if not isinstance(model,Gio.Menu): return GLib.SOURCE_REMOVE
        sec=menu_section(model,'row.rename')
        if not isinstance(sec,Gio.Menu): sec=Gio.Menu(); model.append_section(None,sec)
        sec.append('Changer l’icône','nbi.change-icon')
        ag=Gio.SimpleActionGroup(); act=Gio.SimpleAction.new('change-icon',None)
        act.connect('activate',lambda *_: self.picker(uri,label,row)); ag.add_action(act)
        pop.insert_action_group('nbi',ag); pop._nbi_injected=True
        return GLib.SOURCE_REMOVE

    def picker(self,uri,label,row):
        current=icons(self.settings).get(uri.rstrip('/')); height=ROWS*CELL+(ROWS-1)*SPACING
        pop=Gtk.Popover(); pop.set_parent(row); pop.set_position(Gtk.PositionType.RIGHT)
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8); box.set_margin_top(10); box.set_margin_bottom(10)
        header=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8); header.set_hexpand(True); header.set_margin_start(10); header.set_margin_end(10); box.append(header)
        title=Gtk.Label(label='<b>Icône</b>'); title.set_use_markup(True); title.set_xalign(0); header.append(title)
        search=Gtk.SearchEntry(); search.set_placeholder_text('Rechercher une icône…'); search.connect('stop-search',lambda _e: pop.popdown()); header.append(search)
        flow=Gtk.FlowBox(); flow.set_selection_mode(Gtk.SelectionMode.SINGLE); flow.set_activate_on_single_click(True); flow.set_max_children_per_line(COLS); flow.set_min_children_per_line(COLS); flow.set_homogeneous(True); flow.set_row_spacing(SPACING); flow.set_column_spacing(SPACING); flow.set_valign(Gtk.Align.START); flow.set_halign(Gtk.Align.START); flow.set_margin_start(10); flow.set_margin_end(10)
        resetb=Gtk.Button(label='Réinitialiser'); resetb.set_sensitive(current is not None)
        def activated(_f,child):
            save(self.settings,uri,child._nbi_icon); apply(row,child._nbi_icon); resetb.set_sensitive(True)
        def reset_clicked(_b):
            clear(self.settings,uri); reset(row); flow.unselect_all(); resetb.set_sensitive(False)
        flow.connect('child-activated',activated)
        theme=Gtk.IconTheme.get_for_display(Gdk.Display.get_default()); selected=None
        for name in sorted(n for n in theme.get_icon_names() if n.endswith('-symbolic')):
            img=Gtk.Image.new_from_icon_name(name); img.set_tooltip_text(name); child=Gtk.FlowBoxChild(); child.set_child(img); child.set_size_request(CELL,CELL); child._nbi_icon=name; flow.append(child)
            if name==current: selected=child
        if selected: flow.select_child(selected)
        flow.set_filter_func(lambda c: not (q:=search.get_text().strip().lower()) or q in c._nbi_icon.lower()); search.connect('search-changed',lambda _e: flow.invalidate_filter())
        scroll=Gtk.ScrolledWindow(); scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC); scroll.set_size_request(-1,height); scroll.set_child(flow); box.append(scroll)
        resetb.set_margin_start(10); resetb.set_margin_end(10); resetb.connect('clicked',reset_clicked); box.append(resetb)
        pop.set_child(box); pop.connect('closed',lambda p:p.unparent()); pop.popup()
