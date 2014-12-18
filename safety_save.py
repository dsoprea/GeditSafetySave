import logging

from datetime import datetime
from os import environ, makedirs, unlink, listdir, rmdir
from os.path import expanduser, join, exists

from gi.repository import GObject, Gedit
from gi.repository.Gio import Settings

_log = logging.getLogger('SafetySave')

if environ.get('DEBUG', '').lower() == 'true':
    _log.setLevel(logging.DEBUG)

# For some reason our logging won't emit correctly unless an initial message is
# sent in.
logging.debug("")

_SETTINGS_KEY = "org.gnome.gedit.preferences.editor"
_MAX_STORED_AGE_S = 86400 * 7 * 4
_DATETIME_FORMAT = '%Y%m%d-%H%M%S'
_PREF_DIR_NAME = '.gedit-unsaved'

_gedit_settings = Settings(_SETTINGS_KEY)
_start_timestamp = datetime.now().strftime(_DATETIME_FORMAT)
_store_root = join(expanduser('~'), _PREF_DIR_NAME)
_store_path = join(_store_root, _start_timestamp)


class SafetySavePluginAppExtension(GObject.Object, Gedit.AppActivatable):
    __gtype_name__ = "SafetySavePluginAppExtension"
    app = GObject.property(type=Gedit.App)

    def __init__(self):
        GObject.Object.__init__(self)

    def __do_cleanup(self):
        """Determine if any old session backups need to be cleared."""

        _log.debug("Doing old-session cleanup.")

        try:
            timestamp_subdirs = listdir(_store_root)
        except OSError:
            _log.debug("The storage path doesn't exist: %s" % (_store_path))
            return

        _log.debug("(%d) session-backup directories found." %
                   (len(timestamp_subdirs)))
        for timestamp_subdir in sorted(timestamp_subdirs):
            dt = datetime.strptime(timestamp_subdir, _DATETIME_FORMAT)
            age = (datetime.now() - dt).total_seconds()
            if age < _MAX_STORED_AGE_S:
                _log.debug("[%s] is too recent: (%.2f) days" %
                           (timestamp_subdir, (float(age) / 86400.0)))
                continue

            _log.info("Cleaning-up temporary storage for old session: %s" %
                      (timestamp_subdir))

            path = join(_store_root, timestamp_subdir)
            for filename in listdir(path):
                _log.info("Removing: %s" % (filename))
                file_path = join(path, filename)
                unlink(file_path)

            _log.info("Removing directory for session: %s" % (path))
            rmdir(path)

            print("")

    def do_activate(self):
        self.__do_cleanup()

    def do_deactivate(self):
        pass


class SafetySavePluginViewExtension(GObject.Object, Gedit.ViewActivatable):
    __gtype_name__ = "SafetySavePluginViewExtension"
    view = GObject.property(type=Gedit.View)

    def __init__(self):
        GObject.Object.__init__(self)
        self.__watch_state = False

    # Logging methods.

    def __log(self, method, message):
        method("[%s] %s" % (self.__get_name(), message))

    def __info(self, message):
        self.__log(_log.info, message)

    def __debug(self, message):
        self.__log(_log.debug, message)

    def __error(self, message):
        self.__log(_log.error, message)

    def __warning(self, message):
        self.__log(_log.warning, message)

    ##

    def __ensure_path(self):
        if exists(_store_path) is False:
            self.__info("Creating temporary unsaved store path: %s" %
                        (_store_path))
            makedirs(_store_path)

    def __is_enabled(self):
        "Only run if auto-save is enabled."

        try:
            return self.__enabled
        except AttributeError:
            self.__enabled = _gedit_settings.get_boolean('auto-save')
            self.__run_interval_s = \
                _gedit_settings.get_uint('auto-save-interval')

            if self.__enabled is False:
                self.__warning("Plugin will not do anything because the "
                               "standard 'auto-save' configurable is not "
                               "enabled.")

            self.__debug("Enabled? %s" % (self.__enabled))
            return self.__enabled

    def __set_schedule(self):
        """Schedule our own "save" events (we won't see any from gEdit since
        we're not named).
        """

        wait_s = self.__run_interval_s * 60
        self.__debug("Scheduling save for (%d) second intervals." % (wait_s))

        i = GObject.timeout_add_seconds(wait_s, self.__store_unsaved_cb)
        self.__save_timer_id = i

    def __clear_schedule(self):
        self.__debug("Cancelling save schedule.")

        GObject.source_remove(self.__save_timer_id)
        del self.__save_timer_id

    def __hook_signals(self):
        "Watch for named saves."

        self.__debug("Configuring 'saved' signal handler.")

        self.__sig_saved = self.__document.connect('saved', self.__on_saved)

    def __unhook_signals(self):
        self.__debug("Removing 'saved' signal handler.")

        self.__document.disconnect(self.__sig_saved)
        del self.__sig_saved

    def __watch_start(self):
        "Set-up events and scheduling."

        self.__watch_state = True

        self.__debug("Starting watch.")

        self.__file_path = join(_store_path, self.__get_name())

        self.__hook_signals()
        self.__set_schedule()

    def __watch_stop(self):
        if self.__is_watching() is False:
            return

        self.__watch_state = False

        self.__debug("Stopping watch.")

        self.__clear_schedule()
        self.__unhook_signals()

    def __is_watching(self):
        return self.__watch_state

    def __on_saved(self, widget, *args, **kwargs):
        "This signal only occurs when named documents are successful saved."

        if self.__is_watching() is True:
            self.__watch_stop()
            self.__cleanup_temp_file()

    def __get_name(self):
        return self.__document.get_short_name_for_display()

    def __store_unsaved_cb(self):
        self.__debug("Checking state of unsaved document.")

# TODO: We might think about taking a hash of the document to determine if it
#       has changed.

        # Is it untouched (i.e. empty)?
        if self.__document.is_untouched() is True:
            self.__debug("Unsaved document has not been touched and will not "
                         "be stored/updated on disk.")
            return True

        self.__ensure_path()

        # We're not worried about size since gedit performs poorly with large
        # files. There's also a lesser issue of consistency, if we were to
        # iterate line-by-line.
        text = self.__document.get_text(self.__document.get_start_iter(),
                                        self.__document.get_end_iter(),
                                        True)

        self.__info("Storing unnamed file as (%d) bytes to: %s" %
                    (len(text), self.__file_path))

        with open(self.__file_path, 'w') as f:
            f.write(text)

        # Automatically reschedule.
        return True

    def __cleanup_temp_file(self):
        self.__info("Cleaning-up temporary file: %s" % (self.__file_path))
        unlink(self.__file_path)

        temp_file_count = len(listdir(_store_path))
        if temp_file_count > 0:
            self.__debug("Other temporary files still exist for this session.")
        else:
            self.__info("No more temporary files exist for this session. "
                        "Removing storage path: %s" % (_store_path))

            rmdir(_store_path)

    def do_activate(self):
        self.__document = self.view.get_buffer()

        if self.__is_enabled() is False:
            self.__warning("Plugin is not enabled.")
            return

        if self.__document.is_untitled() is False:
            self.__debug("Document is already assigned a name. Skipping.")
            return

        self.__watch_start()

    def do_deactivate(self):
        if self.__is_enabled() is False:
            return

        self.__watch_stop()
