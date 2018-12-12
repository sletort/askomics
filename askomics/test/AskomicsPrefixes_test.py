#!/usr/bin/env python3

import unittest

import askomics.libaskomics.AskomicsPrefixes as ap

class AskomicsPrefixesTest(unittest.TestCase):
    def setUp(self):
        self.asko_empty_prefix_uri = "prout"
        d_settings = { 'askomics.prefix': self.asko_empty_prefix_uri }
        self.o_ = ap.AskomicsPrefixes(d_settings)

    def test_insert_prefixes(self):
        uri = 'http://example.com'

        self.o_.insert_prefixes({'qq': uri})

        d_prefixes = self.o_._AskomicsPrefixes__ASKOMICS_prefixes
        uri_ = d_prefixes.get('qq', None)
        self.assertEqual(uri,uri_)

    def test_get_sparql_prefixes(self):
        query    = "SELECT * fr WHERE { ?ont a owl:Ontology }"
        prefix   = self.o_.get_sparql_prefixes(query)

        #regexp should be better
        expected = "PREFIX owl: <http://www.w3.org/2002/07/owl#> "
        expected += "\nPREFIX : <{}> ".format(self.asko_empty_prefix_uri)
        self.assertEqual(expected,prefix)

    def test_get_turtle_prefixes(self):
        query = "toto a owl:Ontology ."
        prefix   = self.o_.get_turtle_prefixes(query)

        #regexp should be better
        expected = "@prefix owl: <http://www.w3.org/2002/07/owl#> ."
        expected += "\n@prefix : <{}> .".format(self.asko_empty_prefix_uri)
        self.assertEqual(expected,prefix)

    @unittest.skip("function commented as never used _and test irrelevant IMO (sletort).")
    def test_remove_prefix(self):
        m = ParamManager(self.settings, self.request.session)
        d = m.remove_prefix("SELECT ?a FROM { ?a a http://www.w3.org/2002/07/owl#Class. }")
        assert d == "SELECT ?a FROM { ?a a owl:Class. }"

    @unittest.skip("function commented as never used.")
    def test_reverse_prefix(self):
        m = ParamManager(self.settings, self.request.session)
        assert "xsd" == m.reverse_prefix("http://www.w3.org/2001/XMLSchema#")
        assert "" == m.reverse_prefix("http://totototo")
        assert "yago" == m.reverse_prefix("http://yago-knowledge.org/resource/")

