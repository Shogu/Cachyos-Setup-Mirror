/*
 * exm-extension-toggle.c
 *
 * Copyright 2022 Matthew Jakeman <mjakeman26@outlook.co.nz>
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

#include "exm-extension-toggle.h"

#include "exm-enums.h"
#include "exm-types.h"

static gboolean
transform_to_state (GBinding     *binding G_GNUC_UNUSED,
                    const GValue *from_value,
                    GValue       *to_value,
                    gpointer      user_data G_GNUC_UNUSED)
{
    g_value_set_boolean (to_value,
                         g_value_get_enum (from_value) == EXM_EXTENSION_STATE_ACTIVE);
    return TRUE;
}

void
exm_extension_bind_toggle (ExmExtension *extension,
                            GtkSwitch    *toggle)
{
    gboolean enabled;
    ExmExtensionState state;

    g_return_if_fail (EXM_IS_EXTENSION (extension));
    g_return_if_fail (GTK_IS_SWITCH (toggle));

    g_object_get (extension,
                  "enabled", &enabled,
                  "state",   &state,
                  NULL);

    g_object_bind_property (extension, "enabled",
                            toggle, "active",
                            G_BINDING_SYNC_CREATE);

    g_object_bind_property_full (extension, "state",
                                 toggle, "state",
                                 G_BINDING_SYNC_CREATE,
                                 transform_to_state,
                                 NULL, NULL, NULL);

    // Keep compatibility with GNOME Shell versions prior to 46
    if (gtk_switch_get_state (toggle) != enabled &&
        (state == EXM_EXTENSION_STATE_ACTIVE || state == EXM_EXTENSION_STATE_ACTIVATING))
        g_object_set (extension, "enabled", !enabled, NULL);
}

gboolean
exm_extension_apply_toggle (ExmManager   *manager,
                             ExmExtension *extension,
                             GtkSwitch    *toggle,
                             gboolean      state)
{
    gboolean enabled;

    g_return_val_if_fail (EXM_IS_MANAGER (manager), FALSE);
    g_return_val_if_fail (EXM_IS_EXTENSION (extension), FALSE);
    g_return_val_if_fail (GTK_IS_SWITCH (toggle), FALSE);

    g_object_get (extension, "enabled", &enabled, NULL);

    if (state == enabled)
        return TRUE;

    // Keep compatibility with GNOME Shell versions prior to 46
    if (gtk_switch_get_state (toggle) != enabled)
        g_object_set (extension, "enabled", !enabled, NULL);

    if (state)
        exm_manager_enable_extension (manager, extension);
    else
        exm_manager_disable_extension (manager, extension);

    return TRUE;
}
