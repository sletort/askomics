#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import json

from askomics.libaskomics.ParamManager import ParamManager
from askomics.libaskomics.utils import pformat_generic_object

class AbstractedRelation__( object ):
    """
    An AbstractedRelation represents the relations of the database.
    There are two kinds of relations:
        - ObjectProperty binds an instance of a class with another.
        - DatatypeProperty binds an instance of a class with a string
          or a numeric value.
    In Askomics, an ObjectProperty can be represented as:
        - a node on the display graph (relation_type = entity).
        - an attribute of a node (relation_type = category).
    All DatatypeProperty are represented as nodes attributes.
    Each relation has an uri composed by the database prefix (:), "has_"
    and an 
    Each relation also has a domain (the class of the source node) and a
    range (the class of the target).

    domain --relation--> range
    Note : no check is done !
    """
    def __init__( self, id_, type_, domain, range_, label=None ):
        self.__uri    = ParamManager.encode_to_rdf_uri( id_,prefix="askomics:" )
        self.__type   = type_
        self.__domain = domain
        self.__range  = range_
        self.__label  = uri if None is label else label

        self.log = logging.getLogger(__name__)

    @property
    def _uri( self ):
        return self.__uri

    def get_turtle(self):
        """
        return the turtle code describing an AbstractedRelation
        for the abstraction file generation.
        """
        indent = (len(self._uri)) * " "
        l_prop = []
        l_prop.append(self._uri + " rdf:type "  + self.__type)
        l_prop.append(indent + "askomics:attribute \"true\"^^xsd:boolean" )
        # json.dumps manage quotes - is this the best way ? doesn't ( \" + label + \" ) sufficient ?
        l_prop.append(indent + ' rdfs:label ' + json.dumps( self.__label ) + '^^xsd:string')
        l_prop.append(indent + " rdfs:domain " + self.__domain)
        l_prop.append(indent + " rdfs:range "  + self.__range)

        turtle = " ;\n".join(l_prop)+".\n\n"

        return turtle

class AbstractedRelation( AbstractedRelation__ ):
    """
    specialization for TSV file abstraction.
    ...
    identifier that is the header of the tabulated file being
    converted.
    The range is the header of the
    tabulated file being converted in case of ObjectProperty and a
    specified class (xsd:string or xsd:numeric) in case of DatatypeProperty.
    """

    def __init__(self, relation_type, identifier, label, identifier_prefix,rdfs_domain, prefixDomain, rdfs_range, prefixRange):

        idx = identifier.find("@")
        if idx > 0:
            uridi = identifier[0:idx]
        else:
            uridi = identifier
        if label == "":
            if idx > 0:
                label = identifier[0:idx]
            else:
                label = identifier

        if relation_type.startswith("entity"):
            _type = "owl:ObjectProperty"
        elif relation_type == "goterm":
            _type = "owl:ObjectProperty"
            self.rdfs_range = "owl:Class"
        else:
            _type = "owl:DatatypeProperty"

        rdfs_domain = ParamManager.encode_to_rdf_uri(rdfs_domain,prefixDomain)

        super().__init__( uridi, _type, rdfs_domain, rdfs_range, label )
        self.log = logging.getLogger(__name__)
