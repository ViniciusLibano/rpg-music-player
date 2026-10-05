import gi
gi.require_version('GLib', '2.0')
from gi.repository import GLib

from logger import LOG


class Crossfader:
    def __init__(self):
        self._source_id = None
        self._active = False

    @property
    def active(self):
        return self._active

    def execute(self, source, dest, target_vol_dest, duration_s, on_complete=None):
        if self._active:
            self.cancel()

        self._active = True
        vol_source = source.volume
        target_vol_dest = max(0, min(100, target_vol_dest))

        LOG.info('crossfade start: vol %d -> 0 | 0 -> %d over %.1fs',
                 vol_source, target_vol_dest, duration_s)

        was_looping = source.loop_file == 'inf'
        if was_looping:
            source.loop_file = 'no'

        duration_ms = duration_s * 1000
        step_ms = 50
        start_time = GLib.get_monotonic_time() / 1000

        def on_tick():
            elapsed = (GLib.get_monotonic_time() / 1000) - start_time
            progress = min(elapsed / duration_ms, 1.0)
            new_vol_source = vol_source * (1 - progress)
            new_vol_dest = target_vol_dest * progress
            source.volume = int(new_vol_source)
            dest.volume = int(new_vol_dest)

            if progress >= 1.0:
                source.volume = 0
                source.do_pause()
                self._source_id = None
                self._active = False
                LOG.info('crossfade complete')
                if on_complete:
                    on_complete()
                return False
            return True

        self._source_id = GLib.timeout_add(step_ms, on_tick)

    def cancel(self):
        if self._source_id is not None:
            LOG.info('crossfade cancelled')
            GLib.source_remove(self._source_id)
            self._source_id = None
        self._active = False
