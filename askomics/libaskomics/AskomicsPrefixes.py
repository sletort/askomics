#!/usr/bin/env python3

import logging
import re
import json
import requests

class AskomicsPrefixes():
    __ASKOMICS_prefixes = {
            "xsd"  : """http://www.w3.org/2001/XMLSchema#""",
            "rdfs" : """http://www.w3.org/2000/01/rdf-schema#""",
            "rdf"  : """http://www.w3.org/1999/02/22-rdf-syntax-ns#""",
            "rdfg" : """http://www.w3.org/2004/03/trix/rdfg-1/""",
            "owl"  : """http://www.w3.org/2002/07/owl#""",
            "prov" : """http://www.w3.org/ns/prov#""",
            "dc"   : """http://purl.org/dc/elements/1.1/""",
            "foaf" : """http://xmlns.com/foaf/0.1/""",
            "faldo": """http://biohackathon.org/resource/faldo#"""
        }

    # SLETORT: do a singleton ?
    def __init__(self, d_settings=None):
        self.log = logging.getLogger(__name__)
        if d_settings is not None:
            d_new_prefixes = {
                    ""        : d_settings.get('askomics.prefix', ''),
                    "askomics": d_settings.get('askomics.namespace', ''),
                }
            self.insert_prefixes(d_new_prefixes)

    def insert_prefixes(self, d_prefixes):
        """d_prefixes: {prefix:uri}"""
        for prefix in d_prefixes:
            if prefix not in self.__ASKOMICS_prefixes:
                self.__ASKOMICS_prefixes[prefix] = d_prefixes[prefix]
                msg = "Prefix '{}' for uri '{}' has been saved as Askomics prefix."
                self.log.debug(msg.format(prefix, d_prefixes[prefix]))

    def __check_askomics_prefixes(self,l_prefixes):
        """removes duplicates,
            if the prefix is public, add it to ASKOMICS_prefixes
            else log it."""
        l_prefixes = list(set(l_prefixes)) # remove duplicates

        url = "http://prefix.cc/"
        ext = ".file.json"

        for prefix in l_prefixes:
            if not prefix in self.__ASKOMICS_prefixes:
                # check that prefix correspond to public ontology
                prefix_url = url + prefix + ext
                response = requests.get(prefix_url)
                if response.status_code != 200:
                    self.log.error("request:"+str(prefix_url))
                    self.log.error("status_code:"+str(response.status_code))
                    self.log.error(response)
                    continue
                dic = json.loads(response.text)
                self.__ASKOMICS_prefixes[prefix] = dic[prefix]
                msg = "add prefix:" + str(prefix) + ":" + self.__ASKOMICS_prefixes[prefix]
                self.log.info(msg)
    # __check_askomics_prefixes

    def __get_prefixes(self, fmt, ttl_or_sparql=''):
        """Parse the ttl string, looking for prefix.
            add them to ASKOMICS_prefix if they exist.

            fmt is 'ttl' or 'sparql'.
            Note: empty prefix show have been set."""
        #add new prefix if needed
        # SLETORT: I don't get why this check is needed.
        if ttl_or_sparql == None:
            raise ValueError("string is empty.")

        regex = re.compile('[\s^](\w+):')
        l_prefixes = list(set(regex.findall(ttl_or_sparql)))

        # add unknown prefix to the dictionnary if they are publicly known
        self.__check_askomics_prefixes(l_prefixes)

        d_format  = { 'ttl': ['@prefix','.'], 'sparql': ['PREFIX', ''] }
        format_   = d_format[fmt]
        l_headers = []
        for prefix in l_prefixes+[""]:
            line  = "{} {}: <{}> {}".format(format_[0],
                                            prefix,
                                            self.__ASKOMICS_prefixes[prefix],
                                            format_[1])
            l_headers.append(line)

        return "\n".join(l_headers)

    def get_turtle_prefixes(self,ttl=''):
        """Parse the ttl string, looking for prefix.
            add them to ASKOMICS_prefix if they exist.
            Then return the prefixes as ttl header."""

        # SLETORT: I think it's never used.
        #~ asko_prefix = self.get_param("askomics.prefix")
        #~ header.append("@base <{0}> .".format(asko_prefix))

        # SLETORT: I don't get this.
        # header.append("<{0}> rdf:type owl:Ontology .".format(asko_prefix))
        return self.__get_prefixes('ttl', ttl)

    def get_sparql_prefixes(self, sparqlrequest):
        """return the header lines containing the prefixe definitions."""
        return self.__get_prefixes('sparql', sparqlrequest)


#~ #Not used yet
#~ def reverse_prefix(self,uri):
    #~ url = "http://prefix.cc/reverse?format=json&uri="

    #~ for prefix in self.ASKOMICS_prefix:
        #~ if uri.startswith(self.ASKOMICS_prefix[prefix]):
            #~ return prefix

    #~ response = requests.get(url+uri)
    #~ if response.status_code != 200:
        #~ self.log.error("request:"+str(url+uri))
        #~ self.log.error("status_code:"+str(response.status_code))
        #~ self.log.error(response)
        #~ self.ASKOMICS_prefix[uri]=uri
        #~ return ""

    #~ dic = json.loads(response.text)
    #~ if (len(dic)>0):
        #~ v = list(dic.values())[0]
        #~ k = list(dic.keys())[0]
        #~ self.ASKOMICS_prefix[k]=v
        #~ self.log.info("add prefix:"+str(k)+":"+self.ASKOMICS_prefix[k])
        #~ return k

    #~ return uri

# Not use
#~ def remove_prefix(self, obj):
    #~ for key, value in self.ASKOMICS_prefix.items():
        #~ new = key
        #~ if new:
            #~ new += ":" # if empty prefix, no need for a :
        #~ obj = obj.replace(value, new)

    #~ return obj
