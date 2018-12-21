#! /usr/bin/env python3

import os,sys,traceback
import re,shutil
from collections import defaultdict
from json.decoder import JSONDecodeError

from pyramid.view import view_config, view_defaults
from pyramid.response import FileResponse

import logging
from pprint import pformat
import textwrap
import datetime
import humanize

from pygments import highlight
from pygments.lexers import TurtleLexer
from pygments.formatters import HtmlFormatter

from askomics.libaskomics.ParamManager import ParamManager
from askomics.libaskomics.JobManager import JobManager
from askomics.libaskomics.EndpointManager import EndpointManager

from askomics.libaskomics.TripleStoreExplorer import TripleStoreExplorer
from askomics.libaskomics.TripleStoreInputManager import TripleStoreInputManager
from askomics.libaskomics.SourceFileConvertor import SourceFileConvertor

from askomics.libaskomics.rdfdb.SparqlQueryBuilder import SparqlQueryBuilder
from askomics.libaskomics.rdfdb.SparqlQueryGraph import SparqlQueryGraph
from askomics.libaskomics.rdfdb.SparqlQueryStats import SparqlQueryStats
from askomics.libaskomics.rdfdb.SparqlQueryAuth import SparqlQueryAuth

from askomics.libaskomics.rdfdb.QueryLauncher import QueryLauncher
from askomics.libaskomics.rdfdb.MultipleQueryLauncher import MultipleQueryLauncher
from askomics.libaskomics.rdfdb.FederationQueryLauncher import FederationQueryLauncher

from askomics.libaskomics.source_file.ExternalOntology import *
from askomics.libaskomics.source_file.SourceFile import SourceFile
from askomics.libaskomics.source_file.SourceFileURL import SourceFileURL

from askomics.libaskomics.GalaxyConnector import GalaxyConnector
from askomics.libaskomics.DatabaseConnector import DatabaseConnector


from pyramid.httpexceptions import (
    HTTPForbidden,
    HTTPFound,
    HTTPNotFound,
    exception_response
    )

from validate_email import validate_email

from askomics.libaskomics.Security import Security

@view_defaults(renderer='json', route_name='start_point')
class AskView(object):
    """ This class contains method calling the libaskomics functions using parameters from the js web interface (body variable) """

    def __init__(self, request):
        # Manage solution/data/error inside. This object is return to client side
        self.data = {}
        self.log = logging.getLogger(__name__)
        self.request = request
        self.settings = request.registry.settings

        try:

            if 'admin' not in self.request.session.keys():
                self.request.session['admin'] = False

            if 'blocked' not in self.request.session.keys():
                self.request.session['blocked'] = True

            if 'group' not in self.request.session.keys():
                self.request.session['group'] = ''

            if 'username' not in self.request.session.keys():
                self.request.session['username'] = ''

            if 'galaxy' not in self.request.session.keys():
                self.request.session['galaxy'] = False

        except Exception as e:
                traceback.print_exc(file=sys.stdout)
                self.data['error'] = str(e)
                self.log.error(str(e))

    def checkAuthSession(self):
        #https://fr.wikipedia.org/wiki/Liste_des_codes_HTTP

        # Denny access for non loged users
        if self.request.session['username'] == '':
            raise exception_response(401)

        # Denny for blocked users
        if self.request.session['blocked']:
            raise exception_response(423)


    def checkAdminSession(self):
        #Deny access for non admin session
        if not self.request.session['admin'] :
            raise exception_response(403)


    @view_config(route_name='start_point', request_method='GET')
    def start_points(self):
        """ Get the nodes being query starters """
        self.log.debug("== getting START POINT ==")

        try:

            sqb = SparqlQueryBuilder(self.settings, self.request.session)
            self.settings['graph'] = sqb.getGraphUser([])

            tse = TripleStoreExplorer(self.settings, self.request.session)
            nodes = tse.get_start_points()

            self.data['nodes'] = {}

            for node in nodes:
                if node['uri'] in self.data['nodes'].keys():
                    d_node = self.data['nodes'][node['uri']] # to ease reading
                    if node['public'] and not d_node['public']:
                        d_node['public'] = True
                    if node['private'] and not d_node['private']:
                        d_node['private'] = True
                    d_node['public_and_private'] = bool(
                        d_node['public'] and
                        d_node['private'])
                else:
                    self.data['nodes'][node['uri']] = node

            self.log.debug("== {} START POINTs retrieved ==".format( len(self.data['nodes']) ))

        except Exception as e:
            self.request.response.status = 400
            traceback.print_exc(file=sys.stdout)
            self.data['error'] = str(e)

        return self.data


    @view_config(route_name='statistics', request_method='GET')
    def statistics(self):
        """
        Get stats
        """
        self.checkAuthSession()

        self.log.debug('=== stats ===')

        self.data['username'] = self.request.session['username']

        sqs = SparqlQueryStats(self.settings, self.request.session)
        qlaucher  = QueryLauncher(self.settings, self.request.session)
        qmlaucher = MultipleQueryLauncher(self.settings, self.request.session)
        em = EndpointManager(self.settings, self.request.session)

        public_stats = {}
        private_stats = {}

        lEndp = em.list_endpoints()
        # Number of triples
        results_pub  = qmlaucher.process_query(sqs.get_number_of_triples('public'),lEndp)
        results_priv = qlaucher.process_query(sqs.get_number_of_triples('private'))

        public_stats['ntriples'] = results_pub[0]['number']
        private_stats['ntriples'] = results_priv[0]['number']

        # Number of entities
        results_pub  = qmlaucher.process_query(sqs.get_number_of_entities('public'),lEndp)
        results_priv = qlaucher.process_query(sqs.get_number_of_entities('private'))

        public_stats['nentities'] = results_pub[0]['number']
        private_stats['nentities'] = results_priv[0]['number']

        # Number of classes
        results_pub = qmlaucher.process_query(sqs.get_number_of_classes('public'),lEndp)
        results_priv = qlaucher.process_query(sqs.get_number_of_classes('private'))

        public_stats['nclasses'] = results_pub[0]['number']
        private_stats['nclasses'] = results_priv[0]['number']

        # Number of graphs
        results_pub = qmlaucher.process_query(sqs.get_number_of_subgraph('public'),lEndp)
        results_priv = qlaucher.process_query(sqs.get_number_of_subgraph('private'))

        public_stats['ngraphs'] = results_pub[0]['number']
        private_stats['ngraphs'] = results_priv[0]['number']

        # Graphs info
        results_pub = qmlaucher.process_query(sqs.get_subgraph_infos('public'),lEndp)
        results_priv = qlaucher.process_query(sqs.get_subgraph_infos('private'))

        public_stats['graphs'] = results_pub
        private_stats['graphs'] = results_priv

        # Classes and relations
        results_pub = qmlaucher.process_query(sqs.get_rel_of_classes('public'),lEndp)
        results_priv = qlaucher.process_query(sqs.get_rel_of_classes('private'))

        public_stats['class_rel'] = results_pub
        private_stats['class_rel'] = results_priv

        tmp = {}

        for result in results_pub:
            if result['domain'] not in tmp.keys():
                tmp[result['domain']] = []
            if result['relname'] not in tmp[result['domain']]:
                tmp[result['domain']].append({'relname': result['relname'], 'target': result['range']})
        public_stats['class_rel'] = tmp

        tmp = {}

        for result in results_priv:
            if result['domain'] not in tmp.keys():
                tmp[result['domain']] = []
            if result['relname'] not in tmp[result['domain']]:
                tmp[result['domain']].append({'relname': result['relname'], 'target': result['range']})
        private_stats['class_rel'] = tmp

        # class and attributes
        results_pub = qmlaucher.process_query(sqs.get_attr_of_classes('public'),lEndp)
        results_priv = qlaucher.process_query(sqs.get_attr_of_classes('private'))

        tmp = {}

        for result in results_pub:
            if result['class'] not in tmp.keys():
                tmp[result['class']] = []
            if result['attr'] not in tmp[result['class']]:
                tmp[result['class']].append(result['attr'])
        public_stats['class_attr'] = tmp

        tmp = {}

        for result in results_priv:
            if result['class'] not in tmp.keys():
                tmp[result['class']] = []
            if result['attr'] not in tmp[result['class']]:
                tmp[result['class']].append(result['attr'])
        private_stats['class_attr'] = tmp

        self.data['public'] = public_stats
        self.data['private'] = private_stats

        return self.data

    @view_config(route_name='empty_user_database', request_method='GET')
    def empty_database(self):
        """
        Delete all named graphs and their metadatas
        """

        self.checkAuthSession()

        self.log.debug("=== DELETE ALL NAMED GRAPHS ===")

        try:
            sqb = SparqlQueryBuilder(self.settings, self.request.session)
            ql = QueryLauncher(self.settings, self.request.session)

            named_graphs = self.list_user_graph()

            for graph in named_graphs:

                self.log.debug("--- DELETE GRAPH : %s", graph['g'])
                ql.process_query(sqb.get_drop_named_graph(graph['g']))
                #delete metadatas
                ql.process_query(sqb.get_delete_metadatas_of_graph(graph['g']))

        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            self.data['error'] = str(e)
            self.request.response.status = 400

        return self.data

    @view_config(route_name='delete_graph', request_method='POST')
    def delete_graph(self):
        """

        """

        self.checkAuthSession()

        sqb = SparqlQueryBuilder(self.settings, self.request.session)
        ql = QueryLauncher(self.settings, self.request.session)

        graphs = self.request.json_body['named_graph']

        #TODO: check if the graph belong to user

        for graph in graphs:
            self.log.debug("--- DELETE GRAPH : %s", graph)
            ql.process_query(sqb.get_drop_named_graph(graph),parseResults=False)
            #delete metadatas
            ql.process_query(sqb.get_delete_metadatas_of_graph(graph),parseResults=False)


    @view_config(route_name='delete_endpoints_ext', request_method='POST')
    def delete_endpoints_ext(self):
        # sletort: it's the exact copy of delete_endpoints
        import pyramid.httpexceptions as exc
        """

        """
        self.data = {}

        self.checkAuthSession()

        if 'id_endpoints' not in self.request.json_body:
            self.data['error'] = 'Devel : id_endpoints value is not defined !'
            self.request.response.status = 400
            return self.data

        endpoints = self.request.json_body['id_endpoints']

        em = EndpointManager(self.settings, self.request.session)

        for url in endpoints:
            em.remove(url)
        ##raise ValueError("ok")

    @view_config(route_name='inspect_endpoint_ext', request_method='POST', renderer='json')
    def inspect_endpoint_ext(self):
        self.checkAuthSession()

        try:
            self.log.debug( "inspect_endpoint_ext\n" + str(self.request.json_body) )
        except JSONDecodeError:
            return {}

        name = self.request.json_body['name']
        uri  = self.request.json_body['url']
        em   = ExternalEndpoint(self.settings, self.request.session, uri)

        # return a list of dict { 'ont':x, 'owl':x, 'count':x }
        #   it is the number of owl class per ontology
        ld_counts = em.inspect()

        # usually 1 ont will have 3 owl+count, I group them
        d_ontologies = defaultdict(dict)
        for d_count in ld_counts:
            ont,owl,cnt = [ d_count[k] for k in ('ont','owl','count')]
            owl = owl.replace("http://www.w3.org/2002/07/owl#","") #remove owl prefix.
            d_ontologies[ont][owl] = cnt

        return {
                'name': name,
                'uri' : uri,
                'onto': d_ontologies,
            }

    @view_config(route_name='integrate_endpoint_ext', request_method='POST')
    def integrate_endpoint_ext(self):
        # SLETORT: Note : For SourceFile, everything is in the method persist.
        # SLETORT:  This upset me, the scheme should be the same.
        self.checkAuthSession()
        d_endpoints = self.request.json_body
        self.log.debug( d_endpoints )

        # param used to save abstractions
        urlbase = self.request.host_url # SLETORT: I don't know this param, is it linked to asko deployement ? (which could mean not a param !)
        public  = True # epx are always public
        o_tim = TripleStoreInputManager.create_tim( self.settings, self.request.session,
                                                    public, urlbase )

        for epx_name in d_endpoints:
            # EPx - save in DB
            url = d_endpoints[epx_name]['uri']
            o_epx = ExternalEndpoint(self.settings, self.request.session, url)
            o_tim.store_ttl( o_epx.abstraction() )
            self.log.debug("External endpoint <{}> has been recorded".format(url))

            # Ontologies - store prefix and create/save abstraction in triple store
            ld_onto = d_endpoints[epx_name]['onto']
            for d_onto in ld_onto:
                uri    = d_onto['name']
                prefix = d_onto['prefix']

                # Abstractions
                o_onto = o_epx.create_ontology( {uri:prefix} )
                self.log.debug("Inserting ttl abstraction for {}.".format(uri))
                o_tim.store_ttl( o_onto.abstraction() )
                o_tim.insert_metadata(url)
    # integrate_endpoint_ext

    @view_config(route_name='delete_endpoints', request_method='POST')
    def delete_endpoints(self):
        """

        """
        self.data = {}

        self.checkAuthSession()

        if 'id_endpoints' not in self.request.json_body:
            self.data['error'] = 'Devel : id_endpoints value is not defined !'
            self.request.response.status = 400
            return self.data

        endpoints = self.request.json_body['id_endpoints']

        em = EndpointManager(self.settings, self.request.session)

        for url in endpoints:
            em.remove_endpoint(url)
        ##raise ValueError("ok")

    @view_config(route_name='add_endpoint', request_method='POST')
    def add_endpoint(self):
        """

        """

        self.checkAuthSession()

        if 'name' not in self.request.json_body:
            raise exception_response(404)
        if 'url' not in self.request.json_body:
            raise exception_response(404)
        if 'auth' not in self.request.json_body:
            raise exception_response(404)

        name = self.request.json_body['name']
        url = self.request.json_body['url']
        auth = self.request.json_body['auth']

        em = EndpointManager(self.settings, self.request.session)
        em.save_endpoint(name,url,auth,True)

    @view_config(route_name='enable_endpoints', request_method='POST')
    def enable_endpoints(self):
        """

        """

        self.checkAuthSession()

        if 'id' not in self.request.json_body:
           raise exception_response(404)
        if 'enable' not in self.request.json_body:
           raise exception_response(404)

        id = self.request.json_body['id']
        enable = self.request.json_body['enable']

        em = EndpointManager(self.settings, self.request.session)

        if enable:
           em.enable(id)
        else:
           em.disable(id,"")


    @view_config(route_name='list_user_graph', request_method='GET')
    def list_user_graph(self):
        """
        Return a list with all the named graphs of a user.
        """

        self.checkAuthSession()

        sqg = SparqlQueryGraph(self.settings, self.request.session)
        query_launcher = QueryLauncher(self.settings, self.request.session)

        res = query_launcher.process_query(sqg.get_user_graph_infos_with_count())

        named_graphs = []

        for index_result in range(len(res)):
            if not 'date' in res[index_result]:
                self.log.warn('============= bad results user graph =================')
                self.log.warn(res[index_result])
                self.log.warn("============================================================")
                continue

            dat = datetime.datetime.strptime(res[index_result]['date'], "%Y-%m-%dT%H:%M:%S.%f")

            readable_date = dat.strftime("%d/%m/%Y %H:%M:%S") #dd/mm/YYYY hh:ii:ss
            endpt = ''

            if 'endpoint' in res[index_result].keys():
                endpt = res[index_result]['endpoint'],

            named_graphs.append({
                'endpoint' : endpt,
                'g': res[index_result]['g'],
                'name': res[index_result]['name'],
                'count': res[index_result]['co'],
                'date': res[index_result]['date'],
                'readable_date': readable_date,
                'access': res[index_result]['access'],
                'owner': res[index_result]['owner'],
                'access_bool': bool(res[index_result]['access'] == 'public')
            })

        return named_graphs

    @view_config(route_name='list_endpoints', request_method='GET')
    def list_endpoints(self):
        """
        Return a list with all endpoint using by a askomics session.
        """

        session = {}
        try:
            em = EndpointManager(self.settings, self.request.session)
            session['askomics'] = em.list_endpoints()

            sqb = SparqlQueryBuilder(self.settings, self.request.session)
            session['external'] = sqb.getExternalServiceEndpoint()
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            self.data['error'] = str(e)

        return session


    @view_config(route_name='guess_csv_header_type', request_method='POST')
    def guess_csv_header_type(self):
        """Guess the headers type of a csv file

        Used for the asko-cli scripts

        :returns: list of guessed types
        :rtype: dict
        """

        self.checkAuthSession()

        body = self.request.json_body
        filename = body['filename']

        sfc = SourceFileConvertor(self.settings, self.request.session)
        source_file = sfc.get_source_files([filename])[0]
        headers = source_file.headers
        preview = source_file.get_preview_data()

        guessed_types = []


        for index_header in range(0, len(headers)):
            guessed_types.append(source_file.guess_values_type(preview[index_header], headers[index_header]))

        self.data['types'] = guessed_types

        self.log.debug(self.data)
        return self.data




    @view_config(route_name='source_files_overview', request_method='POST')
    def source_files_overview(self):
        """
        Get preview data for all the available files
        """
        self.checkAuthSession()

        files_to_integrate = self.request.json_body

        self.log.debug(" ========= Askview:source_files_overview =============")
        try:
            sfc = SourceFileConvertor(self.settings, self.request.session)
            source_files = sfc.get_source_files(files_to_integrate)
            self.data['files'] = []

            # get all taxon in the TS
            sqg = SparqlQueryGraph(self.settings, self.request.session)
            ql = MultipleQueryLauncher(self.settings, self.request.session)
            em = EndpointManager(self.settings, self.request.session)
            res = ql.process_query(sqg.get_all_taxons(),em.list_endpoints())
            taxons_list = []
            for elem in res:
                taxons_list.append(elem['taxon'])
            self.data['taxons'] = taxons_list

            for src_file in source_files:
                # Process only selected files
                if src_file.name not in files_to_integrate:
                    continue
                infos = {}
                infos['name'] = src_file.name
                infos['type'] = src_file.type
                if src_file.type == 'tsv':
                    try:
                        infos['headers'] = src_file.get_headers_by_file
                        infos['preview_data'] = src_file.get_preview_data()
                        infos['column_types'] = []
                        header_num = 1
                        infos['column_types'].append('entity_start')
                        for ih in range(1, len(infos['headers'])):
                            #if infos['headers'][ih].find("@")>0:
                            #    infos['column_types'].append("entity")
                            #else:
                            infos['column_types'].append(src_file.guess_values_type(infos['preview_data'][ih], infos['headers'][header_num]))
                            header_num += 1
                    except Exception as e:
                        traceback.print_exc(file=sys.stdout)
                        infos['error'] = 'Could not read input file, are you sure it is a valid tabular file?'
                        self.log.error(str(e))

                    self.data['files'].append(infos)
                elif src_file.type == 'gff':
                    try:
                        entities = src_file.get_entities()
                        infos['entities'] = entities
                    except Exception as e:
                        self.log.debug('error !!')
                        traceback.print_exc(file=sys.stdout)
                        infos['error'] = 'Can not parse the file GFF File :'+ str(e)
                        self.log.error('error with gff examiner: ' + str(e))

                    self.data['files'].append(infos)

                elif src_file.type == 'ttl':
                    infos['preview'] = src_file.get_preview_ttl()
                    self.data['files'].append(infos)

                elif src_file.type == 'bed':
                    try:
                        src_file.open_bed
                        infos['test'] = 'OK'
                    except Exception as e:
                        self.log.error(str(e))
                        infos['error'] = 'Could not read input file, are you sure it is a valid BED file ?'
                    self.data['files'].append(infos)
        except Exception as e:
             traceback.print_exc(file=sys.stdout)
             self.data['error'] = str(e)
             self.request.response.status = 400

        return self.data


    @view_config(route_name='prefix_uri', request_method='POST')
    def prefix_uri(self):
        """
        get prefix uri for each entities finded in he header file
        """

        try:
            body = self.request.json_body
            tse = TripleStoreExplorer(self.settings, self.request.session)
            self.data = tse.get_prefix_uri()
            self.data['__default__'] = tse.get_param("askomics.prefix")
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            self.data['error'] = str(e)
            self.request.response.status = 400

        return self.data

    @view_config(route_name='preview_ttl', request_method='POST')
    def preview_ttl(self):
        """
        Convert tabulated files to turtle according to the type of the columns set by the user
        """

        self.checkAuthSession()

        self.log.debug("preview_ttl")
        try:
            body = self.request.json_body
            file_name = body["file_name"]
            col_types = body["col_types"]
            disabled_columns = body["disabled_columns"]
            key_columns = body["key_columns"]
            uris = None
            if 'uris' in body:
                uris = body['uris']

            sfc = SourceFileConvertor(self.settings, self.request.session)

            src_file = sfc.get_source_files([ file_name ], uri_set=uris)[0]
            src_file.set_forced_column_types(col_types)
            src_file.set_disabled_columns(disabled_columns)
            src_file.set_key_columns(key_columns)

            cont_ttl = '\n'.join(src_file.get_turtle(preview_only=True))
            prefixes = sfc.o_prefixes.get_turtle_prefixes(cont_ttl)
            self.data = textwrap.dedent(
            """
            {header}

            #############
            #  Content  #
            #############

            {content_ttl}

            #################
            #  Abstraction  #
            #################

            {abstraction_ttl}

            ######################
            #  Domain knowledge  #
            ######################

            {domain_knowledge_ttl}
            """).format(header=prefixes,
                    content_ttl = cont_ttl,
                    abstraction_ttl = src_file.get_abstraction(),
                    domain_knowledge_ttl = src_file.get_domain_knowledge()
                    )
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            self.data['error'] = str(e)
            self.request.response.status = 400

        formatter = HtmlFormatter(cssclass='preview_field', nowrap=True, nobackground=True)
        return highlight(self.data, TurtleLexer(), formatter) # Formated html

    @view_config(route_name='load_data_into_graph', request_method='POST')
    def load_data_into_graph(self):
        """
        Load tabulated files to triple store according to the type of the columns set by the user
        """

        self.checkAuthSession()

        body = self.request.json_body
        file_name = body["file_name"]
        col_types = body["col_types"]
        disabled_columns = body["disabled_columns"]
        key_columns = body["key_columns"]
        public = body['public']
        headers = body['headers']
        uris = None
        if 'uris' in body:
            uris = body['uris']

        forced_type = None
        if 'forced_type' in body:
            forced_type = body['forced_type']

        # Allow data integration in public graph only if user is an admin
        if public and not self.request.session['admin']:
            raise ValueError("Can not load public data with a non admin account !")

        sfc = SourceFileConvertor(self.settings, self.request.session)
        src_file = sfc.get_source_files([file_name], forced_type, uri_set=uris)[0]
        src_file.set_headers(headers)
        src_file.set_forced_column_types(col_types)
        src_file.set_disabled_columns(disabled_columns)
        src_file.set_key_columns(key_columns)

        return src_file.persist(self.request.host_url, public)

    @view_config(route_name='load_remote_data_into_graph', request_method='POST')
    def load_remote_data_into_graph(self):
        """
        Load tabulated files to triple store according to the type of the columns set by the user
        """

        self.checkAuthSession()

        body = self.request.json_body
        public = None

        if 'public' in body:
            public = body['public']
        else:
            raise ValueError("Dev error: Can not find 'public' POST value.")

        url = None
        if 'url' in body:
            url = body['url']
        else:
            raise ValueError("Dev error: Can not find 'uri' POST value.")

        # Allow data integration in public graph only if user is an admin
        if public and not self.request.session['admin']:
            raise ValueError("Can not import public data with a non admin account !")

        src_file = SourceFileURL(self.settings, self.request.session, url)
        return src_file.persist(url, public)

    @view_config(route_name='load_gff_into_graph', request_method='POST')
    def load_gff_into_graph(self):
        """
        Load GFF file into the triplestore
        """

        self.checkAuthSession()

        self.log.debug("== load_gff_into_graph ==")

        body = self.request.json_body
        file_name = body['file_name']
        taxon = body['taxon']
        entities = body['entities']
        public = body['public']
        uri = None
        if 'uri' in body:
            uri = body['uri']

        forced_type = None
        if 'forced_type' in body:
            forced_type = body['forced_type']

        # Allow data integration in public graph only if user is an admin
        if public and not self.request.session['admin']:
            raise ValueError("Cannot import public gff with a non admin account !")

        sfc = SourceFileConvertor(self.settings, self.request.session)
        src_file_gff = sfc.get_source_files([file_name], forced_type, uri_set={0: uri})[0]
        src_file_gff.set_taxon(taxon)
        src_file_gff.set_entities(entities)

        return src_file_gff.persist(self.request.host_url, public)

    @view_config(route_name='load_ttl_into_graph', request_method='POST')
    def load_ttl_into_graph(self):
        """
        Load TTL file into the triplestore
        """

        self.checkAuthSession()

        self.log.debug('*** load_ttl_into_graph ***')

        body = self.request.json_body
        file_name = body['file_name']
        public = body['public']

        forced_type = None
        if 'forced_type' in body:
            forced_type = body['forced_type']
        # Allow data integration in public graph only if user is an admin
        if public and not self.request.session['admin']:
            raise ValueError("Can not import public turtle file with a non admin account !")

        sfc = SourceFileConvertor(self.settings, self.request.session)
        src_file_ttl = sfc.get_source_files([file_name], forced_type)[0]

        return src_file_ttl.persist(self.request.host_url, public)

    @view_config(route_name='load_bed_into_graph', request_method='POST')
    def load_bed_into_graph(self):
        """
        Load a BED file into the triplestore
        """

        self.checkAuthSession()

        body = self.request.json_body

        file_name = body['file_name']
        taxon  = body['taxon']
        entity = body['entity_name']
        public = body['public']
        uri = None
        if 'uri' in body:
            uri = body['uri']

        forced_type = None
        if 'forced_type' in body:
            forced_type = body['forced_type']

        # Allow data integration in public graph only if user is an admin
        if public and not self.request.session['admin']:
            raise ValueError("Cannot import public BED file with a non admin account !")

        sfc = SourceFileConvertor(self.settings, self.request.session)
        src_file_bed = sfc.get_source_files([file_name], forced_type, uri_set={0: uri})[0]

        src_file_bed.set_taxon(taxon)
        src_file_bed.set_entity_name(entity)

        return src_file_bed.persist(self.request.host_url, public)

    @view_config(route_name='getUserAbstraction', request_method='POST')
    def getUserAbstraction(self):

        """ Get the user asbtraction to manage relation inside javascript """
        self.log.debug("== getUserAbstraction ==")

        tse = TripleStoreExplorer(self.settings, self.request.session)
        self.data.update(tse.getUserAbstraction())
        return self.data

    # TODO : this method is too generic. The build of RDF Shortucts should be here to avoid injection with bad intention...

    @view_config(route_name='importShortcut', request_method='POST')
    def importShortcut(self):
        """
        Import a shortcut definition into the triplestore
        """
        self.checkAuthSession()
        self.checkAdminSession()

        self.log.debug('*** importShortcut ***')

        body = self.request.json_body
        sqb = SparqlQueryBuilder(self.settings, self.request.session)
        ql = QueryLauncher(self.settings, self.request.session)
        query = sqb.add_prefix_headers(body["prefix"])

        try:
            query += "\n"
            ql.insert_data(body["shortcut_def"],'askomics:graph:shortcut',query);
        except Exception as e:
            #exc_type, exc_value, exc_traceback = sys.exc_info()
            #traceback.print_exc(limit=8)
            traceback.print_exc(file=sys.stdout)
            self.data['error'] = str(e)
            self.request.response.status = 400

        return self.data

    @view_config(route_name='deleteShortcut', request_method='POST')
    def deleteShortcut(self):
        """
        Delete a shortcut definition into the triplestore
        """
        self.checkAuthSession()
        self.checkAdminSession()

        self.log.debug('*** importShortcut ***')

        body = self.request.json_body
        sqb = SparqlQueryBuilder(self.settings, self.request.session)
        ql = QueryLauncher(self.settings, self.request.session)

        try:
            query_string  = "DELETE {\n"
            query_string += "\tGRAPH "+ "<askomics:graph:shortcut>" +"\n"
            query_string += "\t\t{\n"
            query_string += "<"+body["shortcut"]+">" + " ?r ?a.\n"
            query_string += "\t\t}\n"
            query_string += "\t}\n"
            query_string += "WHERE{\n"
            query_string += "<"+body["shortcut"]+">" + " ?r ?a.\n"
            query_string += "\t}\n"
            query = sqb.add_prefix_headers(query_string)
            res = ql.process_query(query)
        except Exception as e:
            #exc_type, exc_value, exc_traceback = sys.exc_info()
            #traceback.print_exc(limit=8)
            traceback.print_exc(file=sys.stdout)
            self.data['error'] = str(e)
            self.request.response.status = 400

        return self.data

    @view_config(route_name='sparqlquery', request_method='POST')
    def get_value(self):
        """ Build a request from a json whith the following contents :variates,constraintesRelations"""

        body = self.request.json_body

        persist = False
        if 'jobManager' in body :
            if body['jobManager']:
                persist = True

        jobid = -1

        try:
            if persist:
                jm = JobManager(self.settings, self.request.session)
                rg = ""
                if 'requestGraph' in body:
                    rg = body['requestGraph']
                jobid = jm.save_query_job(rg, body['variates'])


            typeRequest = ''
            tse = TripleStoreExplorer(self.settings, self.request.session)
            variates = []

            if 'variates' in body:
                if type(body["variates"])==dict:
                    [ variates.extend(listValues) for k,listValues in body["variates"].items()]
                elif type(body["variates"])==list:
                    variates = body["variates"]

            if len(variates)<= 0 :
                raise ValueError("No sparql variable was found !")
            results, query, typeRequest = tse.build_sparql_query_from_json(
                                                 body["endpoints"],
                                                 body["type_endpoints"],
                                                 body["graphs"],
                                                 variates,
                                                 body["constraintesRelations"],
                                                 True)
            # Remove prefixes in the results table
            limit = int(body["limit"]) + 1
            if body["limit"] != -1 and limit < len(results):
                self.data['values'] = results[1:limit+1]
            else:
                self.data['values'] = results

            self.data['nrow'] = len(results)

            # Provide results file
            if (not 'nofile' in body) or not body['nofile']:
                query_laucher = QueryLauncher(self.settings, self.request.session)
                self.data['file'] = query_laucher.format_results_csv(results)

            if persist:
                npreview = 30
                if "limit" in body:
                    npreview = body["limit"]

                jm.done_query_job(jobid, len(results), self.data['values'][0:npreview], self.data['file'])

        except Exception as e:
            #exc_type, exc_value, exc_traceback = sys.exc_info()
            #traceback.print_exc(limit=8)
            traceback.print_exc(file=sys.stdout)
            self.data['values'] = ""
            self.data['file'] = ""

            if persist:
                jm.done_query_job(jobid, None, None, None)
                jm.set_error_message('query', str(e), jobid)

        self.data['galaxy'] = self.request.session['galaxy']

        return self.data

    @view_config(route_name='listjob', request_method='GET')
    def listjob(self):
        ''' Get all jobs recorded in database '''

        maxrows = self.settings['askomics.triplestore_results_max_rows'] if 'askomics.triplestore_results_max_rows' in self.settings else None

        jm = JobManager(self.settings, self.request.session)
        integration_jobs = jm.list_integration_jobs()
        query_jobs = jm.list_query_jobs()

        return {'maxrows': maxrows, 'integration': integration_jobs, 'query': query_jobs}


    @view_config(route_name='deljob', request_method='POST')
    def deljob(self):
        ''' Remove job from database '''

        body = self.request.json_body

        jm = JobManager(self.settings, self.request.session)
        jm.remove_job(body['table'], body['jobid'])


    @view_config(route_name='getSparqlQueryInTextFormat', request_method='POST')
    def getSparqlQueryInTextFormat(self):
        """ Build a request from a json whith the following contents :variates,constraintesRelations"""
        self.log.debug("== Attribute Value ==")

        try:
            tse = TripleStoreExplorer(self.settings, self.request.session)

            body = self.request.json_body
            lfrom = []
            if 'from' in body:
                lfrom = body['from']

            typeRequest = ''
            endp = []
            typeEnd = []
            variates = []
            [ variates.extend(listValues) for k,listValues in body["variates"].items()]
            results,query, typeRequest = tse.build_sparql_query_from_json(endp,typeEnd,lfrom,variates,body["constraintesRelations"],-1,send_request_to_tps=False)

            self.data['query'] = query
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            self.data['error'] = str(e)
            self.request.response.status = 400

        return self.data

    @view_config(route_name='ttl', request_method='GET')
    def uploadTtl(self):
        param_manager = ParamManager(self.settings, self.request.session)

        splited = os.path.split(self.request.matchdict['name'])
        username = splited[0]
        filename = splited[1]
        rdf_path = param_manager.get_directory('rdf', force_username=username)

        path_url = rdf_path + filename

        response = FileResponse(path_url, content_type='text/turtle')
        return response

    @view_config(route_name='csv', request_method='GET')
    def uploadCsv(self):

        pm = ParamManager(self.settings, self.request.session)
        response = FileResponse(
            pm.get_user_csv_directory()+self.request.matchdict['name'],
            content_type='text/csv'
            )
        return response


    @view_config(route_name='del_csv', request_method='GET')
    def deletCsv(self):

        pm = ParamManager(self.settings, self.request.session)
        try:
            os.remove(pm.get_user_csv_directory()+self.request.matchdict['name']),
        except Exception as e:
            self.log.warn(str(e))


    @view_config(route_name='signup', request_method='POST')
    def signup(self):
        body = self.request.json_body
        username = body['username']
        email = body['email']
        password = body['password']
        password2 = body['password2']

        self.log.debug('==== user info ====')
        self.log.debug('username: ' + username)
        self.log.debug('email: ' + email)



        try:
            security = Security(self.settings, self.request.session, username, email, password, password2)

            is_valid_email = security.check_email()
            are_passwords_identical = security.check_passwords()
            is_pw_enough_longer = security.check_password_length()
            is_username_already_exist = security.check_username_in_database()
            is_email_already_exist = security.check_email_in_database()

            self.data['error'] = []
            error = False

            if not is_valid_email:
                self.data['error'].append('Email is not valid')
                error = True

            if not are_passwords_identical:
                self.data['error'].append('Passwords are not identical')
                error = True

            if not is_pw_enough_longer:
                self.data['error'].append('Password must be at least 8 characters')
                error = True

            if is_username_already_exist:
                self.data['error'].append('Username already exist')
                error = True

            if is_email_already_exist:
                self.data['error'].append('Email already exist')
                error = True

            if error:
                return self.data

            self.data['error'] = []

            security.persist_user(self.request.host_url)
            security.create_user_graph()
            security.log_user(self.request)

            self.data['username'] = username
            admin_blocked = security.get_admin_blocked_by_username()
            self.data['admin'] = admin_blocked['admin']
            self.data['blocked'] = admin_blocked['blocked']
            self.data['galaxy'] = security.check_galaxy()
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            self.data['error'] = "Bad server configuration!"
            self.request.response.status = 400

        return self.data

    @view_config(route_name='checkuser', request_method='GET')
    def checkuser(self):

        if self.request.session['username'] != '':
            # User connected, get admin and blocked status
            security = Security(self.settings, self.request.session, self.request.session['username'], '', '', '')
            admin_blocked_status = security.get_admin_blocked_by_username()
            self.request.session['admin'] = admin_blocked_status['admin']
            self.request.session['blocked'] = admin_blocked_status['blocked']

        self.data['username'] = self.request.session['username']
        self.data['admin'] = self.request.session['admin']
        self.data['blocked'] = self.request.session['blocked']
        self.data['galaxy'] = self.request.session['galaxy']

        return self.data

    @view_config(route_name='nbUsers', request_method='GET')
    def nbUsers(self):

        self.data = {}

        sqa = SparqlQueryAuth(self.settings, self.request.session)
        ql = QueryLauncher(self.settings, self.request.session)

        try:

            self.data['count'] =  0
            res = ql.process_query(sqa.get_number_of_users())
            if len(res)>0 and 'count' in res[0]:
                self.data['count'] = res[0]['count']

        except Exception as e:
            self.data['error'] = str(e)
            self.log.error(str(e))

        return self.data


    @view_config(route_name='logout', request_method='GET')
    def logout(self):
        """
        Log out the user, reset the session
        """

        self.request.session['username'] = ''
        self.request.session['admin'] = ''
        self.request.session['graph'] = ''
        self.request.session['galaxy'] = False
        self.request.session = {}

        return

    @view_config(route_name='login', request_method='POST')
    def login(self):

        body = self.request.json_body
        username_email = body['username_email']
        password = body['password']
        username = ''
        email = ''

        self.data['error'] = []

        if validate_email(username_email):
            email = username_email
            auth_type = 'email'
        else:
            username = username_email
            auth_type = 'username'

        security = Security(self.settings, self.request.session, username, email, password, password)

        if auth_type == 'email':
            email_in_ts = security.check_email_in_database()

            if not email_in_ts:
                self.data['error'].append('email is not registered')
                return self.data

            password_is_correct = security.check_email_password()

            if not password_is_correct:
                self.data['error'].append('Password is incorrect')
                return self.data

            # Set username
            security.set_username_by_email()

            # Get the admin and blocked status
            admin_blocked = security.get_admin_blocked_by_email()
            security.set_admin(admin_blocked['admin'])
            security.set_blocked(admin_blocked['blocked'])


        elif auth_type == 'username':
            username_in_ts = security.check_username_in_database()

            if not username_in_ts:
                self.data['error'].append('username is not registered')
                return self.data

            # Get the admin and blocked status
            admin_blocked = security.get_admin_blocked_by_username()
            security.set_admin(admin_blocked['admin'])
            security.set_blocked(admin_blocked['blocked'])

            # Get if user has a connected Galaxy account
            galaxy = security.check_galaxy()
            security.set_galaxy(galaxy)

            password_is_correct = security.check_username_password()

            if not password_is_correct:
                self.data['error'].append('Password is incorrect')
                return self.data

        # User pass the authentication, log him
        try:
            security.log_user(self.request)
            self.data['username'] = username
            self.data['admin'] = admin_blocked['admin']
            self.data['blocked'] = admin_blocked['blocked']
            self.data['galaxy'] = self.request.session['galaxy']

        except Exception as e:
            self.data['error'] = str(e)
            self.request.response.status = 400
            return self.data

        param_manager = ParamManager(self.settings, self.request.session)
        param_manager.get_upload_directory()

        return self.data

    @view_config(route_name='api_key', request_method='POST')
    def api_key(self):

        self.checkAuthSession()

        body = self.request.json_body
        self.log.debug(body)
        username = body['username']
        keyname = body['keyname']

        security = Security(self.settings, self.request.session, username, '', '', '')

        try:
            security.add_apikey(keyname)
            # query_laucher.process_query(sqa.add_apikey(username, keyname))
        except Exception as e:
            self.log.debug(str(e))
            self.data['error'] = str(e)
            self.request.response.status = 400
            return self.data

        self.data['sucess'] = 'success'
        return self.data

    @view_config(route_name='renew_apikey', request_method='GET')
    def renew_apikey(self):

        self.checkAuthSession()

        security = Security(self.settings, self.request.session, self.request.session['username'], '', '', '')
        security.renew_apikey()

    @view_config(route_name='connect_galaxy', request_method='POST')
    def connect_galaxy(self):

        self.checkAuthSession()

        body = self.request.json_body
        url = body['url']
        key = body['key']

        security = Security(self.settings, self.request.session, self.request.session['username'], '', '', '')


        # Check if a galaxy is already registred
        if security.check_galaxy():
            security.delete_galaxy()
            self.request.session['galaxy'] = False

        # If url or apikey are empty, do nothing (only deletion)
        if not url or not key:
            self.data['success'] = 'deleted'
            return self.data

        # Insert the new Galaxy
        try:
            security.add_galaxy(url, key)
            self.request.session['galaxy'] = True
        except Exception as e:

            self.data['error'] = 'Connection to Galaxy failed'
            return self.data

        self.data['success'] = 'inserted'

        return self.data

    @view_config(route_name='login_api_gie', request_method='GET')
    def login_api_gie(self):

        apikey = self.request.GET['key']

        self.data['error'] = ''

        security = Security(self.settings, self.request.session, '', '', '', '')

        # Check if API key exist, and if yes, get the user
        security.get_owner_of_apikey(apikey)

        if not security.get_username():
            self.data['error'] = 'API key belong to nobody'
            return self.data

        # Get the admin and blocked status
        admin_blocked = security.get_admin_blocked_by_username()
        security.set_admin(admin_blocked['admin'])
        security.set_blocked(admin_blocked['blocked'])
        # Get if user has a connected Galaxy account
        galaxy = security.check_galaxy()
        security.set_galaxy(galaxy)

        # Log the user
        try:
            security.log_user(self.request)
            self.data['username'] = security.get_username()
            self.data['admin'] = admin_blocked['admin']
            self.data['blocked'] = admin_blocked['blocked']

        except Exception as e:
            self.data['error'] = str(e)
            self.log.error(str(e))
            return self.data

        param_manager = ParamManager(self.settings, self.request.session)
        param_manager.get_upload_directory()

        if self.request.application_url.endswith('/'):
            return HTTPFound(self.request.application_url)

        return HTTPFound(self.request.application_url + '/')


    @view_config(route_name='login_api', request_method='POST')
    def login_api(self):

        body = self.request.json_body
        apikey = body['apikey']

        self.data['error'] = ''

        security = Security(self.settings, self.request.session, '', '', '', '')

        # Check if API key exist, and if yes, get the user
        security.get_owner_of_apikey(apikey)

        if not security.get_username():
            self.data['error'] = 'API key belong to nobody'
            return self.data

        # Get the admin and blocked status
        admin_blocked = security.get_admin_blocked_by_username()
        security.set_admin(admin_blocked['admin'])
        security.set_blocked(admin_blocked['blocked'])
        # Get if user has a connected Galaxy account
        galaxy = security.check_galaxy()
        security.set_galaxy(galaxy)

        # Log the user
        try:
            security.log_user(self.request)
            self.data['username'] = security.get_username()
            self.data['admin'] = admin_blocked['admin']
            self.data['blocked'] = admin_blocked['blocked']

        except Exception as e:
            self.data['error'] = str(e)
            self.log.error(str(e))
            self.request.response.status = 400
            return self.data

        param_manager = ParamManager(self.settings, self.request.session)
        param_manager.get_upload_directory()

        return self.data


    @view_config(route_name='get_users_infos', request_method='GET')
    def get_users_infos(self):
        """
        For each users store in the triplesore, get their username, email,
        and admin status
        """

        self.checkAuthSession()
        self.checkAdminSession()

        security = Security(self.settings, self.request.session, self.request.session['username'], '', '', '')
        infos = security.get_users_infos()

        self.data['result'] = infos
        self.data['me'] = self.request.session['username']

        return self.data

    @view_config(route_name='lockUser', request_method='POST')
    def lock_user(self):
        """
        Change a user lock status
        """

        self.checkAuthSession()
        self.checkAdminSession()

        body = self.request.json_body

        self.data = {}

        username = body['username']
        new_status = body['lock']

        # Convert bool to string for the database
        if new_status:
            new_status = 'true'
        else:
            new_status = 'false'

        try:
            security = Security(self.settings, self.request.session, self.request.session['username'], '', '', '')
            security.lock_user(new_status, username)
        except Exception as e:
            self.data['error'] = str(e)
            self.log.error(str(e))
            self.request.response.status = 400
            return self.data


        return 'success'

    @view_config(route_name='setAdmin', request_method='POST')
    def set_admin(self):
        """
        Change a user admin status
        """

        self.checkAuthSession()
        self.checkAdminSession()

        body = self.request.json_body

        username = body['username']
        new_status = body['admin']

        # Convert bool to string for the database
        if new_status:
            new_status = 'true'
        else:
            new_status = 'false'

        try:
            security = Security(self.settings, self.request.session, self.request.session['username'], '', '', '')
            security.admin_user(new_status, username)
        except Exception as e:
            self.data['error'] = str(e)
            self.log.error(str(e))
            self.request.response.status = 400
            return self.data


        return 'success'


    @view_config(route_name='delete_user', request_method='POST')
    def delete_user(self):
        """
        Delete a user from the user graphs, and remove all his data
        """

        self.checkAuthSession()

        body = self.request.json_body

        username = body['username']
        passwd = body['passwd']
        confirmation = body['passwd_conf']

        # Non admin can only delete himself
        if self.request.session['username'] != username and not self.request.session['admin']:
            raise Exception('forbidden')

        # If confirmation, check the user passwd
        if confirmation:
            security = Security(self.settings, self.request.session, username, '', passwd, passwd)
            if not security.check_username_password():
                self.data['error'] = 'Wrong password'
                self.request.response.status = 400
                return self.data

        security = Security(self.settings, self.request.session, self.request.session['username'], '', '', '')
        sqb = SparqlQueryBuilder(self.settings, self.request.session)
        query_laucher = QueryLauncher(self.settings, self.request.session)

        # Get all graph of a user
        res = query_laucher.process_query(sqb.get_graph_of_user(username))

        list_graph = []
        for graph in res:
            list_graph.append(graph['g'])

        # Drop all this graph
        for graph in list_graph:
            try:
                query_laucher.process_query(sqb.get_drop_named_graph(graph))
                query_laucher.process_query(sqb.get_delete_metadatas_of_graph(graph))
            except Exception as e:
                self.data['error'] = str(e)
                self.log.error(str(e))
                self.request.response.status = 400
                return self.data


        # Delete user infos
        try:
            security.delete_user(username)
        except Exception as e:
            return 'failed: ' + str(e)

        # Is user delete himself, delog him
        if self.request.session['username'] == username:
            self.request.session['username'] = ''
            self.request.session['admin'] = ''
            self.request.session['graph'] = ''

        return 'success'

    @view_config(route_name='get_my_infos', request_method='GET')
    def get_my_infos(self):
        """
        Get all infos about a user
        """

        self.checkAuthSession()

        security = Security(self.settings, self.request.session, self.request.session['username'], '', '', '')
        infos = security.get_user_infos()

        result = {}

        result['email'] = infos[0][0]
        result['username'] = self.request.session['username']
        result['admin'] = infos[0][1]
        result['blocked'] = infos[0][2]
        result['apikey'] = infos[0][3]

        galaxy_dict = {}

        if infos[1]:
            result['galaxy'] = {'url': infos[1][0], 'key': infos[1][1]}

        return result


    @view_config(route_name='update_mail', request_method='POST')
    def update_mail(self):
        """
        Chage email of a user
        """

        body = self.request.json_body
        username = body['username']
        email = body['email']

        # Check email

        security = Security(self.settings, self.request.session, username, email, '', '')

        if not security.check_email():
            self.data['error'] = 'Not a valid email'
            return self.data

        try:
            security.update_email()
        except Exception as e:
            self.data['error'] = 'error when updating mail: ' + str(e)
            return self.data

        self.data['success'] = 'success'

        return self.data

    @view_config(route_name='update_passwd', request_method='POST')
    def update_passwd(self):
        """
        Change password of a user
        """

        body = self.request.json_body
        username = body['username']
        passwd = body['passwd']
        passwd2 = body['passwd2']
        current_passwd = body['current_passwd']

        security1 = Security(self.settings, self.request.session, username, '', current_passwd, current_passwd)

        if not security1.check_username_password():
            self.data['error'] = 'Current password is wrong'
            return self.data

        security = Security(self.settings, self.request.session, username, '', passwd, passwd2)


        # check if the passwd are identical
        if not security.check_passwords():
            self.data['error'] = 'Passwords are not identical'
            return self.data

        if not security.check_password_length():
            self.data['error'] = 'Password is too small (8char min)'
            return self.data


        try:
            security.update_passwd()
        except Exception as e:
            self.data['error'] = 'error when updating password: ' + str(e)
            return self.data

        self.data['success'] = 'success'

        return self.data



    @view_config(route_name='get_data_from_galaxy', request_method='POST')
    def get_data_from_galaxy(self):

        body = self.request.json_body
        history = body['history']
        allowed_files = body['allowed_files']

        try:
            self.data = {}

            # Check if a galaxy is registered
            security = Security(self.settings, self.request.session, self.request.session['username'], '', '', '')

            galaxy_auth = security.get_galaxy_infos()

            self.log.debug(galaxy_auth)

            if not galaxy_auth:
                self.data['galaxy'] = False
                return self.data

            # check if the galaxy connection is ok
            galaxy = GalaxyConnector(self.settings, self.request.session, galaxy_auth['url'], galaxy_auth['key'])
            if not galaxy.check_galaxy_instance():
                self.data['error'] = 'Wrong galaxy'
                self.data['galaxy'] = False
                return self.data

            self.data['galaxy'] = True

            # Then, get the datasets
            results = galaxy.get_datasets_and_histories(allowed_files, history_id=history)

            # Boolean values for handlebars
            for dataset in results['datasets']:
                if dataset['state'] == 'ok':
                    dataset['success'] = True
                elif dataset['state'] == 'queued':
                    dataset['notick'] = False
                    dataset['queued'] = True
                else:
                    dataset['notick'] = False
                    dataset['error'] = True

            self.data['datasets'] = results['datasets']
            self.data['histories'] = results['histories']
        except Exception as e:
            self.data['error'] = str(e)

        return self.data

    @view_config(route_name='upload_galaxy_files', request_method='POST')
    def upload_galaxy_file(self):

        self.data = {}

        body = self.request.json_body

        # get galaxy infos
        security = Security(self.settings, self.request.session, self.request.session['username'], '', '', '')

        galaxy_auth = security.get_galaxy_infos()

        if not galaxy_auth:
            self.data['error'] = 'No Galaxy'
            return self.data

        # Upload files
        try:
            galaxy = GalaxyConnector(self.settings, self.request.session, galaxy_auth['url'], galaxy_auth['key'])
            galaxy.upload_files(body['datasets'])
        except Exception as e:
            self.data['error'] = 'Error during galaxy upload: ' + str(e)
            return self.data

        self.data['success'] = 'Success'
        return self.data

    @view_config(route_name='get_galaxy_file_content', request_method='POST')
    def get_galaxy_file_content(self):

        self.data = {}
        body = self.request.json_body
        dataset_id = body['dataset']

        # get galaxy infos
        security = Security(self.settings, self.request.session, self.request.session['username'], '', '', '')

        galaxy_auth = security.get_galaxy_infos()

        if not galaxy_auth:
            self.data['error'] = 'No Galaxy'
            return self.data

        # Get the file content
        try:
            galaxy = GalaxyConnector(self.settings, self.request.session, galaxy_auth['url'], galaxy_auth['key'])
            self.data['json_query'] = galaxy.get_file_content(dataset_id)
        except Exception as e:
            self.data['error'] = 'Error during galaxy upload: ' + str(e)
            return self.data

        return self.data

    @view_config(route_name='send_to_galaxy', request_method='POST')
    def send2galaxy(self):
        self.data = {}

        body = self.request.json_body

        # get Galaxy infos
        security = Security(self.settings, self.request.session, self.request.session['username'], '', '', '')

        galaxy_auth = security.get_galaxy_infos()

        if not galaxy_auth:
            self.data['error'] = 'No Galaxy'
            return self.data

        # Send the file to Galaxy
        try:
            galaxy = GalaxyConnector(self.settings, self.request.session, galaxy_auth['url'], galaxy_auth['key'])
            if 'json' in body:
                galaxy.send_json_to_history(body['json'])
            else:
                param_manager = ParamManager(self.settings, self.request.session)
                path = param_manager.get_user_csv_directory() + body['path']
                name = body['name']
                galaxy.send_to_history(path, name, body['type'])
        except Exception as e:
            self.data['error'] = 'Error during sending: ' + str(e)
            return self.data

        self.data['success'] = 'path successfully sended in Galaxy'
        return self.data


    @view_config(route_name='get_uploaded_files', request_method="GET")
    def get_uploaded_files(self):

        self.checkAuthSession()

        param_manager = ParamManager(self.settings, self.request.session)
        path = param_manager.get_upload_directory()

        self.data = {}
        self.data['files'] = {}
        files = os.listdir(path)

        for file in files:
            file_path = path + '/' + file
            file_size = humanize.naturalsize(os.path.getsize(file_path), binary=True)
            self.data['files'][file] = file_size

        self.data['galaxy'] = self.request.session['galaxy']
        return self.data

    @view_config(route_name="delete_uploaded_files", request_method="POST")
    def delete_uploaded_files(self):

        try:
            #should be in a administration session....to check
            #self.checkAdminSession()

            files_to_delete = self.request.json_body
            param_manager = ParamManager(self.settings, self.request.session)
            path = param_manager.get_upload_directory()


            for file in files_to_delete:
                os.remove(path + '/' + file)

        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            self.data['error'] = str(e)
            self.request.response.status = 400

    @view_config(route_name='serverinformations', request_method='GET')
    def serverinformations(self):
        import platform
        import os
        from humanize import naturalsize
        from glob2 import iglob
        import psutil

        try:
            pid = os.getpid()
            py = psutil.Process(pid)
            memoryUse = py.memory_info()[0]/2.**30

            infomem = psutil.virtual_memory()
            diskinfo = psutil.disk_usage('.')

            self.checkAdminSession()

            pm = ParamManager(self.settings, self.request.session)

            self.data = {}
            self.data['values'] = []

            self.data['values'].append({ 'key' : 'System', 'value' : platform.system() } )
            self.data['values'].append({ 'key' : 'Release', 'value' : platform.release() } )
            self.data['values'].append({ 'key' : 'N CPU', 'value' : str(psutil.cpu_count()) } )
            self.data['values'].append({ 'key' : 'Memory total', 'value' : str(round(infomem.total/(1024**3),2)) + " GB" } )
            self.data['values'].append({ 'key' : 'Memory used', 'value' : str(round(infomem.used/(1024**3),2)) + " GB" } )
            self.data['values'].append({ 'key' : 'Memory free', 'value' : str(round(infomem.free/(1024**3),2)) + " GB" } )
            self.data['values'].append({ 'key' : 'Disk total', 'value' : str(round(diskinfo.total/(1024**3),2)) + " GB" } )
            self.data['values'].append({ 'key' : 'Disk used', 'value' : str(round(diskinfo.used/(1024**3),2)) + " GB" } )
            self.data['values'].append({ 'key' : 'Disk free', 'value' : str(round(diskinfo.free/(1024**3),2)) + " GB" } )
            self.data['values'].append({ 'key' : 'temp directory', 'value' : pm.user_dir } )
            self.data['values'].append({ 'key' : 'temp directory size', 'value' : naturalsize(sum(os.path.getsize(x) for x in iglob(pm.user_dir+'/**'))) } )
            self.data['values'].append({ 'key' : 'Upload directory', 'value' : pm.get_upload_directory() } )
            self.data['values'].append({ 'key' : 'Upload directory size', 'value' : naturalsize(sum(os.path.getsize(x) for x in iglob(pm.get_upload_directory()+'/**'))) } )
            self.data['values'].append({ 'key' : 'Rdf generated files directory', 'value' : pm.get_rdf_user_directory() } )
            self.data['values'].append({ 'key' : 'Rdf generated files directory size', 'value' : naturalsize(sum(os.path.getsize(x) for x in iglob(pm.get_rdf_user_directory()+'/**'))) } )
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            self.data['error'] = str(e)
            self.request.response.status = 400

        return self.data

    @view_config(route_name='cleantmpdirectory', request_method='POST')
    def cleantmpdirectory(self):
        import os
        import glob2


        try:
            self.checkAdminSession()
            pm = ParamManager(self.settings, self.request.session)

            files = glob2.glob(pm.get_rdf_user_directory()+'/**')
            for f in files:
                if os.path.isfile(f):
                    os.remove(f)
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            self.data['error'] = str(e)
            self.request.response.status = 400

        return
