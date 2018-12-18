#!/usr/bin/python3
# -*- coding: utf-8 -*-

import logging

from askomics.libaskomics.ParamManager import ParamManager
from askomics.libaskomics.AskomicsPrefixes import AskomicsPrefixes
from askomics.libaskomics.Abstractor import Abstractor

from askomics.libaskomics.integration.AbstractedEntity import AbstractedEntity__
from askomics.libaskomics.integration.AbstractedRelation import AbstractedRelation__

from askomics.libaskomics.rdfdb.QueryLauncher import QueryLauncher
from askomics.libaskomics.rdfdb.SparqlQueryBuilder import SparqlQueryBuilder

class ExternalEndpoint(Abstractor):
    """
    Class representing an external Endpoint.

    Note: this class aims only (for the moment) to separate the inspect method.
        Maybe this method can be integrated to QueryLauncher, I did not study this yet.
    """
    def __init__(self, d_settings, d_session, ep_uri ):
        super().__init__(d_settings, d_session)
        self.log   = logging.getLogger(__name__)
        self.__uri = ep_uri

        self.__o_launcher = QueryLauncher( d_settings, d_session, endpoint=ep_uri )
        #SLETORT: TODO self._o_launcher.test_endpoint() ?

    @property
    def o_launcher( self ):
        return self.__o_launcher
    @property
    def _uri( self ):
        return self.__uri

    def create_ontology(self, d_onto):
        """Create an ExternalOntology object.

        d_onto"""
        return ExternalOntology(self.settings, self.session, d_onto, self)

    def inspect(self):
        """ask the endpoint for ontologies, and some counts.
        
        For each ontology, get the count of owl:Class, owl:ObjectProperty
            and owl:DatatypeProperty."""
        query = """
            SELECT ?ont ?owl ( count( distinct * ) as ?count )
            WHERE {
              ?ont a owl:Ontology .
            ?uri a ?owl .
            ?uri rdfs:isDefinedBy ?ont .
              FILTER ( ?owl = owl:ObjectProperty || ?owl = owl:DatatypeProperty || ?owl = owl:Class ) .
            }
            GROUP BY ?ont ?owl
        """
        sqb = SparqlQueryBuilder(self.settings, self.session)
        query  = sqb.add_prefix_headers(query)
        self.log.debug( 'entities:\n' + query )

        # will return a list of dict
        return self.o_launcher.process_query( query )

    def abstraction(self):
        # maybe later something more precise
        ttl_service = self.__service()
        return [ ttl_service ]

    def __service(self):
        return """
            [] a sd:Service ;
                sd:endpoint <{}> ;
                sd:supportedLanguage sd:SPARQL11Query .
#                sd:defaultDataset [
#                    a sd:Dataset ;
#                    ].
            """.format(self._uri)


class ExternalOntology(Abstractor):
    """
    Class representing an external Endpoint.

    Abstractor is an interface.
    Note: For the moment the ontology is not linked to an external endpoint.
        In the future, it should be. (ep_uri is only used to build abstractions)
    """

    def __init__(self, d_settings, d_session, d_ontology, o_endpoint ):
        """d_ontology : {uri:prefix}"""
        super().__init__(d_settings, d_session)
        self.log = logging.getLogger(__name__)

        self.__o_sqb  = SparqlQueryBuilder(d_settings, d_session)
        self.__uri    = list( d_ontology.keys() )[0]
        self.__prefix = d_ontology[self._uri]
        self.__o_ep   = o_endpoint

        # prefix integration
        if self._prefix != '':
            o_prefixes = self._o_query_builder.o_prefixes
            o_prefixes.insert_prefixes({self._prefix:self._uri})

    @property
    def _prefix( self ):
        return self.__prefix
    @property
    def _uri( self ):
        return self.__uri
    @property
    def _o_ep( self ):
        return self.__o_ep
    @property
    def _o_query_builder( self ):
        return self.__o_sqb

    def __ttl_entity(self, entity=""):
        # for the moment always use with entity empty !
        if "" != self._prefix:
            return self._prefix + ":" + entity

        return "<" + self._uri + entity + ">"

    def abstraction(self):
        # maybe later something more precise
        ttl_entities = self.__ask_entities()
        self.log.debug( 'entities : {}'.format(ttl_entities) )
        ttl_object_prop = self.__ask_attributes( 'owl:ObjectProperty' )
        self.log.debug( 'OP : {}'.format(ttl_object_prop) )
        ttl_dt_prop = self.__ask_attributes( 'owl:DatatypeProperty' )
        self.log.debug( 'DP : {}'.format(ttl_dt_prop) )

        l_ttl = [ ttl_entities,
                  ttl_object_prop, ttl_dt_prop ]
        return l_ttl

    def __ask_entities(self):
        query = """
        SELECT DISTINCT ?uri ?label
        WHERE {{
            ?uri a owl:Class .
            ?uri rdfs:isDefinedBy {0} .
            OPTIONAL {{ ?uri rdfs:label ?label }}
        }}""".format( self.__ttl_entity() )
        query  = self._o_query_builder.add_prefix_headers(query)

        self.log.debug( 'entities Query:\n' + query )


        ttl = ''
        for d_res in self._o_ep.o_launcher.process_query( query ):
            uri   = '<' + d_res['uri'] + '>'
            label = d_res.get('label', d_res['uri'])
            ttl  += AbstractedEntity__( uri, label, startpoint=True ).get_turtle()

        return ttl
    # __ask_entities

    def __ask_attributes( self, rdf_type ):
        query = """
        SELECT ?uri ?label ?domain ?range
        WHERE {{
            ?uri a {1} .
            ?uri rdfs:isDefinedBy {0} .
            ?uri rdfs:domain ?domain .
            ?uri rdfs:range  ?range .
            OPTIONAL {{ ?uri rdfs:label  ?label }}
        }}
        """.format(self.__ttl_entity(), rdf_type)
        query  = self._o_query_builder.add_prefix_headers(query)
        self.log.debug( 'attribute Query:\n' + query )


        ttl = ''
        for d_res in self._o_ep.o_launcher.process_query( query ):
            uri   = '<' + d_res['uri'] + '>'
            label = d_res.get('label', d_res['uri'])
            domain = '<' + d_res['domain'] + '>'
            range_ = '<' + d_res['range'] + '>'
            ttl  += AbstractedRelation__( uri, rdf_type, domain, range_, label ).get_turtle()

        return ttl
    # __ask_entities
