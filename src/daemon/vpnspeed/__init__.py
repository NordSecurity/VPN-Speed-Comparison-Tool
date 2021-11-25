import logging

log = logging.getLogger(__name__)
try:
    from systemd.journal import JournalHandler

    log.addHandler(JournalHandler())
except ImportError:
    pass
