#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Classes to import data from a RDF source files
"""

import os,sys,traceback
import shutil
import textwrap
from pygments import highlight
from pygments.lexers import TurtleLexer
from pygments.formatters import HtmlFormatter

from askomics.libaskomics.source_file.SourceFile import SourceFile
from askomics.libaskomics.rdfdb.QueryLauncher import QueryLauncher
from askomics.libaskomics.rdfdb.SparqlQueryBuilder import SparqlQueryBuilder
from askomics.libaskomics.JobManager import JobManager
from askomics.libaskomics.TripleStoreInputManager import *

class SourceFileTtl(SourceFile):
    """
    Class representing a ttl Source file
    """

    def __init__(self, settings, session, path, file_type='ttl'):

        newfile = path
        
        if not file_type == 'ttl':
            newfile = self.convert_to_ttl(path,file_type)

        super().__init__(settings, session, newfile)

        self.type = 'ttl'
        self.origine_type = file_type
        #overload name in case of convert_to_ttl
        self.name =  os.path.basename(path)

    def get_preview_ttl(self):
        """
        Return the first 100 lines of a ttl file,
        text is formated with syntax color
        """

        head = ''

        with open(self.path, 'r', encoding="utf-8", errors="ignore") as fp:
            for x in range(1,100):
                head += fp.readline()

        ttl = textwrap.dedent("""
        {content}
        """).format(content=head)

        formatter = HtmlFormatter(cssclass='preview_field', nowrap=True, nobackground=True)
        return highlight(ttl, TurtleLexer(), formatter) # Formated html

    def persist(self, urlbase, public):
        """
        insert the ttl sourcefile in the TS

        """
        # SLETORT: This is big copy-paste of mother class, with difference
        #   It could certainly be rationalized, but for the moment
        #   I only want it to work and pass the test.
        pathttl  = self.get_rdf_user_directory()
        shutil.copy(self.path, pathttl)
        filepath = pathttl + '/' + os.path.basename(self.path)

        jm    = JobManager(self.settings, self.session)
        jobid = jm.save_integration_job(self.name)
        o_tim = TripleStoreInputManager.create_tim( self.settings, self.session, public, self.name, urlbase )

        d_data = {
                'expected_lines_number':self.get_number_of_lines(),
            }
        try:
            self.timestamp = o_tim.timestamp
            self.log.debug("Inserting ttl data")

            total_triple_count = o_tim.store_ttl_file(filepath)
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

    @staticmethod
    def load_data_from_url(self, url,public):
        """
        insert the ttl sourcefile in the TS

        """

        data = {}

        ql = QueryLauncher(self.settings, self.session)
        try:
            queryResults = ql.load_data(url, self.graph)
        except Exception as e:
            self.log.error(self._format_exception(e))
            raise e
        finally:
            if self.settings["askomics.debug"]:
                data['url'] = url

        data["status"] = "ok"

        #~ self.insert_metadatas(public)

        return data

    def convert_to_ttl(self,filepath,file_type):
        from rdflib import Graph
        newfilepath = filepath

        newfilepath = os.path.splitext(filepath)[0]+".ttl"
        g = Graph()
        if file_type == 'owl':
            g.parse(filepath)
        else:
            g.parse(filepath, format=file_type)
        #print(g.serialize(format='turtle'))
        g.serialize(destination=newfilepath, format='turtle')
        return newfilepath
