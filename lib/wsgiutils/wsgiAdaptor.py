""" wsgiAdaptor

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
		
		Provides a basic web environment within a WSGI server.
"""

import Cookie, hmac, base64, socket, xdrlib, struct, pickle, cgi, urllib, os, os.path, SimpleHTTPServer
import logging	
		
class simpleCookie (Cookie.SimpleCookie):
	def __init__ (self, digestKey, dataToLoad = None):
		self.digestKey = digestKey
		self.log = logging.getLogger ("simpleCookie")
		if (dataToLoad is not None):
			Cookie.BaseCookie.__init__ (self, dataToLoad)
		else:
			Cookie.BaseCookie.__init__ (self)
		
	def value_decode (self, avalue):
		""" Return the value decoded - note that the documentation is wrong and the return value
			is actuall a tuple of unquotedvalue, originalvalue
		"""
		unqoutedvalue, dummy = Cookie.SimpleCookie.value_decode (self, avalue)
		if (self.digestKey is None):
			return unqoutedvalue, dummy 
		coder = hmac.new(self.digestKey)
		expectedKey = unqoutedvalue [0:32]
		realValue = unqoutedvalue [32:]
		coder.update (realValue)
		if (coder.hexdigest() == expectedKey):
			# Correctly encoded!
			return realValue, avalue
		else:
			self.log.warn ("Cookie tampering detected!")
			return None, avalue
	
	def value_encode (self, avalue):
		""" Return the value encoded - note that the documentation is wrong and the return value
			is actuall a tuple of originalvalue, quotedevalue
		"""
		if (self.digestKey is None):
			return Cookie.SimpleCookie.value_encode (self, avalue)
		coder = hmac.new(self.digestKey)
		coder.update (avalue)
		valuetostore = coder.hexdigest() + avalue
		return Cookie.SimpleCookie.value_encode (self, valuetostore)
		
class Request (object):
	def __init__ (self, errorStream, relativePath):
		self.session = None
		self.user = None
		self.password = None
		self.formFields = None
		self.contentType = 'text/plain'
		self.contentValue = "Application returned no content."
		self.response = "500 Internal Server Error"
		self.authorisationHeaders = []
		self.errorStream = errorStream
		self.relativePath = relativePath
	
	def getFormFields (self):
		return self.formFields
		
	def getSession (self):
		return self.session
		
	def getUsername (self):
		return self.user
		
	def getPassword (self):
		return self.password
		
	def getErrorStream (self):
		return self.errorStream 
		
	def getRelativePath (self):
		return self.relativePath
		
	def sendContent (self, contentValue, contentType = "text/plain"):
		self.contentValue = contentValue
		self.contentType = contentType
		self.response = "200 OK"
		
	def sendUnauthorisedBasic (self, realm):
		self.response = "401 Unauthorized"
		self.authorisationHeaders.append (('WWW-Authenticate','Basic realm="%s"' % realm))
		
	def sendResponse (self, responseStr, contentValue, contentType = "text/plain"):
		self.response = responseStr
		self.contentValue = contentValue
		self.contentType = contentType
		
	def sendFileForPath (self, path, rootDir = None):
		""" Returns a tuple of the file found at path as a string and the guessed content type of the file.
			path - URL Encoded path that points to a file.
			rootDir - The root directory the path is relative to.  If None is specified then use CWD
		"""
		if (rootDir is None):
			startDir = os.path.abspath (os.getcwd ())
		else:
			startDir = os.path.abspath (rootDir)
		
		decodedPath = urllib.unquote (path)
		if (decodedPath.startswith ('/')):
			decodedPath = decodedPath [1:]
		# Build the path and collapse any indirection (../)
		realPath = os.path.abspath (os.path.join (startDir, decodedPath))
		# Check that the path is really underneath the root directory
		if (os.path.commonprefix ([startDir, realPath]) != startDir):
			msg = "Attempt to read file %s which is outside of root directory %s" % (realPath, startDir)
			raise IOError (msg)
		# Read the file and return it
		try:
			theFile = open (realPath, 'r')
			theFileContents = theFile.read()
		finally:
			try:
				theFile.close()
			except:
				pass
			
		# Guess the content type.
		fileExtension = os.path.splitext (realPath)[1]
		contentType = SimpleHTTPServer.SimpleHTTPRequestHandler.extensions_map [fileExtension]
		self.contentValue = theFileContents
		self.contentType = contentType
		self.response = "200 OK"
	
class wsgiAdaptor (object):
	def __init__ (self, application, cookieKey, sessionClient):
		self.application = application
		self.cookieKey = cookieKey
		self.sessionClient = sessionClient
		self.log = logging.getLogger ("wsgiAdaptor")
		
	def parseBasicAuthorisation (self, request, authCredentials):
		userpass = base64.decodestring (authCredentials)
		userpassOffset = userpass.find (':')
		userName = userpass [0:userpassOffset]
		password = userpass [userpassOffset + 1:]
		request.user = userName
		request.password = password
		self.log.info ("Received via basic authorisation username: %s password: %s" % (userName, password))

	def wsgiHook (self, environment, start_response):
		request = Request (environment ['wsgi.errors'], environment.get ('PATH_INFO', ""))
		
		# Look for authorised users.
		if (environment.has_key ('HTTP_AUTHORIZATION')):
			self.log.debug ("Found authorization header.")
			credentials = environment ['HTTP_AUTHORIZATION']
			authTypeOffset = credentials.find (' ')
			authType = credentials [:authTypeOffset]
			authCredentials = credentials [authTypeOffset + 1:]
			if (authType.lower() == 'basic'):
				self.log.debug ("Found basic authorization header.")
				self.parseBasicAuthorisation (request, authCredentials)
			else:
				self.log.error ("Unsupported authorisation method %s used!" % authType)
				# Internal application error.
				headers = []
				headers.append (('Content-type', request.contentType))
				start_response ("501 Not Implemented", headers)
				return []
		
		# Do we have any cookies?
		if (environment.has_key ('HTTP_COOKIE')):
			# Yes we have cookies!
			cookieValue = environment ['HTTP_COOKIE']
			cookies = simpleCookie (self.cookieKey, cookieValue)
		else:
			cookies = simpleCookie (self.cookieKey, "")
		
		# Get our session
		request.session = self.sessionClient.getSession (cookies)
		# And the form parameters
		request.formFields = cgi.FieldStorage (fp=environment ['wsgi.input'], environ=environment)
		
		# Things left to do:
		# 1 - Get the output from the application
		# 2 - Save the session 
		# 3 - Output headers, including the Cookies.
		
		# Get the application output
		try:
			self.application.requestHandler (request)
		except Exception, e:
			self.log.critical ("Application experienced unhandled error: " + str (e))
			request.sendResponse ("500 Internal Server Error", "Internal application error")
			start_response (request.response, [])
			return iter ([request.contentValue])
		# Persist the session
		self.sessionClient.saveSession (request.session)
		# Get all the headers 
		if (request.response == "401 Unauthorized"):
			headers = request.authorisationHeaders
		else:
			headers = []
		headers.append (('Content-type', request.contentType))
		headers.append (('Content-length', str (len (request.contentValue))))
		# Add the cookies
		for cookie in cookies.values():
			headers.append (('Set-Cookie', cookie.OutputString()))
		
		# Finally start the transaction with wsgi
		start_response (request.response, headers)
		# Now return an iterator for the output
		return iter ([request.contentValue])
		
