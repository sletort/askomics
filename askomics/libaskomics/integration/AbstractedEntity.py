#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import json

from askomics.libaskomics.ParamManager import ParamManager
from askomics.libaskomics.utils import pformat_generic_object

class AbstractedEntity__( object ):
    """
    An AbstractedEntity represents the classes of the database.
    It is defined by an uri and a label.
    """
    def __init__( self, uri, label, startpoint=False ):
        self.__uri   = uri
        self.__label = label
        self.__startpoint = startpoint

        self.log = logging.getLogger(__name__)

    @property
    def _uri( self ):
        return self.__uri
    @property
    def _label( self ):
        return self.__label

    def get_turtle(self):
        """
        return the turtle code describing an AbstractedEntity
        for the abstraction file generation.
        """
        # Note: we cannot ends the string with '; .'
        #   This is SPARQL compliant, but virtuoso use SPARQL-BI, which do not tolerate this
        turtle = self._uri + "\n"

        indent = (len(self._uri) + 1) * " "
        l_prop = []
        l_prop.append(indent + "askomics:entity \"true\"^^xsd:boolean")
        l_prop.append(indent + "rdfs:label " + json.dumps(self._label) + "^^xsd:string")
        if self.__startpoint:
            l_prop.append(indent + "askomics:startPoint \"true\"^^xsd:boolean")
        turtle += " ;\n".join(l_prop) + ".\n\n"

        return turtle
	
class AbstractedEntity( AbstractedEntity__ ):
    """
    An AbstractedEntity represents the classes of the database.
    It is defined by an uri and a label.
    """

    def __init__(self, identifier,prefix):
        uri = ParamManager.encode_to_rdf_uri(identifier,prefix)
        label = identifier
        super().__init__( uri, label )
