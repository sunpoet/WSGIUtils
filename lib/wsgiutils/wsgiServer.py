""" wsgiServer

		Copyright (c) 2004 Colin Stewart (http://www.owlfish.com/)
		All rights reserved.
		
		Redistribution and use in source and binary forms, with or without
		modification, are permitted provided that the following conditions
		are met:
		1. Redistributions of source code must retain the above copyright
		   notice, this list of conditions and the following disclaimer.
		2. Redistributions in binary form must reproduce the above copyright
		   notice, this list of conditions and the following disclaimer in the
		   documentation and/or other materials provided with the distribution.
		3. The name of the author may not be used to endorse or promote products
		   derived from this software without specific prior written permission.
		
		THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
		IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
		OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
		IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
		INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
		NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
		DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
		THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
		(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
		THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
		
		If you make any bug fixes or feature enhancements please let me know!
		
		A basic multi-threaded WSGI server.
"""

import SimpleHTTPServer, SocketServer, BaseHTTPServer, urlparse
import sys, logging

class WSGIHandler (SimpleHTTPServer.SimpleHTTPRequestHandler):
	def log_message (self, *args):
		pass
		
	def log_request (self, *args):
		pass
		
	def do_GET (self):
		protocol, host, path, parameters, query, fragment = urlparse.urlparse ('http://dummyhost%s' % self.path)
		logging.info ("Received GET for path %s" % path)
		if (not self.server.wsgiApplications.has_key (path)):
			# Not a request for an application, just a file.
			SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET (self)
			return
		self.runWSGIApp (self.server.wsgiApplications [path], path, query)

	def do_POST (self):
		protocol, host, path, parameters, query, fragment = urlparse.urlparse ('http://dummyhost%s' % self.path)
		logging.info ("Received POST for path %s" % path)
		if (not self.server.wsgiApplications.has_key (path)):
			# We don't have an application corresponding to this path!
			self.send_error (404, 'Application not found.')
			return
		self.runWSGIApp (self.server.wsgiApplications [path], path, query)

	def runWSGIApp (self, application, path, query):
		logging.info ("Running application for path %s" % path)
		env = {'wsgi.version': (1,0)
			   ,'wsgi.url_scheme': 'http'
			   ,'wsgi.input': self.rfile
			   ,'wsgi.errors': sys.stderr
			   ,'wsgi.multithread': 1
			   ,'wsgi.multiprocess': 0
			   ,'wsgi.run_once': 0
			   ,'REQUEST_METHOD': self.command
			   ,'SCRIPT_NAME': path
			   ,'PATH_INFO': ''
			   ,'QUERY_STRING': query
			   ,'CONTENT_TYPE': self.headers.get ('Content-Type', '')
			   ,'CONTENT_LENGTH': self.headers.get ('Content-Length', '')
			   ,'REMOTE_ADDR': self.client_address[0]
			   ,'SERVER_NAME': self.server.server_address [0]
			   ,'SERVER_PORT': self.server.server_address [1]
			   ,'SERVER_PROTOCOL': self.request_version
			   }
		for httpHeader, httpValue in self.headers.items():
			env ['HTTP_%s' % httpHeader.replace ('-', '_').upper()] = httpValue

		# Setup the state
		self.wsgiSentHeaders = 0
		self.wsgiHeaders = []

		# We have the environment, now invoke the application
		result = application (env, self.wsgiStartResponse)
		for data in result:
			if data:
				self.wsgiWriteData (data)
		if (not self.wsgiSentHeaders):
			# We must write out something!
			self.wsgiWriteData ("")
		return

	def wsgiStartResponse (self, response_status, response_headers, exc_info=None):
		if (self.wsgiSentHeaders):
			raise Exception ("Headers already sent and start_response called again!")
		# Should really take a copy to avoid changes in the application....
		self.wsgiHeaders = (response_status, response_headers)
		return self.wsgiWriteData

	def wsgiWriteData (self, data):
		if (not self.wsgiSentHeaders):
			status, headers = self.wsgiHeaders
			# Need to send header prior to data
			statusCode = status [:status.find (' ')]
			statusMsg = status [status.find (' ') + 1:]
			self.send_response (int (statusCode), statusMsg)
			for header, value in headers:
				self.send_header (header, value)
			self.end_headers()
			self.wsgiSentHeaders = 1
		# Send the data
		self.wfile.write (data)

class WSGIServer (SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
	def __init__ (self, serverAddress, wsgiApplications):
		BaseHTTPServer.HTTPServer.__init__ (self, serverAddress, WSGIHandler)
		self.wsgiApplications = wsgiApplications
		self.serverShuttingDown = 0


