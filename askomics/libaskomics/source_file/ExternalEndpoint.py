#!/usr/bin/python3
# -*- coding: utf-8 -*-

import logging

from askomics.libaskomics.Abstractor import Abstractor
from askomics.libaskomics.integration.AbstractedEntity import AbstractedEntity__
from askomics.libaskomics.integration.AbstractedRelation import AbstractedRelation__

from askomics.libaskomics.rdfdb.QueryLauncher import QueryLauncher

class ExternalEndpoint(Abstractor):
    """
    Class representing an external Endpoint.
    
    Abstractor is an interface.
    """

    def __init__(self, d_settings, d_session, d_endpoint ):
        """d_endpoint : prefix: uri"""

        super().__init__(d_settings, d_session)
        self.log = logging.getLogger(__name__)

        ch = logging.StreamHandler()
        self.log.addHandler(ch)
        self.log.setLevel(logging.DEBUG)

        self.__ep_prefix = list( d_endpoint.keys() )[0]
        self.__ep_uri    = d_endpoint[self._ep_prefix]

        self.__o_launcher = QueryLauncher( d_settings, d_session, endpoint=self._ep_uri )
        #SLETORT: TODO self._o_launcher.test_endpoint()

    @property
    def _ep_prefix( self ):
        return self.__ep_prefix
    @property
    def _ep_uri( self ):
        return self.__ep_uri
    @property
    def _o_launcher( self ):
        return self.__o_launcher


    def abstraction(self):
        return self.ontogies()
        #~ print( o_abstractor.get_prefixes() )
        #~ ttl_entities = self.__ask_entities()
        #~ o_abstractor.print_attributes( 'owl:ObjectProperty' )
        #~ o_abstractor.print_attributes( 'owl:DatatypeProperty' )

        #~ return ttl_entities

    def inspect(self):
        """ask the endpoint for ontologies, and some counts.
        
        For each ontology, get the count of owl:Class, owl:ObjectProperty
            and owl:DatatypeProperty."""
        #~ fh = logging.FileHandler('/root/ExternalEndpoint.log')
        fh = logging.FileHandler('ExternalEndpoint.log')
        fh.setLevel(logging.DEBUG)
        self.log.addHandler(fh)

        query = """
            SELECT ?ont ?owl ( count( distinct * ) as ?count )
            WHERE {
              ?ont a owl:Ontology .
            ?uri a ?owl .
            ?uri rdfs:isDefinedBy ?ont .
            ?uri rdfs:label  ?label .
              FILTER ( ?owl = owl:ObjectProperty || ?owl = owl:DatatypeProperty || ?owl = owl:Class ) .
            }
            GROUP BY ?ont ?owl
        """
        prefixes  = self.get_sparql_prefixes(query)

        full_query = prefixes + "\n" + query + "\n"
        self.log.debug( 'entities:\n' + full_query )

        # will return a list of dict
        return self._o_launcher.process_query( full_query )

    def __ask_entities( self ):
        #~ query += 'SELECT ( COUNT( distinct *) as ?count )'
        query = """
        SELECT ?uri ?label
        WHERE {{
            ?uri a owl:Class .
            ?uri rdfs:isDefinedBy {0}: .
            ?uri rdfs:label ?label .
        #~  FILTER ( ?uri = {0}:Protein || ?uri = {0}:Gene  ) .
        }}""".format(self._ep_prefix)
        prefixes  = self.get_sparql_prefixes(query)

        full_query = prefixes + "\n" + query + "\n"
        self.log.debug( 'entities:\n' + full_query )


        ttl = ''
        for d_res in self._o_launcher.process_query( full_query ):
            uri   = '<' + d_res['uri'] + '>'
            label = d_res[ 'label' ]
            ttl  += AbstractedEntity__( uri, label, startpoint=True ).get_turtle()

        return ttl
    # __ask_entities

    def __ask_attributes( self, rdf_type ):
        #~ query += 'SELECT ( COUNT( distinct *) as ?count )'
        query = """
        SELECT ?uri ?label ?domain ?range
        WHERE {{
            ?uri a {1} .
            ?uri rdfs:isDefinedBy {0}: .
            ?uri rdfs:label  ?label .
            ?uri rdfs:domain ?domain .
            ?uri rdfs:range  ?range .
        #~  FILTER ( ?uri = {0}:Protein || ?uri = {0}:Gene  ) .
        }}  LIMIT 3
        """.format(self._ep_prefix)
        prefixes  = self.get_sparql_prefixes(query)

        full_query = prefixes + "\n" + query + "\n"
        self.log.debug( 'entities:\n' + full_query )


        ttl = ''
        for d_res in self._o_launcher.process_query( full_query ):
            uri   = '<' + d_res['uri'] + '>'
            label = d_res[ 'label' ]
            domain = '<' + d_res['domain'] + '>'
            range_ = '<' + d_res['range'] + '>'
            ttl  += AbstractedRelation__( uri, rdf_type, domain, range_, label ).get_turtle()

        return ttl
    # __ask_entities

    def debug( self ):
        self.log.debug( dir( self._o_launcher ) )
        self.log.debug( self._o_launcher.endpoint )
        return self.inspect()

# ----------------------------------------

if __name__ == '__main__':
    #for debug purpose
    d_setting = { 'askomics.endpoint': '<http:/example.com>' }
    d_session = { 'username': 'seb', 'group': 'gg' }

    d_ep = { 'up': 'https://sparql.uniprot.org/sparql' }
    o_ = ExternalEndpoint( d_setting, d_session, d_ep )
    print( o_.debug() )
