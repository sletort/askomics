
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os.path
import re
import requests
import json
import tempfile
import logging
import urllib.parse

from askomics.libaskomics.AskomicsPrefixes import AskomicsPrefixes

class ParamManager(object):
    """
        Manage static file and template sparql queries
    """
    def __init__(self, settings, session):
        self.log = logging.getLogger(__name__)
        # User parameters
        self.settings = settings
        self.session = session

        self.__o_prefixes = AskomicsPrefixes(settings)

        self.user_dir = self.get_param('askomics.files_dir') + '/'

        self.escape = {
            'numeric' : lambda str,str2: str,
            'text'    : lambda str,str2: json.dumps(str),
            'category': self.encode_to_rdf_uri,
            'taxon': self.encode_to_rdf_uri,
            'ref': self.encode_to_rdf_uri,
            'strand': self.encode_to_rdf_uri,
            'start' : lambda str,str2: str,
            'end' : lambda str,str2: str,
            'entity'  : self.encode_to_rdf_uri,
            'entitySym'  : self.encode_to_rdf_uri,
            'entity_start'  : self.encode_to_rdf_uri,
            'goterm': lambda str,str2: str.replace("GO:", ""),
            'date': lambda str,str2: json.dumps(str)
            }

    def get_directory(self, name, force_username=None):
        """Get a named directory of a user, create it if not exist"""

        if force_username:
            username = force_username
        elif 'username' in self.session:
            username = self.session['username']
        else:
            username = '_guest'

        mdir = self.user_dir + username + '/' + name + '/'

        if not os.path.isdir(mdir):
            os.makedirs(mdir)

        return mdir


    def get_upload_directory(self):
        """Get the upload directory of a user, create it if not exist

        :returns: The path of the user upload directory
        :rtype: string
        """

        return self.get_directory('upload')


    def get_user_csv_directory(self):

        return self.get_directory('result')

    def get_rdf_directory(self):

        mdir = self.user_dir+"rdf/"
        if not os.path.isdir(mdir):
            os.makedirs(mdir)

        return mdir

    def get_rdf_user_directory(self):

        return self.get_directory('rdf')

    def set_param(self, key,value):
        self.settings[key] = value

    def get_param(self, key):
        if key in self.settings:
            return self.settings[key]
        else:
            return ''

    def is_defined(self, key):
        return key in self.settings.keys()

    @staticmethod
    def encode(toencode):

        obj = urllib.parse.quote(toencode)
        obj = obj.replace("'", "_qu_")
        obj = obj.replace(".", "_d_")
        obj = obj.replace("-", "_t_")
        obj = obj.replace(":", "_s1_")
        obj = obj.replace("/", "_s2_")
        obj = obj.replace("%", "_s3_")

        return obj

    @staticmethod
    def encode_to_rdf_uri(toencode,prefix=None):

        if toencode.startswith("<") and toencode.endswith(">"):
            return toencode

        idx = toencode.find(":")
        if idx > -1:
            return toencode[:idx+1]+ParamManager.encode(toencode[idx+1:])

        pref = ":"
        suf  = ""
        if prefix:
            prefix = prefix.strip()
            if prefix[len(prefix)-1] == ":":
                pref = prefix
            elif prefix.startswith("<") and prefix.endswith(">"):
                pref = prefix[:len(prefix)-1]
                suf  = ">"
            else:
                pref = "<" + prefix
                suf  = ">"

        v = pref+ParamManager.encode(toencode)+suf
        return v

    @staticmethod
    def decode(toencode):

        obj = toencode.replace("_d_", ".")
        obj = obj.replace("_t_", "-")
        obj = obj.replace("_s1_", ":")
        obj = obj.replace("_s2_","/")
        obj = obj.replace("_s3_","%")
        obj = obj.replace("_qu_","'")

        obj = urllib.parse.unquote(obj)

        return obj


    @staticmethod
    def decode_to_rdf_uri(todecode, prefix=""):

        obj = todecode.strip()

        if obj.startswith("<") and obj.endswith(">"):
            obj = obj[1:len(obj)-1]
            if prefix != "":
                obj = obj.replace(prefix,"")

        idx = obj.find(":")
        if idx > -1 :
            obj = obj[idx+1:]

        return ParamManager.decode(obj)

    @staticmethod
    def Bool(result):

        if type(result) != str:
            raise ValueError("Can not convert string to boolean : "+str(result))

        if result.lower() == 'false':
            return False

        if result.lower() == 'true':
            return True

        if result.isdigit():
            return bool(int(result))

    def send_mails(self, host_url, dests, subject, text):
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        """
        Send a mail to a list of Recipients
        """
        self.log.debug(" == Security.py:send_mails == ")
        # Don't send mail if the smtp server is not in
        # the config file
        if not self.get_param('askomics.smtp_host'):
            return
        if not self.get_param('askomics.smtp_port'):
            return
        if not self.get_param('askomics.smtp_login'):
            return
        if not self.get_param('askomics.smtp_password'):
            return
        starttls = False
        if self.get_param('askomics.smtp_starttls'):
            starttls = self.get_param('askomics.smtp_starttls').lower() == 'yes' or \
                       self.get_param('askomics.smtp_starttls').lower() == 'ok' or \
                       self.get_param('askomics.smtp_starttls').lower() == 'true'

        host = self.get_param('askomics.smtp_host')
        port = self.get_param('askomics.smtp_port')
        login = self.get_param('askomics.smtp_login')
        password = self.get_param('askomics.smtp_password')

        msg = MIMEMultipart()
        msg['From'] = 'AskoMics@'+host_url
        msg['To'] = ", ".join(dests)
        msg['Subject'] = subject
        msg.attach(MIMEText(text, 'plain'))

        try:
            smtp = smtplib.SMTP(host, port)
            smtp.set_debuglevel(1)
            if starttls:
                smtp.ehlo()
                askomics.smtp_starttls()
            askomics.smtp_login(login, password)
            smtp.sendmail(dests[0], dests, msg.as_string())
            smtp.quit()
            self.log.debug("Successfully sent email")
        except Exception as e:
            self.log.debug("Error: unable to send email: " + str(e))
