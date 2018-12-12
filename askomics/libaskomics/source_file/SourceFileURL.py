#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Classes to import data from an URL
"""

import os,sys,traceback
import shutil
import textwrap

from pygments import highlight
from pygments.lexers import TurtleLexer
from pygments.formatters import HtmlFormatter

from askomics.libaskomics.source_file.SourceFile import SourceFile
from askomics.libaskomics.rdfdb.QueryLauncher import QueryLauncher
from askomics.libaskomics.JobManager import JobManager
from askomics.libaskomics.rdfdb.SparqlQueryBuilder import SparqlQueryBuilder
from askomics.libaskomics.TripleStoreInputManager import TripleStoreInputManager

class SourceFileURL(SourceFile):
    """
    Class representing ?
    """
    def persist(self, urlbase, public):
        #SLETORT: Ok, now I'm convinced that the try/rollback should be part of TIM responsabilities.
        jm = JobManager(self.settings, self.session)
        jobid = jm.save_integration_job(urlbase)
        o_tim = TripleStoreInputManager.create_tim( self.settings, self.session, public, self.name, urlbase )

        try:
            self.timestamp = o_tim.timestamp
            d_data = o_tim.load_data_from_url(urlbase, public)
            o_tim.insert_metadata(public)

            jm.done_integration_job(jobid)
        except Exception as e:
            # rollback
            sqb = SparqlQueryBuilder(self.settings, self.session)
            graph = o_tim.graph_uri
            query_laucher = QueryLauncher(self.settings, self.session)
            query_laucher.process_query(sqb.get_drop_named_graph(graph))
            query_laucher.process_query(sqb.get_delete_metadatas_of_graph(graph))

            traceback.print_exc(file=sys.stdout)

            if jobid != -1:
                jm.set_error_message('integration', str(e), jobid)

            self.request.response.status = 400

        return d_data
