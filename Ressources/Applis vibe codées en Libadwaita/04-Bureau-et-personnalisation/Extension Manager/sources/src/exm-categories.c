/*
 * exm-categories.c
 *
 * Local classification of installed extensions (Ogu fork).
 *
 * An extension is classified, in this order:
 *  1. by the category the user chose (stored in GSettings, indexed by UUID);
 *  2. by a short list of known UUIDs;
 *  3. by keywords found in its name or description;
 *  4. otherwise it goes to "Other".
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "exm-categories.h"

#include <glib/gi18n.h>
#include <string.h>

typedef struct
{
    const char *id;
    const char *title;
} Category;

/* The ids are stored in the user's settings: never rename them. */
static const Category categories[] = {
    { "appearance",   N_("Interface & Appearance") },
    { "windows",      N_("Desktop & Windows") },
    { "panel",        N_("Top Bar & Quick Settings") },
    { "productivity", N_("Productivity") },
    { "power",        N_("System & Power") },
    { "media",        N_("Multimedia") },
    { "other",        N_("Other") },
};

typedef struct
{
    const char *uuid;
    const char *id;
} KnownUuid;

static const KnownUuid known_uuids[] = {
    { "just-perfection-desktop@just-perfection",  "appearance" },
    { "auto-activities@CleoMenezesJr.github.io",  "windows" },
    { "hotedge@jonathan.jdoda.ca",                "windows" },
    { "power-switching-manager@joseruibarros.com", "power" },
    { "auto-power-profile@dmy3k.github.io",       "power" },
    { "caffeine@patapon.info",                    "power" },
};

typedef struct
{
    const char *id;
    const char *keywords; /* '|'-separated, already lowercase */
} KeywordRule;

/* Checked in this order: the first match wins. */
static const KeywordRule keyword_rules[] = {
    { "power",
      "battery|batterie|power profile|power-profile|power switching|power-switching|"
      "caffeine|énergie|energy|cpu" },
    { "media",
      "musicaa|musicäa|now playing|now-playing|mpris|media player|music|audio|volume" },
    { "productivity",
      "copyous|clipboard|presse-papier|pomodoro|todo|to-do|notes|productivity" },
    { "appearance",
      "just perfection|just-perfection|blur|theme|thème|wallpaper|fond d’écran|"
      "fond d'écran|rounded window" },
    { "windows",
      "auto activities|auto-activities|autoactivities|hot edge|hotedge|drag n tile|"
      "dragntile|always on top|always-on-top|quick close|quick-close|tiling|"
      "workspace|overview|fenêtre|window manag" },
    { "panel",
      "quick settings|quick-settings|focus|boutons|panel|top bar|top-bar|indicator" },
};

guint
exm_categories_get_n (void)
{
    return G_N_ELEMENTS (categories);
}

const char *
exm_categories_get_id (guint index)
{
    g_return_val_if_fail (index < G_N_ELEMENTS (categories), NULL);
    return categories[index].id;
}

const char *
exm_categories_get_title (guint index)
{
    g_return_val_if_fail (index < G_N_ELEMENTS (categories), NULL);
    return _(categories[index].title);
}

/* Accept the id under the spelling an older build may have stored. */
static const char *
normalize_id (const char *id)
{
    if (id == NULL)
        return NULL;

    if (g_strcmp0 (id, "multimedia") == 0)
        return "media";

    for (guint i = 0; i < G_N_ELEMENTS (categories); i++)
    {
        if (g_strcmp0 (categories[i].id, id) == 0)
            return categories[i].id;
    }

    return NULL;
}

gboolean
exm_categories_is_valid_id (const char *id)
{
    return normalize_id (id) != NULL;
}

static gboolean
text_matches (const char *haystack,
              const char *keywords)
{
    g_auto (GStrv) words = g_strsplit (keywords, "|", -1);

    for (guint i = 0; words[i] != NULL; i++)
    {
        g_autofree char *needle = g_utf8_casefold (words[i], -1);

        if (*needle != '\0' && strstr (haystack, needle) != NULL)
            return TRUE;
    }

    return FALSE;
}

const char *
exm_categories_get_automatic (ExmExtension *extension)
{
    g_autofree char *uuid = NULL;
    g_autofree char *name = NULL;
    g_autofree char *description = NULL;
    g_autofree char *joined = NULL;
    g_autofree char *haystack = NULL;

    g_return_val_if_fail (EXM_IS_EXTENSION (extension), "other");

    g_object_get (extension,
                  "uuid", &uuid,
                  "name", &name,
                  "description", &description,
                  NULL);

    for (guint i = 0; uuid != NULL && i < G_N_ELEMENTS (known_uuids); i++)
    {
        if (g_strcmp0 (known_uuids[i].uuid, uuid) == 0)
            return known_uuids[i].id;
    }

    joined = g_strjoin (" ",
                        name ? name : "",
                        description ? description : "",
                        uuid ? uuid : "",
                        NULL);
    haystack = g_utf8_casefold (joined, -1);

    for (guint i = 0; i < G_N_ELEMENTS (keyword_rules); i++)
    {
        if (text_matches (haystack, keyword_rules[i].keywords))
            return keyword_rules[i].id;
    }

    return "other";
}

const char *
exm_categories_resolve (ExmExtension *extension,
                        GHashTable   *overrides)
{
    g_return_val_if_fail (EXM_IS_EXTENSION (extension), "other");

    if (overrides != NULL)
    {
        g_autofree char *uuid = NULL;
        const char *chosen;

        g_object_get (extension, "uuid", &uuid, NULL);
        chosen = normalize_id (uuid ? g_hash_table_lookup (overrides, uuid) : NULL);
        if (chosen != NULL)
            return chosen;
    }

    return exm_categories_get_automatic (extension);
}

const char *
exm_categories_get_override (GSettings  *settings,
                             const char *uuid)
{
    g_autoptr (GVariant) value = NULL;
    const char *id = NULL;
    const char *result;

    g_return_val_if_fail (G_IS_SETTINGS (settings), EXM_CATEGORY_AUTO);

    if (uuid == NULL)
        return EXM_CATEGORY_AUTO;

    value = g_settings_get_value (settings, EXM_CATEGORIES_KEY);
    if (!g_variant_lookup (value, uuid, "&s", &id))
        return EXM_CATEGORY_AUTO;

    result = normalize_id (id);
    return result != NULL ? result : EXM_CATEGORY_AUTO;
}

GHashTable *
exm_categories_load_overrides (GSettings *settings)
{
    GHashTable *table = g_hash_table_new_full (g_str_hash, g_str_equal, g_free, g_free);
    g_autoptr (GVariant) value = NULL;
    GVariantIter iter;
    const char *uuid;
    const char *id;

    g_return_val_if_fail (G_IS_SETTINGS (settings), table);

    value = g_settings_get_value (settings, EXM_CATEGORIES_KEY);
    g_variant_iter_init (&iter, value);
    while (g_variant_iter_next (&iter, "{&s&s}", &uuid, &id))
        g_hash_table_insert (table, g_strdup (uuid), g_strdup (id));

    return table;
}

void
exm_categories_set_override (GSettings  *settings,
                             const char *uuid,
                             const char *id)
{
    g_autoptr (GVariant) old_value = NULL;
    GVariantBuilder builder;
    GVariantIter iter;
    const char *key;
    const char *value;

    g_return_if_fail (G_IS_SETTINGS (settings));
    g_return_if_fail (uuid != NULL);

    old_value = g_settings_get_value (settings, EXM_CATEGORIES_KEY);
    g_variant_builder_init (&builder, G_VARIANT_TYPE ("a{ss}"));

    g_variant_iter_init (&iter, old_value);
    while (g_variant_iter_next (&iter, "{&s&s}", &key, &value))
    {
        if (g_strcmp0 (key, uuid) != 0)
            g_variant_builder_add (&builder, "{ss}", key, value);
    }

    id = normalize_id (id);
    if (id != NULL)
        g_variant_builder_add (&builder, "{ss}", uuid, id);

    g_settings_set_value (settings, EXM_CATEGORIES_KEY, g_variant_builder_end (&builder));
}
