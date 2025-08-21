import os
import functools
import threading
import json
import collections

from concurrent.futures import ThreadPoolExecutor
from pathlib2 import Path
from mako.template import Template
from mako.lookup import TemplateLookup
import plim
from tornado.ioloop import IOLoop
from tornado.web import Application, RequestHandler, StaticFileHandler
from tornado.websocket import WebSocketHandler
from tornado import gen

if os.environ.get('MOCK'):
    from . import mock_commands as commands
else:
    from . import commands


COMMAND_PAGES = [
    # (slug, function)
    ('new-artists', commands.new_artists),
    ('update-artist-whitelist', commands.update_artist_whitelist),
    ('push-artist-whitelist', commands.push_artist_whitelist),
    ('check-music', commands.check_music),
    ('import-music', commands.import_music),
    ('generate-traktor', commands.generate_traktor),
    ('upload', commands.upload),
    ('update-mp3s-in-database', commands.update_mp3s_in_database)
]

site_path = Path(__file__).parent.parent.absolute() / 'site'
template_lookup = TemplateLookup(
    directories=[str(site_path)], preprocessor=plim.preprocessor)
executor = ThreadPoolExecutor(1)
app = None


def get_app(**settings):
    global app

    handlers = [(r'/', IndexHandler)]
    for slug, func in COMMAND_PAGES:
        handlers.extend([
            (r'/%s/' % slug, CommandPageHandler, {'slug': slug}),
            (r'/%s/start/' % slug, StartCommandHandler, {'slug': slug, 'func': func}),
            (r'/%s/stop/' % slug, StopCommandHandler, {'slug': slug}),
            (r'/%s/messages/' % slug, MessageHandler, {'slug': slug}),
        ])
    handlers.append(
        (r'/(.*)', NoCacheStaticFileHandler, {'path': str(site_path)}))

    app = CommandCenterApplication(handlers, **settings)
    return app


class CommandCenterApplication(Application):
    def __init__(self, *args, **kwargs):
        super(CommandCenterApplication, self).__init__(*args, **kwargs)

        self.sockets = collections.defaultdict(set)
        self.current_task = None
        self.loop = IOLoop.current()

    def write_message(self, slug, message=None, **kwargs):
        """
        It is safe to call this method from outside the main thread that is
        running the Tornado event loop.

        """
        if not len(kwargs):
            obj = dict(type='info', value=message)
        else:
            obj = kwargs
            if message is not None:
                kwargs['value'] = message

        data = json.dumps(obj)
        self.loop.add_callback(self._write_message, slug, data)

    def _write_message(self, slug, data):
        """
        Write the given data to all connected websockets for a particular
        slug.

        """
        for socket in self.sockets[slug]:
            socket.write_message(data)


class IndexHandler(RequestHandler):
    def get(self):
        self.write(render('index.plim', task=app.current_task))


class CommandPageHandler(RequestHandler):
    def initialize(self, slug):
        self.slug = slug

    def get(self):
        template_name = self.slug + '.plim'

        task = app.current_task
        task_is_running = task is not None and task.slug == self.slug
        self.write(render(template_name, task_is_running=task_is_running))


class StartCommandHandler(RequestHandler):
    def initialize(self, slug, func):
        self.slug = slug
        self.func = func

    def get(self):
        # Convert query arguments to dict of strings (instead of dict of lists).
        func_kwargs = dict(
            (k, v[0]) for k, v
            in self.request.query_arguments.items())

        if app.current_task is not None:
            self.write('fail: command is still running')
            return

        task_func = get_task_func(self.slug, self.func, func_kwargs)
        task = CommandTask(self.slug, task_func)
        app.current_task = task

        # Add callbacks.
        def on_done(finished):
            app.current_task = None
            app.write_message(self.slug, type='finish' if finished else 'stop')
        task.add_done_callback(on_done)

        def on_error(ex):
            import traceback
            app.current_task = None
            app.write_message(
                self.slug, str(ex), type='failure', stacktrace=traceback.format_exc())
        task.add_error_callback(on_error)

        task.start()
        self.write('ok')


class StopCommandHandler(RequestHandler):
    def initialize(self, slug):
        self.slug = slug

    def get(self):
        task = app.current_task
        if task is None:
            self.write('fail: no command is running')
            return
        if task.slug != self.slug:
            self.write('fail: cannot stop other command')
            return

        task.stop()
        app.current_task = None
        self.write('ok')


class MessageHandler(WebSocketHandler):
    def initialize(self, slug):
        self.slug = slug

    def open(self):
        app.sockets[self.slug].add(self)

    def on_close(self):
        app.sockets[self.slug].remove(self)


class NoCacheStaticFileHandler(StaticFileHandler):
    def set_extra_headers(self, path):
        self.set_header('Cache-Control', 'no-store')


class CommandTask(object):
    def __init__(self, slug, func):
        self.slug = slug
        self.func = func
        self.stop_event = threading.Event()
        self.future = None
        self.done_callbacks = []
        self.error_callbacks = []
        self.finished = None

    def stop(self):
        self.finished = False
        self.stop_event.set()

    def done(self):
        return self.stop_event.is_set()

    def start(self):
        """
        Unlike asyncio's run_in_executor(), submit() does not raise an exception
        when the function it tries to run errors out.

        """
        self.future = executor.submit(self._stoppable_run)
        self.future.add_done_callback(self._done_callback)

    def add_done_callback(self, callback):
        self.done_callbacks.append(callback)

    def add_error_callback(self, callback):
        self.error_callbacks.append(callback)

    def _stoppable_run(self):
        for obj in self.func():
            if self.stop_event.is_set():
                self.finished = False
                self.stop_event.set()
                return

        self.finished = True
        self.stop_event.set()

    def _done_callback(self, future):
        """
        If there was an exception inside of self._stoppable_run, then it won't
        be raised until you call future.result().

        """
        try:
            future.result()
            for cb in self.done_callbacks:
                cb(self.finished)
        except Exception as ex:
            for cb in self.error_callbacks:
                cb(ex)


def render(template_name, **kwargs):
    path = site_path / template_name
    tmpl = Template(
        text=path.read_text(),
        lookup=template_lookup,
        preprocessor=plim.preprocessor)
    return tmpl.render(**kwargs)


def get_task_func(slug, func, kwargs):
    from chirp.common.printing import cprint

    def write_func(message, **kwargs):
        app.write_message(slug, message, **kwargs)
        # print(message)

    def new_func():
        with cprint.use_write_function(write_func):
            for obj in func(**kwargs):
                yield obj

    return new_func


if __name__ == '__main__':
    main()
