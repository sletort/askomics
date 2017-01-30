import logging
# from pprint import pformat
# from string import Template

# from askomics.libaskomics.rdfdb.SparqlQuery import SparqlQuery
# from askomics.libaskomics.ParamManager import ParamManager
from askomics.libaskomics.rdfdb.SparqlQueryBuilder import SparqlQueryBuilder

class SparqlQueryStats(SparqlQueryBuilder):
    """
    This class contain method to build a sparql query to
    extract data from the users graph
    """

    def __init__(self, settings, session):
        SparqlQueryBuilder.__init__(self, settings, session)
        self.log = logging.getLogger(__name__)


    def get_number_of_triples(self):
        """
        Get number of triples in public graph
        """
        return self.build_query_on_the_fly({
            'select': '(COUNT(*) AS ?number)',
            'query': '?s ?p ?o'
        })

    def get_number_of_entities(self):
        """
        Get number of triples in public graph
        """
        return self.build_query_on_the_fly({
            'select': '(COUNT(DISTINCT ?s) AS ?number)',
            'query': '?s a []'
        })


    def get_number_of_classes(self):
        """
        Get number of triples in public graph
        """
        return self.build_query_on_the_fly({
            'select': '(COUNT(DISTINCT ?s) AS ?number)',
            'query': '?s rdf:type owl:Class'
        })

    def get_number_of_subgraph(self):
        """
        Get number of triples in public graph
        """
        return self.build_query_on_the_fly({
            'select': '(COUNT(DISTINCT ?g) AS ?number)',
            'query': '?s ?p ?o'
        })


    def get_subgraph_infos(self):
        """
        Get number of triples in public graph
        """
        return self.build_query_on_the_fly({
            'select': '?graph ?date ?owner ?server ?version',
            'query': '?graph_uri prov:wasDerivedFrom ?graph .\n' +
                     '\t?graph_uri dc:creator ?owner .\n' +
                     '\t?graph_uri dc:hasVersion ?version .\n' +
                     '\t?graph_uri prov:describesService ?server .\n' +
                     '\t?graph_uri prov:generatedAtTime ?date .'
        })


    def get_attr_of_classes(self):
        """
        Get all the attributes of a class
        """
        return self.build_query_on_the_fly({
            'select': '?class ?attr',
            'query': '?uri_class a owl:Class .\n' +
                     '\t?uri_class rdfs:label ?class .\n' +
                     '\t?uri_attr rdfs:domain ?uri_class .\n' +
                     '\t?uri_attr rdfs:label ?attr .'
            })


    def get_rel_of_classes(self):
        """
        Get all the attributes of a class
        """
        return self.build_query_on_the_fly({
            'select': '?domain ?relname ?range',
            'query': '?rel a owl:ObjectProperty .\n' +
                     '\t?rel rdfs:label ?relname .\n' +
                     '\t?rel rdfs:domain ?uri_domain .\n' +
                     '\t?rel rdfs:range ?uri_range .\n' +
                     '\t?uri_domain rdfs:label ?domain .\n' +
                     '\t?uri_range rdfs:label ?range .'
            })