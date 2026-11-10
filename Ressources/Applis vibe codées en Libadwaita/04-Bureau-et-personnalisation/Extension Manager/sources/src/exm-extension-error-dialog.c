/*
 * exm-extension-error-dialog.c
 *
 * Copyright 2022-2025 Matthew Jakeman <mjakeman26@outlook.co.nz>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "exm-extension-error-dialog.h"

#include "exm-config.h"

#include <glib/gi18n.h>

struct _ExmExtensionErrorDialog
{
    AdwDialog parent_instance;

    AdwToastOverlay *toast_overlay;
    GtkLabel *title_label;
    AdwPreferencesGroup *trace_group;
    GtkTextView *text_view;
    GtkButton *report_btn;
    char *error_string;
    char *homepage;
};

G_DEFINE_FINAL_TYPE (ExmExtensionErrorDialog, exm_extension_error_dialog, ADW_TYPE_DIALOG)

ExmExtensionErrorDialog *
exm_extension_error_dialog_new (const char *extension_name,
                                const char *error_text,
                                const char *homepage)
{
    ExmExtensionErrorDialog *self;
    char *title;

    self = g_object_new (EXM_TYPE_EXTENSION_ERROR_DIALOG, NULL);

    title = extension_name != NULL
        ? g_strdup_printf (_("“%s” Failed to Load"), extension_name)
        : g_strdup (_("Extension Failed to Load"));
    gtk_label_set_text (self->title_label, title);
    g_free (title);

    self->error_string = g_strdup (error_text);
    gtk_text_buffer_set_text (gtk_text_view_get_buffer (self->text_view),
                              self->error_string, -1);

    self->homepage = g_strdup (homepage);
    gtk_widget_set_visible (GTK_WIDGET (self->report_btn), self->homepage != NULL);
    gtk_widget_set_tooltip_text (GTK_WIDGET (self->report_btn), self->homepage);

    return self;
}

static void
on_copy_button_clicked (GtkButton                *button G_GNUC_UNUSED,
                        ExmExtensionErrorDialog  *self)
{
    GdkDisplay *display;
    GdkClipboard *clipboard;

    display = gdk_display_get_default ();
    clipboard = gdk_display_get_clipboard (display);

    gdk_clipboard_set_text (clipboard, self->error_string);

    adw_toast_overlay_add_toast (self->toast_overlay, adw_toast_new (_("Copied")));
}

static void
on_report_button_clicked (GtkButton               *button G_GNUC_UNUSED,
                          ExmExtensionErrorDialog *self)
{
    GtkWidget *toplevel;
    GtkUriLauncher *uri;

    if (!self->homepage)
        return;

    toplevel = GTK_WIDGET (gtk_widget_get_root (GTK_WIDGET (self)));

    uri = gtk_uri_launcher_new (self->homepage);
    gtk_uri_launcher_launch (uri, GTK_WINDOW (toplevel), NULL, NULL, NULL);
}

static void
exm_extension_error_dialog_finalize (GObject *object)
{
    ExmExtensionErrorDialog *self = EXM_EXTENSION_ERROR_DIALOG (object);

    g_clear_pointer (&self->error_string, g_free);
    g_clear_pointer (&self->homepage, g_free);

    G_OBJECT_CLASS (exm_extension_error_dialog_parent_class)->finalize (object);
}

static void
exm_extension_error_dialog_class_init (ExmExtensionErrorDialogClass *klass)
{
    GObjectClass *object_class = G_OBJECT_CLASS (klass);

    object_class->finalize = exm_extension_error_dialog_finalize;

    GtkWidgetClass *widget_class = GTK_WIDGET_CLASS (klass);

    gtk_widget_class_set_template_from_resource (widget_class, g_strdup_printf ("%s/exm-extension-error-dialog.ui", RESOURCE_PATH));

    gtk_widget_class_bind_template_child (widget_class, ExmExtensionErrorDialog, toast_overlay);
    gtk_widget_class_bind_template_child (widget_class, ExmExtensionErrorDialog, title_label);
    gtk_widget_class_bind_template_child (widget_class, ExmExtensionErrorDialog, trace_group);
    gtk_widget_class_bind_template_child (widget_class, ExmExtensionErrorDialog, text_view);
    gtk_widget_class_bind_template_child (widget_class, ExmExtensionErrorDialog, report_btn);

    gtk_widget_class_bind_template_callback (widget_class, on_copy_button_clicked);
    gtk_widget_class_bind_template_callback (widget_class, on_report_button_clicked);
}

static void
exm_extension_error_dialog_init (ExmExtensionErrorDialog *self)
{
    gtk_widget_init_template (GTK_WIDGET (self));
}
