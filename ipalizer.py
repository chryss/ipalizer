# -*- coding: utf-8 -*-

import cgi
from UserList import UserList

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app

# dictionary mapping MW-style phonetics to IPA
# restrictions: voiced TH is broken (MW's uses <u> markup)
# M-W source: http://www.merriam-webster.com/pronsymbols.html
MWtoIPA = {
	u' ':	u' ',
	u"'": u"'",
	u"'\u0259": u"'\u028c",
	u',': u',',
	u',\u0259': u',\u028c',
	u'-':	u'.',
	u'\\': u'/',
	u'/': u'/',
	u'(': u'(',
	u')': u')',
	u'[': u'[',
	u']': u']',
	u'a': u'\u00e6',
	u'au\u0307': u'a\u028a',
	u'ä': u'\u0251',
	u'b': u'b',
	u'ch': u't\u0283',
	u'd': u'd',
	u'e': u'\u025b',
	u'f': u'f',
	u'g': u'g',
	u'h': u'h',
	u'i': u'\u026a',
	u'j': u'd\u0292',
	u'k': u'k',
	u'k\u0331': u'x',
	u'l': u'l',
	u'm': u'm',
	u'n': u'n',
	u'o\u0307': u'\u0254',
	u'o\u0307i': u'\u0254\u026a',
	u'p': u'p',
	u'r': u'\u0279',
	u's': u's',
	u'sh': u'\u0283',
	u't': u't',
	u'th': u'[\u03b8|\u00f0]', 							# theta - unvoiced TH. MW does not distinguish
	u'u\u0307': u'\u028a',
	u'ü': u'u',
	u'v': u'v',
	u'w': u'w',
	u'y': u'j',
	u'yu\u0307': u'(j)\u028a',
	u'yü': u'(j)u',
	u'z': u'z',
	u'zh': u'\u0292',
	u'\u0101': u'e\u026a',					# LATIN SMALL LETTER A WITH MACRON
	u'\u0113': u'i',								# LATIN SMALL LETTER E WITH MACRON
	u'\u012b': u'a\u026a',					# LATIN SMALL LETTER I WITH MACRON
	u'\u014b': u'\u014b',						# LATIN SMALL LETTER ENG
	u'\u014d': u'o\u028a',					# LATIN SMALL LETTER O WITH MACRON
	u'\u0259': u'\u0259',						# LATIN SMALL LETTER SCHWA
	u'\u0259r': u'\u025d',					# LATIN SMALL LETTER REVERSED OPEN E WITH HOOK
	u'\u02c8': u'\u02c8',						# MODIFIER LETTER VERTICAL LINE
	u'\u02c8\u0259': u'\u02c8\u028c',
	u'\u02cc': u'\u02cc',						# MODIFIER LETTER LOW VERTICAL LINE
	u"'\u0259": u"'\u028c"
	}

# a set of all characters in any MW phonetic string	
MWcharset = set(list(''.join(MWtoIPA.keys())))

# lookaheads contains chars with more than one occurrence
firstcharfreq = {}
for char in MWcharset:
	for token in MWtoIPA.keys():
		if (token[0] == char):
			if char in firstcharfreq:
				firstcharfreq[char] += 1
			else:
				firstcharfreq[char] = 1
lookaheads = dict([(char, firstcharfreq[char]) for char in firstcharfreq.keys() if firstcharfreq[char] > 1])


class PhoneticsPair(db.Model):
	"""Saves phonetic string pairs to datastore.
	
	fromstyle, tostyle: IPA, MW, KB...
	"""
	instring = db.StringProperty(multiline=True)
	outstring = db.StringProperty(multiline=True)
	instyle = db.StringProperty()
	outstyle = db.StringProperty()
	date = db.DateTimeProperty(auto_now_add=True)

class Phonetics(UserList):
	"""Stores phonetic transcription as list of tokens.
	
	inputstring: byte string
	data attribute is token list from input string
	IPA attribute is IPA transcription
	"""
	def __init__(self,inputstring,style='MW'):
		self.data = []
		self.data, self.warning = tokenize(inputstring,style)
		self.inputstyle = style
		
	def toIPA(self):
		if hasattr(self, 'IPA'):
			return self.IPA
		else:
			self.IPA = IPAlize(self.data,self.inputstyle)
			return self.IPA

def IPAlize(tokens,style='MW'):
	"""Takes list of tokens in input style, returns list of IPA chars.
	
	both input and output lists contain unicode strings
	"""
	IPAsymbols = []
	for token in tokens:
		try:
			IPAsymbols.append(MWtoIPA[token])
		except KeyError:
			IPAsymbols.append(token)
	return IPAsymbols	

def tokenize(inputstring,style='MW'):
	"""Converts input string into list of unicode tokens"""
	charstring = inputstring.decode('utf8')
	tokens = []
	warning = ""
	while(charstring):
		nextsymbol = nextmatch(charstring, MWtoIPA.keys())
		if nextsymbol:
			tokens.append(nextsymbol)
			charstring = charstring[len(nextsymbol):]
		else:
			# nothing matches. lop off 1 character, return warning and try again
			tokens.append(charstring[:1])
			charstring = charstring[1:]
			if not warning:
				warning = "The input string didn't fully conform to M-W's IPA standard."
	return tokens, warning
			
def nextmatch(string, keys):
		"""Returns longest key that matches start of string or None
		"""
		longest = None
		for i in range(len(string)):
				substr = string[:i+1]
				candidates = [k for k in keys if k.startswith(substr)]
				if not candidates:
						break
				if substr in keys:
						longest = substr
		return longest
	
def ipale(bytestring, debug=False):
	"""Wraps Phonetics class to return utf-8 string from imput string
	
	mostly for testing, or direct translation
	"""
	phonetics = Phonetics(bytestring)
	IPAstring = phonetics.toIPA()
	if debug:
		return IPAstring, phonetics.warning
	else:
		return IPAstring
	
class MainPage(webapp.RequestHandler):
	def get(self):
		self.response.out.write("""
			<html><body>
				<h1>Nothing yet to see here</h1>
				<h2>This is still a placeholder page.</h2>
				<p>Take a look at <a href='test'>the test page</a> meanwhile, there may be something there.
				</body>
				</html>
			""")
			
class PhoneticsInput(webapp.RequestHandler):
	def post(self):
		phoneticspair = PhoneticsPair()

		phoneticspair.instring = self.request.get('content')
		phoneticspair.put()
		self.redirect('/')
		
class Datatest(webapp.RequestHandler):
	def get(self):
		self.response.out.write("""
			<html><body>
				<h1>Test Page</h1>
				<h2>Merriam-Webster to IPA output for testdata</h2>
				<ol>
		""")
		fh = open('data/testdata.txt', 'rU')
		for line in fh:
			input = line.strip()
			output, warning = ipale(input, debug=True)
			if warning:
				warning = '      (WARNING: ' + warning + ')'
			self.response.out.write("""
				<li>%s ==> %s  %s</li>
			""" % (input, ''.join(output).encode('utf8'), warning)) 
		self.response.out.write("""
			</ol></body></html>
		""")
		fh.close()

application = webapp.WSGIApplication(
																		 [('/', MainPage),
																			('/submitnew', PhoneticsInput),
																			('/test', Datatest) ],
																		 debug=True)

def main():
	run_wsgi_app(application)

if __name__ == "__main__":
	main()