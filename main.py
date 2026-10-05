import argparse
import threading

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

from player import TrackPlayer
from crossfader import Crossfader
from presets import PresetManager
from library import Library
import logger as log_mod

ACTIVE_TRACK_CSS = b'.active-track { border-color: #4a9; border-width: 2px; }'

TRACK_LABELS = ['Primary', 'Secondary', 'Ambience 1', 'Ambience 2']


class App(Gtk.Window):
    def __init__(self, debug=False):
        Gtk.Window.__init__(self, title='Sound Helper')
        self.set_default_size(820, 720)
        self.connect('destroy', self._on_destroy)
        self._apply_css()

        self._debug = debug
        self._players = [TrackPlayer(index=i, debug=debug) for i in range(4)]
        self._widgets = []
        self._source_mode = [0] * 4
        self._active_index = -1
        self._crossfader = Crossfader()
        self._presets = PresetManager()
        self._library = Library()
        self._lib_files_store = Gtk.ListStore(str)
        self._build_ui()
        self._refresh_presets()
        self._refresh_library_list()
        log_mod.LOG.info('App initialized (%d tracks)', 4)

    def _apply_css(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(ACTIVE_TRACK_CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _build_ui(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox.set_border_width(10)
        self.add(vbox)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        vbox.pack_start(scrolled, True, True, 0)

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        scrolled.add(inner)

        for i in range(4):
            inner.pack_start(self._make_track_frame(i), False, True, 0)

        inner.pack_start(self._make_fade_row(), False, True, 0)
        inner.pack_start(self._make_presets_row(), False, True, 0)
        inner.pack_start(self._make_library_section(), True, True, 0)

        vbox.show_all()

    def _make_track_frame(self, index):
        frame = Gtk.Frame(label=TRACK_LABELS[index])
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        inner.set_border_width(6)

        source_row = Gtk.Box(spacing=4)
        lib_btn = Gtk.ToggleButton.new_with_label('Lib')
        lib_btn.set_tooltip_text('Use local library file')
        lib_btn.connect('toggled', self._on_source_toggle, index)
        source_row.pack_start(lib_btn, False, False, 0)

        url_entry = Gtk.Entry()
        url_entry.set_placeholder_text('YouTube URL or file path...')
        source_row.pack_start(url_entry, True, True, 0)

        lib_combo = Gtk.ComboBox.new_with_model_and_entry(self._lib_files_store)
        lib_combo.set_entry_text_column(0)
        lib_combo.get_child().set_placeholder_text('Select a file...')
        source_row.pack_start(lib_combo, True, True, 0)

        inner.pack_start(source_row, False, True, 0)

        btn_row = Gtk.Box(spacing=4)
        play = Gtk.Button.new_with_label('Play')
        play.connect('clicked', self._on_play, index)
        btn_row.pack_start(play, False, False, 0)
        pause = Gtk.Button.new_with_label('Pause')
        pause.connect('clicked', self._on_pause, index)
        btn_row.pack_start(pause, False, False, 0)
        stop = Gtk.Button.new_with_label('Stop')
        stop.connect('clicked', self._on_stop, index)
        btn_row.pack_start(stop, False, False, 0)
        if index == 1:
            play.set_no_show_all(True); play.hide()
            pause.set_no_show_all(True); pause.hide()
            stop.set_no_show_all(True); stop.hide()
        loop = Gtk.ToggleButton.new_with_label('Loop')
        if index >= 2:
            loop.set_active(True)
            self._players[index].set_loop(True)
        loop.connect('toggled', self._on_loop, index)
        btn_row.pack_start(loop, False, False, 0)
        inner.pack_start(btn_row, False, True, 0)

        vol_row = Gtk.Box(spacing=4)
        vol_row.pack_start(Gtk.Label(label='Vol:'), False, False, 0)
        vol_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        vol_scale.set_value(50)
        vol_scale.connect('value-changed', self._on_volume, index)
        vol_row.pack_start(vol_scale, True, True, 0)
        inner.pack_start(vol_row, False, True, 0)

        swap_btn = Gtk.Button.new_with_label('Swap to Primary')
        swap_btn.get_style_context().add_class('suggested-action')
        swap_btn.connect('clicked', self._on_swap, index)
        if index != 1:
            swap_btn.set_no_show_all(True)
            swap_btn.hide()
        inner.pack_start(swap_btn, False, True, 0)

        frame.add(inner)

        lib_combo.hide()

        self._widgets.append({
            'frame': frame,
            'url_entry': url_entry,
            'lib_combo': lib_combo,
            'lib_btn': lib_btn,
            'vol_scale': vol_scale,
            'loop_btn': loop,
            'swap_btn': swap_btn,
        })
        return frame

    def _make_fade_row(self):
        row = Gtk.Box(spacing=6)
        row.pack_start(Gtk.Label(label='Crossfade duration:'), False, False, 0)
        self._fade_spin = Gtk.SpinButton.new_with_range(0.5, 30.0, 0.5)
        self._fade_spin.set_value(3.0)
        self._fade_spin.set_digits(1)
        row.pack_start(self._fade_spin, False, False, 0)
        row.pack_start(Gtk.Label(label='s'), False, False, 0)
        return row

    def _make_presets_row(self):
        row = Gtk.Box(spacing=6)
        row.pack_start(Gtk.Label(label='Presets:'), False, False, 0)
        self._presets_combo = Gtk.ComboBoxText()
        row.pack_start(self._presets_combo, True, True, 0)
        for label, handler in [
            ('Load', self._on_load_preset),
            ('Save', self._on_save_preset),
            ('Delete', self._on_delete_preset),
        ]:
            btn = Gtk.Button.new_with_label(label)
            btn.connect('clicked', handler)
            row.pack_start(btn, False, False, 0)
        return row

    def _make_library_section(self):
        expander = Gtk.Expander(label='Library')
        expander.set_expanded(True)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        vbox.set_border_width(6)

        dl_row = Gtk.Box(spacing=4)
        self._lib_url_entry = Gtk.Entry()
        self._lib_url_entry.set_placeholder_text('YouTube URL to download...')
        dl_row.pack_start(self._lib_url_entry, True, True, 0)

        self._lib_dl_btn = Gtk.Button.new_with_label('Download')
        self._lib_dl_btn.connect('clicked', self._on_library_download)
        dl_row.pack_start(self._lib_dl_btn, False, False, 0)

        self._lib_progress = Gtk.ProgressBar()
        self._lib_progress.set_show_text(True)
        self._lib_progress.set_text('')

        vbox.pack_start(dl_row, False, True, 0)
        vbox.pack_start(self._lib_progress, False, True, 0)

        self._lib_list = Gtk.ListBox()
        self._lib_list.set_selection_mode(Gtk.SelectionMode.NONE)
        vbox.pack_start(self._lib_list, False, True, 0)

        expander.add(vbox)
        return expander

    def _refresh_library_list(self):
        for child in self._lib_list.get_children():
            self._lib_list.remove(child)

        for fname in self._library.list_files():
            row = Gtk.Box(spacing=4)
            row.pack_start(Gtk.Label(label=fname, xalign=0), True, True, 0)

            del_btn = Gtk.Button.new_with_label('Delete')
            del_btn.connect('clicked', self._on_lib_delete, fname)
            row.pack_start(del_btn, False, False, 0)

            row.show_all()
            self._lib_list.add(row)

        self._lib_files_store.clear()
        for fname in self._library.list_files():
            self._lib_files_store.append([fname])

    def _on_source_toggle(self, btn, index):
        w = self._widgets[index]
        self._source_mode[index] = 1 if btn.get_active() else 0
        if btn.get_active():
            w['url_entry'].hide()
            w['lib_combo'].show()
        else:
            w['lib_combo'].hide()
            w['url_entry'].show()

    def _get_track_source(self, index):
        if self._source_mode[index]:
            e = self._widgets[index]['lib_combo'].get_child()
            name = e.get_text().strip()
            if name:
                return self._library.path(name)
            return ''
        return self._widgets[index]['url_entry'].get_text().strip()

    def _on_play(self, btn, index):
        src = self._get_track_source(index)
        log_mod.LOG.info('[ui] play track %d src=%s', index, src)
        if not src:
            self._error('No source', 'Enter a URL or select a library file.')
            return
        try:
            player = self._players[index]
            player.load(src)
            self._active_index = index
            self._update_highlights()
        except Exception as e:
            log_mod.LOG.error('[ui] play error: %s', e)
            self._error('Play Error', str(e))

    def _on_pause(self, btn, index):
        log_mod.LOG.info('[ui] pause track %d', index)
        self._players[index].do_pause()

    def _on_stop(self, btn, index):
        log_mod.LOG.info('[ui] stop track %d', index)
        self._players[index].stop()
        if self._active_index == index:
            self._active_index = -1
            self._update_highlights()

    def _on_loop(self, btn, index):
        self._players[index].set_loop(btn.get_active())

    def _on_volume(self, scale, index):
        if self._crossfader.active:
            return
        self._players[index].set_volume(scale.get_value())

    def _on_swap(self, btn, index):
        if self._crossfader.active:
            return

        src = self._get_track_source(1)
        primary_src = self._get_track_source(0)
        duration = self._fade_spin.get_value()
        duration_ms = int(duration * 1000)
        target_vol = self._widgets[1]['vol_scale'].get_value()

        def swapped():
            self._swap_both()
            self._active_index = 0
            self._update_highlights()

        if primary_src and src:
            log_mod.LOG.info('[ui] crossfade: primary -> secondary')
            dest = self._players[1]
            dest.volume = 0
            try:
                dest.load(src)
                dest.play()
            except Exception as e:
                log_mod.LOG.error('[ui] swap load error: %s', e)
                self._error('Load Error', str(e))
                return
            self._crossfader.execute(self._players[0], dest, target_vol, duration, swapped)

        elif primary_src and not src:
            log_mod.LOG.info('[ui] fade to silence')
            def fade_done():
                self._players[0].stop()
                swapped()
            self._players[0].fade_volume(0, duration_ms, fade_done)

        elif not primary_src and src:
            log_mod.LOG.info('[ui] fade from silence')
            dest = self._players[1]
            dest.volume = 0
            try:
                dest.load(src)
                dest.play()
            except Exception as e:
                log_mod.LOG.error('[ui] swap load error: %s', e)
                self._error('Load Error', str(e))
                return
            dest.fade_volume(target_vol, duration_ms, swapped)

        else:
            log_mod.LOG.info('[ui] swap widgets (both empty)')
            swapped()

    def _swap_both(self):
        w0 = self._widgets[0]
        w1 = self._widgets[1]

        self._players[0], self._players[1] = self._players[1], self._players[0]
        self._players[0]._index = 0
        self._players[1]._index = 1

        self._swap_widget_value(w0['url_entry'], w1['url_entry'])
        self._swap_widget_value(w0['lib_combo'].get_child(), w1['lib_combo'].get_child())

        vol0 = w0['vol_scale'].get_value()
        vol1 = w1['vol_scale'].get_value()
        w0['vol_scale'].set_value(vol1)
        w1['vol_scale'].set_value(vol0)

        loop0 = w0['loop_btn'].get_active()
        loop1 = w1['loop_btn'].get_active()
        w0['loop_btn'].set_active(loop1)
        w1['loop_btn'].set_active(loop0)

        src_mode0 = self._source_mode[0]
        self._source_mode[0] = self._source_mode[1]
        self._source_mode[1] = src_mode0

        w0['lib_btn'].set_active(bool(self._source_mode[0]))
        w1['lib_btn'].set_active(bool(self._source_mode[1]))

        log_mod.LOG.info('[ui] widgets swapped')

    def _swap_widget_value(self, a, b):
        av = a.get_text()
        bv = b.get_text()
        a.set_text(bv)
        b.set_text(av)

    def _on_library_download(self, btn):
        url = self._lib_url_entry.get_text().strip()
        if not url:
            self._error('No URL', 'Enter a YouTube URL to download.')
            return

        self._lib_dl_btn.set_sensitive(False)
        self._lib_url_entry.set_sensitive(False)
        self._lib_progress.set_fraction(0)
        self._lib_progress.set_text('Downloading...')

        def progress_cb(fraction):
            GLib.idle_add(self._lib_progress.set_fraction, fraction)
            GLib.idle_add(self._lib_progress.set_text, f'{int(fraction * 100)}%')

        def download_thread():
            try:
                fname = self._library.download(url, progress_cb)
                GLib.idle_add(self._on_download_done, fname, None)
            except Exception as e:
                log_mod.LOG.error('[library] download error: %s', e)
                GLib.idle_add(self._on_download_done, None, str(e))

        threading.Thread(target=download_thread, daemon=True).start()

    def _on_download_done(self, fname, error):
        self._lib_dl_btn.set_sensitive(True)
        self._lib_url_entry.set_sensitive(True)
        if error:
            self._lib_progress.set_text('Error')
            self._error('Download Error', error)
        else:
            self._lib_progress.set_text('Done')
            self._lib_url_entry.set_text('')
            self._refresh_library_list()

    def _on_lib_delete(self, btn, fname):
        dialog = Gtk.MessageDialog(
            parent=self,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=f'Delete "{fname}"?',
        )
        if dialog.run() == Gtk.ResponseType.OK:
            self._library.delete(fname)
            self._refresh_library_list()
        dialog.destroy()

    def _on_load_preset(self, btn):
        name = self._presets_combo.get_active_text()
        if not name:
            return
        log_mod.LOG.info('[ui] loading preset: %s', name)
        data = self._presets.load(name)
        for i, t in enumerate(data.get('tracks', [])[:4]):
            src_mode = t.get('source', 'url')
            self._source_mode[i] = 1 if src_mode == 'library' else 0
            w = self._widgets[i]
            if src_mode == 'library':
                w['url_entry'].hide()
                w['lib_combo'].show()
                w['lib_btn'].set_active(True)
                w['lib_combo'].get_child().set_text(t.get('value', ''))
            else:
                w['lib_combo'].hide()
                w['url_entry'].show()
                w['lib_btn'].set_active(False)
                w['url_entry'].set_text(t.get('value', ''))
            vol = t.get('volume', 50)
            w['vol_scale'].set_value(vol)
            self._players[i].set_volume(vol)
            looping = t.get('loop', False)
            w['loop_btn'].set_active(looping)
            self._players[i].set_loop(looping)

    def _on_save_preset(self, btn):
        dialog = Gtk.Dialog(title='Save Preset', parent=self)
        dialog.add_button('Cancel', Gtk.ResponseType.CANCEL)
        dialog.add_button('Save', Gtk.ResponseType.OK)

        box = dialog.get_content_area()
        box.pack_start(Gtk.Label(label='Preset name:'), False, False, 6)
        name_entry = Gtk.Entry()
        box.pack_start(name_entry, False, False, 6)
        dialog.show_all()

        if dialog.run() != Gtk.ResponseType.OK:
            dialog.destroy()
            return

        name = name_entry.get_text().strip()
        dialog.destroy()
        if not name:
            return

        log_mod.LOG.info('[ui] saving preset: %s', name)
        data = {
            'tracks': [
                {
                    'source': 'library' if self._source_mode[i] else 'url',
                    'value': self._get_track_source(i),
                    'volume': int(self._widgets[i]['vol_scale'].get_value()),
                    'loop': self._widgets[i]['loop_btn'].get_active(),
                }
                for i in range(4)
            ],
        }
        self._presets.save(name, data)
        self._refresh_presets()

    def _on_delete_preset(self, btn):
        name = self._presets_combo.get_active_text()
        if not name:
            return

        dialog = Gtk.MessageDialog(
            parent=self,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=f'Delete preset "{name}"?',
        )
        if dialog.run() == Gtk.ResponseType.OK:
            log_mod.LOG.info('[ui] deleting preset: %s', name)
            self._presets.delete(name)
            self._refresh_presets()
        dialog.destroy()

    def _on_destroy(self, widget):
        log_mod.LOG.info('[ui] shutting down')
        for player in self._players:
            try:
                player.terminate()
            except Exception:
                pass
        Gtk.main_quit()

    def _update_highlights(self):
        for i, w in enumerate(self._widgets):
            ctx = w['frame'].get_style_context()
            if i == self._active_index:
                ctx.add_class('active-track')
            else:
                ctx.remove_class('active-track')

    def _refresh_presets(self):
        self._presets_combo.remove_all()
        for name in self._presets.list_presets():
            self._presets_combo.append_text(name)

    def _error(self, title, message):
        d = Gtk.MessageDialog(
            parent=self,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=message,
        )
        d.set_title(title)
        d.run()
        d.destroy()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()

    log_mod.setup(debug=args.debug)

    app = App(debug=args.debug)
    app.show_all()
    Gtk.main()
