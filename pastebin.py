#!/usr/bin/env python3

#############################################################################
#    pastebin.py - Python 3.2 Pastebin API.
#    Copyright (C) 2017 entourloop
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################

# This software is a derivative work of:
# - https://github.com/Morrolan/PastebinAPI
# - http://winappdbg.sourceforge.net/blog/pastebin.py

#############################################################################

from datetime import date
import json
import urllib
import xml.etree.ElementTree as ET
from urllib import request


class PastebinError(RuntimeError):
    """Pastebin API Error.
    The error message returned by the web application is stored as the Python
    exception message."""


class Paste:
    """Paste model.
    """

    # Valid paste_expire_date values
    paste_expire_date = ('N', '10M', '1H', '1D', '1W', '2W', '1M', '6M', '1Y')

    # Valid paste_type values (integer values)
    paste_type = ('public', 'unlisted', 'private')

    def __init__(self, key=None, date=None, title=None, size=None,
                 expire_date=None, private=0, format_long=None,
                 format_short=None, url=None, hits=0, scrape_url=None,
                 user=None):
        self.key = key
        self.date = date
        self.title = title
        self.size = size
        self.expire_date = expire_date
        self.private = private
        self.format_long = format_long
        self.format_short = format_short
        self.url = url
        self.hits = hits
        self.scrape_url = scrape_url
        self.user = user

    def __str__(self):
        if self.scrape_url:
            return 'Paste: key %s date %s title %s size %d expire date %s \
private %d format (long %s short %s) url %s hits %d scrape URL %s user %s' % (
                self.key, self.date, self.title, self.size, self.expire_date,
                self.private, self.format_long, self.format_short, self.url,
                self.hits, self.scrape_url, self.user)
        return 'Paste: key %s date %s title %s size %d expire date %s \
private %d format (long %s short %s) url %s hits %d' % (
                self.key, self.date, self.title, self.size, self.expire_date,
                self.private, self.format_long, self.format_short, self.url,
                self.hits)


class PastesParserXML:
    """Parser for Pastebin pastes.
    To be used with an XML array received from Pastebin.
    """

    def parse(pastes_xml):
        """Parse an XML array containing pastes.

        @type   pastes_xml: string
        @param  pastes_xml: An XML array, representing pastes.

        @rtype: array
        @returns: Array of Paste objects.
        """

        if pastes_xml is None:
            return []

        # FIXME Workaround for non-root document
        tree = ET.fromstring('<root>' + pastes_xml + '</root>')
        pastes_array = []
        paste_elems = {}
        for paste in tree:
            for elem in paste:
                paste_elems[elem.tag] = elem.text
            expire_date = None
            if int(paste_elems['paste_expire_date']) > 0:
                expire_date = date.fromtimestamp(
                    int(paste_elems['paste_expire_date']))
            format_long = None
            if paste_elems['paste_format_long'] != 'None':
                format_long = paste_elems['paste_format_long']
            format_short = None
            if paste_elems['paste_format_short'] != 'None':
                format_short = paste_elems['paste_format_short']
            new_paste = Paste(
                key=paste_elems['paste_key'],
                date=date.fromtimestamp(int(paste_elems['paste_date'])),
                title=paste_elems['paste_title'],
                size=int(paste_elems['paste_size']),
                expire_date=expire_date,
                private=int(paste_elems['paste_private']),
                format_long=format_long,
                format_short=format_short,
                url=paste_elems['paste_url'],
                hits=int(paste_elems['paste_hits'])
            )
            pastes_array.append(new_paste)

        # Prefer a single object instead of an array
        if len(pastes_array) == 1:
            return pastes_array[0]
        return pastes_array


class PastesParserJSON:
    """Parser for Pastebin pastes.
    To be used with a JSON array received from Pastebin.
    """

    def parse(pastes_json):
        """Parse a JSON array containing pastes.

        @type   pastes_json: string
        @param  pastes_json: A JSON array, representing pastes.

        @rtype: array
        @returns: Array of Paste objects.
        """

        if pastes_json is None:
            return []

        tree = json.loads(pastes_json.decode('utf-8'))
        pastes_array = []
        for paste in tree:
            expire_date = None
            if int(paste['expire']) > 0:
                expire_date = date.fromtimestamp(int(paste['expire']))
            format_short = None
            if paste['syntax'] != 'text':
                format_short = paste['syntax']
            user = None
            if len(paste['user']) > 0:
                user = paste['user']
            new_paste = Paste(
                key=paste['key'],
                date=date.fromtimestamp(int(paste['date'])),
                title=paste['title'],
                size=int(paste['size']),
                expire_date=expire_date,
                format_short=format_short,
                url=paste['full_url'],
                scrape_url=paste['scrape_url'],
                hits=int(paste['hits']),
                user=user
            )
            pastes_array.append(new_paste)

        # Prefer a single object instead of an array
        if len(pastes_array) == 1:
            return pastes_array[0]
        return pastes_array


class User:
    """Pastebin user model.
    """

    # Base domain name
    _base_domain = 'pastebin.com'

    # Valid Pastebin URLs
    _prefix_url = 'https://%s/' % _base_domain

    _user_type = ('normal', 'pro')

    _user_default_avatar = '%si/guest.png' % _prefix_url

    def __init__(self, name=None, format_short='text', expiration='N',
                 avatar_url=_user_default_avatar, private=0, website=None,
                 email=None, location=None,
                 account_type=_user_type.index('normal')):
        self.name = name
        self.format_short = format_short
        self.expiration = expiration
        self.avatar_url = avatar_url
        self.private = int(private)
        self.website = website
        self.email = email
        self.location = location
        self.account_type = int(account_type)

    def __str__(self):
        return 'User: name %s def. format %s def. expiration %s avatar URL %s \
def. private paste %s website %s email %s location %s account type %s' % (
            self.name, self.format_short, self.expiration, self.avatar_url,
            Paste.paste_type[self.private], self.website, self.email,
            self.location, self._user_type[self.account_type])


class UsersParser:
    """Parser for Pastebin users.
    To be used with an XML array received from Pastebin.
    """

    def parse(users_xml):
        """Parse an XML array containing users.

        @type   users_xml: string
        @param  users_xml: An XML array, representing users.

        @rtype:     array
        @returns:   Array of User objects.
        """

        # FIXME Workaround for non-root document
        tree = ET.fromstring('<root>' + users_xml + '</root>')
        users_array = []
        user_elems = {}
        for user in tree:
            for elem in user:
                user_elems[elem.tag] = elem.text
            format_short = None
            if user_elems['user_format_short'] != 'None':
                format_short = user_elems['user_format_short']
            new_user = User(
                name=user_elems['user_name'],
                format_short=format_short,
                expiration=user_elems['user_expiration'],
                avatar_url=user_elems['user_avatar_url'],
                private=user_elems['user_private'],
                website=user_elems['user_website'],
                email=user_elems['user_email'],
                location=user_elems['user_location'],
                account_type=user_elems['user_account_type']
            )
            # print ('New user; %s' % new_user)
            users_array.append(new_user)
        return users_array


class PastebinAPI:
    # Base domain name
    _base_domain = 'pastebin.com'

    # String to determine bad API requests
    _bad_request = 'Bad API request'
    _bad_scrape = 'VISIT: https://%s/scraping TO GET ACCESS!' % _base_domain
    _request_error = 'Error, '

    # Valid Pastebin URLs
    _prefix_url = 'https://%s/' % _base_domain

    # Valid Pastebin URLs w/ custom subdomain
    _subdomain_url = 'https://%%s.%s' % _base_domain

    # DEPRECATED
    # Legacy API
    # _api_legacy_url = 'http://%s/api_public.php' % _base_domain

    # POST API
    _api_url = 'https://%s/api/api_post.php' % _base_domain

    # Login API
    _api_login_url = 'https://%s/api/api_login.php' % _base_domain

    # Raw API
    _api_raw_url = 'https://%s/api/api_raw.php' % _base_domain

    # Scraping API
    _api_scraping_url = 'https://%s/api_scraping.php' % _base_domain

    paste_format = (
        '4cs',      # 4CS
        '6502acme',      # 6502 ACME Cross Assembler
        '6502kickass',      # 6502 Kick Assembler
        '6502tasm',      # 6502 TASM/64TASS
        'abap',      # ABAP
        'actionscript',      # ActionScript
        'actionscript3',      # ActionScript 3
        'ada',      # Ada
        'aimms',      # AIMMS
        'algol68',      # ALGOL 68
        'apache',      # Apache Log
        'applescript',      # AppleScript
        'apt_sources',      # APT Sources
        'arm',      # ARM
        'asm',      # ASM (NASM)
        'asp',      # ASP
        'asymptote',      # Asymptote
        'autoconf',      # autoconf
        'autohotkey',      # Autohotkey
        'autoit',      # AutoIt
        'avisynth',      # Avisynth
        'awk',      # Awk
        'bascomavr',      # BASCOM AVR
        'bash',      # Bash
        'basic4gl',      # Basic4GL
        'dos',      # Batch
        'bibtex',      # BibTeX
        'blitzbasic',      # Blitz Basic
        'b3d',      # Blitz3D
        'bmx',      # BlitzMax
        'bnf',      # BNF
        'boo',      # BOO
        'bf',      # BrainFuck
        'c',      # C
        'c_winapi',      # C (WinAPI)
        'c_mac',      # C for Macs
        'cil',      # C Intermediate Language
        'csharp',      # C#
        'cpp',      # C++
        'cpp-winapi',      # C++ (WinAPI)
        'cpp-qt',      # C++ (with Qt extensions)
        'c_loadrunner',      # C: Loadrunner
        'caddcl',      # CAD DCL
        'cadlisp',      # CAD Lisp
        'ceylon',      # Ceylon
        'cfdg',      # CFDG
        'chaiscript',      # ChaiScript
        'chapel',      # Chapel
        'clojure',      # Clojure
        'klonec',      # Clone C
        'klonecpp',      # Clone C++
        'cmake',      # CMake
        'cobol',      # COBOL
        'coffeescript',      # CoffeeScript
        'cfm',      # ColdFusion
        'css',      # CSS
        'cuesheet',      # Cuesheet
        'd',      # D
        'dart',      # Dart
        'dcl',      # DCL
        'dcpu16',      # DCPU-16
        'dcs',      # DCS
        'delphi',      # Delphi
        'oxygene',      # Delphi Prism (Oxygene)
        'diff',      # Diff
        'div',      # DIV
        'dot',      # DOT
        'e',      # E
        'ezt',      # Easytrieve
        'ecmascript',      # ECMAScript
        'eiffel',      # Eiffel
        'email',      # Email
        'epc',      # EPC
        'erlang',      # Erlang
        'euphoria',      # Euphoria
        'fsharp',      # F#
        'falcon',      # Falcon
        'filemaker',      # Filemaker
        'fo',      # FO Language
        'f1',      # Formula One
        'fortran',      # Fortran
        'freebasic',      # FreeBasic
        'freeswitch',      # FreeSWITCH
        'gambas',      # GAMBAS
        'gml',      # Game Maker
        'gdb',      # GDB
        'genero',      # Genero
        'genie',      # Genie
        'gettext',      # GetText
        'go',      # Go
        'groovy',      # Groovy
        'gwbasic',      # GwBasic
        'haskell',      # Haskell
        'haxe',      # Haxe
        'hicest',      # HicEst
        'hq9plus',      # HQ9 Plus
        'html4strict',      # HTML
        'html5',      # HTML 5
        'icon',      # Icon
        'idl',      # IDL
        'ini',      # INI file
        'inno',      # Inno Script
        'intercal',      # INTERCAL
        'io',      # IO
        'ispfpanel',      # ISPF Panel Definition
        'j',      # J
        'java',      # Java
        'java5',      # Java 5
        'javascript',      # JavaScript
        'jcl',      # JCL
        'jquery',      # jQuery
        'json',      # JSON
        'julia',      # Julia
        'kixtart',      # KiXtart
        'kotlin',      # Kotlin
        'latex',      # Latex
        'ldif',      # LDIF
        'lb',      # Liberty BASIC
        'lsl2',      # Linden Scripting
        'lisp',      # Lisp
        'llvm',      # LLVM
        'locobasic',      # Loco Basic
        'logtalk',      # Logtalk
        'lolcode',      # LOL Code
        'lotusformulas',      # Lotus Formulas
        'lotusscript',      # Lotus Script
        'lscript',      # LScript
        'lua',      # Lua
        'm68k',      # M68000 Assembler
        'magiksf',      # MagikSF
        'make',      # Make
        'mapbasic',      # MapBasic
        'markdown',      # Markdown
        'matlab',      # MatLab
        'mirc',      # mIRC
        'mmix',      # MIX Assembler
        'modula2',      # Modula 2
        'modula3',      # Modula 3
        '68000devpac',      # Motorola 68000 HiSoft Dev
        'mpasm',      # MPASM
        'mxml',      # MXML
        'mysql',      # MySQL
        'nagios',      # Nagios
        'netrexx',      # NetRexx
        'newlisp',      # newLISP
        'nginx',      # Nginx
        'nimrod',      # Nimrod
        'text',      # None
        'nsis',      # NullSoft Installer
        'oberon2',      # Oberon 2
        'objeck',      # Objeck Programming Langua
        'objc',      # Objective C
        'ocaml-brief',      # OCalm Brief
        'ocaml',      # OCaml
        'octave',      # Octave
        'oorexx',      # Open Object Rexx
        'pf',      # OpenBSD PACKET FILTER
        'glsl',      # OpenGL Shading
        'oobas',      # Openoffice BASIC
        'oracle11',      # Oracle 11
        'oracle8',      # Oracle 8
        'oz',      # Oz
        'parasail',      # ParaSail
        'parigp',      # PARI/GP
        'pascal',      # Pascal
        'pawn',      # Pawn
        'pcre',      # PCRE
        'per',      # Per
        'perl',      # Perl
        'perl6',      # Perl 6
        'php',      # PHP
        'php-brief',      # PHP Brief
        'pic16',      # Pic 16
        'pike',      # Pike
        'pixelbender',      # Pixel Bender
        'pli',      # PL/I
        'plsql',      # PL/SQL
        'postgresql',      # PostgreSQL
        'postscript',      # PostScript
        'povray',      # POV-Ray
        'powershell',      # Power Shell
        'powerbuilder',      # PowerBuilder
        'proftpd',      # ProFTPd
        'progress',      # Progress
        'prolog',      # Prolog
        'properties',      # Properties
        'providex',      # ProvideX
        'puppet',      # Puppet
        'purebasic',      # PureBasic
        'pycon',      # PyCon
        'python',      # Python
        'pys60',      # Python for S60
        'q',      # q/kdb+
        'qbasic',      # QBasic
        'qml',      # QML
        'rsplus',      # R
        'racket',      # Racket
        'rails',      # Rails
        'rbs',      # RBScript
        'rebol',      # REBOL
        'reg',      # REG
        'rexx',      # Rexx
        'robots',      # Robots
        'rpmspec',      # RPM Spec
        'ruby',      # Ruby
        'gnuplot',      # Ruby Gnuplot
        'rust',      # Rust
        'sas',      # SAS
        'scala',      # Scala
        'scheme',      # Scheme
        'scilab',      # Scilab
        'scl',      # SCL
        'sdlbasic',      # SdlBasic
        'smalltalk',      # Smalltalk
        'smarty',      # Smarty
        'spark',      # SPARK
        'sparql',      # SPARQL
        'sqf',      # SQF
        'sql',      # SQL
        'standardml',      # StandardML
        'stonescript',      # StoneScript
        'sclang',      # SuperCollider
        'swift',      # Swift
        'systemverilog',      # SystemVerilog
        'tsql',      # T-SQL
        'tcl',      # TCL
        'teraterm',      # Tera Term
        'thinbasic',      # thinBasic
        'typoscript',      # TypoScript
        'unicon',      # Unicon
        'uscript',      # UnrealScript
        'upc',      # UPC
        'urbi',      # Urbi
        'vala',      # Vala
        'vbnet',      # VB.NET
        'vbscript',      # VBScript
        'vedit',      # Vedit
        'verilog',      # VeriLog
        'vhdl',      # VHDL
        'vim',      # VIM
        'visualprolog',      # Visual Pro Log
        'vb',      # VisualBasic
        'visualfoxpro',      # VisualFoxPro
        'whitespace',      # WhiteSpace
        'whois',      # WHOIS
        'winbatch',      # Winbatch
        'xbasic',      # XBasic
        'xml',      # XML
        'xorg_conf',      # Xorg Config
        'xpp',      # XPP
        'yaml',      # YAML
        'z80',      # Z80 Assembler
        'zxbasic',      # ZXBasic
    )

    def __init__(self, api_dev_key, api_user_key=None):
        """ New PastebinAPI object.

        @type   api_dev_key: string
        @param  api_dev_key: The API Developer key of a registered Pastebin
        user.

        @type   api_user_key: string
        @param  api_user_key: (Optional) The API User key of a registered
        Pastebin user.
        """

        self.api_dev_key = api_dev_key
        self.api_user_key = api_user_key

    def generate_user_key(self, username, password):
        """ Generate a user key - needed for private API access.

        @type   username: string
        @param  username: The username of a registered U{https://pastebin.com}
        account.

        @type   password: string
        @param  password: The password of a registered U{https://pastebin.com}
        account.

        @rtype: string
        @returns: User key (api_user_key) to allow authenticated
        interaction to the API.
        """

        # Valid API dev key
        argv = {'api_dev_key': str(self.api_dev_key)}

        # Requires pre-registered Pastebin account
        if username is not None:
            argv['api_user_name'] = str(username)
        if password is not None:
            argv['api_user_password'] = str(password)

        request_string = request.urlopen(self._api_login_url,
                                         urllib.parse.urlencode(argv)
                                         .encode('utf-8')
                                         )
        response = request_string.read()

        # Error checking
        if response.startswith(bytes(self._bad_request, 'utf-8')):
            raise PastebinError((str(response).split(',')[1]).strip("' "))

        self.api_user_key = response
        return response

    def paste(self, paste_content, paste_title=None, paste_format=None,
              paste_guest=True, paste_type='public', paste_expire_date='N'):
        """Submit a code snippet to Pastebin.

        @type   paste_content: string
        @param  paste_content: Content of the paste.

        @type   paste_title: string
        @param  paste_title: (Optional) Title of the paste.

        @type   paste_format: string
        @param  paste_format: (Optional) Programming language of the code being
            pasted. This enables syntax highlighting when reading the code in
            U{https://pastebin.com}. Default is no syntax highlighting (text
            is just text and not source code).

        @type   paste_guest: boolean
        @param  paste_guest: (Optional) Represents whether this paste should
        be posted under the user's account, or as guest. 'True' means guest.

        @type   paste_type: string
        @param  paste_type: (Optional) C{'public'} if the paste is public
            (visible by everyone), C{'unlisted'} if it's public but not
            searchable. C{'private'} if the paste is private and not
            searchable or indexed. The Pastebin FAQ
            (U{https://pastebin.com/faq}) claims private pastes are not indexed
            by search engines.

        @type   paste_expire_date: string
        @param  paste_expire_date: (Optional) Expiration date for the paste.
            Once past this date the paste is deleted automatically. Valid
            values are found in the L{PastebinAPI.paste_expire_date} class
            member. If not provided, the paste never expires.

        @rtype:  string
        @return: Returns the URL to the newly created paste.
        """

        # Prepare args
        argv = {'api_dev_key': self.api_dev_key}
        if not paste_guest:
            if self.api_user_key is None:
                raise PastebinError('Generate a user key before adding a \
                                    user-registered paste')
            argv['api_user_key'] = self.api_user_key
        argv['api_option'] = str('paste')

        if paste_content is not None:
            argv['api_paste_code'] = paste_content
        if paste_title is not None:
            argv['api_paste_name'] = paste_title
        if paste_format is not None:
            argv['api_paste_format'] = paste_format
        if paste_type is not None:
            if Paste.paste_type.index(paste_type) != -1:
                argv['api_paste_private'] = Paste.paste_type.index(paste_type)
            else:
                argv['api_paste_private'] = Paste.paste_type.index('unlisted')
        if paste_expire_date is not None:
            paste_expire_date = str(paste_expire_date).strip().upper()
            argv['api_paste_expire_date'] = paste_expire_date

        # POST everything
        request_string = request.urlopen(self._api_url,
                                         urllib.parse.urlencode(argv)
                                         .encode('utf-8')
                                         )
        response = request_string.read()

        # Error checking
        if response.startswith(self._bad_request.encode('utf-8')):
            raise PastebinError((str(response).split(',')[1]).strip("' "))
        elif not response.startswith(self._prefix_url.encode('utf-8')):
            raise PastebinError(response)

        return str(response)

    def list_user_pastes_mdata(self, api_user_key=None, results_limit=None):
        """Returns all pastes for the provided api_user_key.

        Note: Returns multiple pastes, not just 1.

        @type        api_user_key: string
        @param       api_user_key: (Optional) The API UserKey of a registered
        user. If you don't provide the user key, your own key will be used.

        @type        results_limit: number
        @param       results_limit: (Optional) The number of pastes to
        return (1-1000)

        @rtype:      string
        @returns:    An XML containing pastes of the user.
        """

        argv = {'api_dev_key': self.api_dev_key}
        argv['api_option'] = 'list'
        if api_user_key is not None:
            argv['api_user_key'] = api_user_key
        elif self.api_user_key is not None:
            argv['api_user_key'] = self.api_user_key
        else:
            raise PastebinError('Generate a user key before listing pasties')
        if results_limit is not None:
            if results_limit < 1:
                argv['api_results_limit'] = 1
            elif results_limit > 1000:
                argv['api_results_limit'] = 1000
            else:
                argv['api_results_limit'] = int(results_limit)
        else:
            argv['api_results_limit'] = 50

        # POST everything
        request_string = request.urlopen(self._api_url,
                                         urllib.parse.urlencode(argv)
                                         .encode('utf-8')
                                         )
        response = request_string.read()

        # Error checking
        if response.startswith(self._bad_request.encode('utf-8')):
            raise PastebinError((str(response).split(',')[1]).strip("' "))
        elif response.startswith('No pastes found'.encode('utf-8')):
            return None
        elif not response.startswith('<paste>'.encode('utf-8')):
            raise PastebinError(response)

        return str(response)

    def trending(self):
        """Returns the top trending paste details.

        Note: Returns multple trending pastes, not just 1.

        @rtype:     string
        @return:    Returns the XML containing the top trending pastes.
        """

        argv = {'api_dev_key': self.api_dev_key}
        argv['api_option'] = 'trends'

        # POST everything
        request_string = request.urlopen(self._api_url,
                                         urllib.parse.urlencode(argv)
                                         .encode('utf-8')
                                         )
        response = request_string.read()

        # Error checking
        if response.startswith(self._bad_request.encode('utf-8')):
            raise PastebinError((str(response).split(',')[1]).strip("' "))

        return str(response)

    def delete_paste(self, paste_key, api_user_key=None):
        """ Delete the paste specified by paste_key.

        @type   paste_key:      string
        @param  paste_key:      The unique key for a paste.

        @type   api_user_key:   string
        @param  api_user_key:   (Optional) The API User Key of a registered
        Pastebin account. If not provided, your own key will be used instead.

        @rtype:     boolean
        @returns:   Whether the deletion was successful.
        """

        argv = {'api_dev_key': self.api_dev_key}
        argv['api_option'] = 'delete'
        if api_user_key is not None:
            argv['api_user_key'] = api_user_key
        elif self.api_user_key is not None:
            argv['api_user_key'] = self.api_user_key
        else:
            raise PastebinError('Generate a user key before deleting pasties')
        argv['api_paste_key'] = str(paste_key)

        # POST everything
        request_string = request.urlopen(self._api_url,
                                         urllib.parse.urlencode(argv)
                                         .encode('utf-8')
                                         )
        response = request_string.read()

        # Error checking
        if response.startswith(self._bad_request.encode('utf-8')):
            raise PastebinError((str(response).split(',')[1]).strip("' "))

        return True

    def user_details(self, api_user_key=None):
        """Return user details for the provided api_user_key.

        @type   api_user_key:   string
        @param  api_user_key:   (Optional) The API User key of a registered
        Pastebin user. If not provided, your own key will be used instead.

        @rtype:     string
        @returns:   Returns an XML string containing user information.
        """

        argv = {'api_dev_key': self.api_dev_key}
        argv['api_option'] = 'userdetails'
        if api_user_key is not None:
            argv['api_user_key'] = api_user_key
        elif self.api_user_key is not None:
            argv['api_user_key'] = self.api_user_key
        else:
            raise PastebinError('Generate a user key before requesting user\
details.')

        # POST everything
        request_string = request.urlopen(self._api_url,
                                         urllib.parse.urlencode(argv)
                                         .encode('utf-8')
                                         )
        response = request_string.read()

        # Error checking
        if response.startswith(self._bad_request.encode('utf-8')):
            raise PastebinError((str(response).split(',')[1]).strip("' "))
        elif not response.startswith('<user>'.encode('utf-8')):
            raise PastebinError(response)

        return response

    def get_user_pastes_content(self, paste_key, api_user_key=None):
        """Returns paste content for a paste key (and it's user's key).

        Note: Returns one paste only. Includes private pastes.

        @type        paste_key: string
        @param       paste_key: The key of a requested paste.

        @type        api_user_key: string
        @param       api_user_key: (Optional) The API UserKey of a registered
        user. If you don't provide the user key, your own key will be used.

        @rtype:      string
        @returns:    An XML containing the requested paste.
        """

        argv = {'api_dev_key': self.api_dev_key}
        argv['api_option'] = 'show_paste'
        if api_user_key is not None:
            argv['api_user_key'] = api_user_key
        elif self.api_user_key is not None:
            argv['api_user_key'] = self.api_user_key
        else:
            raise PastebinError('You need a key to request a private \
                                paste\'s content. Else use the raw API \
                                (method `get_paste`)')
        argv['api_paste_key'] = paste_key

        # POST everything
        request_string = request.urlopen(self._api_raw_url,
                                         urllib.parse.urlencode(argv)
                                         .encode('utf-8')
                                         )
        response = request_string.read()

        # Error checking
        if response.startswith(self._bad_request.encode('utf-8')):
            raise PastebinError((str(response).split(',')[1]).strip("' "))

        return response

    def get_paste(paste_key):
        """Get a paste's raw content.

        @type paste_key: string
        @param paste_key: The unique key for the paste.

        @rtype: string
        @return: Returns the XML string containing the raw paste.
        """

        # POST directly
        url = '%sraw/%s' % (PastebinAPI._prefix_url, paste_key)
        request_string = request.urlopen(url)
        response = request_string.read()

        # Error checking
        if response.startswith(PastebinAPI._request_error.encode('utf-8')):
            raise PastebinError(str(response, 'utf-8').strip("' "))
        return response

    def scrape_recents_pastes(limit=0, language=None):
        """Get most recents pastes from Pastebin.

        Note: Scraping APIs require IP whitelisting.

        @type limit: int
        @param limit: (Optional) Number of pastes to return (1-250).

        @type language: string
        @param language: (Optional) Language the pastes must comply to.

        @rtype: string
        @return: Returns a JSON array containing recent pastes.
        """

        # Prepare the arguments
        url = PastebinAPI._api_scraping_url
        argv = {}
        if limit > 0:
            argv['limit'] = limit
        if language is not None:
            argv['lang'] = language

        # POST
        if len(argv) > 0:
            url = '%s%s' % (PastebinAPI._api_scraping_url,
                            urllib.parse.urlencode(argv).encode('utf-8')
                            )
        request_string = request.urlopen(url)
        response = request_string.read()

        # Error checking
        if response.find(PastebinAPI._bad_scrape.encode('utf-8')) != -1:
            raise PastebinError('Not using a whitelisted IP!')
        return response

    def scrape_get_data(key):
        """Get raw data for a paste from Pastebin.

        Note: Scraping APIs require IP whitelisting.

        @type key: string
        @param key: Key for the paste to retrieve.

        @rtype: string
        @return: Raw data for the requested paste.
        """

        # Prepare the URL
        base_url = "%sapi_scrape_item.php" % PastebinAPI._prefix_url
        argv = {'i': key}
        url = '%s?%s' % (base_url, urllib.parse.urlencode(argv))

        # POST
        request_string = request.urlopen(url)
        response = request_string.read()

        # Error checking
        if response.find(PastebinAPI._bad_scrape.encode('utf-8')) != -1:
            raise PastebinError(str(response, 'utf-8').strip("' "))
        elif response.startswith(PastebinAPI._request_error.encode('utf-8')):
            raise PastebinError(
                str(response, 'utf-8')[len(PastebinAPI._request_error):]
            )
        return response

    def scrape_get_metadata(key):
        """ Get metadata for a paste from Pastebin.

        Note: Scraping APIs require IP whitelisting.

        @type key: string
        @param key: Key for the paste to retrieve.

        @rtype: string
        @return: Metadata for the requested paste.
        """

        # Prepare the URL
        base_url = "%sapi_scrape_item_meta.php" % PastebinAPI._prefix_url
        argv = {'i': key}
        url = '%s?%s' % (base_url, urllib.parse.urlencode(argv))

        # POST
        request_string = request.urlopen(url)
        response = request_string.read()

        # Error checking
        if response.find(PastebinAPI._bad_scrape.encode('utf-8')) != -1:
            raise PastebinError(str(response, 'utf-8').strip("' "))
        if response.startswith(PastebinAPI._request_error.encode('utf-8')):
            raise PastebinError(
                str(response, 'utf-8')[len(PastebinAPI._request_error):]
            )
        return response
