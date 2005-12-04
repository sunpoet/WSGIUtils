WSGI Utils (Version 0.7)
------------------------
WSGI Utils are a package of standalone utility libraries that ease the
development of simple WSGI programs.  The functionality provided is limited
at the moment, patches to add new features and address defects are most 
welcome.

The following components are included please refer to the documentation 
for more details:

wsgiServer
----------
This module provides a very simple multi-threaded WSGI server implementation
based on SimpleHTTPServer from Python's standard library.  Multiple 
applications can be hosted at different URLs.

wsgiAdaptor
-----------
A very basic web application framework that works with WSGI compliant servers.
Provides Basic authentication, signed cookies, and persistent sessions 
(see SessionClient).

SessionClient
-------------
This module provides simple session management.  Two implementations are
given: LocalSessionClient and SessionServerClient.  The LocalSessionClient
class is suitable for use with multi-threaded, single process, long-lived WSGI
implementations such as wsgiServer.  SessionServerClient communicates to the
SessionServer via Unix domain sockets and is suitable for multi-process WSGI
implementations such as CGI.

SessionServer & SessionServerDaemon
-----------------------------------
Listens on a Unix domain socket for connections from a single client and
provides session persistence.

