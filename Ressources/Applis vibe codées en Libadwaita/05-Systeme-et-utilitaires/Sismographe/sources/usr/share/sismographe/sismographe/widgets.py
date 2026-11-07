"""Petites briques d’interface communes."""
from gi.repository import Adw, Gdk, GLib, Gtk, Pango

STATUS = {
    "ok": ("object-select-symbolic", "success"),
    "info": ("dialog-information-symbolic", "accent"),
    "warn": ("dialog-warning-symbolic", "warning"),
    "error": ("dialog-error-symbolic", "error"),
    "off": ("action-unavailable-symbolic", "dim-label"),
    "wait": ("content-loading-symbolic", "dim-label"),
}
RANK = {"ok": 0, "off": 0, "info": 0, "wait": 0, "warn": 1, "error": 2}

LEVEL_CLASS = {0: "lvl-err", 1: "lvl-err", 2: "lvl-err", 3: "lvl-err", 4: "lvl-warn",
               5: "lvl-notice", 6: "lvl-info", 7: "lvl-info"}

CSS = """
.lvl { border-radius: 99px; padding: 1px 8px; font-size: 0.8em; font-weight: 700; min-width: 3em; }
.lvl-err { background: alpha(@error_color, 0.16); color: @error_color; }
.lvl-warn { background: alpha(@warning_color, 0.18); color: @warning_color; }
.lvl-notice { background: alpha(@accent_color, 0.14); color: @accent_color; }
.lvl-info { background: alpha(currentColor, 0.08); color: alpha(currentColor, 0.65); }
.unit-label { color: @accent_color; font-weight: 600; }
.event-row { padding: 5px 12px; }
.hero-title { font-size: 1.6em; font-weight: 800; }
.hero-icon.success { color: @success_color; }
.hero-icon.warning { color: @warning_color; }
.hero-icon.error { color: @error_color; }
.mono-card { padding: 12px 14px; }
.journal-controls { padding: 8px 12px; }
.legend-dot { border-radius: 99px; min-width: 10px; min-height: 10px; }
"""


def install_css():
    provider = Gtk.CssProvider()
    if hasattr(provider, "load_from_string"):
        provider.load_from_string(CSS)
    else:
        provider.load_from_data(CSS.encode())
    Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider,
                                              Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


def status_icon(kind, size=16):
    icon, css = STATUS.get(kind, STATUS["off"])
    image = Gtk.Image.new_from_icon_name(icon)
    image.set_pixel_size(size)
    image.add_css_class(css)
    return image


def worst(kinds):
    kinds = list(kinds) or ["ok"]
    return max(kinds, key=lambda k: RANK.get(k, 0))


def row(title, subtitle="", status=None, value=None, activatable=False, wrap_subtitle=False):
    r = Adw.ActionRow(title=title, use_markup=False)
    if subtitle:
        r.set_subtitle(subtitle)
    if not wrap_subtitle:
        r.set_subtitle_lines(2)
    if status:
        r.add_prefix(status_icon(status))
    if value is not None:
        r.add_suffix(value_label(value))
    if activatable:
        r.set_activatable(True)
        r.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
    return r


def expander(title, subtitle="", status=None):
    r = Adw.ExpanderRow(title=title, use_markup=False)
    if subtitle:
        r.set_subtitle(subtitle)
    if status:
        r.add_prefix(status_icon(status))
    return r


def value_label(text, css="dim-label"):
    text = str(text)
    label = Gtk.Label(label=text, xalign=1, wrap=len(text) > 22, max_width_chars=36,
                      valign=Gtk.Align.CENTER, justify=Gtk.Justification.RIGHT)
    if css:
        label.add_css_class(css)
    return label


def mono_block(text, wrap=False):
    label = Gtk.Label(label=text, xalign=0, yalign=0, selectable=True, wrap=wrap)
    label.add_css_class("monospace")
    if wrap:
        label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
    box = Gtk.ScrolledWindow(vscrollbar_policy=Gtk.PolicyType.NEVER,
                             hscrollbar_policy=Gtk.PolicyType.NEVER if wrap else Gtk.PolicyType.AUTOMATIC,
                             propagate_natural_height=True)
    box.set_child(label)
    frame = Gtk.Box()
    frame.add_css_class("card")
    frame.add_css_class("mono-card")
    frame.append(box)
    box.set_hexpand(True)
    return frame


def level_pill(priority, text):
    label = Gtk.Label(label=text, valign=Gtk.Align.CENTER)
    label.add_css_class("lvl")
    label.add_css_class(LEVEL_CLASS[priority])
    return label


def button(label, icon=None, css=(), tooltip=None, callback=None):
    btn = Gtk.Button()
    if icon:
        content = Adw.ButtonContent(label=label, icon_name=icon)
        btn.set_child(content)
    else:
        btn.set_label(label)
    for c in css:
        btn.add_css_class(c)
    if tooltip:
        btn.set_tooltip_text(tooltip)
    if callback:
        btn.connect("clicked", lambda *_: callback())
    return btn


def spinner(size=32):
    sp = Adw.Spinner()
    sp.set_size_request(size, size)
    sp.set_halign(Gtk.Align.CENTER)
    sp.set_valign(Gtk.Align.CENTER)
    return sp


def loading_page(title="Chargement…"):
    page = Adw.StatusPage(title=title)
    page.set_child(spinner(32))
    return page


def copy_text(widget, text):
    clipboard = widget.get_clipboard()
    data = GLib.Bytes.new(text.encode("utf-8"))
    clipboard.set_content(Gdk.ContentProvider.new_union([
        Gdk.ContentProvider.new_for_bytes("text/plain;charset=utf-8", data),
        Gdk.ContentProvider.new_for_bytes("text/plain", data),
    ]))


def clear_page(page, groups):
    for group in groups:
        page.remove(group)
    groups.clear()
