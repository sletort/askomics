#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Classes to import data from source files
"""
import os,sys,traceback
import re
import logging
import os.path
import tempfile
import getpass
import datetime

from askomics.libaskomics.ParamManager import ParamManager
from askomics.libaskomics.rdfdb.SparqlQueryBuilder import SparqlQueryBuilder
from askomics.libaskomics.rdfdb.SparqlQueryGraph import SparqlQueryGraph
from askomics.libaskomics.rdfdb.QueryLauncher import QueryLauncher
from askomics.libaskomics.utils import cached_property, HaveCachedProperties
from askomics.libaskomics.TripleStoreInputManager import TripleStoreInputManager
from askomics.libaskomics.Abstractor import Abstractor
from askomics.libaskomics.JobManager import JobManager

class SourceFileSyntaxError(SyntaxError):
    pass

class SourceFile(Abstractor, HaveCachedProperties):
    """
    Class representing a source file.
    
    Abstractor is an interface.
    """

    def __init__(self, settings, session, path, uri_set=None):

        super().__init__(settings, session)
        self.log = logging.getLogger(__name__)

        self.path = path
        self.metadatas = {}

        #~ self.timestamp = datetime.datetime.now().isoformat()
        self.timestamp = None


        # The name should not contain extension as dots are not allowed in rdf names
        # self.name = os.path.splitext(os.path.basename(path))[0]
        self.name = os.path.basename(path) # i did not manage yet this for metadata through TripleStoreInputManager

        self.reset_cache()

        self.uri = []
        if uri_set != None:
            for idx,uri in uri_set.items():
                if uri:
                    # uri have to end with # or /
                    if not uri.endswith('#') and not uri.endswith('/'):
                        uri = uri + "/"
                    self.uri.append(uri)
                else:
                    self.uri.append(self.get_param("askomics.prefix"))

    def persist(self, urlbase, public):
        """
        Store the current source file in the triple store

        :param urlbase: the base URL of current askomics instance. It is used to let triple stores access some askomics temporary ttl files using http.
        :return: a dictionnary with information on the success or failure of the operation
        :rtype: Dict
        """
        # SLETORT: timestamp is set here because it is needed by SourceFile* test.
        #   TODO: rewrite tests.
        jm    = JobManager(self.settings, self.session)
        jobid = jm.save_integration_job(self.name)
        o_tim = TripleStoreInputManager.create_tim( self.settings, self.session, public, self.name, urlbase )

        d_data = {
                'expected_lines_number':self.get_number_of_lines(),
            }
        try:
            self.timestamp = o_tim.timestamp
            self.log.debug("Inserting ttl data")
            total_triple_count = o_tim.store_ttl( self.get_turtle() )
            self.log.debug("Inserting ttl abstraction")
            o_tim.store_ttl( self.abstraction() )
            o_tim.insert_metadata(self.name)

            jm.done_integration_job(jobid)
            d_data['status'] = 'ok'
            d_data['total_triple_count'] = total_triple_count
        except Exception as e:
            # rollback
            # SLETORT: Some method test if graph is not None
            #   I think it can never be None, the good test should be
            #       if the_graph_is_in_the_triple_store
            #   Here I do not test like in former load_data_into_graph
            sqb   = SparqlQueryBuilder(self.settings, self.session)
            graph = o_tim.graph_uri
            o_ql  = QueryLauncher(self.settings, self.session)
            o_ql.process_query(sqb.get_drop_named_graph(graph))
            o_ql.process_query(sqb.get_delete_metadatas_of_graph(graph))

            traceback.print_exc(file=sys.stdout)
            if jobid != -1:
                jm.set_error_message('integration', str(e), jobid)

            self.log.error(str(e))
            d_data['status'] = 'ko'

        return d_data

    def abstraction(self):
        # cf doc Abstractor.py
        abstraction_ttl = self.get_abstraction()
        domain_knowledge_ttl = self.get_domain_knowledge()
        
        return [ abstraction_ttl, domain_knowledge_ttl ]

    def get_number_of_lines(self):
        """
        Get the number of line of a tabulated file

        :return: number of ligne (int)
        """

        with open(self.path, encoding="utf-8", errors="ignore") as f:
            for number, l in enumerate(f):
                pass

        return number
