# -*- coding: utf-8 -*-
"""
    tornadio.router
    ~~~~~~~~~~~~~~~

    Transport protocol router and main entry point for all socket.io clients.

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""
import logging

from tornado.web import RequestHandler, HTTPError

from tornadio import persistent, polling

PROTOCOLS = {
    'websocket': persistent.TornadioWebSocketHandler,
    'flashsocket': persistent.TornadioFlashSocketHandler,
    'xhr-polling': polling.TornadioXHRPollingSocketHandler,
    'xhr-multipart': polling.TornadioXHRMultipartSocketHandler,
    'htmlfile': polling.TornadioHtmlFileSocketHandler,
    'jsonp-polling': polling.TornadioJSONPSocketHandler,
    }

class SocketRouterBase(RequestHandler):
    """Main request handler.

    Manages creation of appropriate transport protocol implementations and
    passing control to them.
    """
    _connection = None
    _route = None

    def _execute(self, transforms, *args, **kwargs):
        try:
            extra = kwargs['extra']
            proto_name = kwargs['protocol']
            proto_init = kwargs['protocol_init']
            session_id = kwargs['session_id']

            logging.debug('Incoming session %s(%s) Session ID: %s Extra: %s' % (
                proto_name,
                proto_init,
                session_id,
                extra
                ))

            protocol = PROTOCOLS.get(proto_name, None)

            # TODO: Enabled transports configuration
            if protocol:
                handler = protocol(self, session_id)
                handler._execute(transforms, *extra, **kwargs)
            else:
                raise Exception('Handler for protocol "%s" is not available' %
                                proto_name)
        except ValueError:
            # TODO: Debugging
            raise HTTPError(400)

    @property
    def connection(self):
        """Return associated connection class."""
        return self._connection

    @classmethod
    def route(cls):
        """Returns prepared Tornado routes"""
        return cls._route

    @classmethod
    def initialize(cls, connection, resource, extra_re=None, extra_sep=None):
        """Initialize class with the connection and resource.

        Does all behind the scenes work to setup routes, etc. Partially
        copied from SocketTornad.IO implementation.
        """
        cls._connection = connection

        # Copied from SocketTornad.IO with minor formatting
        if extra_re:
            if extra_re[0] != '(?P<extra>':
                if extra_re[0] == '(':
                    extra_re = r'(?P<extra>%s)' % extra_re
                else:
                    extra_re = r"(?P<extra>%s)" % extra_re
            if extra_sep:
                extra_re = extra_sep + extra_re
        else:
            extra_re = "(?P<extra>)"

        proto_re = "(%s)" % "|".join(PROTOCOLS.keys())

        cls._route = (r"/(?P<resource>%s)%s/"
                      "(?P<protocol>%s)/?"
                      "(?P<session_id>[0-9a-zA-Z]*)/?"
                      "((?P<protocol_init>\d*?)|(?P<xhr_path>\w*?))/?"
                      "(?P<jsonp_index>\d*?)" % (resource,
                                                 extra_re,
                                                 proto_re),
                      cls)

def get_router(handler, resource, extra_re=None, extra_sep=None):
    """Create new router class with desired properties.

    Use this function to create new socket.io server. For example:

       class PongConnection(SocketConnection):
           def on_message(self, message):
               self.send(message)

       PongRouter = get_router(PongConnection, 'socket.io/*')

       application = tornado.web.Application([PongRouter.route()])
    """
    router = type('SocketRouter', (SocketRouterBase,), {})
    router.initialize(handler, resource, extra_re, extra_sep)
    return router
