import gi
gi.require_version('GLib', '2.0')
from gi.repository import GLib
import mpv

from logger import LOG


class TrackPlayer(mpv.MPV):
    def __init__(self, index=0, debug=False):
        self._index = index
        super().__init__(
            log_handler=self._mpv_log if debug else None,
            loglevel='v' if debug else None,
        )
        self.video = False
        self.ytdl = True
        self.volume = 50
        self.loop_file = 'no'
        self._fade_source_id = None
        self.register_event_callback(self._on_mpv_event)
        LOG.debug('[track %d] created (mpv log handler: %s)', index, debug)

    def _mpv_log(self, level, prefix, text):
        LOG.debug('[track %d] mpv/%s: %s', self._index, prefix, text)

    def _on_mpv_event(self, event):
        eid = event.event_id.value

        if eid == mpv.MpvEventID.FILE_LOADED:
            LOG.info('[track %d] file loaded: %s', self._index, self.path)

        elif eid == mpv.MpvEventID.END_FILE:
            reason = event.data.reason if event.data else '?'
            LOG.info('[track %d] end-file (reason=%s)', self._index, reason)

    def load(self, url):
        if not url.strip():
            return
        LOG.info('[track %d] loading: %s', self._index, url)
        self.command('playlist-clear')
        self.command('loadfile', url, 'replace')

    def play(self):
        LOG.info('[track %d] play', self._index)
        self.command('set', 'pause', 'no')

    def do_pause(self):
        LOG.info('[track %d] pause', self._index)
        self.command('set', 'pause', 'yes')

    def stop(self):
        LOG.info('[track %d] stop', self._index)
        self.command('stop')

    def set_volume(self, vol):
        vol = max(0, min(100, int(vol)))
        self.volume = vol

    def set_loop(self, enabled):
        LOG.debug('[track %d] loop = %s', self._index, enabled)
        if enabled:
            self.loop_file = 'inf'
        else:
            self.loop_file = 'no'

    def fade_volume(self, target, duration_ms, callback=None):
        self.cancel_fade()
        start_vol = self.volume
        target = max(0, min(100, target))
        LOG.debug('[track %d] fade %d -> %d over %dms',
                  self._index, start_vol, target, duration_ms)

        if duration_ms <= 0:
            self.volume = target
            if callback:
                callback()
            return

        step_ms = 50
        start_time = GLib.get_monotonic_time() / 1000

        def on_tick():
            elapsed = (GLib.get_monotonic_time() / 1000) - start_time
            progress = min(elapsed / duration_ms, 1.0)
            new_vol = start_vol + (target - start_vol) * progress
            self.volume = int(new_vol)

            if progress >= 1.0:
                self._fade_source_id = None
                LOG.debug('[track %d] fade complete at vol=%d', self._index, target)
                if callback:
                    callback()
                return False
            return True

        self._fade_source_id = GLib.timeout_add(step_ms, on_tick)

    def cancel_fade(self):
        if self._fade_source_id is not None:
            LOG.debug('[track %d] fade cancelled', self._index)
            GLib.source_remove(self._fade_source_id)
            self._fade_source_id = None
