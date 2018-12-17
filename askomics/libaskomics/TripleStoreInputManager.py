#!/usr/bin/env python3

import os
import logging
import re
from pkg_resources import get_distribution
import datetime
import tempfile

from askomics.libaskomics.ParamManager import ParamManager
from askomics.libaskomics.AskomicsPrefixes import AskomicsPrefixes


from askomics.libaskomics.rdfdb.QueryLauncher import QueryLauncher
from askomics.libaskomics.rdfdb.SparqlQueryBuilder import SparqlQueryBuilder

from askomics.libaskomics.integration.AbstractedEntity import AbstractedEntity__
from askomics.libaskomics.integration.AbstractedRelation import AbstractedRelation__

class TripleStoreInputManager(ParamManager):
    """It deals with data integration."""

    @staticmethod
    def create_tim( d_settings, d_session, access_lvl, src='unknown', urlbase=None ):
        method = d_settings.get( "askomics.upload_user_data_method", 'load' )

        if method == 'load':
            return Load( d_settings, d_session, access_lvl, src, urlbase )
        else:
            return NotLoad( d_settings, d_session, access_lvl, src )

    def __init__( self, settings, session, access_lvl, src ):
        """X
        
        src:string used to generate graph name."""
        # SLETORT: It is not clear yet if there should be one TIM per input/graph (the actual case)
        #   if the same TIM can deal with several graphs
        super().__init__(settings, session)
        self.log = logging.getLogger(__name__)

        self.__o_prefixes = AskomicsPrefixes(settings)

        endpoint = self.get_param('askomics.endpoint')
        self.log.debug( "endpoint used : " + str( endpoint ) + "\n" )
        self.__o_launcher = QueryLauncher( settings, session, endpoint=endpoint )
        self.__timestamp  = datetime.datetime.now().isoformat()

        self.__access_lvl = 'public' if access_lvl else 'private'
        self.__src        = re.sub('[^0-9a-zA-Z]+', '_', src)

        # attribute defines later, elsewhere
        self.__graph_uri    = None
        self.__set_graph_uri()

    @property
    def _o_prefixes(self):
        return self.__o_prefixes
    @property
    def timestamp(self):    # public acessor because SourceFile* test need it. This is the only reason -> TODO : rewrite test
        return self.__timestamp
    @property
    def _access_lvl(self):
        return self.__access_lvl
    @property
    def _src(self):
        return self.__src
    @property
    def graph_uri(self): # public to allow rollback (should it be managed in this class ?)
        return self.__graph_uri

    def __set_graph_uri(self):
        if 'graph' in self.session:
            debut = self.session['graph']
        else:
            debut = 'askomics:unkown:uri:graph'

        # Graph name can't contain any non alphanumeric characters. replace all with _
        self.__graph_uri = debut + ':' + self._src + '_' + self.timestamp


    def insert_metadata(self, origin):
        """insert the provenance metadata."""
        if self.is_defined("askomics.endpoint"):
            asko_ep = self.get_param("askomics.endpoint")
        else:
            raise ValueError("askomics.endpoint does not exit.")

        ttl = """
        <{0}> prov:generatedAtTime "{1}"^^xsd:dateTime ;
                 dc:creator "{2}" ;
                 :accessLevel "{3}" ;
                 foaf:Group "{4}" ;
                 prov:wasDerivedFrom "{5}" ;
                 dc:hasVersion "{6}" ;
                 prov:describesService "{7}" ;
                 prov:atLocation "{8}" .
          """.format(
                self.graph_uri, self.timestamp,
                self.session['username'],
                self._access_lvl,
                self.session['group'],
                origin,
                get_distribution('Askomics').version,
                os.uname()[1],
                asko_ep,
            )

        sparql_header = self._o_prefixes.get_sparql_prefixes(ttl)

        self.log.debug('--- insert_metadatas ---')
        o_ql = QueryLauncher(self.settings, self.session)
        o_ql.insert_data(ttl, self.graph_uri, sparql_header)

    def store_ttl( self, gl_ttl, urlbase=None ):
        """store a ttl string by chunk
        g_ttl is a generator or a list of ttl string"""
        # SLETORT why not use get_param ? or why get_param exist ?
        max_size = int(self.settings['askomics.max_content_size_to_update_database'])

        total_triple_count = 0
        chunk_count  = 1
        triple_count = 0
        chunk = ""
        for triple in gl_ttl:
            chunk += triple + '\n'
            triple_count += 1
            self.log.debug( "triple {} = {}".format(str(triple_count), triple) )

            if triple_count > max_size:
                self.log.debug("store ttl chunk %s" % (chunk_count))
                self._store_ttl_chunk(chunk, chunk_count)
                total_triple_count += triple_count
                chunk = ""
                triple_count = 0
                chunk_count += 1

        # Load the last chunk
        if triple_count > 0:
            self._store_ttl_chunk(chunk, chunk_count)

        total_triple_count += triple_count
        #SLETORT : total_triple_count = len( l_ttl ) ?
        self.log.debug("N triples %s" % (total_triple_count))

        return total_triple_count
    #store_ttl

    def _store_ttl_chunk(self, ttl_chunk, chunk_num):
        """store a ttl string, part of a bigger set.
            """
        # Xavier thought it could be possible to always use the insert_data method (cf NotLoad)
        raise NotImplementedError("_store_ttl_chunk should be defined in subclasses.")

    def store_ttl_file(self, fp):
        """Shortcut to store a complete file.

            Main differences with store_ttl : no chunk and no prefix management."""
        raise NotImplementedError("store_ttl_file should be defined in subclasses.")

    def _format_exception(self, e, data=None, ctx='loading data'):
        from traceback import format_tb, format_exception_only
        from html import escape

        fexception = format_exception_only(type(e), e)
        ftb = format_tb(e.__traceback__)
        self.log.debug(ftb)
        #fexception = fexception + ftb

        self.log.error("Error in %s while %s: %s", __name__, ctx, '\n'.join(fexception))

        fexception = escape('\n'.join(fexception))
        error = '<strong>Error while %s:</strong><pre>%s</pre>' % (ctx, fexception)

        if self.settings["askomics.debug"]:
            error += """<p><strong>Traceback</strong> (most recent call last): <br />
                    <ul>
                        <li><pre>%s</pre></li>
                    </ul>
                    """ % '</pre></li><pre><li>'.join(map(escape, ftb))

        if data is None:
            data = {}
        data['status'] = 'failed'
        data['error'] = error
        return data

    def load_data_from_url(self, url, public):
        """
        insert the distant ttl sourcefile in the TS
        """
        ql = QueryLauncher(self.settings, self.session)
        d_data = {}
        try:
            queryResults = ql.load_data(url, self.graph_uri)
        except Exception as e:
            self.log.error(self._format_exception(e))
            raise e
        finally:
            if self.settings["askomics.debug"]:
                d_data['url'] = url

        d_data['status'] = 'ok'

        return d_data


    def debug(self):
        return self._insert_metadata( True )

# ========================================
class Load(TripleStoreInputManager):
    def __init__(self, d_settings, d_session, access_lvl, src, urlbase):
        """
        :param urlbase:the base URL of current askomics instance. It is used to let triple stores access some askomics temporary ttl files using http.
        """
        super().__init__(d_settings, d_session, access_lvl, src)
        self.__urlbase = urlbase

    @property
    def _urlbase(self):
        return self.__urlbase

    def _store_ttl_chunk( self, ttl_chunk, chunk_count ):
        """ X """
        fp = tempfile.NamedTemporaryFile(
                                dir=self.get_rdf_user_directory(),
                                prefix="tmp_"+self._src,
                                suffix=".ttl",
                                mode="w", delete=False)

        self.log.debug("Loading ttl chunk %s file %s" % (chunk_count, fp.name))
        self.log.debug("ttl = %s" % (ttl_chunk))

        header_ttl = self._o_prefixes.get_turtle_prefixes(ttl_chunk)
        fp.write(header_ttl + '\n')
        fp.write(ttl_chunk)
        fp.close()
        d_infos = self.__load_data_from_file(fp)
        if d_infos['status'] == 'failed':
            return d_infos

        return d_infos

    def __load_data_from_file(self, fp):
        """
        Load a locally created ttl file in the triplestore using http (with load_data(url)) or with the filename for Fuseki (with fuseki_load_data(fp.name)).

        :param fp: a file handle for the file to load
        :return: a dictionnary with information on the success or failure of the operation
        """
        if not fp.closed:
            fp.flush() # This is required as otherwise, data might not be really written to the file before being sent to triplestore

        if self.is_defined('askomics.load_url'):
            urlbase = self.settings['askomics.load_url']
        else:
            urlbase = self._urlbase

        # SLETORT: use it as attribute ? is it costly to generate one for each chunk ?
        ql = QueryLauncher(self.settings, self.session)

        try:
            if self.is_defined("askomics.file_upload_url"):
                ql.upload_data(fp.name, self.graph_uri)
            else:
                url = urlbase+"/ttl/"+ self.session['username'] + '/' + os.path.basename(fp.name)
                ql.load_data(url, self.graph_uri)
        except Exception as e:
            self.log.error(self._format_exception(e))
            raise e

        finally:
            # SLETORT: I think it should the method that generate the file that has to delete it.
            #	I didn't do it myself because of the try/except thing (which i don't like it here either)
            os.remove(fp.name) # Everything ok, remove temp file

        return { "status": "ok" }

    def store_ttl_file(self, filepath):
        """Shortcut to store a complete file.
        
            Main differences with store_ttl : no chunk and no prefix management."""
        n_triple = None
        with open(filepath) as o_file:
            d_data = self.__load_data_from_file(o_file)

        return d_data

# ========================================
class NotLoad( TripleStoreInputManager ):
    def _store_ttl_chunk( self, ttl_chunk, chunk_count ):
        """"""
        # SLETORT: looks strange to name ttl_chunk when it use get_sparql_prefixes
        try:
            # SLETORT: use it as attribute ? is it costly to generate one for each chunk ?
            ql = QueryLauncher(self.settings, self.session)
            header_ttl = self._o_prefixes.get_sparql_prefixes(ttl_chunk)
            queryResults = ql.insert_data(ttl_chunk, self.graph_uri, header_ttl)
        except Exception as e:
            return self._format_exception(e)

        self.log.debug("Loading ttl chunk %s" % (chunk_count))
        self.log.debug("ttl = %s" % (ttl_chunk))

    def store_ttl_file(self, filepath):
        """Shortcut to store a complete file.
        
            Main differences with store_ttl : no chunk and no prefix management.
            filepath is not used, but needed to have the same signature."""
        # SLETORT: looks strange to name ttl_chunk when it use get_sparql_prefixes
        n_triple = None
        with open(filepath) as f:
            o_ql = QueryLauncher(self.settings, self.session)
            n_triples = o_ql.insert_data(f.read(), self.graph_uri, '')

        return n_triples
