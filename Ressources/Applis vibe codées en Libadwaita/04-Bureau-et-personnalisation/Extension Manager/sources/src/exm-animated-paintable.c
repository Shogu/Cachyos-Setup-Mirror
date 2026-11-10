/*
 * exm-animated-paintable.c
 *
 * Copyright 2022-2026 Matthew Jakeman <mjakeman26@outlook.co.nz>
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

#include "exm-animated-paintable.h"

#include <glycin-gtk4.h>

struct _ExmAnimatedPaintable
{
    GObject parent_instance;

    GlyImage *image;
    GdkTexture *current_frame;
    GCancellable *cancellable;
    guint timeout_id;
};

static void exm_animated_paintable_paintable_init (GdkPaintableInterface *iface);

G_DEFINE_FINAL_TYPE_WITH_CODE (ExmAnimatedPaintable, exm_animated_paintable, G_TYPE_OBJECT,
                               G_IMPLEMENT_INTERFACE (GDK_TYPE_PAINTABLE, exm_animated_paintable_paintable_init))

static gboolean on_timeout (gpointer user_data);

static void
schedule_next_frame (ExmAnimatedPaintable *self,
                     gint64                 delay_us)
{
    g_clear_handle_id (&self->timeout_id, g_source_remove);

    // A non-positive delay means the animation has no more frames to show
    if (delay_us <= 0)
        return;

    self->timeout_id = g_timeout_add (delay_us / 1000, on_timeout, self);
}

static void
on_next_frame (GObject      *source,
               GAsyncResult *res,
               gpointer      user_data)
{
    ExmAnimatedPaintable *self = EXM_ANIMATED_PAINTABLE (user_data);
    GError *error = NULL;
    GlyFrame *frame = gly_image_next_frame_finish (GLY_IMAGE (source), res, &error);

    if (error)
    {
        if (!g_error_matches (error, G_IO_ERROR, G_IO_ERROR_CANCELLED))
            g_warning ("Could not load next GIF frame: %s\n", error->message);

        g_error_free (error);
        g_object_unref (self);
        return;
    }

    g_clear_object (&self->current_frame);
    self->current_frame = gly_gtk_frame_get_texture (frame);

    gint64 delay_us = gly_frame_get_delay (frame);
    g_object_unref (frame);

    gdk_paintable_invalidate_contents (GDK_PAINTABLE (self));
    schedule_next_frame (self, delay_us);

    g_object_unref (self);
}

static gboolean
on_timeout (gpointer user_data)
{
    ExmAnimatedPaintable *self = EXM_ANIMATED_PAINTABLE (user_data);

    self->timeout_id = 0;

    // Keep self alive for the duration of the request; released in on_next_frame
    gly_image_next_frame_async (self->image, self->cancellable, on_next_frame, g_object_ref (self));

    return G_SOURCE_REMOVE;
}

ExmAnimatedPaintable *
exm_animated_paintable_new (GlyImage   *image,
                            GdkTexture *first_frame,
                            gint64      delay_us)
{
    ExmAnimatedPaintable *self;

    g_return_val_if_fail (GLY_IS_IMAGE (image), NULL);
    g_return_val_if_fail (GDK_IS_TEXTURE (first_frame), NULL);

    self = g_object_new (EXM_TYPE_ANIMATED_PAINTABLE, NULL);

    self->image = image;
    self->current_frame = first_frame;
    self->cancellable = g_cancellable_new ();

    schedule_next_frame (self, delay_us);

    return self;
}

static void
exm_animated_paintable_snapshot (GdkPaintable *paintable,
                                 GdkSnapshot  *snapshot,
                                 double        width,
                                 double        height)
{
    ExmAnimatedPaintable *self = EXM_ANIMATED_PAINTABLE (paintable);

    if (self->current_frame)
        gdk_paintable_snapshot (GDK_PAINTABLE (self->current_frame), snapshot, width, height);
}

static int
exm_animated_paintable_get_intrinsic_width (GdkPaintable *paintable)
{
    ExmAnimatedPaintable *self = EXM_ANIMATED_PAINTABLE (paintable);

    return gdk_texture_get_width (self->current_frame);
}

static int
exm_animated_paintable_get_intrinsic_height (GdkPaintable *paintable)
{
    ExmAnimatedPaintable *self = EXM_ANIMATED_PAINTABLE (paintable);

    return gdk_texture_get_height (self->current_frame);
}

static GdkPaintableFlags
exm_animated_paintable_get_flags (GdkPaintable *paintable G_GNUC_UNUSED)
{
    return GDK_PAINTABLE_STATIC_SIZE;
}

static void
exm_animated_paintable_paintable_init (GdkPaintableInterface *iface)
{
    iface->snapshot = exm_animated_paintable_snapshot;
    iface->get_intrinsic_width = exm_animated_paintable_get_intrinsic_width;
    iface->get_intrinsic_height = exm_animated_paintable_get_intrinsic_height;
    iface->get_flags = exm_animated_paintable_get_flags;
}

static void
exm_animated_paintable_dispose (GObject *object)
{
    ExmAnimatedPaintable *self = (ExmAnimatedPaintable *)object;

    if (self->cancellable)
        g_cancellable_cancel (self->cancellable);

    g_clear_handle_id (&self->timeout_id, g_source_remove);
    g_clear_object (&self->current_frame);
    g_clear_object (&self->image);
    g_clear_object (&self->cancellable);

    G_OBJECT_CLASS (exm_animated_paintable_parent_class)->dispose (object);
}

static void
exm_animated_paintable_class_init (ExmAnimatedPaintableClass *klass)
{
    GObjectClass *object_class = G_OBJECT_CLASS (klass);

    object_class->dispose = exm_animated_paintable_dispose;
}

static void
exm_animated_paintable_init (ExmAnimatedPaintable *self G_GNUC_UNUSED)
{
}
