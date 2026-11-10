/*
 * exm-categories.h
 *
 * Local classification of installed extensions (Ogu fork).
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <gio/gio.h>

#include "local/exm-extension.h"

G_BEGIN_DECLS

#define EXM_CATEGORY_AUTO "auto"
#define EXM_CATEGORIES_KEY "extension-categories"

guint        exm_categories_get_n        (void);
const char  *exm_categories_get_id       (guint index);
const char  *exm_categories_get_title    (guint index);
gboolean     exm_categories_is_valid_id  (const char *id);

const char  *exm_categories_get_automatic (ExmExtension *extension);

/* overrides: GHashTable<uuid, id> read from GSettings, may be NULL */
const char  *exm_categories_resolve      (ExmExtension *extension,
                                          GHashTable   *overrides);

/* Returns the chosen id, or EXM_CATEGORY_AUTO when none is stored */
const char  *exm_categories_get_override   (GSettings  *settings,
                                            const char *uuid);
GHashTable  *exm_categories_load_overrides (GSettings *settings);
void         exm_categories_set_override   (GSettings  *settings,
                                            const char *uuid,
                                            const char *id);

G_END_DECLS
