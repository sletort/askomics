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
        turtle = self._uri + "\n"

        turtle += (len(self._uri) + 1) * " " + "askomics:entity \"true\"^^xsd:boolean ;\n"
        turtle += (len(self._uri) + 1) * " " + "rdfs:label " + json.dumps(self._label) + "^^xsd:string ;\n"
        if self.__startpoint:
            turtle += (len(self._uri) + 1) * " " + "askomics:startPoint \"true\"^^xsd:boolean ;\n"
        turtle += '.\n\n'

        return turtle

class AbstractedEntity( AbstractedEntity__ ):
    """
    An AbstractedEntity represents the classes of the database.
    It is defined by an uri and a label.
    """

    def __init__(self, identifier,prefix):
        uri = ParamManager.encode_to_rdf_uri(identifier,prefix)
        label = identifier
        __AbstractedEntity.__init__( uri, label )
